import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import IMAGE_BYTES, FakeNas
from qnap_photo_api import PhotoStationClient, QnapApiOptions
from qnap_photo_api.proxy import create_image_router


def make_app(options: QnapApiOptions, nas: FakeNas) -> FastAPI:
    client = PhotoStationClient(options, transport=httpx.MockTransport(nas))
    app = FastAPI()
    app.include_router(create_image_router(lambda: client))
    return app


@pytest.mark.parametrize(("path", "size"), [("/image/abc", "0"), ("/thumb/abc", "1")])
def test_proxy_streams_image(options: QnapApiOptions, nas: FakeNas, path: str, size: str) -> None:
    with TestClient(make_app(options, nas)) as http:
        response = http.get(path)

    assert response.status_code == 200
    assert response.content == IMAGE_BYTES
    assert response.headers["content-type"] == "image/jpeg"
    assert "set-cookie" not in response.headers
    upstream = nas.api_calls[0]
    assert upstream.url.params["s"] == size
    assert upstream.headers["Cookie"] == "NAS_SID=sid123"


def test_other_paths_not_handled(options: QnapApiOptions, nas: FakeNas) -> None:
    with TestClient(make_app(options, nas)) as http:
        assert http.get("/other").status_code == 404
    assert nas.requests == []
