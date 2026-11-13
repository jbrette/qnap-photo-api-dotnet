# Architecture — qnap-photo-api-dotnet

For whoever is about to **change** the code; read at edit time, not at session start. Name
modules and types, do not link them (links go stale). No shell walkthroughs, no runbooks, no
version or tag literals — those belong in `README.md`, a skill, or `--version`.

## Role and boundaries

Leaf library (producer). This repo owns a client for the QNAP Photo Station HTTP API, in two implementations: the C# NuGet package `Ragware.QnapPhotoApi` and the Python package `qnap_photo_api`. The client covers listing photos, albums and album photos, NAS session authentication, and an image/thumbnail proxy. It must **not** own application concerns such as the routes a consumer exposes, paging policy, UI or caching of image bytes. The sample hosts (`QnapPhotoApi.WebHost`, `python/examples/webhost.py`) are demonstrations, not part of the package.

## Module map

C# (repo root):
- `QnapPhotoApi/Configuration` — DI entry: binds `QnapApiOptions`, registers the named `HttpClient` with `AuthenticationHandler`, and registers `IPhotoStationClient`. It may import everything in the library.
- `QnapPhotoApi/DelegatingHandlers` — `AuthenticationHandler`: NAS login and the `NAS_SID` cookie. It imports `QnapApi.Login`, `Extensions`, and `PhotoStationClient` constants only.
- `QnapPhotoApi/QnapApi` — `PhotoStationClient`, the request and response types per endpoint (`List`, `ListAlbums`, `ListAlbumPhotos`, `Login`), `Enums`, and `Converters` (QNAP JSON formats). It has no ASP.NET dependency.
- `QnapPhotoApi/Middleware` — `QnapImageMiddleware`, the `/image` and `/thumb` reverse proxy. It imports `QnapApi` for the client key only.
- `QnapPhotoApi/Extensions` — XML deserialization and base64 helpers.
- `QnapPhotoApi.WebHost` — the sample minimal-API host. It is the only consumer of the library in this repo.
- `QnapPhotoApi.Tests` — deserialization tests. `InternalsVisibleTo` lets them see the internal converters.

Python (`python/src/qnap_photo_api`):
- `config` — `QnapApiOptions` with validation and `from_env`.
- `enums` — enums whose values are the literal QNAP query values. `StarRating` maps 1–5 to and from QNAP's 0–100 scale.
- `requests` — request dataclasses. `to_params()` is the only place a query string is built.
- `models` — pydantic response models with tolerant per-field validators.
- `auth` — `QnapAuth` (`httpx.Auth`) and `LoginResponse`. The login XML is parsed only through `defusedxml`.
- `client` — the async `PhotoStationClient`. It imports `auth`, `config`, `enums`, `models` and `requests`.
- `proxy` — the FastAPI router for `/image` and `/thumb`. It is the only module that imports FastAPI or Starlette.

## Entry points

- C# `Configuration.AddQnapPhotoApi(IServiceCollection, IConfiguration)` and `Configuration.UseQnapImageMiddleware(WebApplication)`.
- C# `IPhotoStationClient`: `ListAsync`, `ListAlbumsAsync`, `ListAlbumPhotosAsync`.
- Python `PhotoStationClient`: `list`, `list_albums`, `list_album_photos`, `open_image`. It is an async context manager.
- Python `proxy.create_image_router(get_client)`.
- Both sample hosts serve the same HTTP surface: `/list/{page}`, `/list-album/{page}`, `/list-album-photos/{albumId}/{page}`, `/image/{id}` and `/thumb/{id}`.

## Data and contracts

- **NAS endpoints used:** `/cgi-bin/authLogin.cgi` (form POST with `user` and a base64 `pwd`, XML reply with root `QDocRoot` and fields `authPassed` and `authSid`), `/photo/api/list.php` (JSON; the `t` parameter selects photos, albums or album photos), and `/photo/api/thumb.php` (`s=0` gives the full image, `s=1` the thumbnail, with `f={id}`). List calls also send `X-Requested-With: XMLHttpRequest`.
- **Session:** the cookie `NAS_SID={authSid}`, reused until `AuthTimeoutInHours` / `auth_timeout_hours` expires.
- **Configuration:** C# reads the `QnapApi` section (`BaseUrl`, `Username`, `Password`, `AuthTimeoutInHours`, all required). Python reads the `QNAP_*` environment variables.
- **QNAP JSON formats:** numbers arrive as strings; dates as `yyyy-MM-dd HH:mm:ss`, empty, or `0000-00-00 …`; keywords as a `;`-delimited string; ratings as 0–100 in steps of 20. Items are wrapped as `DataList[].FileItem`. Album responses also carry `KeywordList[].Item.Keyword`; that shape has not been checked against a NAS.
- The public C# types are the NuGet package's contract, so renaming or retyping a property is a breaking change for consumers.

## Invariants — and why

- **Authentication lives only in the HTTP pipeline** (`AuthenticationHandler` / `QnapAuth`), never in the client methods. The image proxy and every list call share the authenticated named client, and adding auth anywhere else would split session handling.
- **Build query strings only in the request types** (`ToString()` / `to_params()`). Endpoint methods stay one generic call, and the enum-to-QNAP mapping has one home.
- **One malformed field must not fail a page** in the Python models, because QNAP data is inconsistent (photos without EXIF data, videos larger than 2 GB, unrated items). The C# models do not yet meet this; see `docs/review.md`.
- **The image proxy streams raw bytes** without buffering or decoding them, and it forwards `Content-Encoding` and `Content-Length` unchanged. Python drops `Set-Cookie` and hop-by-hop headers so the NAS session never reaches a browser.
- **The Python login is not cached on failure**, so a corrected password or a NAS that has finished booting takes effect on the next request. The C# handler does cache failures, which is a known divergence.
- **C#:** `PhotoStationClient` and the test fixture register the same JSON converter list, and the two must stay identical until they share one options instance. The library logs through `Serilog.ILogger` (a global alias), so a host must register Serilog.

- **Python code is fully typed and lint-clean** under `mypy --strict` and ruff `ALL` (configured in `python/pyproject.toml`), with 100% branch coverage. The package ships `py.typed`, so consumers type-check against it, and an untyped or untested addition would break that for them.

## Cross-references

- what the Python port must do: `openspec/specs/python-*` (config, NAS auth, listing, response parsing, image proxy) · open review findings: `docs/review.md`
- the C# library has no specs yet; its behaviour differs where `python/README.md` says so
- upstream: forked from `robgray/qnap-photo-api-dotnet`; the CI workflows and package metadata still target the upstream repo and feeds
- for a human at a shell: [`README.md`](README.md) (Python: `python/README.md`) · for a session: [`CLAUDE.md`](CLAUDE.md)
