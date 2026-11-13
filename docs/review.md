# Code review: 41d55c9 "improved response object typing"

Reviewed `HEAD~1..HEAD` (41d55c9) on 2026-11-13 with `/code-review`. Findings were deduplicated but **not independently verified**.

## Likely to break against real responses

1. **`FileSize` overflows on files ≥ 2 GB** — `QnapPhotoApi/QnapApi/List/ListResponse.cs:45`, `QnapPhotoApi/QnapApi/ListAlbumPhotos/ListResponse.cs:45`.
   `FileSize` is now `int?`. A video with `iFileSize: "3221225472"` throws `JsonException` and fails the whole page. Should be `long?`.

2. **`DateTime.Parse` throws on empty/null/zero dates** — `QnapPhotoApi/QnapApi/Converters/QnapDateTimeJsonConverter.cs:11`.
   `"dateTime": ""` or `"0000-00-00 00:00:00"` (photo without EXIF, album without modified date) throws `FormatException`, even for `DateTime?` properties. Use `TryParseExact` and return default/null.

3. **Non-nullable `ImportYearMonthDay` throws on empty/null** — `QnapPhotoApi/QnapApi/List/ListResponse.cs:122` (and `ListAlbumPhotos/ListResponse.cs:122`).
   `DateOnly.Parse("")` throws. Same for the non-nullable `Timestamp`/`DateCreated`/`DateModified` in `ListAlbumsResponse`.

4. **`required` on `Id`/`FileName`** — `QnapPhotoApi/QnapApi/List/ListResponse.cs:30`.
   An entry missing `cFileName` now raises "missing required properties" and fails the page (previously null). Also breaks consumers constructing `FileItem` without those members.

5. **Rating converter is brittle** — `QnapPhotoApi/QnapApi/Converters/QnapStartRatingJsonConverter.cs:10`.
   `GetString()` throws if `rating` arrives as a JSON number; any value other than 20/40/60/80/100 (e.g. `"0"`, `"50"`) silently becomes null. The mapping is duplicated in `ListRequest.StarRatingParam` (`ListRequest.cs:60`).

## Correctness, lower risk

6. **Culture-dependent, asymmetric date round-trip** — `QnapDateTimeJsonConverter.cs:11`, same in `QnapDateOnlyJsonConverter`.
   Read uses the current culture; Write uses `InvariantCulture` default (`MM/dd/yyyy`). Round-tripping on en-GB/de-DE throws or swaps day/month. Use `ParseExact`/`ToString("yyyy-MM-dd HH:mm:ss", InvariantCulture)` in both directions.

7. **`QnapStringArrayJsonConverter` registered globally** — `QnapPhotoApi/QnapApi/PhotoStationClient.cs:59`.
   Every `string[]` goes through `GetString()`, so a real JSON array (`["a","b"]`) in any future response throws `InvalidOperationException`. Apply via `[JsonConverter]` on `Keywords` only. Global DateTime/DateOnly overrides have the same effect on non-QNAP date formats.

8. **`Keywords` can be null despite non-nullable type** — `QnapPhotoApi/QnapApi/List/ListResponse.cs:109`.
   JSON `null` bypasses the converter (`HandleNull` is false for reference types), so `item.Keywords.Length` throws `NullReferenceException`. The split also does not trim (`"a; b"` → `" b"`).

## Cleanup

9. **`JsonSerializerOptions` rebuilt per request** — `QnapPhotoApi/QnapApi/PhotoStationClient.cs:48`.
   Discards System.Text.Json's metadata cache on every call. A single `internal static readonly JsonSerializerOptions` shared by the client and tests removes the cost and the duplicated converter list.

10. **Duplicated, already-diverging response types** — `QnapPhotoApi/QnapApi/ListAlbumPhotos/ListResponse.cs:17`.
    `Timestamp` is `DateTime?` here but `DateTime` in `ListResponse`/`ListAlbumsResponse`. `FileItem`/`DataList` are near-identical copies, so every fix (e.g. `FileSize` → `long?`) must be made twice. Share one type.
