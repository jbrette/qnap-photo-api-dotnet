"""Enums whose values are the literal Photo Station query-string values."""

from enum import IntEnum, StrEnum

QNAP_RATING_STEP = 20
QNAP_RATING_MAX = 100


class MediaType(StrEnum):
    """Media filter for the ``t`` parameter of the media list."""

    ALL = "allMedia"
    PHOTOS = "photos"
    VIDEOS = "videos"


class Collection(StrEnum):
    """Collection selector for the ``h`` parameter."""

    SHARED = "0"
    PRIVATE = "1"


class Sort(StrEnum):
    """Sort key for the ``s`` parameter of media lists."""

    SIZE = "size"
    RATING = "rating"
    DATE_ADDED = "time"


class SortDirection(StrEnum):
    """Sort direction for the ``sd`` parameter."""

    ASCENDING = "ASC"
    DESCENDING = "DESC"


class AlbumType(StrEnum):
    """Album filter for the ``t`` parameter of the album list."""

    ALL = "allAlbums"
    MANUAL = "albums"
    SMART = "smartAlbums"


class AlbumSort(StrEnum):
    """Sort key for the ``s`` parameter of the album list."""

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
        """The rating on QNAP's 0-100 scale, as sent in query strings."""
        return str(self.value * QNAP_RATING_STEP)

    @classmethod
    def from_qnap(cls, raw: object) -> StarRating | None:
        """Parse ``"100"``/``100`` to FIVE.

        Unrated (0), empty, off-grid and non-numeric values return None.
        """
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, StarRating):
            return raw
        try:
            value = int(str(raw).strip())
        except ValueError:
            return None
        if value <= 0 or value > QNAP_RATING_MAX or value % QNAP_RATING_STEP:
            return None
        return cls(value // QNAP_RATING_STEP)
