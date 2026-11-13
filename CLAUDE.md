# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A wrapper around the QNAP Photo Station HTTP API, in two implementations:

- **C# / .NET 8** (repo root): the NuGet package `Ragware.QnapPhotoApi` plus a sample minimal-API host. Consumers call `services.AddQnapPhotoApi(configuration)` and `app.UseQnapImageMiddleware()` (see `README.md`). This is the version CI builds and publishes.
- **Python** (`python/`): a port with the same features, described in the "Python port" section below.

Other directories: `docs/review.md` holds the open code-review findings for the C# response models (most are already fixed in the Python port). `openspec/` holds the OpenSpec change workflow used by the `opsx:*` skills (`changes/`, `specs/`); it has no changes yet.

## Commands (C#)

- Build: `dotnet build -c Release`. This also produces the `.nupkg`, because `GeneratePackageOnBuild` is true.
- Test: `dotnet test` (xunit + Shouldly). For a single test: `dotnet test --filter "FullyQualifiedName~ListResponseSerializationTests.WhenFieldsAreFilled_ThenCanBeDeserialized"`.
- Run the sample host: `dotnet run --project QnapPhotoApi.WebHost`. The Swagger UI is available in Development.

`QnapPhotoApi.WebHost/QnapPhotoDotNet.http` has sample requests. The WebHost loads user secrets, so put NAS credentials there (`dotnet user-secrets set "QnapApi:Password" ... --project QnapPhotoApi.WebHost`), not in `appsettings.json`. `QnapApi:AuthTimeoutInHours` is required as well, and `appsettings.json` doesn't set it.

## Projects

- `QnapPhotoApi/` – the packaged library. Root namespace and assembly name are `Ragware.QnapPhotoApi`, not the folder name. `InternalsVisibleTo` exposes internals to `QnapPhotoApi.Tests`.
- `QnapPhotoApi.WebHost/` – sample app that maps `/list/{page}`, `/list-album/{page}`, `/list-album-photos/{albumId}/{page}` onto `IPhotoStationClient`.
- `QnapPhotoApi.Tests/` – JSON deserialization tests against captured Photo Station responses.

## Architecture

**Configuration** (`QnapPhotoApi/Configuration.cs`): binds `QnapApiOptions` from the `QnapApi` section with data-annotation validation on start. All four properties (`BaseUrl`, `Username`, `Password`, `AuthTimeoutInHours`) are required. Registers a named `HttpClient` (`PhotoStationClient.HttpClientKey`) and a scoped `IPhotoStationClient`.

**Authentication** is not in the client; it lives in `DelegatingHandlers/AuthenticationHandler.cs`, attached to the named HttpClient. On each request it gets-or-creates a cached `LoginResponse` in `IMemoryCache` (key `NAS_SID`, expiry `AuthTimeoutInHours`) by POSTing to `/cgi-bin/authLogin.cgi` with a base64-encoded password, parses the XML response, and adds a `NAS_SID` cookie. A failed login is logged and the request proceeds without the cookie. Because `GetOrCreateAsync` also caches the `null` result, a failed login is not retried until the cache entry expires. Anything that uses the named client (including the image middleware) gets auth for free.

**Listing** (`QnapApi/PhotoStationClient.cs`): every list call goes through one generic `ListAsync<TRequest,TResult>` that GETs `/photo/api/list.php?{request}`. The query string is produced by each request type's `ToString()` override (e.g. `List/ListRequest.cs`), which maps enums to Photo Station's parameter values. To add a new endpoint: add a request class with a `ToString()` that emits the query, a response class, and a method on `IPhotoStationClient`/`PhotoStationClient`.

**Deserialization quirks**: Photo Station returns numbers as strings, dates as `yyyy-MM-dd HH:mm:ss`, semicolon-delimited keyword strings, and ratings as 0–100. These are handled by `JsonNumberHandling.AllowReadingFromString` plus the converters in `QnapApi/Converters/`. The converter list is duplicated in `PhotoStationClient` and in the test fixture constructor; keep them in sync.

**Image proxy** (`Middleware/QnapImageMiddleware.cs`): intercepts `/image/{id}` and `/thumb/{id}` and streams `/photo/api/thumb.php?s=0|1&m=display&f={id}` from the NAS through the authenticated named client, copying status and headers. Other paths fall through to the next middleware.

The library depends on Serilog: `ILogger` is globally aliased to `Serilog.ILogger` in the csproj, and the handler resolves it from DI, so the host must register Serilog.

## Python port (`python/`)

A port of the library to Python 3.11+ (httpx + pydantic v2, FastAPI optional). It sits alongside the C# code; CI does not build it yet.

Run these from `python/`:
- Install: `pip install -e '.[dev,server]'`.
- Test: `pytest`. For a single test: `pytest tests/test_models.py::test_full_response_deserializes`.
- Run the sample host: `uvicorn examples.webhost:app --reload`, with `QNAP_BASE_URL`, `QNAP_USERNAME` and `QNAP_PASSWORD` set (keep them in an ignored `.env`).

How the pieces map to the C# code: `QnapAuth` (`auth.py`) is an `httpx.Auth` that replaces `AuthenticationHandler`. `PhotoStationClient` (`client.py`) is async, and each request type's `to_params()` replaces the C# `ToString()`. Enum values are the literal QNAP query values. QNAP's odd field formats are handled by per-field `Annotated` validators in `models.py`, which replace the global JSON converters. `proxy.create_image_router()` replaces `QnapImageMiddleware`. `python/README.md` lists where the port deliberately behaves differently (tolerant parsing, failed logins not cached, `Sort.RATING` sends `s=rating`).

## CI / release

- `ci.yml` (push to `main`): runs `_build.yml` (restore, Release build, test, upload `.nupkg`), then pushes a pre-release package to GitHub Packages.
- `create-release.yml` (tag `X.Y.Z` or `X.Y.Z-beta`): builds and creates a draft GitHub release with the package.
- `publish-release.yml` (release published): pushes the release's `.nupkg` to nuget.org.

The package version comes from `<Version>` in `QnapPhotoApi.csproj`. The csproj contains MinVer properties/targets, but the MinVer package is not referenced, so they are currently inert. Workflows and package metadata point at the upstream `robgray/qnap-photo-api-dotnet` repo.
