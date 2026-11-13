# qnap-photo-api (Python)

Python port of `Ragware.QnapPhotoApi`: an async client for the QNAP Photo Station API, plus an optional FastAPI router that proxies `/image/{id}` and `/thumb/{id}` from the NAS.

## Install

```bash
uv sync                   # client + dev tools (Python 3.14+; httpx, pydantic, defusedxml)
uv sync --all-extras      # + FastAPI image proxy and sample host
pip install .             # consumers without uv
```

## Configuration

`QnapApiOptions(base_url, username, password, auth_timeout_hours=1)`, or `QnapApiOptions.from_env()` reading `QNAP_BASE_URL`, `QNAP_USERNAME`, `QNAP_PASSWORD`, `QNAP_AUTH_TIMEOUT_HOURS`.

## Usage

```python
from qnap_photo_api import ListRequest, MediaType, PhotoStationClient, QnapApiOptions

options = QnapApiOptions(base_url="http://nas", username="rob", password="...")
async with PhotoStationClient(options) as client:
    page = await client.list(ListRequest(media_type=MediaType.PHOTOS, page_number=1))
    albums = await client.list_albums()
    photos = await client.list_album_photos(ListAlbumPhotosRequest(album_id="42"))
```

Image proxy in a FastAPI app:

```python
from qnap_photo_api.proxy import create_image_router

# get_client: a FastAPI dependency returning the shared client
app.include_router(create_image_router(get_client))
```

`examples/webhost.py` mirrors the C# `QnapPhotoApi.WebHost`:

```bash
QNAP_BASE_URL=http://nas QNAP_USERNAME=... QNAP_PASSWORD=... uvicorn examples.webhost:app --reload
```

## Checks

ruff runs with every rule family enabled, and mypy runs in strict mode with the pydantic plugin. Every function, test and example is fully typed (the package ships `py.typed`). The few ignores are documented in `pyproject.toml`.

```bash
uv run pytest                                   # fails under 100% branch coverage
uv run pytest tests/test_models.py::test_full_response_deserializes
uv run ruff check . && uv run ruff format --check .
uv run mypy                                     # --strict over src/, tests/, examples/
```

## Differences from the C# library

- Response parsing is tolerant: blank or `0000-00-00` dates, blank numbers and off-grid ratings become `None` instead of failing the page; `keywords` is always a trimmed list; file sizes are unbounded ints (fixes items 1–8 in `../docs/review.md`).
- `id` is the only required `FileItem` field. List and album-photo responses share one `FileItem` model.
- `StarRating` values are 1–5 (QNAP's 20–100 via `.qnap_value` / `StarRating.from_qnap`).
- `Sort.RATING` sends `s=rating`; the C# `ListRequest` sent `s=time` for it.
- A failed login is not cached; the C# handler cached the failure for `AuthTimeoutInHours`. Concurrent requests share one login.
- Query parameters are URL-encoded (e.g. album IDs).
- The image proxy drops hop-by-hop headers and the NAS `Set-Cookie`, so the NAS session is not exposed to browsers.
- The login XML is parsed with `defusedxml`, so entity expansion and external references are refused.
