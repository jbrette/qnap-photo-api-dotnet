import json
from datetime import date, datetime

from qnap_photo_api import AlbumItem, FileItem, ListAlbumsResponse, ListResponse, StarRating

# Captured response, same fixture as QnapPhotoApi.Tests/ListResponseSerializationTests.cs
LIST_RESPONSE = """{"status":"0","photoCount":"16492","DataList":[{"FileItem":{"MediaType":"photo","id":"fWQJEk","cFileName":"pure-pleasure-v0-lllr7dwp7k8e1.jpg","cPictureTitle":"pure-pleasure-v0-lllr7dwp7k8e1","comment":"","mime":"image\\/jpeg","iFileSize":"2071098","iWidth":"3667","iHeight":"5500","YearMonth":"2024-12","YearMonthDay":"2024-12-26","dateTime":"2024-12-26 10:14:48","DateCreated":"2024-12-26 10:16:31","DateModified":"2024-12-26 10:14:48","AddToDbTime":"2024-12-26 10:16:36","LastUpdate":"2024-12-26 10:17:18","ScannedFlag":"1","ColorLevel":"0","longitude":"","latitude":"","location":null,"Orientation":"1","ProtectionStatus":"0","lensInfo":"","Aperture":"","Exposure":"","ISO":"","Maker":"","Model":"","FocalLength":"","WhiteBalance":"","FlashFiring":"","MeteringMode":"","ProjectionType":"0","prefix":"Multimedia\\/Images\\/Adult\\/2024\\/","keywords":"test1;test2;test3","rating":"100","writable":"-1","Dimension":"3667 X 5500","uid":"pfWQJEk","ImportYearMonthDay":"2024-12-26"}}],"timestamp":"2024-12-29 08:05:52"}"""


def parse_item(**fields: object) -> FileItem:
    """Parse a one-item page whose item has ``id``/``cFileName`` plus ``fields``."""
    item = {"id": "abc", "cFileName": "a.jpg", **fields}
    payload = {"status": "0", "photoCount": "1", "DataList": [{"FileItem": item}], "timestamp": ""}
    parsed = ListResponse.model_validate_json(json.dumps(payload)).data[0].file_item
    assert parsed is not None
    return parsed


def test_full_response_deserializes() -> None:
    response = ListResponse.model_validate_json(LIST_RESPONSE)

    assert response.status == "0"
    assert response.total_items == 16492
    assert response.timestamp == datetime(2024, 12, 29, 8, 5, 52)
    assert len(response.data) == 1

    item = response.data[0].file_item
    assert item is not None
    assert item.id == "fWQJEk"
    assert item.keywords == ["test1", "test2", "test3"]
    assert item.date_created == datetime(2024, 12, 26, 10, 16, 31)
    assert item.date_modified == datetime(2024, 12, 26, 10, 14, 48)
    assert item.date_time == datetime(2024, 12, 26, 10, 14, 48)
    assert item.add_to_db_time == datetime(2024, 12, 26, 10, 16, 36)
    assert item.last_update == datetime(2024, 12, 26, 10, 17, 18)
    assert item.file_size == 2071098
    assert item.width == 3667
    assert item.height == 5500
    assert item.rating is StarRating.FIVE
    assert item.import_year_month_day == date(2024, 12, 26)
    assert item.mime == "image/jpeg"


def test_large_file_size_does_not_overflow() -> None:
    assert parse_item(iFileSize="3221225472").file_size == 3_221_225_472


def test_blank_and_zero_dates_become_none() -> None:
    payload = {"DataList": [], "timestamp": ""}
    assert ListResponse.model_validate_json(json.dumps(payload)).timestamp is None
    item = parse_item(
        dateTime="", DateCreated="0000-00-00 00:00:00", ImportYearMonthDay="", LastUpdate=None
    )
    assert item.date_time is None
    assert item.date_created is None
    assert item.import_year_month_day is None
    assert item.last_update is None


def test_iso_datetime_fallback() -> None:
    assert parse_item(dateTime="2024-12-26T10:14:48").date_time == datetime(
        2024, 12, 26, 10, 14, 48
    )
    assert parse_item(dateTime="garbage").date_time is None


def test_blank_numbers_become_none() -> None:
    item = parse_item(iWidth="", iHeight=None)
    assert item.width is None
    assert item.height is None


def test_keywords_null_trimmed_and_list() -> None:
    assert parse_item(keywords=None).keywords == []
    assert parse_item(keywords="a; b ;;c").keywords == ["a", "b", "c"]
    assert parse_item(keywords=["x", ""]).keywords == ["x"]


def test_rating_variants() -> None:
    assert parse_item(rating=60).rating is StarRating.THREE
    assert parse_item(rating="20").rating is StarRating.ONE
    assert parse_item(rating="0").rating is None
    assert parse_item(rating="50").rating is None
    assert parse_item(rating="").rating is None
    assert parse_item(rating=True).rating is None
    assert StarRating.FOUR.qnap_value == "80"


def test_missing_file_name_does_not_fail_page() -> None:
    payload = json.dumps({"DataList": [{"FileItem": {"id": "x"}}]})
    item = ListResponse.model_validate_json(payload).data[0].file_item
    assert item is not None
    assert item.file_name is None


def test_unknown_fields_are_kept() -> None:
    item = parse_item(NewQnapField="v")
    assert item.model_extra == {"NewQnapField": "v"}


def test_albums_response() -> None:
    payload = json.dumps(
        {
            "status": "0",
            "DataList": [
                {
                    "FileItem": {
                        "iPhotoAlbumId": "7",
                        "cAlbumTitle": "Holidays",
                        "DateCreated": "2024-01-02 03:04:05",
                        "DateModified": "",
                        "albumType": "1",
                        "PhotoCount": "12",
                        "VideoCount": "0",
                    }
                }
            ],
            "KeywordList": [{"Item": {"Keyword": "beach"}}],
            "timestamp": "2024-12-29 08:05:52",
        }
    )
    response = ListAlbumsResponse.model_validate_json(payload)
    album: AlbumItem | None = response.data[0].file_item
    assert album is not None
    assert album.album_title == "Holidays"
    assert album.date_created == datetime(2024, 1, 2, 3, 4, 5)
    assert album.date_modified is None
    assert album.photo_count == 12
    keyword = response.keywords[0].item
    assert keyword is not None
    assert keyword.keyword == "beach"


def test_date_field_edge_cases() -> None:
    assert parse_item(ImportYearMonthDay="0000-00-00").import_year_month_day is None
    assert parse_item(ImportYearMonthDay="not-a-date").import_year_month_day is None
    assert parse_item(ImportYearMonthDay="2024-12-26 10:00:00").import_year_month_day == date(
        2024, 12, 26
    )
    by_name = FileItem(id="x", import_year_month_day=datetime(2024, 12, 26, 10, 0, 0))
    assert by_name.import_year_month_day == date(2024, 12, 26)
    assert type(by_name.import_year_month_day) is date


def test_star_rating_from_qnap_edge_cases() -> None:
    assert StarRating.from_qnap(StarRating.TWO) is StarRating.TWO
    assert StarRating.from_qnap("abc") is None
    assert StarRating.from_qnap(None) is None
    assert StarRating.from_qnap(120) is None
