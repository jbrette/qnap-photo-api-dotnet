# python-photo-listing Specification

## Summary

`PhotoStationClient` is the async entry point of the Python port. It exposes three list operations: `list` for media, `list_albums` for albums, and `list_album_photos` for the media in one album. All three are a GET to Photo Station's single `/photo/api/list.php` endpoint and differ only in their query parameters. Each request dataclass builds its own parameters in `to_params()`, and the enum values are the literal QNAP query values, so no other code maps enums to parameters. Responses are checked for HTTP errors and then parsed into the typed models (see `python-response-parsing`).

## Purpose

Defining the client's lifecycle, its list operations, and the exact query parameters each request type sends to Photo Station.

## Requirements

### Requirement: Client lifecycle

`PhotoStationClient(options, *, transport=None, timeout=30.0)` SHALL own one `httpx.AsyncClient`, with its base URL set to `options.base_url` and its auth set to a `QnapAuth`. A custom transport SHALL be injectable for tests. The client SHALL be an async context manager that closes the HTTP client on exit, and SHALL also offer `aclose()`. `PhotoStationClient.from_env()` SHALL build the client from `QnapApiOptions.from_env()`.

#### Scenario: context manager closes the HTTP client

- **WHEN** `async with PhotoStationClient(options) as client:` exits
- **THEN** the underlying `httpx.AsyncClient` is closed

### Requirement: List calls share one request shape

Every list operation SHALL send `GET /photo/api/list.php` with the request's `to_params()` as URL-encoded query parameters and the header `X-Requested-With: XMLHttpRequest`. A 4xx or 5xx response SHALL raise `httpx.HTTPStatusError`. A successful body SHALL be parsed into the operation's response model.

#### Scenario: NAS error

- **WHEN** `list.php` returns HTTP 500
- **THEN** `list()` raises `httpx.HTTPStatusError`

#### Scenario: album id is URL-encoded

- **WHEN** `list_album_photos(ListAlbumPhotosRequest(album_id="5"))` is called
- **THEN** the request URL's query has `a=5`, with any reserved characters in the id percent-encoded

### Requirement: Media list parameters

`list(request=None)` SHALL use a default `ListRequest` when no request is given and SHALL return a `ListResponse`. `ListRequest.to_params()` SHALL emit `h` (`0` shared, `1` private), `json=1`, `t` (`allMedia` | `photos` | `videos`), `sd` (`ASC` | `DESC`), `c` (page size), `p` (page) and `s` (`size` | `rating` | `time`). The defaults SHALL be: shared, all media, page size 100, page 1, sort by rating, descending.

#### Scenario: defaults

- **WHEN** `ListRequest().to_params()` is called
- **THEN** it returns `{"h": "0", "json": "1", "t": "allMedia", "sd": "DESC", "c": "100", "p": "1", "s": "rating"}`

### Requirement: Media list rating filter

`ListRequest.to_params()` SHALL add `m`, set to the star rating × 20, only when `rating` is set, and SHALL omit `m` otherwise.

#### Scenario: no rating filter

- **WHEN** a `ListRequest` without `rating` is converted
- **THEN** the parameters contain no `m`

#### Scenario: rating filter

- **WHEN** a `ListRequest` with `rating=StarRating.FOUR` is converted
- **THEN** the parameters include `m=80`

### Requirement: Album photo list parameters

`list_album_photos(request)` SHALL require a `ListAlbumPhotosRequest` and SHALL return a `ListAlbumPhotosResponse`. `to_params()` SHALL emit `h`, `json=1`, `t=albumPhotos`, `a` (the album id), `sd`, `c`, `p` and `s`. The defaults SHALL be: shared collection, page size 100, page 1, sort by date added (`time`), descending.

#### Scenario: album photos defaults

- **WHEN** `ListAlbumPhotosRequest(album_id="42").to_params()` is called
- **THEN** the parameters include `t=albumPhotos`, `a=42` and `s=time`

### Requirement: Album list parameters

`list_albums(request=None)` SHALL use a default `ListAlbumsRequest` when no request is given and SHALL return a `ListAlbumsResponse`. `to_params()` SHALL emit `json=1`, `t` (`allAlbums` | `albums` | `smartAlbums`), `h`, `s=name`, `sd`, `c` and `p`. The defaults SHALL be: all album types, shared collection, sort by title, ascending, page 1, page size 50.

#### Scenario: smart albums

- **WHEN** `ListAlbumsRequest(album_type=AlbumType.SMART).to_params()` is called
- **THEN** it returns `{"json": "1", "t": "smartAlbums", "h": "0", "s": "name", "sd": "ASC", "c": "50", "p": "1"}`
