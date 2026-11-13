"""FastAPI image proxy (equivalent of the C# ``QnapImageMiddleware``).

Mounts ``GET /image/{image_id}`` and ``GET /thumb/{image_id}`` and streams the NAS response
through the authenticated client, so browsers never need the NAS session cookie.
Requires the ``server`` extra (``pip install qnap-photo-api[server]``).
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from .client import (
    PhotoStationClient,  # noqa: TC001 - FastAPI resolves route annotations at runtime
)
from .enums import ImageSize

if TYPE_CHECKING:
    from collections.abc import Callable

# No `from __future__ import annotations` here, and PhotoStationClient stays a runtime
# import: FastAPI inspects the route signatures when the routes are registered.

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


async def stream_image(
    client: PhotoStationClient, image_id: str, size: ImageSize
) -> StreamingResponse:
    """Relay one NAS image as a streaming response, minus session and hop-by-hop headers."""
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
    """Build a router serving ``/image/{image_id}`` and ``/thumb/{image_id}``.

    Args:
        get_client: FastAPI dependency returning the shared ``PhotoStationClient``.
    """
    router = APIRouter(tags=["QnapImages"])

    @router.get("/image/{image_id}", name="GetImage")
    async def image(
        image_id: str,
        client: Annotated[PhotoStationClient, Depends(get_client)],
    ) -> StreamingResponse:
        return await stream_image(client, image_id, ImageSize.FULL)

    @router.get("/thumb/{image_id}", name="GetThumbnail")
    async def thumb(
        image_id: str,
        client: Annotated[PhotoStationClient, Depends(get_client)],
    ) -> StreamingResponse:
        return await stream_image(client, image_id, ImageSize.THUMBNAIL)

    return router
