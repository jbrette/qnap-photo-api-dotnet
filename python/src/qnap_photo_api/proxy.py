"""FastAPI image proxy (equivalent of the C# ``QnapImageMiddleware``).

Mounts ``GET /image/{image_id}`` and ``GET /thumb/{image_id}`` and streams the NAS response
through the authenticated client, so browsers never need the NAS session cookie.
Requires the ``server`` extra (``pip install qnap-photo-api[server]``).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from .client import PhotoStationClient
from .enums import ImageSize

# Hop-by-hop headers, plus Set-Cookie so the NAS session never leaks to browsers.
_DROPPED_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "set-cookie",
    }
)


async def stream_image(client: PhotoStationClient, image_id: str, size: ImageSize) -> StreamingResponse:
    upstream = await client.open_image(image_id, size)
    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _DROPPED_HEADERS}
    # aiter_raw keeps the body byte-identical, so Content-Encoding/Content-Length stay valid.
    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=headers,
        background=BackgroundTask(upstream.aclose),
    )


def create_image_router(get_client: Callable[..., PhotoStationClient]) -> APIRouter:
    """``get_client`` is a FastAPI dependency returning the shared ``PhotoStationClient``."""
    router = APIRouter(tags=["QnapImages"])

    @router.get("/image/{image_id}", name="GetImage")
    async def image(image_id: str, client: PhotoStationClient = Depends(get_client)) -> StreamingResponse:
        return await stream_image(client, image_id, ImageSize.FULL)

    @router.get("/thumb/{image_id}", name="GetThumbnail")
    async def thumb(image_id: str, client: PhotoStationClient = Depends(get_client)) -> StreamingResponse:
        return await stream_image(client, image_id, ImageSize.THUMBNAIL)

    return router
