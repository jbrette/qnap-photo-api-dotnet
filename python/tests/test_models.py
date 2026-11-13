import json
from datetime import date, datetime

from qnap_photo_api import ListAlbumsResponse, ListResponse, StarRating

# Captured response, same fixture as QnapPhotoApi.Tests/ListResponseSerializationTests.cs
LIST_RESPONSE = """{"status":"0","photoCount":"16492","DataList":[{"FileItem":{"MediaType":"photo","id":"fWQJEk","cFileName":"pure-pleasure-v0-lllr7dwp7k8e1.jpg","cPictureTitle":"pure-pleasure-v0-lllr7dwp7k8e1","comment":"","mime":"image\\/jpeg","iFileSize":"2071098","iWidth":"3667","iHeight":"5500","YearMonth":"2024-12","YearMonthDay":"2024-12-26","dateTime":"2024-12-26 10:14:48","DateCreated":"2024-12-26 10:16:31","DateModified":"2024-12-26 10:14:48","AddToDbTime":"2024-12-26 10:16:36","LastUpdate":"2024-12-26 10:17:18","ScannedFlag":"1","ColorLevel":"0","longitude":"","latitude":"","location":null,"Orientation":"1","ProtectionStatus":"0","lensInfo":"","Aperture":"","Exposure":"","ISO":"","Maker":"","Model":"","FocalLength":"","WhiteBalance":"","FlashFiring":"","MeteringMode":"","ProjectionType":"0","prefix":"Multimedia\\/Images\\/Adult\\/2024\\/","keywords":"test1;test2;test3","rating":"100","writable":"-1","Dimension":"3667 X 5500","uid":"pfWQJEk","ImportYearMonthDay":"2024-12-26"}}],"timestamp":"2024-12-29 08:05:52"}"""


def _item(**overrides):
    base = {"id": "abc", "cFileName": "a.jpg"}
    base.update(overrides)
    return json.dumps({"status": "0", "photoCount": "1", "DataList": [{"FileItem": base}], "timestamp": ""})


def test_full_response_deserializes():
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


def test_large_file_size_does_not_overflow():
    item = ListResponse.model_validate_json(_item(iFileSize="3221225472")).data[0].file_item
    assert item.file_size == 3_221_225_472


def test_blank_and_zero_dates_become_none():
    response = ListResponse.model_validate_json(
        _item(dateTime="", DateCreated="0000-00-00 00:00:00", ImportYearMonthDay="", LastUpdate=None)
    )
    item = response.data[0].file_item
    assert response.timestamp is None
    assert item.date_time is None
    assert item.date_created is None
    assert item.import_year_month_day is None
    assert item.last_update is None


def test_blank_numbers_become_none():
    item = ListResponse.model_validate_json(_item(iWidth="", iHeight=None)).data[0].file_item
    assert item.width is None
    assert item.height is None


def test_keywords_null_trimmed_and_list():
    assert ListResponse.model_validate_json(_item(keywords=None)).data[0].file_item.keywords == []
    assert ListResponse.model_validate_json(_item(keywords="a; b ;;c")).data[0].file_item.keywords == ["a", "b", "c"]
    assert ListResponse.model_validate_json(_item(keywords=["x", ""])).data[0].file_item.keywords == ["x"]


def test_rating_variants():
    def rating(value):
        return ListResponse.model_validate_json(_item(rating=value)).data[0].file_item.rating

    assert rating(60) is StarRating.THREE
    assert rating("20") is StarRating.ONE
    assert rating("0") is None
    assert rating("50") is None
    assert rating("") is None


def test_missing_file_name_does_not_fail_page():
    payload = json.dumps({"DataList": [{"FileItem": {"id": "x"}}]})
    assert ListResponse.model_validate_json(payload).data[0].file_item.file_name is None


def test_albums_response():
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
    album = response.data[0].file_item
    assert album.album_title == "Holidays"
    assert album.date_created == datetime(2024, 1, 2, 3, 4, 5)
    assert album.date_modified is None
    assert album.photo_count == 12
    assert response.keywords[0].item.keyword == "beach"
