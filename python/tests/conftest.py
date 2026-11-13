"""Shared fixtures: NAS options and a fake Photo Station behind ``httpx.MockTransport``."""

import base64
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import httpx
import pytest

from qnap_photo_api import QnapApiOptions

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

LOGIN_OK = (
    "<QDocRoot><authPassed><![CDATA[1]]></authPassed>"
    "<authSid><![CDATA[sid123]]></authSid></QDocRoot>"
)
LOGIN_FAIL = "<QDocRoot><authPassed><![CDATA[0]]></authPassed></QDocRoot>"
LOGIN_PATH = "/cgi-bin/authLogin.cgi"
IMAGE_BYTES = b"\xff\xd8jpegbytes"
TEST_USER = "rob"
TEST_PASSWORD = "pw"  # noqa: S105 - fixture credential for the fake NAS


@pytest.fixture
def options() -> QnapApiOptions:
    return QnapApiOptions(
        base_url="http://nas", username=TEST_USER, password=TEST_PASSWORD, auth_timeout_hours=1
    )


async def _image_body() -> AsyncIterator[bytes]:
    # Streamed like a real socket; a bytes body would arrive already read.
    yield IMAGE_BYTES[:2]
    yield IMAGE_BYTES[2:]


class FakeNas:
    """Records every request and answers like Photo Station."""

    def __init__(self, login_body: str = LOGIN_OK) -> None:
        self.login_body = login_body
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == LOGIN_PATH:
            form = parse_qs(request.content.decode())
            assert form["user"] == [TEST_USER]
            assert base64.b64decode(form["pwd"][0]) == TEST_PASSWORD.encode()
            return httpx.Response(200, text=self.login_body)
        if path == "/photo/api/list.php":
            return httpx.Response(200, json={"status": "0", "photoCount": "0", "DataList": []})
        if path == "/photo/api/thumb.php":
            return httpx.Response(
                200,
                content=_image_body(),
                headers={"Content-Type": "image/jpeg", "Set-Cookie": "NAS_SID=leak"},
            )
        return httpx.Response(404)

    @property
    def logins(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == LOGIN_PATH]

    @property
    def api_calls(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path != LOGIN_PATH]


@pytest.fixture
def nas() -> FakeNas:
    return FakeNas()
