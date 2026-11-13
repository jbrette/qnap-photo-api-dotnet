"""Response models for Photo Station's ``list.php`` JSON.

Photo Station returns numbers as strings, dates as ``yyyy-MM-dd HH:mm:ss`` (or empty /
``0000-00-00 ...``), keywords as a ``;``-delimited string and ratings as 0-100. The
annotated types below normalise those per field, and are tolerant: a malformed value
becomes ``None`` instead of failing the whole page.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .enums import StarRating

QNAP_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
QNAP_DATE_FORMAT = "%Y-%m-%d"


def _blank_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _parse_datetime(value: object) -> datetime | None:
    value = _blank_to_none(value)
    if value is None or isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.startswith("0000-00-00"):
        return None
    try:
        return datetime.strptime(text, QNAP_DATETIME_FORMAT)  # noqa: DTZ007 - NAS local time, no zone
    except ValueError:
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None


def _parse_date(value: object) -> date | None:
    value = _blank_to_none(value)
    if isinstance(value, datetime):  # check first: datetime is a subclass of date
        return value.date()
    if value is None or isinstance(value, date):
        return value
    text = str(value).strip()
    if text.startswith("0000-00-00"):
        return None
    try:
        return datetime.strptime(text[:10], QNAP_DATE_FORMAT).date()  # noqa: DTZ007 - date only
    except ValueError:
        return None


def _parse_keywords(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(";") if part.strip()]


QnapDateTime = Annotated[datetime | None, BeforeValidator(_parse_datetime)]
QnapDate = Annotated[date | None, BeforeValidator(_parse_date)]
QnapInt = Annotated[int | None, BeforeValidator(_blank_to_none)]
QnapKeywords = Annotated[list[str], BeforeValidator(_parse_keywords)]
QnapRating = Annotated[StarRating | None, BeforeValidator(StarRating.from_qnap)]


class QnapModel(BaseModel):
    """Base model: accepts QNAP aliases or field names and keeps unknown fields."""

    # Unknown fields are kept (accessible via model_extra) rather than rejected.
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class FileItem(QnapModel):
    """A photo or video. Shared by the list and album-photos endpoints."""

    id: str
    media_type: str | None = Field(None, alias="MediaType")
    file_name: str | None = Field(None, alias="cFileName")
    picture_title: str | None = Field(None, alias="cPictureTitle")
    comment: str | None = None
    mime: str | None = None
    file_size: QnapInt = Field(None, alias="iFileSize")
    width: QnapInt = Field(None, alias="iWidth")
    height: QnapInt = Field(None, alias="iHeight")
    year_month: str | None = Field(None, alias="YearMonth")
    year_month_day: str | None = Field(None, alias="YearMonthDay")
    date_time: QnapDateTime = Field(None, alias="dateTime")
    date_created: QnapDateTime = Field(None, alias="DateCreated")
    date_modified: QnapDateTime = Field(None, alias="DateModified")
    add_to_db_time: QnapDateTime = Field(None, alias="AddToDbTime")
    last_update: QnapDateTime = Field(None, alias="LastUpdate")
    scanned_flag: str | None = Field(None, alias="ScannedFlag")
    color_level: str | None = Field(None, alias="ColorLevel")
    longitude: str | None = None
    latitude: str | None = None
    location: Any = None
    orientation: str | None = Field(None, alias="Orientation")
    protection_status: str | None = Field(None, alias="ProtectionStatus")
    lens_info: str | None = Field(None, alias="lensInfo")
    aperture: str | None = Field(None, alias="Aperture")
    exposure: str | None = Field(None, alias="Exposure")
    iso: str | None = Field(None, alias="ISO")
    maker: str | None = Field(None, alias="Maker")
    model: str | None = Field(None, alias="Model")
    focal_length: str | None = Field(None, alias="FocalLength")
    white_balance: str | None = Field(None, alias="WhiteBalance")
    flash_firing: str | None = Field(None, alias="FlashFiring")
    metering_mode: str | None = Field(None, alias="MeteringMode")
    projection_type: str | None = Field(None, alias="ProjectionType")
    prefix: str | None = None
    keywords: QnapKeywords = Field(default_factory=list)
    rating: QnapRating = None
    writable: str | None = None
    dimension: str | None = Field(None, alias="Dimension")
    uid: str | None = None
    import_year_month_day: QnapDate = Field(None, alias="ImportYearMonthDay")


class FileEntry(QnapModel):
    """One ``DataList`` entry of a media list."""

    file_item: FileItem | None = Field(None, alias="FileItem")


class ListResponse(QnapModel):
    """Page of media from ``list.php``."""

    status: str | None = None
    total_items: QnapInt = Field(None, alias="photoCount")
    data: list[FileEntry] = Field(default_factory=list, alias="DataList")
    timestamp: QnapDateTime = None


class ListAlbumPhotosResponse(ListResponse):
    """Page of media inside one album; same shape as ``ListResponse``."""


class AlbumItem(QnapModel):
    """An album (manual or smart)."""

    photo_album_id: str | None = Field(None, alias="iPhotoAlbumId")
    album_title: str | None = Field(None, alias="cAlbumTitle")
    date_created: QnapDateTime = Field(None, alias="DateCreated")
    date_modified: QnapDateTime = Field(None, alias="DateModified")
    album_type: str | None = Field(None, alias="albumType")
    photo_count: QnapInt = Field(None, alias="PhotoCount")
    video_count: QnapInt = Field(None, alias="VideoCount")


class AlbumEntry(QnapModel):
    """One ``DataList`` entry of the album list."""

    file_item: AlbumItem | None = Field(None, alias="FileItem")


class KeywordItem(QnapModel):
    """A keyword known to the NAS."""

    keyword: str | None = Field(None, alias="Keyword")


class KeywordEntry(QnapModel):
    """One ``KeywordList`` entry of the album list (shape unverified against a NAS)."""

    item: KeywordItem | None = Field(None, alias="Item")


class ListAlbumsResponse(QnapModel):
    """Page of albums from ``list.php``."""

    status: str | None = None
    data: list[AlbumEntry] = Field(default_factory=list, alias="DataList")
    keywords: list[KeywordEntry] = Field(default_factory=list, alias="KeywordList")
    timestamp: QnapDateTime = None
