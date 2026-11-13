import asyncio
from typing import TYPE_CHECKING

import httpx
import pytest

from conftest import IMAGE_BYTES, LOGIN_FAIL, TEST_PASSWORD, FakeNas
from qnap_photo_api import (
    ImageSize,
    ListAlbumPhotosRequest,
    LoginResponse,
    PhotoStationClient,
    QnapApiOptions,
)

if TYPE_CHECKING:
    from collections.abc import Coroutine


def run[T](coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)


def make_client(
    options: QnapApiOptions, nas: FakeNas, clock: list[float] | None = None
) -> PhotoStationClient:
    transport = httpx.MockTransport(nas)
    if clock is None:
        return PhotoStationClient(options, transport=transport)
    return PhotoStationClient(options, transport=transport, clock=lambda: clock[0])


def test_login_once_and_cookie_sent(options: QnapApiOptions, nas: FakeNas) -> None:
    async def go() -> None:
        async with make_client(options, nas) as client:
            await client.list()
            await client.list_album_photos(ListAlbumPhotosRequest(album_id="5"))

    run(go())
    assert len(nas.logins) == 1
    assert len(nas.api_calls) == 2
    for call in nas.api_calls:
        assert call.headers["Cookie"] == "NAS_SID=sid123"
        assert call.headers["X-Requested-With"] == "XMLHttpRequest"
    assert nas.api_calls[1].url.params["a"] == "5"


def test_concurrent_requests_share_one_login(options: QnapApiOptions, nas: FakeNas) -> None:
    async def go() -> None:
        async with make_client(options, nas) as client:
            await asyncio.gather(*(client.list() for _ in range(5)))

    run(go())
    assert len(nas.logins) == 1


def test_failed_login_is_not_cached(options: QnapApiOptions) -> None:
    nas = FakeNas(login_body=LOGIN_FAIL)

    async def go() -> None:
        async with make_client(options, nas) as client:
            await client.list()
            await client.list()

    run(go())
    assert len(nas.logins) == 2
    assert all("Cookie" not in r.headers for r in nas.api_calls)


def test_session_expires(options: QnapApiOptions, nas: FakeNas) -> None:
    now = [0.0]

    async def go() -> None:
        async with make_client(options, nas, clock=now) as client:
            await client.list()
            now[0] = 3601.0
            await client.list()

    run(go())
    assert len(nas.logins) == 2


def test_invalidate_forces_login(options: QnapApiOptions, nas: FakeNas) -> None:
    async def go() -> None:
        async with make_client(options, nas) as client:
            await client.list()
            client.auth.invalidate()
            await client.list()

    run(go())
    assert len(nas.logins) == 2


def test_image_request(options: QnapApiOptions, nas: FakeNas) -> None:
    async def go() -> bytes:
        async with make_client(options, nas) as client:
            response = await client.open_image("abc", ImageSize.THUMBNAIL)
            try:
                return await response.aread()
            finally:
                await response.aclose()

    assert run(go()) == IMAGE_BYTES
    params = nas.api_calls[0].url.params
    assert (params["s"], params["m"], params["f"]) == ("1", "display", "abc")


def test_http_error_raises(options: QnapApiOptions) -> None:
    fake = FakeNas()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("authLogin.cgi"):
            return fake(request)
        return httpx.Response(500)

    async def go() -> None:
        async with PhotoStationClient(options, transport=httpx.MockTransport(handler)) as client:
            await client.list()

    with pytest.raises(httpx.HTTPStatusError, match="500"):
        run(go())


def test_sync_client_uses_same_auth(options: QnapApiOptions, nas: FakeNas) -> None:
    async_client = make_client(options, nas)
    with httpx.Client(
        base_url=options.base_url, auth=async_client.auth, transport=httpx.MockTransport(nas)
    ) as client:
        client.get("/photo/api/list.php")
        client.get("/photo/api/list.php")
    run(async_client.aclose())
    assert len(nas.logins) == 1
    assert all(r.headers["Cookie"] == "NAS_SID=sid123" for r in nas.api_calls)


def test_login_xml_parsing() -> None:
    assert LoginResponse.from_xml("not xml") is None
    assert LoginResponse.from_xml("<Other/>") is None
    login = LoginResponse.from_xml(
        "<QDocRoot><authPassed>1</authPassed><authSid>s</authSid></QDocRoot>"
    )
    assert login is not None
    assert login.auth_passed
    assert login.sid == "s"


def test_login_xml_rejects_entity_expansion() -> None:
    bomb = '<!DOCTYPE r [<!ENTITY a "aaaa">]><QDocRoot><authSid>&a;</authSid></QDocRoot>'
    assert LoginResponse.from_xml(bomb) is None


def test_options_validation() -> None:
    with pytest.raises(ValueError, match="base_url"):
        QnapApiOptions(base_url="nas", username="u", password=TEST_PASSWORD)
    with pytest.raises(ValueError, match="QNAP_USERNAME, QNAP_PASSWORD"):
        QnapApiOptions.from_env({"QNAP_BASE_URL": "http://nas"})
    opts = QnapApiOptions.from_env(
        {
            "QNAP_BASE_URL": "http://nas/",
            "QNAP_USERNAME": "u",
            "QNAP_PASSWORD": "p",
            "QNAP_AUTH_TIMEOUT_HOURS": "2",
        }
    )
    assert opts.base_url == "http://nas"
    assert opts.auth_timeout_hours == 2


def test_unparseable_login_sends_unauthenticated(options: QnapApiOptions) -> None:
    nas = FakeNas(login_body="<html>maintenance</html>")

    async def go() -> None:
        async with make_client(options, nas) as client:
            await client.list()

    run(go())
    assert "Cookie" not in nas.api_calls[0].headers


def test_list_albums_and_from_env(nas: FakeNas, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QNAP_BASE_URL", "http://nas")
    monkeypatch.setenv("QNAP_USERNAME", "rob")
    monkeypatch.setenv("QNAP_PASSWORD", TEST_PASSWORD)

    async def go() -> None:
        async with PhotoStationClient.from_env(transport=httpx.MockTransport(nas)) as client:
            response = await client.list_albums()
            assert response.data == []

    run(go())
    assert nas.api_calls[0].url.params["t"] == "allAlbums"


@pytest.mark.parametrize(
    ("username", "password", "hours", "message"),
    [
        ("", TEST_PASSWORD, 1.0, "username"),
        ("u", "", 1.0, "password"),
        ("u", TEST_PASSWORD, 0.0, "auth_timeout_hours"),
    ],
)
def test_options_field_errors(username: str, password: str, hours: float, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        QnapApiOptions(
            base_url="http://nas", username=username, password=password, auth_timeout_hours=hours
        )
