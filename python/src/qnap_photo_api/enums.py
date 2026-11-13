"""Enums whose values are the literal Photo Station query-string values."""

from enum import IntEnum, StrEnum


class MediaType(StrEnum):
    ALL = "allMedia"
    PHOTOS = "photos"
    VIDEOS = "videos"


class Collection(StrEnum):
    SHARED = "0"
    PRIVATE = "1"


class Sort(StrEnum):
    SIZE = "size"
    RATING = "rating"
    DATE_ADDED = "time"


class SortDirection(StrEnum):
    ASCENDING = "ASC"
    DESCENDING = "DESC"


class AlbumType(StrEnum):
    ALL = "allAlbums"
    MANUAL = "albums"
    SMART = "smartAlbums"


class AlbumSort(StrEnum):
    TITLE = "name"


class ImageSize(StrEnum):
    """Value of the ``s`` parameter of ``thumb.php``."""

    FULL = "0"
    THUMBNAIL = "1"


class StarRating(IntEnum):
    """Star count. Photo Station encodes ratings as 0-100 in steps of 20."""

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

    @property
    def qnap_value(self) -> str:
        return str(self.value * 20)

    @classmethod
    def from_qnap(cls, raw: object) -> "StarRating | None":
        """Parse ``"100"``/``100`` -> FIVE. Unrated (0), empty or off-grid values return None."""
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, StarRating):
            return raw
        try:
            value = int(str(raw).strip())
        except ValueError:
            return None
        if value <= 0 or value > 100 or value % 20:
            return None
        return cls(value // 20)
