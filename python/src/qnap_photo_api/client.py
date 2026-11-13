"""Async Photo Station client (equivalent of the C# ``PhotoStationClient``)."""

from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel

from .auth import QnapAuth
from .config import QnapApiOptions
from .enums import ImageSize
from .models import ListAlbumPhotosResponse, ListAlbumsResponse, ListResponse
from .requests import ListAlbumPhotosRequest, ListAlbumsRequest, ListRequest

LIST_PATH = "/photo/api/list.php"
THUMB_PATH = "/photo/api/thumb.php"

T = TypeVar("T", bound=BaseModel)


class PhotoStationClient:
    """Use as ``async with PhotoStationClient(options) as client: ...`` or call ``aclose()``."""

    def __init__(
        self,
        options: QnapApiOptions,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float | httpx.Timeout = 30.0,
    ) -> None:
        self.options = options
        self.auth = QnapAuth(options)
        self.http = httpx.AsyncClient(
            base_url=options.base_url,
            auth=self.auth,
            transport=transport,
            timeout=timeout,
        )

    @classmethod
    def from_env(cls, **kwargs) -> PhotoStationClient:
        return cls(QnapApiOptions.from_env(), **kwargs)

    async def __aenter__(self) -> PhotoStationClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self.http.aclose()

    async def list(self, request: ListRequest | None = None) -> ListResponse:
        return await self._list((request or ListRequest()).to_params(), ListResponse)

    async def list_albums(self, request: ListAlbumsRequest | None = None) -> ListAlbumsResponse:
        return await self._list((request or ListAlbumsRequest()).to_params(), ListAlbumsResponse)

    async def list_album_photos(self, request: ListAlbumPhotosRequest) -> ListAlbumPhotosResponse:
        return await self._list(request.to_params(), ListAlbumPhotosResponse)

    async def _list(self, params: dict[str, str], model: type[T]) -> T:
        response = await self.http.get(LIST_PATH, params=params, headers={"X-Requested-With": "XMLHttpRequest"})
        response.raise_for_status()
        return model.model_validate_json(response.content)

    def build_image_request(self, image_id: str, size: ImageSize = ImageSize.FULL) -> httpx.Request:
        return self.http.build_request(
            "GET", THUMB_PATH, params={"s": size.value, "m": "display", "f": image_id}
        )

    async def open_image(self, image_id: str, size: ImageSize = ImageSize.FULL) -> httpx.Response:
        """Start streaming an image. The caller must ``await response.aclose()`` when done."""
        return await self.http.send(self.build_image_request(image_id, size), stream=True)
