"""Connection settings (equivalent of the C# ``QnapApiOptions``)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Mapping

ENV_PREFIX = "QNAP_"
_REQUIRED_ENV = ("BASE_URL", "USERNAME", "PASSWORD")


@dataclass(frozen=True)
class QnapApiOptions:
    """Validated, immutable NAS connection settings."""

    base_url: str
    username: str
    password: str
    auth_timeout_hours: float = 1.0

    def __post_init__(self) -> None:
        """Validate every field and strip trailing slashes from ``base_url``.

        Raises:
            ValueError: if any field is missing or invalid.
        """
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            msg = f"base_url must be an absolute http(s) URL, got {self.base_url!r}"
            raise ValueError(msg)
        if not self.username:
            msg = "username is required"
            raise ValueError(msg)
        if not self.password:
            msg = "password is required"
            raise ValueError(msg)
        if self.auth_timeout_hours <= 0:
            msg = "auth_timeout_hours must be positive"
            raise ValueError(msg)
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Self:
        """Build options from ``QNAP_BASE_URL``, ``QNAP_USERNAME``, ``QNAP_PASSWORD``.

        ``QNAP_AUTH_TIMEOUT_HOURS`` is optional and defaults to 1.

        Args:
            environ: Mapping to read instead of ``os.environ``.

        Raises:
            ValueError: naming every missing required variable, or if a value is invalid.
        """
        env = os.environ if environ is None else environ
        missing = [ENV_PREFIX + key for key in _REQUIRED_ENV if not env.get(ENV_PREFIX + key)]
        if missing:
            msg = "missing environment variables: " + ", ".join(missing)
            raise ValueError(msg)
        return cls(
            base_url=env[ENV_PREFIX + "BASE_URL"],
            username=env[ENV_PREFIX + "USERNAME"],
            password=env[ENV_PREFIX + "PASSWORD"],
            auth_timeout_hours=float(env.get(ENV_PREFIX + "AUTH_TIMEOUT_HOURS", "1")),
        )
