import httpx
import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from qnap_photo_api import PhotoStationClient  # noqa: E402
from qnap_photo_api.proxy import create_image_router  # noqa: E402


def make_app(options, nas):
    client = PhotoStationClient(options, transport=httpx.MockTransport(nas))
    app = FastAPI()
    app.include_router(create_image_router(lambda: client))
    return app


@pytest.mark.parametrize(("path", "size"), [("/image/abc", "0"), ("/thumb/abc", "1")])
def test_proxy_streams_image(options, nas, path, size):
    with TestClient(make_app(options, nas)) as http:
        response = http.get(path)

    assert response.status_code == 200
    assert response.content == b"\xff\xd8jpegbytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert "set-cookie" not in response.headers
    upstream = nas.api_calls[0]
    assert upstream.url.params["s"] == size
    assert upstream.headers["Cookie"] == "NAS_SID=sid123"


def test_other_paths_not_handled(options, nas):
    with TestClient(make_app(options, nas)) as http:
        assert http.get("/other").status_code == 404
