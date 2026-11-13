"""The package version matches the installed distribution metadata."""

from importlib.metadata import version

import qnap_photo_api


def test_version_matches_metadata() -> None:
    assert qnap_photo_api.__version__ == version("qnap-photo-api")
