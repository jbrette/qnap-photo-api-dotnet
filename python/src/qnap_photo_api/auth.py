"""NAS session authentication as an ``httpx.Auth`` (equivalent of the C# ``AuthenticationHandler``).

On the first request (and after ``auth_timeout_hours``) it POSTs to ``/cgi-bin/authLogin.cgi``,
reads ``authSid`` from the XML reply and sends it as the ``NAS_SID`` cookie. Any request made
through an ``httpx`` client configured with this auth, including image streaming, is authenticated.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, override
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    from .config import QnapApiOptions

AUTH_COOKIE_NAME = "NAS_SID"
LOGIN_PATH = "/cgi-bin/authLogin.cgi"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoginResponse:
    """Parsed ``authLogin.cgi`` reply."""

    auth_passed: bool
    sid: str | None = None
    username: str | None = None
    is_media_ready: bool = False
    is_booting: bool = False

    @classmethod
    def from_xml(cls, text: str) -> Self | None:
        """Parse a ``QDocRoot`` reply; return None for anything else.

        Parsing is hardened (``defusedxml``): entity expansion and external
        references are refused rather than resolved.
        """
        try:
            root = fromstring(text)
        except ParseError, DefusedXmlException:
            return None
        if root.tag != "QDocRoot":
            return None

        def field(name: str) -> str | None:
            element = root.find(name)
            if element is None or element.text is None:
                return None
            return element.text.strip()

        def flag(name: str) -> bool:
            return (field(name) or "").lower() in {"1", "true"}

        return cls(
            auth_passed=flag("authPassed"),
            sid=field("authSid"),
            username=field("username"),
            is_media_ready=flag("mediaReady"),
            is_booting=flag("is_booting"),
        )


class QnapAuth(httpx.Auth):
    """Logs in once, caches the session, and adds the ``NAS_SID`` cookie to every request."""

    def __init__(
        self,
        options: QnapApiOptions,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create the auth for one NAS.

        Args:
            options: NAS connection settings.
            clock: Monotonic clock in seconds; injectable for tests.
        """
        self._options = options
        self._clock = clock
        self._sid: str | None = None
        self._expires_at = 0.0
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def invalidate(self) -> None:
        """Drop the cached session so the next request logs in again."""
        self._sid = None
        self._expires_at = 0.0

    def _cached_sid(self) -> str | None:
        if self._sid is not None and self._clock() < self._expires_at:
            return self._sid
        return None

    def _login_request(self) -> httpx.Request:
        password = base64.b64encode(self._options.password.encode()).decode("ascii")
        return httpx.Request(
            "POST",
            self._options.base_url + LOGIN_PATH,
            data={"user": self._options.username, "pwd": password},
        )

    def _store_login(self, response: httpx.Response) -> str | None:
        login = LoginResponse.from_xml(response.text)
        if login is None:
            logger.warning(
                "Could not parse QNAP login response; requests will be sent unauthenticated"
            )
            return None
        if not login.auth_passed or not login.sid:
            logger.warning("Login to QNAP NAS failed; check username and password")
            return None
        # Only successful logins are cached, so a failure is retried on the next request.
        self._sid = login.sid
        self._expires_at = self._clock() + self._options.auth_timeout_hours * 3600
        return login.sid

    @staticmethod
    def _apply(request: httpx.Request, sid: str | None) -> None:
        if sid:
            request.headers["Cookie"] = f"{AUTH_COOKIE_NAME}={sid}"

    @override
    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        """Authenticate a request from a synchronous ``httpx.Client``."""
        with self._sync_lock:
            sid = self._cached_sid()
            if sid is None:
                login_response = yield self._login_request()
                login_response.read()
                sid = self._store_login(login_response)
        self._apply(request, sid)
        yield request

    @override
    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """Authenticate a request from an ``httpx.AsyncClient``.

        The lock stops concurrent requests from each logging in.
        """
        async with self._async_lock:
            sid = self._cached_sid()
            if sid is None:
                login_response = yield self._login_request()
                await login_response.aread()
                sid = self._store_login(login_response)
        self._apply(request, sid)
        yield request
