"""Sample host (equivalent of ``QnapPhotoApi.WebHost``).

    export QNAP_BASE_URL=http://nas QNAP_USERNAME=... QNAP_PASSWORD=...
    uvicorn examples.webhost:app --reload      # from the python/ directory; docs at /docs
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with PhotoStationClient.from_env() as client:
        app.state.qnap = client
        yield


def get_client(request: Request) -> PhotoStationClient:
    return request.app.state.qnap


app = FastAPI(title="QNAP Photo API", lifespan=lifespan)
app.include_router(create_image_router(get_client))


@app.get("/list/{page}", response_model=ListResponse, response_model_by_alias=False, tags=["QnapPhotos"])
async def list_photos(page: int, request: Request) -> ListResponse:
    return await get_client(request).list(
        ListRequest(media_type=MediaType.PHOTOS, sort_direction=SortDirection.DESCENDING, page_number=page, page_size=100)
    )


@app.get(
    "/list-album-photos/{album_id}/{page}",
    response_model=ListAlbumPhotosResponse,
    response_model_by_alias=False,
    tags=["QnapPhotos"],
)
async def list_album_photos(album_id: str, page: int, request: Request) -> ListAlbumPhotosResponse:
    return await get_client(request).list_album_photos(
        ListAlbumPhotosRequest(
            album_id=album_id,
            sort=Sort.DATE_ADDED,
            sort_direction=SortDirection.DESCENDING,
            page_number=page,
            page_size=100,
        )
    )


@app.get("/list-album/{page}", response_model=ListAlbumsResponse, response_model_by_alias=False, tags=["QnapPhotos"])
async def list_albums(page: int, request: Request) -> ListAlbumsResponse:
    return await get_client(request).list_albums(
        ListAlbumsRequest(
            album_type=AlbumType.ALL,
            sort=AlbumSort.TITLE,
            sort_direction=SortDirection.DESCENDING,
            page_number=page,
            page_size=100,
        )
    )
