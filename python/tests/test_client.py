import asyncio

import httpx
import pytest

from conftest import LOGIN_FAIL, FakeNas
from qnap_photo_api import ImageSize, ListAlbumPhotosRequest, LoginResponse, PhotoStationClient, QnapApiOptions


def run(coro):
    return asyncio.run(coro)


def test_login_once_and_cookie_sent(options, nas):
    async def go():
        async with PhotoStationClient(options, transport=httpx.MockTransport(nas)) as client:
            await client.list()
            await client.list_album_photos(ListAlbumPhotosRequest(album_id="5"))

    run(go())
    assert len(nas.logins) == 1
    assert len(nas.api_calls) == 2
    for call in nas.api_calls:
        assert call.headers["Cookie"] == "NAS_SID=sid123"
        assert call.headers["X-Requested-With"] == "XMLHttpRequest"
    assert nas.api_calls[1].url.params["a"] == "5"


def test_concurrent_requests_share_one_login(options, nas):
    async def go():
        async with PhotoStationClient(options, transport=httpx.MockTransport(nas)) as client:
            await asyncio.gather(*(client.list() for _ in range(5)))

    run(go())
    assert len(nas.logins) == 1


def test_failed_login_is_not_cached(options):
    nas = FakeNas(login_body=LOGIN_FAIL)

    async def go():
        async with PhotoStationClient(options, transport=httpx.MockTransport(nas)) as client:
            await client.list()
            await client.list()

    run(go())
    assert len(nas.logins) == 2
    assert all("Cookie" not in r.headers for r in nas.api_calls)


def test_session_expires(options, nas):
    now = [0.0]

    async def go():
        async with PhotoStationClient(options, transport=httpx.MockTransport(nas)) as client:
            client.auth._clock = lambda: now[0]
            await client.list()
            now[0] = 3601
            await client.list()

    run(go())
    assert len(nas.logins) == 2


def test_image_request(options, nas):
    async def go():
        async with PhotoStationClient(options, transport=httpx.MockTransport(nas)) as client:
            response = await client.open_image("abc", ImageSize.THUMBNAIL)
            body = await response.aread()
            await response.aclose()
            return body

    assert run(go()) == b"\xff\xd8jpegbytes"
    params = nas.api_calls[0].url.params
    assert (params["s"], params["m"], params["f"]) == ("1", "display", "abc")


def test_http_error_raises(options):
    def handler(request):
        if request.url.path.endswith("authLogin.cgi"):
            return FakeNas()(request)
        return httpx.Response(500)

    async def go():
        async with PhotoStationClient(options, transport=httpx.MockTransport(handler)) as client:
            await client.list()

    with pytest.raises(httpx.HTTPStatusError):
        run(go())


def test_login_xml_parsing():
    assert LoginResponse.from_xml("not xml") is None
    assert LoginResponse.from_xml("<Other/>") is None
    login = LoginResponse.from_xml("<QDocRoot><authPassed>1</authPassed><authSid>s</authSid></QDocRoot>")
    assert login.auth_passed and login.sid == "s"


def test_options_validation():
    with pytest.raises(ValueError):
        QnapApiOptions(base_url="nas", username="u", password="p")
    with pytest.raises(ValueError):
        QnapApiOptions.from_env({"QNAP_BASE_URL": "http://nas"})
    opts = QnapApiOptions.from_env(
        {"QNAP_BASE_URL": "http://nas/", "QNAP_USERNAME": "u", "QNAP_PASSWORD": "p", "QNAP_AUTH_TIMEOUT_HOURS": "2"}
    )
    assert opts.base_url == "http://nas"
    assert opts.auth_timeout_hours == 2
