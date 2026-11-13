# python-nas-auth Specification

## Summary

NAS authentication is implemented by `QnapAuth`, an `httpx.Auth` attached to the client's HTTP pipeline, so every request through that client is authenticated, including image streaming. When no valid session is cached, the first request triggers a form POST to `/cgi-bin/authLogin.cgi`. The `authSid` from the XML reply is cached for `auth_timeout_hours` and sent as the `NAS_SID` cookie. A failed or unreadable login is logged and never cached: the request goes out without the cookie, and the next request tries again. Concurrent requests share a single login.

## Purpose

Defining how the Python client obtains, caches, attaches and renews the QNAP NAS session, and what happens when login fails.

## Requirements

### Requirement: Login request format

When it needs a session, `QnapAuth` SHALL send `POST {base_url}/cgi-bin/authLogin.cgi` with a form-encoded body. The body SHALL contain `user` (the configured username) and `pwd` (the base64 of the UTF-8 encoded password). The login response body SHALL be read in full before it is parsed.

#### Scenario: first request logs in

- **WHEN** a client with no cached session makes its first request
- **THEN** the NAS receives a POST to `/cgi-bin/authLogin.cgi` with `user=<username>` and `pwd=<base64(password)>` before the original request

### Requirement: Login response parsing

`LoginResponse.from_xml` SHALL parse the XML reply with `defusedxml`, and SHALL return `None` when the text is not well-formed XML, declares entities or external references, or has a root element other than `QDocRoot`. `auth_passed`, `is_media_ready` and `is_booting` SHALL be true only when the element text is `1` or `true`, compared case-insensitively. `sid` SHALL come from `authSid` and `username` from `username`, with surrounding whitespace stripped. CDATA content SHALL be treated as text.

#### Scenario: successful CDATA reply

- **WHEN** the reply is `<QDocRoot><authPassed><![CDATA[1]]></authPassed><authSid><![CDATA[sid123]]></authSid></QDocRoot>`
- **THEN** `auth_passed` is true and `sid` is `"sid123"`

#### Scenario: entity declarations refused

- **WHEN** the reply declares a DTD entity and uses it inside `QDocRoot`
- **THEN** `from_xml` returns `None` and the entity is not expanded

#### Scenario: not a QNAP reply

- **WHEN** the reply is `not xml` or `<Other/>`
- **THEN** `from_xml` returns `None`

### Requirement: Session cookie attached

After a successful login, or when a cached session is still valid, `QnapAuth` SHALL set the request's `Cookie` header to `NAS_SID=<sid>`, replacing any `Cookie` header already on the request.

#### Scenario: authenticated list call

- **WHEN** a list request is sent after a successful login
- **THEN** it carries the header `Cookie: NAS_SID=sid123`

### Requirement: Successful sessions are cached until expiry

A successful login SHALL be cached for `auth_timeout_hours × 3600` seconds, measured by a monotonic clock that can be injected. Requests made within that window SHALL reuse the cached session without logging in again. The first request after the window SHALL log in again. `invalidate()` SHALL drop the cached session.

#### Scenario: reuse within the window

- **WHEN** two list calls are made one after another within the session lifetime
- **THEN** the NAS receives exactly one login

#### Scenario: renewal after expiry

- **WHEN** the clock passes the expiry time (3601 s with a 1-hour lifetime) before the second call
- **THEN** the NAS receives a second login

### Requirement: Failed logins are not cached

When the login reply cannot be parsed, has `authPassed` false, or has no `authSid`, `QnapAuth` SHALL log a warning on the `qnap_photo_api.auth` logger, cache nothing, and send the original request without a `NAS_SID` cookie. The next request SHALL attempt a fresh login.

#### Scenario: wrong credentials

- **WHEN** the NAS answers every login with `authPassed` 0 and two list calls are made
- **THEN** the NAS receives two logins and neither list call carries a `Cookie` header

### Requirement: Concurrent requests share one login

With an async client, `QnapAuth` SHALL hold an `asyncio.Lock` while it checks for a cached session and logs in, so concurrent requests wait for the first login and do not start their own. A synchronous client SHALL get the same guarantee from a `threading.Lock`.

#### Scenario: parallel list calls

- **WHEN** five `list()` calls run concurrently on a client with no session
- **THEN** the NAS receives exactly one login

### Requirement: Authenticated responses are not buffered

`QnapAuth` SHALL NOT read the body of the authenticated request's response, so callers can stream it.

#### Scenario: image streaming through auth

- **WHEN** an image is opened with `stream=True` through the authenticated client
- **THEN** the response body has not been consumed when it is returned to the caller
