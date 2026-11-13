# python-response-parsing Specification

## Summary

Photo Station's list JSON is loosely typed. Numbers arrive as strings. Dates arrive as `yyyy-MM-dd HH:mm:ss`, as empty strings, or as `0000-00-00 …`. Keywords arrive as one `;`-delimited string and ratings on a 0–100 scale. The pydantic models in `qnap_photo_api.models` normalise these per field with `Annotated` validators, and blank or nonsensical values become `None`, so one odd item does not fail the whole page. Media items share one `FileItem` model across the list and album-photos endpoints, and `id` is its only required field. Field names are snake_case, the QNAP names are kept as aliases, and unknown fields are preserved.

## Purpose

Defining how Photo Station JSON responses map to the Python models, and which malformed values are tolerated.

## Requirements

### Requirement: Model conventions

Every response model SHALL accept input by QNAP alias (for example `cFileName`) or by Python field name (`file_name`). It SHALL keep unknown fields in `model_extra` rather than reject them. Collection fields (`data`, `keywords`) SHALL default to empty lists when absent.

#### Scenario: missing DataList

- **WHEN** a list response has no `DataList`
- **THEN** `response.data` is `[]`

#### Scenario: unknown field kept

- **WHEN** a `FileItem` payload contains a field the model does not declare
- **THEN** parsing succeeds and the field is available in `model_extra`

### Requirement: Media list response shape

`ListResponse` SHALL map `status`, `photoCount` → `total_items`, `DataList[].FileItem` → `data[].file_item`, and `timestamp`. `ListAlbumPhotosResponse` SHALL have the same shape. `FileItem` SHALL require only `id`, and every other field SHALL be optional.

#### Scenario: captured response

- **WHEN** the captured fixture (`photoCount` "16492", one photo, `timestamp` "2024-12-29 08:05:52") is parsed
- **THEN** `total_items` is 16492, `timestamp` is 2024-12-29 08:05:52, and the item's `file_size`, `width`, `height`, dates, keywords and rating are typed values

#### Scenario: item without file name

- **WHEN** a `FileItem` has `id` but no `cFileName`
- **THEN** parsing succeeds and `file_name` is `None`

### Requirement: Date and time fields

Date-time fields SHALL parse `%Y-%m-%d %H:%M:%S` first and then ISO 8601, and SHALL become `None` for `null`, blank strings, values starting with `0000-00-00`, and unparseable text. `import_year_month_day` SHALL parse the first ten characters as `%Y-%m-%d`, with the same `None` rules, and SHALL reduce a `datetime` input to its `date`. Parsed values SHALL be naive (no time zone).

#### Scenario: blank and zero dates

- **WHEN** an item has `dateTime=""`, `DateCreated="0000-00-00 00:00:00"`, `ImportYearMonthDay=""` and `LastUpdate=null`
- **THEN** all four fields are `None` and the page parses

### Requirement: Integer fields

Integer fields (`total_items`, `file_size`, `width`, `height`, `photo_count`, `video_count`) SHALL accept numeric strings and JSON numbers with no upper bound, and SHALL become `None` for `null` or blank strings. A non-blank, non-numeric value SHALL fail validation.

#### Scenario: file larger than 2 GB

- **WHEN** `iFileSize` is `"3221225472"`
- **THEN** `file_size` is 3221225472

#### Scenario: blank dimensions

- **WHEN** `iWidth` is `""` and `iHeight` is `null`
- **THEN** `width` and `height` are `None`

### Requirement: Keywords field

`keywords` SHALL always be a list of strings. `null` SHALL become `[]`. A string SHALL be split on `;`, with each part stripped and empty parts dropped. A JSON array SHALL be kept, with its items stripped and empty items dropped.

#### Scenario: keyword normalisation

- **WHEN** `keywords` is `"a; b ;;c"`
- **THEN** `keywords` is `["a", "b", "c"]`

#### Scenario: null keywords

- **WHEN** `keywords` is `null`
- **THEN** `keywords` is `[]`

### Requirement: Rating field

`rating` SHALL map QNAP values 20, 40, 60, 80 and 100, given as strings or numbers, to `StarRating.ONE` through `StarRating.FIVE` (integer values 1–5). Values of 0 or below, values above 100, values that are not a multiple of 20, booleans, blanks and non-numeric text SHALL become `None`. `StarRating.qnap_value` SHALL give the reverse mapping as a string.

#### Scenario: numeric and string ratings

- **WHEN** `rating` is `60` or `"20"`
- **THEN** it parses to `StarRating.THREE` or `StarRating.ONE` respectively

#### Scenario: unrated or off-grid

- **WHEN** `rating` is `"0"`, `"50"` or `""`
- **THEN** `rating` is `None`

### Requirement: Album list response shape

`ListAlbumsResponse` SHALL map `status`, `DataList[].FileItem` → `data[].file_item` (an `AlbumItem` with `iPhotoAlbumId`, `cAlbumTitle`, `DateCreated`, `DateModified`, `albumType`, `PhotoCount` and `VideoCount`), `KeywordList[].Item.Keyword` → `keywords[].item.keyword`, and `timestamp`. The date and integer rules above SHALL apply to album fields. The `KeywordList` shape is inferred from the C# model and has not been checked against a NAS.

#### Scenario: album with blank modified date

- **WHEN** an album has `DateCreated="2024-01-02 03:04:05"`, `DateModified=""` and `PhotoCount="12"`
- **THEN** `date_created` is 2024-01-02 03:04:05, `date_modified` is `None` and `photo_count` is 12
