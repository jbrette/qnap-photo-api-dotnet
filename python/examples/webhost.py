"""Sample host (equivalent of ``QnapPhotoApi.WebHost``).

Set ``QNAP_BASE_URL``, ``QNAP_USERNAME`` and ``QNAP_PASSWORD``, then run
``uvicorn examples.webhost:app --reload`` from the ``python/`` directory (docs at ``/docs``).
"""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request

from qnap_photo_api import (
    AlbumSort,
    AlbumType,
    ListAlbumPhotosRequest,
    ListAlbumPhotosResponse,
    ListAlbumsRequest,
    ListAlbumsResponse,
    ListRequest,
    ListResponse,
    MediaType,
    PhotoStationClient,
    Sort,
    SortDirection,
)
from qnap_photo_api.proxy import create_image_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open one shared client for the app's lifetime."""
    async with PhotoStationClient.from_env() as client:
        app.state.qnap = client
        yield


def get_client(request: Request) -> PhotoStationClient:
    """FastAPI dependency: the client opened by ``lifespan``."""
    client: PhotoStationClient = request.app.state.qnap
    return client


app = FastAPI(title="QNAP Photo API", lifespan=lifespan)
app.include_router(create_image_router(get_client))


@app.get(
    "/list/{page}", response_model=ListResponse, response_model_by_alias=False, tags=["QnapPhotos"]
)
async def list_photos(page: int, request: Request) -> ListResponse:
    """List photos, newest rating first."""
    return await get_client(request).list(
        ListRequest(
            media_type=MediaType.PHOTOS,
            sort_direction=SortDirection.DESCENDING,
            page_number=page,
            page_size=100,
        )
    )


@app.get(
    "/list-album-photos/{album_id}/{page}",
    response_model=ListAlbumPhotosResponse,
    response_model_by_alias=False,
    tags=["QnapPhotos"],
)
async def list_album_photos(album_id: str, page: int, request: Request) -> ListAlbumPhotosResponse:
    """List the media in one album, most recently added first."""
    return await get_client(request).list_album_photos(
        ListAlbumPhotosRequest(
            album_id=album_id,
            sort=Sort.DATE_ADDED,
            sort_direction=SortDirection.DESCENDING,
            page_number=page,
            page_size=100,
        )
    )


@app.get(
    "/list-album/{page}",
    response_model=ListAlbumsResponse,
    response_model_by_alias=False,
    tags=["QnapPhotos"],
)
async def list_albums(page: int, request: Request) -> ListAlbumsResponse:
    """List all albums by title."""
    return await get_client(request).list_albums(
        ListAlbumsRequest(
            album_type=AlbumType.ALL,
            sort=AlbumSort.TITLE,
            sort_direction=SortDirection.DESCENDING,
            page_number=page,
            page_size=100,
        )
    )
