# python-image-proxy Specification

## Summary

Browsers cannot fetch images from the NAS directly, because they do not hold the NAS session cookie. The Python port therefore streams images through the authenticated client. `PhotoStationClient.open_image` opens a streamed response from Photo Station's `/photo/api/thumb.php`, either full size or thumbnail. The optional `proxy.create_image_router` mounts `GET /image/{image_id}` and `GET /thumb/{image_id}` on a FastAPI app and relays that stream unchanged. Hop-by-hop headers and the NAS `Set-Cookie` are dropped so the session never reaches the browser. This is the Python counterpart of the C# `QnapImageMiddleware`.

## Purpose

Defining how images and thumbnails are fetched from the NAS and relayed to HTTP clients without exposing the NAS session.

## Requirements

### Requirement: Image request format

`PhotoStationClient.build_image_request(image_id, size=ImageSize.FULL)` SHALL build `GET /photo/api/thumb.php` with the query parameters `s` (`0` for `ImageSize.FULL`, `1` for `ImageSize.THUMBNAIL`), `m=display` and `f=<image_id>`. `open_image` SHALL send that request through the authenticated client with streaming enabled and return the unread response. The caller SHALL close the response.

#### Scenario: thumbnail request

- **WHEN** `open_image("abc", ImageSize.THUMBNAIL)` is called
- **THEN** the NAS receives `GET /photo/api/thumb.php?s=1&m=display&f=abc` with the `NAS_SID` cookie

### Requirement: Proxy routes

`create_image_router(get_client)` SHALL return a FastAPI `APIRouter` with `GET /image/{image_id}` (full size) and `GET /thumb/{image_id}` (thumbnail), where `get_client` is a FastAPI dependency that returns the shared `PhotoStationClient`. `image_id` SHALL be a single path segment. The router SHALL handle no other paths. The module SHALL be importable only when the `server` extra (FastAPI) is installed, and no other module of the package SHALL import FastAPI.

#### Scenario: route mapping

- **WHEN** a client requests `/image/abc` or `/thumb/abc`
- **THEN** the upstream request has `s=0` or `s=1` respectively

#### Scenario: unrelated path

- **WHEN** a client requests `/other` on an app that only includes the image router
- **THEN** the response is 404 from FastAPI and no NAS request is made

### Requirement: Response relayed unchanged

The proxy SHALL respond with the upstream status code, including error statuses. It SHALL stream the upstream body as raw bytes (`aiter_raw`), without buffering or content decoding, so the upstream `Content-Type`, `Content-Encoding` and `Content-Length` stay valid and are forwarded. It SHALL close the upstream response after the body has been sent.

#### Scenario: JPEG relayed

- **WHEN** the NAS returns 200 with `Content-Type: image/jpeg` and a streamed body
- **THEN** the proxy returns 200 with `content-type: image/jpeg` and a byte-identical body

### Requirement: Session and hop-by-hop headers are not forwarded

The proxy SHALL drop these upstream headers, compared case-insensitively: `Connection`, `Keep-Alive`, `Proxy-Authenticate`, `Proxy-Authorization`, `TE`, `Trailer`, `Transfer-Encoding`, `Upgrade` and `Set-Cookie`.

#### Scenario: NAS cookie not leaked

- **WHEN** the NAS image response includes `Set-Cookie: NAS_SID=…`
- **THEN** the proxy response has no `set-cookie` header
