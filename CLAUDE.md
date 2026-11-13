# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read `README.md` for installation and consumer usage, and `architecture.md` before changing code: it covers the module map, the NAS contracts and the invariants. This file holds the commands and the notes a session needs on every task.

## What this is

A wrapper around the QNAP Photo Station HTTP API, in two implementations:

- **C# / .NET 8** (repo root): the NuGet package `Ragware.QnapPhotoApi` plus a sample minimal-API host. This is the version CI builds and publishes.
- **Python** (`python/`): a port with the same features (Python 3.14+, uv, httpx, pydantic v2, defusedxml, optional FastAPI). It sits alongside the C# code, and CI does not build it yet. `python/README.md` lists where it deliberately behaves differently.

`docs/review.md` holds the open code-review findings for the C# response models; most are already fixed in the Python port. `openspec/` holds the OpenSpec change workflow (the `opsx:*` skills).

## Commands (C#)

- Build: `dotnet build -c Release`. This also produces the `.nupkg`, because `GeneratePackageOnBuild` is true.
- Test: `dotnet test` (xunit + Shouldly). For a single test: `dotnet test --filter "FullyQualifiedName~ListResponseSerializationTests.WhenFieldsAreFilled_ThenCanBeDeserialized"`.
- Run the sample host: `dotnet run --project QnapPhotoApi.WebHost`. The Swagger UI is available in Development. `QnapPhotoApi.WebHost/QnapPhotoDotNet.http` has sample requests.

The WebHost loads user secrets, so put NAS credentials there (`dotnet user-secrets set "QnapApi:Password" ... --project QnapPhotoApi.WebHost`), not in `appsettings.json`. `QnapApi:AuthTimeoutInHours` is required as well, and `appsettings.json` doesn't set it.

The root namespace and assembly name are `Ragware.QnapPhotoApi`, not the folder name.

## Commands (Python)

Run these from `python/`:
- Install: `uv sync --all-extras`.
- Test: `uv run pytest`. It fails below 100% branch coverage. For a single test: `uv run pytest tests/test_models.py::test_full_response_deserializes`.
- Lint and type-check: `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy`. ruff uses `select = ["ALL"]`, and mypy runs `--strict` over `src`, `tests` and `examples`. Every function must be fully annotated. Any ignore needs an inline reason or an entry in `pyproject.toml`'s documented ignore list.
- Pre-commit: `.pre-commit-config.yaml` (repo root) runs ruff, `mypy --strict` and pytest on staged `python/` changes. Install it once per clone with `uv run --project python pre-commit install`. Keep its ruff `rev` equal to the `ruff==` pin.
- Run the sample host: `uv run uvicorn examples.webhost:app --reload`, with `QNAP_BASE_URL`, `QNAP_USERNAME` and `QNAP_PASSWORD` set (keep them in an ignored `.env`).

## CI / release

- `ci.yml` (push to `main`): runs `_build.yml` (restore, Release build, test, upload `.nupkg`), then pushes a pre-release package to GitHub Packages.
- `create-release.yml` (tag `X.Y.Z` or `X.Y.Z-beta`): builds and creates a draft GitHub release with the package.
- `publish-release.yml` (release published): pushes the release's `.nupkg` to nuget.org.

The package version comes from `<Version>` in `QnapPhotoApi.csproj`. The csproj contains MinVer properties/targets, but the MinVer package is not referenced, so they are currently inert. Workflows and package metadata point at the upstream `robgray/qnap-photo-api-dotnet` repo.
