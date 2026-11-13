"""Request objects for ``/photo/api/list.php``. ``to_params()`` builds the query string."""

from __future__ import annotations

from dataclasses import dataclass

from .enums import AlbumSort, AlbumType, Collection, MediaType, Sort, SortDirection, StarRating


@dataclass
class ListRequest:
    """Page of media (photos, videos or both)."""

    collection: Collection = Collection.SHARED
    media_type: MediaType = MediaType.ALL
    page_size: int = 100  # matches the page size of the Photo Station app
    page_number: int = 1
    sort: Sort = Sort.RATING
    sort_direction: SortDirection = SortDirection.DESCENDING
    rating: StarRating | None = None

    def to_params(self) -> dict[str, str]:
        """Query parameters for ``list.php``."""
        params = {
            "h": self.collection.value,
            "json": "1",
            "t": self.media_type.value,
            "sd": self.sort_direction.value,
            "c": str(self.page_size),
            "p": str(self.page_number),
            "s": self.sort.value,
        }
        if self.rating is not None:
            params["m"] = self.rating.qnap_value
        return params


@dataclass
class ListAlbumPhotosRequest:
    """Page of media inside one album."""

    album_id: str
    collection: Collection = Collection.SHARED
    page_size: int = 100
    page_number: int = 1
    sort: Sort = Sort.DATE_ADDED
    sort_direction: SortDirection = SortDirection.DESCENDING

    def to_params(self) -> dict[str, str]:
        """Query parameters for ``list.php``."""
        return {
            "h": self.collection.value,
            "json": "1",
            "t": "albumPhotos",
            "a": self.album_id,
            "sd": self.sort_direction.value,
            "c": str(self.page_size),
            "p": str(self.page_number),
            "s": self.sort.value,
        }


@dataclass
class ListAlbumsRequest:
    """Page of albums."""

    collection: Collection = Collection.SHARED
    album_type: AlbumType = AlbumType.ALL
    sort: AlbumSort = AlbumSort.TITLE
    sort_direction: SortDirection = SortDirection.ASCENDING
    page_number: int = 1
    page_size: int = 50

    def to_params(self) -> dict[str, str]:
        """Query parameters for ``list.php``."""
        return {
            "json": "1",
            "t": self.album_type.value,
            "h": self.collection.value,
            "s": self.sort.value,
            "sd": self.sort_direction.value,
            "c": str(self.page_size),
            "p": str(self.page_number),
        }
