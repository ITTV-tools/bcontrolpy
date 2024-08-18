import asyncio
import aiohttp
import json
import argparse

key_mapping = {
    "1-0:1.4.0*255": "Active Power+",
    "1-0:1.8.0*255": "Total Energy+",
    "1-0:2.4.0*255": "Active Power-",
    "1-0:2.8.0*255": "Total Energy-",
    "1-0:3.4.0*255": "Reactive Power+",
    "1-0:3.8.0*255": "Reactive Energy+",
    "1-0:4.4.0*255": "Apparent Power+",
    "1-0:4.8.0*255": "Apparent Energy+",
    "1-0:9.4.0*255": "Reactive Power-",
    "1-0:9.8.0*255": "Reactive Energy-",
    "1-0:10.4.0*255": "Apparent Power-",
    "1-0:10.8.0*255": "Apparent Energy-",
    "1-0:13.4.0*255": "Power Factor",
    "1-0:14.4.0*255": "Frequency",
    "1-0:21.4.0*255": "L1 Active Power+",
    "1-0:21.8.0*255": "L1 Total Energy+",
    "1-0:22.4.0*255": "L1 Active Power-",
    "1-0:22.8.0*255": "L1 Total Energy-",
    "1-0:23.4.0*255": "L1 Reactive Power+",
    "1-0:23.8.0*255": "L1 Reactive Energy+",
    "1-0:24.4.0*255": "L1 Apparent Power+",
    "1-0:24.8.0*255": "L1 Apparent Energy+",
    "1-0:29.4.0*255": "L1 Reactive Power-",
    "1-0:29.8.0*255": "L1 Reactive Energy-",
    "1-0:30.4.0*255": "L1 Apparent Power-",
    "1-0:30.8.0*255": "L1 Apparent Energy-",
    "1-0:31.4.0*255": "L1 Power Factor",
    "1-0:32.4.0*255": "L1 Voltage",
    "1-0:33.4.0*255": "L1 Current",
    "1-0:41.4.0*255": "L2 Active Power+",
    "1-0:41.8.0*255": "L2 Total Energy+",
    "1-0:42.4.0*255": "L2 Active Power-",
    "1-0:42.8.0*255": "L2 Total Energy-",
    "1-0:43.4.0*255": "L2 Reactive Power+",
    "1-0:43.8.0*255": "L2 Reactive Energy+",
    "1-0:44.4.0*255": "L2 Apparent Power+",
    "1-0:44.8.0*255": "L2 Apparent Energy+",
    "1-0:49.4.0*255": "L2 Reactive Power-",
    "1-0:49.8.0*255": "L2 Reactive Energy-",
    "1-0:50.4.0*255": "L2 Apparent Power-",
    "1-0:50.8.0*255": "L2 Apparent Energy-",
    "1-0:51.4.0*255": "L2 Power Factor",
    "1-0:52.4.0*255": "L2 Voltage",
    "1-0:53.4.0*255": "L2 Current",
    "1-0:61.4.0*255": "L3 Active Power+",
    "1-0:61.8.0*255": "L3 Total Energy+",
    "1-0:62.4.0*255": "L3 Active Power-",
    "1-0:62.8.0*255": "L3 Total Energy-",
    "1-0:63.4.0*255": "L3 Reactive Power+",
    "1-0:63.8.0*255": "L3 Reactive Energy+",
    "1-0:64.4.0*255": "L3 Apparent Power+",
    "1-0:64.8.0*255": "L3 Apparent Energy+",
    "1-0:69.4.0*255": "L3 Reactive Power-",
    "1-0:69.8.0*255": "L3 Reactive Energy-",
    "1-0:70.4.0*255": "L3 Apparent Power-",
    "1-0:70.8.0*255": "L3 Apparent Energy-",
    "1-0:71.4.0*255": "L3 Power Factor",
    "1-0:72.4.0*255": "L3 Voltage",
    "1-0:73.4.0*255": "L3 Current",
    "status": "Status"
    # Add any additional mappings here
}

class CookieRetrievalError(Exception):
    pass

class LoginValueError(Exception):
    pass

class CookieValueError(Exception):
    pass

