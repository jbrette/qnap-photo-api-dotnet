"""Async Photo Station client (equivalent of the C# ``PhotoStationClient``)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Self

import httpx

from .auth import QnapAuth
from .config import QnapApiOptions
from .enums import ImageSize
from .models import ListAlbumPhotosResponse, ListAlbumsResponse, ListResponse
from .requests import ListAlbumPhotosRequest, ListAlbumsRequest, ListRequest

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from pydantic import BaseModel

LIST_PATH = "/photo/api/list.php"
THUMB_PATH = "/photo/api/thumb.php"
DEFAULT_TIMEOUT_SECONDS = 30.0


class PhotoStationClient:
    """Use as ``async with PhotoStationClient(options) as client: ...`` or call ``aclose()``."""

    def __init__(
        self,
        options: QnapApiOptions,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a client for one NAS.

        Args:
            options: NAS connection settings.
            transport: Custom ``httpx`` transport (tests use ``httpx.MockTransport``).
            timeout: Request timeout in seconds, or an ``httpx.Timeout``.
            clock: Monotonic clock used for session expiry; injectable for tests.
        """
        self.options = options
        self.auth = QnapAuth(options, clock=clock)
        self.http = httpx.AsyncClient(
            base_url=options.base_url,
            auth=self.auth,
            transport=transport,
            timeout=timeout,
        )

    @classmethod
    def from_env(
        cls,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
    ) -> Self:
        """Create a client from the ``QNAP_*`` environment variables."""
        return cls(QnapApiOptions.from_env(), transport=transport, timeout=timeout)

    async def __aenter__(self) -> Self:
        """Return the client itself."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the underlying HTTP client."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self.http.aclose()

    async def list(self, request: ListRequest | None = None) -> ListResponse:
        """List media; defaults to the first page of everything, best rated first."""
        return await self._list((request or ListRequest()).to_params(), ListResponse)

    async def list_albums(self, request: ListAlbumsRequest | None = None) -> ListAlbumsResponse:
        """List albums; defaults to the first page of all albums by title."""
        return await self._list((request or ListAlbumsRequest()).to_params(), ListAlbumsResponse)

    async def list_album_photos(self, request: ListAlbumPhotosRequest) -> ListAlbumPhotosResponse:
        """List the media in one album."""
        return await self._list(request.to_params(), ListAlbumPhotosResponse)

    async def _list[T: BaseModel](self, params: dict[str, str], model: type[T]) -> T:
        response = await self.http.get(
            LIST_PATH, params=params, headers={"X-Requested-With": "XMLHttpRequest"}
        )
        response.raise_for_status()
        return model.model_validate_json(response.content)

    def build_image_request(self, image_id: str, size: ImageSize = ImageSize.FULL) -> httpx.Request:
        """Build the ``thumb.php`` request for one image or thumbnail."""
        return self.http.build_request(
            "GET", THUMB_PATH, params={"s": size.value, "m": "display", "f": image_id}
        )

    async def open_image(self, image_id: str, size: ImageSize = ImageSize.FULL) -> httpx.Response:
        """Start streaming an image. The caller must ``await response.aclose()`` when done."""
        return await self.http.send(self.build_image_request(image_id, size), stream=True)
