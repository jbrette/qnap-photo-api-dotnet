import base64
import json

import httpx
import pytest

from qnap_photo_api import QnapApiOptions

LOGIN_OK = "<QDocRoot><authPassed><![CDATA[1]]></authPassed><authSid><![CDATA[sid123]]></authSid></QDocRoot>"
LOGIN_FAIL = "<QDocRoot><authPassed><![CDATA[0]]></authPassed></QDocRoot>"


@pytest.fixture
def options():
    return QnapApiOptions(base_url="http://nas", username="rob", password="pw", auth_timeout_hours=1)


class FakeNas:
    """Records requests and answers like Photo Station."""

    def __init__(self, login_body=LOGIN_OK):
        self.login_body = login_body
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/cgi-bin/authLogin.cgi":
            form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
            assert form["user"] == "rob"
            assert base64.b64decode(httpx.QueryParams(f"p={form['pwd']}")["p"]) == b"pw"
            return httpx.Response(200, text=self.login_body)
        if path == "/photo/api/list.php":
            return httpx.Response(200, json={"status": "0", "photoCount": "0", "DataList": []})
        if path == "/photo/api/thumb.php":
            async def body():  # streamed, like a real socket (bytes would be pre-read)
                yield b"\xff\xd8"
                yield b"jpegbytes"

            return httpx.Response(
                200,
                content=body(),
                headers={"Content-Type": "image/jpeg", "Set-Cookie": "NAS_SID=leak"},
            )
        return httpx.Response(404)

    @property
    def logins(self):
        return [r for r in self.requests if r.url.path == "/cgi-bin/authLogin.cgi"]

    @property
    def api_calls(self):
        return [r for r in self.requests if r.url.path != "/cgi-bin/authLogin.cgi"]


@pytest.fixture
def nas():
    return FakeNas()


def dumps(obj):
    return json.dumps(obj)
