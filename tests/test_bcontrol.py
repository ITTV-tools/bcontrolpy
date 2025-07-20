import pytest
import aiohttp
from aioresponses import aioresponses

# Importiere aus dem src-Package
from bcontrolpy.bcontrolpy import BControl, AuthenticationError, LoginValueError, CookieValueError

@pytest.fixture
async def session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()

@pytest.mark.asyncio
async def test_login_success(session):
    bc = BControl(ip="127.0.0.1", password="secret", session=session)
    start_url = "http://127.0.0.1/start.php"
    with aioresponses() as m:
        # GET /start.php liefert Serial und Cookie
        m.get(start_url,
              payload={"serial": "ABC123"},
              headers={"Set-Cookie": "PHPSESSID=XYZ; Path=/"})
        # POST /start.php authentifiziert
        m.post(start_url,
               payload={"serial": "ABC123", "app_version": "1.0", "authentication": True},
               status=200)

        result = await bc.login()
        assert result == {"serial": "ABC123", "app_version": "1.0", "authentication": True}
        assert bc.logged_in
        assert bc.serial == "ABC123"
        assert bc.app_version == "1.0"

@pytest.mark.asyncio
async def test_login_invalid_credentials(session):
    bc = BControl(ip="127.0.0.1", password="wrong", session=session)
    start_url = "http://127.0.0.1/start.php"
    with aioresponses() as m:
        m.get(start_url,
              payload={"serial": "ABC123"},
              headers={"Set-Cookie": "PHPSESSID=XYZ; Path=/"})
        # POST gibt 403 zurück
        m.post(start_url, status=403)
        with pytest.raises(AuthenticationError):
            await bc.login()

@pytest.mark.asyncio
async def test_get_data_refresh(session):
    bc = BControl(ip="127.0.0.1", password="secret", session=session)
    start_url = "http://127.0.0.1/start.php"
    data_url = "http://127.0.0.1/mum-webservice/data.php"
    with aioresponses() as m:
        # initial login
        m.get(start_url,
              payload={"serial": "ABC123"},
              headers={"Set-Cookie": "PHPSESSID=XYZ; Path=/"})
        m.post(start_url,
               payload={"serial": "ABC123", "app_version": "1.0", "authentication": True},
               status=200)
        # erste Datenabfrage: session expired
        m.get(data_url,
              payload={"authentication": False},
              status=200)
        # re-login
        m.get(start_url,
              payload={"serial": "ABC123"},
              headers={"Set-Cookie": "PHPSESSID=NEW; Path=/"})
        m.post(start_url,
               payload={"serial": "ABC123", "app_version": "1.0", "authentication": True},
               status=200)
        # zweite Datenabfrage: echte Werte
        sample = {"1-0:1.4.0*255": 42, "authentication": True}
        m.get(data_url,
              payload=sample,
              status=200)

        data = await bc.get_data()
        assert data.get("Active Power+") == 42
        assert bc.logged_in

@pytest.mark.asyncio
async def test_start_missing_serial(session):
    bc = BControl(ip="127.0.0.1", password="secret", session=session)
    start_url = "http://127.0.0.1/start.php"
    with aioresponses() as m:
        m.get(start_url, payload={})
        with pytest.raises(LoginValueError):
            await bc.login()

@pytest.mark.asyncio
async def test_missing_cookie(session):
    bc = BControl(ip="127.0.0.1", password="secret", session=session)
    start_url = "http://127.0.0.1/start.php"
    with aioresponses() as m:
        m.get(start_url,
              payload={"serial": "ABC123"},
              headers={})
        with pytest.raises(CookieValueError):
            await bc.login()


@pytest.mark.asyncio
async def test_external_session_not_closed(session):
    """Ensure `BControl.close()` doesn't close externally supplied sessions."""
    bc = BControl(ip="127.0.0.1", password="secret", session=session)

    # close without performing any network interactions
    await bc.close()
    assert not session.closed
