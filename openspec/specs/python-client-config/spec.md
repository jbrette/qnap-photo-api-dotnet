# python-client-config Specification

## Summary

The Python port is configured by one immutable `QnapApiOptions` value: the NAS base URL, the NAS username and password, and how long a login session is trusted (`auth_timeout_hours`). Construction validates every field and normalises the base URL, so an invalid configuration fails when the client is built rather than on the first NAS call. `QnapApiOptions.from_env` builds the same value from the `QNAP_*` environment variables and names every missing variable at once. This is the Python counterpart of the C# `QnapApi` configuration section.

## Purpose

Defining which connection settings the Python client needs, how they are validated, and how they are read from the environment.

## Requirements

### Requirement: Options are validated at construction

`QnapApiOptions` SHALL raise `ValueError` at construction when `base_url` is not an absolute `http` or `https` URL with a host, when `username` or `password` is empty, or when `auth_timeout_hours` is zero or negative. `auth_timeout_hours` SHALL default to 1 hour. The value SHALL be immutable once constructed.

#### Scenario: relative base URL is rejected

- **WHEN** `QnapApiOptions(base_url="nas", username="u", password="p")` is constructed
- **THEN** a `ValueError` is raised naming `base_url`

#### Scenario: empty password is rejected

- **WHEN** `QnapApiOptions` is constructed with `password=""`
- **THEN** a `ValueError` is raised

#### Scenario: default session lifetime

- **WHEN** `QnapApiOptions` is constructed without `auth_timeout_hours`
- **THEN** `auth_timeout_hours` is `1.0`

### Requirement: Base URL is normalised

`QnapApiOptions` SHALL strip trailing `/` characters from `base_url`, so that joining it with an absolute NAS path never produces `//`.

#### Scenario: trailing slash removed

- **WHEN** `QnapApiOptions` is constructed with `base_url="http://nas/"`
- **THEN** `options.base_url` is `"http://nas"`

### Requirement: Options can be read from the environment

`QnapApiOptions.from_env` SHALL read `QNAP_BASE_URL`, `QNAP_USERNAME`, `QNAP_PASSWORD`, and optionally `QNAP_AUTH_TIMEOUT_HOURS` (parsed as a float, default `1`). It SHALL read `os.environ` unless a mapping is passed. When any of the three required variables is missing or empty, it SHALL raise one `ValueError` listing every missing variable. The values it reads SHALL go through the same validation as direct construction.

#### Scenario: all variables present

- **WHEN** `from_env` is called with `QNAP_BASE_URL=http://nas/`, `QNAP_USERNAME=u`, `QNAP_PASSWORD=p` and `QNAP_AUTH_TIMEOUT_HOURS=2`
- **THEN** it returns options with base URL `http://nas` and a session lifetime of 2 hours

#### Scenario: missing variables are all reported

- **WHEN** `from_env` is called with only `QNAP_BASE_URL` set
- **THEN** a `ValueError` is raised that names both `QNAP_USERNAME` and `QNAP_PASSWORD`
