"""Connection settings (equivalent of the C# ``QnapApiOptions``)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

ENV_PREFIX = "QNAP_"


@dataclass(frozen=True)
class QnapApiOptions:
    base_url: str
    username: str
    password: str
    auth_timeout_hours: float = 1.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"base_url must be an absolute http(s) URL, got {self.base_url!r}")
        if not self.username:
            raise ValueError("username is required")
        if not self.password:
            raise ValueError("password is required")
        if self.auth_timeout_hours <= 0:
            raise ValueError("auth_timeout_hours must be positive")
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> QnapApiOptions:
        """Read ``QNAP_BASE_URL``, ``QNAP_USERNAME``, ``QNAP_PASSWORD``, ``QNAP_AUTH_TIMEOUT_HOURS``."""
        env = os.environ if environ is None else environ
        missing = [k for k in ("BASE_URL", "USERNAME", "PASSWORD") if not env.get(ENV_PREFIX + k)]
        if missing:
            raise ValueError("missing environment variables: " + ", ".join(ENV_PREFIX + k for k in missing))
        return cls(
            base_url=env[ENV_PREFIX + "BASE_URL"],
            username=env[ENV_PREFIX + "USERNAME"],
            password=env[ENV_PREFIX + "PASSWORD"],
            auth_timeout_hours=float(env.get(ENV_PREFIX + "AUTH_TIMEOUT_HOURS", "1")),
        )
