import asyncio
import aiohttp
import json
import logging
from async_timeout import timeout
from .key_mapping import key_mapping

_LOGGER = logging.getLogger(__name__)

# Eigene Exceptions
class CookieRetrievalError(Exception):
    pass

class LoginValueError(Exception):
    pass

class CookieValueError(Exception):
    pass

class AuthenticationError(Exception):
    """Raised when login fails due to invalid credentials."""
    pass

class NotAuthenticatedError(Exception):
    """Raised when trying to get data without authentication."""
    pass

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
    async with timeout(timeout_seconds):
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.text()


def translate_keys(data: dict, mapping: dict) -> dict:
    return {mapping.get(k, k): v for k, v in data.items()}

class BControl:
    def __init__(self, ip: str, password: str, session: aiohttp.ClientSession | None = None, timeout_seconds: int = 10):
        self.base_url = f"http://{ip}"
        self.password = password
        self.session = session or aiohttp.ClientSession()
        self.timeout = timeout_seconds
        self.cookie_value = None
        self.logged_in = False
        self.serial = None
        self.app_version = None

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
            init_data = json.loads(text)
            login_val = init_data.get("serial")
            if not login_val:
                raise LoginValueError("Start response missing 'serial'.")

            phpsess = cookies.get("PHPSESSID")
            if not phpsess or not phpsess.value:
                raise CookieValueError("PHPSESSID cookie missing after start.")
            self.cookie_value = phpsess.value

            auth_text = await authenticate(self.session, self.base_url, login_val, self.password, self.cookie_value, self.timeout)
            auth = json.loads(auth_text)

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
        if not self.logged_in:
            _LOGGER.info("Session not valid, logging in first...")
            await self.login()

        raw = await getdata(self.session, self.base_url, self.cookie_value, self.timeout)
        data = json.loads(raw)
        if data.get("authentication") is False:
            _LOGGER.warning("Session expired, re-login")
            await self.login()
            raw = await getdata(self.session, self.base_url, self.cookie_value, self.timeout)
            data = json.loads(raw)

        return translate_keys(data, key_mapping)

    async def close(self):
        """Close the underlying :class:`aiohttp.ClientSession` if owned."""
        if self._session_owner:
            await self.session.close()
