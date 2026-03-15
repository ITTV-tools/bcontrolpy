import asyncio
import aiohttp
import json
import logging
from typing import Optional
from async_timeout import timeout
from .key_mapping import key_mapping

_LOGGER = logging.getLogger(__name__)

# Library exception hierarchy to support clean Home Assistant error mapping.
class BControlError(Exception):
    """Base exception for all library errors."""


class BControlCommunicationError(BControlError):
    """Raised for network and transport errors."""


class BControlParseError(BControlCommunicationError):
    """Raised when API responses cannot be parsed as valid JSON."""


class CookieRetrievalError(BControlCommunicationError):
    pass


class LoginValueError(BControlCommunicationError):
    pass


class CookieValueError(BControlCommunicationError):
    pass


class AuthenticationError(BControlError):
    """Raised when login fails due to invalid credentials."""
    pass


class NotAuthenticatedError(BControlError):
    """Raised when trying to get data without authentication."""
    pass


def _decode_json(payload: str, context: str) -> dict:
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        raise BControlParseError(f"Invalid JSON in {context}: {e}")

async def getcookie(session: aiohttp.ClientSession, base_url: str, timeout_seconds: int):
    url = f"{base_url}/start.php"
    try:
        async with timeout(timeout_seconds):
            async with session.get(url) as resp:
                resp.raise_for_status()
                return resp.cookies, await resp.text()
    except aiohttp.ClientError as e:
        raise CookieRetrievalError(f"HTTP error during initial request: {e}")
    except asyncio.TimeoutError:
        raise CookieRetrievalError("Initial request timed out")
    except Exception as e:
        raise CookieRetrievalError(f"Unexpected error during cookie retrieval: {e}")

async def authenticate(session: aiohttp.ClientSession, base_url: str, login: str, password: str, cookie_value: str, timeout_seconds: int):
    url = f"{base_url}/start.php"
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Cookie': f'PHPSESSID={cookie_value}'}
    data = {'login': login, 'password': password}
    try:
        async with timeout(timeout_seconds):
            async with session.post(url, data=data, headers=headers) as resp:
                # Spezielles Handling für falsche Anmeldedaten
                if resp.status == 403:
                    raise AuthenticationError("Invalid credentials: access forbidden (403)")
                resp.raise_for_status()
                return await resp.text()
    except AuthenticationError:
        raise
    except aiohttp.ClientResponseError as e:
        raise AuthenticationError(f"Authentication failed: HTTP {e.status}")
    except aiohttp.ClientError as e:
        raise AuthenticationError(f"HTTP error during authentication: {e}")
    except asyncio.TimeoutError:
        raise AuthenticationError("Authentication request timed out")
    except Exception as e:
        raise AuthenticationError(f"Unexpected error during authentication: {e}")

async def getdata(session: aiohttp.ClientSession, base_url: str, cookie_value: str, timeout_seconds: int):
    url = f"{base_url}/mum-webservice/data.php"
    headers = {'Cookie': f'PHPSESSID={cookie_value}'}
    try:
        async with timeout(timeout_seconds):
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.text()
    except aiohttp.ClientError as e:
        raise BControlCommunicationError(f"HTTP error during data retrieval: {e}")
    except asyncio.TimeoutError:
        raise BControlCommunicationError("Data request timed out")
    except Exception as e:
        raise BControlCommunicationError(f"Unexpected error during data retrieval: {e}")


def translate_keys(data: dict, mapping: dict) -> dict:
    return {mapping.get(k, k): v for k, v in data.items()}

class BControl:
    def __init__(self, ip: str, password: str, session: Optional[aiohttp.ClientSession] = None, timeout_seconds: int = 10):
        self.base_url = f"http://{ip}"
        self.password = password
        self._session_owner = session is None
        self.session = session or aiohttp.ClientSession()
        self.timeout = timeout_seconds
        self.cookie_value = None
        self.logged_in = False
        self.serial = None
        self.app_version = None
        self._request_lock = asyncio.Lock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def login(self) -> dict:
        """
        Logs in and returns a dict with serial, app_version and authentication status.
        Raises AuthenticationError if credentials are invalid.
        """
        try:
            cookies, text = await getcookie(self.session, self.base_url, self.timeout)
            init_data = _decode_json(text, "start.php response")
            login_val = init_data.get("serial")
            if not login_val:
                raise LoginValueError("Start response missing 'serial'.")

            phpsess = cookies.get("PHPSESSID")
            if not phpsess or not phpsess.value:
                raise CookieValueError("PHPSESSID cookie missing after start.")
            self.cookie_value = phpsess.value

            auth_text = await authenticate(self.session, self.base_url, login_val, self.password, self.cookie_value, self.timeout)
            auth = _decode_json(auth_text, "authentication response")

            # nur die benötigten Felder
            self.serial = auth.get("serial")
            self.app_version = auth.get("app_version")
            auth_status = bool(auth.get("authentication"))
            self.logged_in = auth_status

            _LOGGER.info("Login successful: serial=%s, app_version=%s", self.serial, self.app_version)
            return {"serial": self.serial, "app_version": self.app_version, "authentication": auth_status}

        except AuthenticationError as e:
            _LOGGER.error("Authentication error: %s", e)
            self.logged_in = False
            raise
        except (CookieRetrievalError, LoginValueError, CookieValueError) as e:
            _LOGGER.error("Login preparation failed: %s", e)
            self.logged_in = False
            raise

    async def get_data(self) -> dict:
        async with self._request_lock:
            if not self.logged_in:
                _LOGGER.info("Session not valid, logging in first...")
                await self.login()

            raw = await getdata(self.session, self.base_url, self.cookie_value, self.timeout)
            data = _decode_json(raw, "data.php response")
            if data.get("authentication") is False:
                _LOGGER.warning("Session expired, re-login")
                await self.login()
                raw = await getdata(self.session, self.base_url, self.cookie_value, self.timeout)
                data = _decode_json(raw, "data.php response after re-login")

            return translate_keys(data, key_mapping)

    async def async_get_data(self) -> dict:
        """Home Assistant friendly alias for coordinator update methods."""
        return await self.get_data()

    async def async_test_connection(self) -> None:
        """Validate connectivity and credentials for config flow checks."""
        await self.login()

    async def close(self):
        """Close the underlying :class:`aiohttp.ClientSession` if owned."""
        self.logged_in = False
        self.cookie_value = None
        if self._session_owner:
            await self.session.close()
