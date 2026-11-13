from qnap_photo_api import (
    AlbumType,
    Collection,
    ListAlbumPhotosRequest,
    ListAlbumsRequest,
    ListRequest,
    MediaType,
    Sort,
    SortDirection,
    StarRating,
)


def test_list_request_defaults() -> None:
    assert ListRequest().to_params() == {
        "h": "0",
        "json": "1",
        "t": "allMedia",
        "sd": "DESC",
        "c": "100",
        "p": "1",
        "s": "rating",
    }


def test_list_request_with_rating() -> None:
    params = ListRequest(
        media_type=MediaType.PHOTOS,
        collection=Collection.PRIVATE,
        sort=Sort.SIZE,
        sort_direction=SortDirection.ASCENDING,
        rating=StarRating.FOUR,
        page_number=3,
    ).to_params()
    assert params["t"] == "photos"
    assert params["h"] == "1"
    assert params["s"] == "size"
    assert params["sd"] == "ASC"
    assert params["m"] == "80"
    assert params["p"] == "3"


def test_album_photos_request() -> None:
    params = ListAlbumPhotosRequest(album_id="42").to_params()
    assert params["t"] == "albumPhotos"
    assert params["a"] == "42"
    assert params["s"] == "time"


def test_albums_request() -> None:
    params = ListAlbumsRequest(album_type=AlbumType.SMART).to_params()
    assert params == {
        "json": "1",
        "t": "smartAlbums",
        "h": "0",
        "s": "name",
        "sd": "ASC",
        "c": "50",
        "p": "1",
    }
