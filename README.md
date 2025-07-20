# bcontrolpy

[![PyPI - Version](https://img.shields.io/pypi/v/bcontrolpy.svg)](https://pypi.org/project/bcontrolpy)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/bcontrolpy.svg)](https://pypi.org/project/bcontrolpy)
[![License](https://img.shields.io/pypi/l/bcontrolpy.svg)](https://opensource.org/licenses/Apache-2.0)

---

**bcontrolpy** is an asynchronous Python client for the TQ-Systems EM300 energy meter, providing authentication, session management, and data retrieval via the MUM webservice.

## Table of Contents

* [Installation](#installation)
* [Quickstart](#quickstart)
* [Usage](#usage)

  * [Python API](#python-api)
  * [Command Line Example](#command-line-example)
* [Configuration](#configuration)
* [License](#license)

## Installation

Install the latest release from PyPI:

```bash
pip install bcontrolpy
```

Or install the development version directly from GitHub:

```bash
pip install git+https://github.com/ITTV-tools/bcontrolpy.git
```

## Quickstart

```python
import asyncio
from bcontrolpy import BControl, AuthenticationError

async def main():
    # Connect to EM300 meter on local network
    async with BControl(ip="192.168.1.100", password="your_password") as bc:
        try:
            info = await bc.login()
            print("Login successful:", info)

            data = await bc.get_data()
            print("Meter readings:", data)
        except AuthenticationError:
            print("Authentication failed: check your credentials")

asyncio.run(main())
```

## Usage

### Python API

| Method               | Returns                                          | Raises                                                                               |
| -------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `login() -> dict`    | `{'serial', 'app_version', 'authentication'}`    | `AuthenticationError`, `CookieRetrievalError`, `LoginValueError`, `CookieValueError` |
| `get_data() -> dict` | Measurement values mapped to human-readable keys | `NotAuthenticatedError`, HTTP errors                                                 |
| `close() -> None`    |                                                  |                                                                                      |

Example:

```python
async with BControl(ip="192.168.1.100", password="your_password") as bc:
    info = await bc.login()
    values = await bc.get_data()
```

### Command Line Example

Run the provided example script:

```bash
python example/example.py --ip 192.168.1.100 --password "your_password"
```

This prints the login details and current meter readings.

## Configuration

* **Reuse `aiohttp.ClientSession`**: Pass an existing session (e.g., from Home Assistant) to `BControl` to take advantage of connection pooling.
* **Handle Exceptions**: Catch `AuthenticationError` to trigger re-authentication flows.
* **Customize Mapping**: The OBIS code mapping resides in `key_mapping.py` and can be extended for additional measurements.

## License

`bcontrolpy` is distributed under the **Apache 2.0 License**. See [LICENSE](LICENSE) for details.