async def getcookie(base_url):
    """
    Retrieves cookies, status code, and response text from the given base URL.

    Args:
        base_url (str): The base URL to send the request to.

    Returns:
        Tuple[aiohttp.CookieJar, int, str]: A tuple containing the cookies, status code, and response text.

    Raises:
        CookieRetrievalError: If an HTTP error occurs, the request times out, or an unexpected error occurs.
    """
    initial_url = f"{base_url}/start.php"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(initial_url) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                cookies = response.cookies
                status = response.status
                text = await response.text()
                return cookies, status, text
    except aiohttp.ClientError as e:
        raise CookieRetrievalError(f"HTTP error: {e}")
    except asyncio.TimeoutError:
        raise CookieRetrievalError("Request timed out")
    except Exception as e:
        raise CookieRetrievalError(f"An unexpected error occurred: {e}")

async def authenticate(session, base_url, login, password, cookie):
    """
    Authenticates the user by sending a POST request to the login URL with the provided login credentials.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session.
        base_url (str): The base URL of the application.
        login (str): The user's login.
        password (str): The user's password.
        cookie (str): The PHPSESSID cookie value.

    Returns:
        str: The response text from the POST request.

    Raises:
        aiohttp.ClientResponseError: If the POST request returns a non-2xx status code.
        aiohttp.ClientError: If there is an error during the POST request.
    """
    login_url = f"{base_url}/start.php"    
    payload = f"login={login}&password={password}"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': f'PHPSESSID={cookie}'
    }
    async with session.post(login_url, data=payload, headers=headers) as response:
        response.raise_for_status()
        return await response.text()

async def getdata(session, base_url, cookie):
    """
    Retrieves data from a specified URL using an async session.

    Args:
        session (aiohttp.ClientSession): The async session to use for the request.
        base_url (str): The base URL of the data endpoint.
        cookie (str): The cookie value to include in the request headers.

    Returns:
        str: The response text from the data endpoint.

    Raises:
        aiohttp.ClientResponseError: If the response status code is not successful.
        aiohttp.ClientError: If there is an error making the request.
    """
    data_url = f"{base_url}/mum-webservice/data.php"
    headers = {
        'Cookie': f'PHPSESSID={cookie}'
    }
    async with session.get(data_url, headers=headers) as response:
        response.raise_for_status()
        return await response.text()

def translate_keys(data, key_mapping):
    """
    Translates the keys of a dictionary using a provided key mapping.

    Args:
        data (dict): The dictionary whose keys need to be translated.
        key_mapping (dict): A dictionary mapping original keys to translated keys.

    Returns:
        dict: A new dictionary with translated keys.
    """
    translated_data = {}
    for key, value in data.items():
        translated_key = key_mapping.get(key, key)
        translated_data[translated_key] = value
    return translated_data

class BControl:
    def __init__(self, ip, password):
        self.ip = ip
        self.password = password
        self.base_url = f"http://{ip}"
        self.session = aiohttp.ClientSession()
        self.cookie_value = None

    async def login(self):
        """
        Logs in to the application using the provided credentials.

        Returns:
            The authenticated response.

        Raises:
            CookieRetrievalError: If there is an error retrieving the cookies.
            LoginValueError: If the login value is not found in the response.
            CookieValueError: If the 'PHPSESSID' cookie is not found.
        """
        try:
            cookies, status, text = await getcookie(self.base_url)
            if cookies is None:
                raise CookieRetrievalError("Error retrieving cookies")

            # Parse the JSON response to extract the login value
            response_data = json.loads(text)
            login = response_data.get("serial")
            if not login:
                raise LoginValueError("Login value not found")

            self.cookie_value = cookies.get("PHPSESSID").value
            if not self.cookie_value:
                raise CookieValueError("Cookie 'PHPSESSID' not found")

            authenticated_response = await authenticate(self.session, self.base_url, login, self.password, self.cookie_value)
            return authenticated_response
        except (CookieRetrievalError, LoginValueError, CookieValueError) as e:
            print(e)

    async def get_data(self):
        """
        Retrieves data from the server.

        Raises:
            Exception: If not authenticated. Please call login() first.

        Returns:
            dict: Translated data.
        """
        if not self.session or not self.cookie_value:
            raise Exception("Not authenticated. Please call login() first.")
        data = await getdata(self.session, self.base_url, self.cookie_value)
        data_dict = json.loads(data)
        translated_data = translate_keys(data_dict, key_mapping)
        return translated_data

    async def close(self):
        """
        Closes the HTTP session.
        """
        await self.session.close()

