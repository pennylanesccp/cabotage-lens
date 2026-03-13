from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from modules.core.secrets import get_secret

_DEFAULT_DB_SECRET = "SUPABASE_DB_URL"
_DEFAULT_DB_HOST_SECRET = "SUPABASE_DB_HOST"
_DEFAULT_DB_PORT_SECRET = "SUPABASE_DB_PORT"
_DEFAULT_DB_NAME_SECRET = "SUPABASE_DB_NAME"
_DEFAULT_DB_USER_SECRET = "SUPABASE_DB_USER"
_DEFAULT_DB_PASSWORD_SECRET = "SUPABASE_DB_PASSWORD"
_DEFAULT_DB_SSLMODE_SECRET = "SUPABASE_DB_SSLMODE"
_DEFAULT_PROJECT_REF_SECRET = "SUPABASE_PROJECT_REF"
_DEFAULT_DB_PORT = 6543
_DEFAULT_DB_NAME = "postgres"
_DEFAULT_DB_SSLMODE = "require"
_VALID_SCHEMES = {"postgres", "postgresql"}


def _clean_secret(name: str) -> Optional[str]:
    value = get_secret(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_settings_error(*, missing: Optional[list[str]] = None) -> RuntimeError:
    suffix = ""
    if missing:
        suffix = f" Missing: {', '.join(missing)}."
    return RuntimeError(
        "Supabase Postgres requires SUPABASE_DB_URL or split secrets "
        "(SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, SUPABASE_DB_SSLMODE)."
        + suffix
    )


def _mask_postgres_dsn(dsn: str) -> str:
    parsed = urlsplit(dsn)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    auth = ""
    if parsed.username:
        auth = f"{quote(parsed.username, safe='')}:***@"
    return urlunsplit(
        (
            parsed.scheme or "postgresql",
            f"{auth}{host}{port}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


@dataclass(frozen=True)
class DatabaseSettings:
    postgres_dsn: str
    display_target: str
    host: Optional[str]
    port: Optional[int]
    name: Optional[str]
    user: Optional[str]

    @property
    def is_postgres(self) -> bool:
        return True


def build_postgres_dsn_from_parts(
    *,
    host: str,
    port: int,
    name: str,
    user: str,
    password: str,
    sslmode: str = _DEFAULT_DB_SSLMODE,
) -> str:
    host_text = str(host or "").strip()
    name_text = str(name or "").strip()
    user_text = str(user or "").strip()
    password_text = str(password or "").strip()
    sslmode_text = str(sslmode or _DEFAULT_DB_SSLMODE).strip() or _DEFAULT_DB_SSLMODE
    if not host_text or not name_text or not user_text or not password_text:
        missing = []
        if not host_text:
            missing.append(_DEFAULT_DB_HOST_SECRET)
        if not name_text:
            missing.append(_DEFAULT_DB_NAME_SECRET)
        if not user_text:
            missing.append(_DEFAULT_DB_USER_SECRET)
        if not password_text:
            missing.append(_DEFAULT_DB_PASSWORD_SECRET)
        raise _required_settings_error(missing=missing)

    try:
        normalized_port = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{_DEFAULT_DB_PORT_SECRET} must be an integer.") from exc

    auth = f"{quote(user_text, safe='')}:{quote(password_text, safe='')}"
    netloc = f"{auth}@{host_text}:{normalized_port}"
    path = "/" + quote(name_text.lstrip("/"), safe="")
    query = urlencode({"sslmode": sslmode_text})
    return urlunsplit(("postgresql", netloc, path, query, ""))


def database_settings_from_dsn(dsn: str) -> DatabaseSettings:
    candidate = str(dsn or "").strip()
    if not candidate:
        raise RuntimeError(f"Supabase Postgres requires {_DEFAULT_DB_SECRET}.")

    parsed = urlsplit(candidate)
    scheme = str(parsed.scheme or "").strip().lower()
    if scheme not in _VALID_SCHEMES:
        raise ValueError(
            f"{_DEFAULT_DB_SECRET} must be a postgres connection string; got scheme={parsed.scheme or '<missing>'!r}."
        )
    if not parsed.hostname:
        raise ValueError(f"{_DEFAULT_DB_SECRET} must include a hostname.")

    database_name = parsed.path.lstrip("/") or None
    if not database_name:
        raise ValueError(f"{_DEFAULT_DB_SECRET} must include a database name in the path component.")

    return DatabaseSettings(
        postgres_dsn=candidate,
        display_target=_mask_postgres_dsn(candidate),
        host=parsed.hostname,
        port=parsed.port,
        name=database_name,
        user=parsed.username,
    )


def _database_settings_from_split_secrets() -> Optional[DatabaseSettings]:
    host = _clean_secret(_DEFAULT_DB_HOST_SECRET)
    password = _clean_secret(_DEFAULT_DB_PASSWORD_SECRET)
    project_ref = _clean_secret(_DEFAULT_PROJECT_REF_SECRET)
    explicit_user = _clean_secret(_DEFAULT_DB_USER_SECRET)
    explicit_name = _clean_secret(_DEFAULT_DB_NAME_SECRET)
    explicit_sslmode = _clean_secret(_DEFAULT_DB_SSLMODE_SECRET)
    user = explicit_user or (f"postgres.{project_ref}" if project_ref else None)
    port_text = _clean_secret(_DEFAULT_DB_PORT_SECRET)
    name = explicit_name or _DEFAULT_DB_NAME
    sslmode = explicit_sslmode or _DEFAULT_DB_SSLMODE

    provided = [host, password, explicit_user, port_text, explicit_name, explicit_sslmode, project_ref]
    if not any(value is not None for value in provided):
        return None

    missing: list[str] = []
    if host is None:
        missing.append(_DEFAULT_DB_HOST_SECRET)
    if password is None:
        missing.append(_DEFAULT_DB_PASSWORD_SECRET)
    if user is None:
        missing.append(_DEFAULT_DB_USER_SECRET)
        if project_ref is None:
            missing.append(_DEFAULT_PROJECT_REF_SECRET)

    if missing:
        raise _required_settings_error(missing=missing)

    try:
        port = _DEFAULT_DB_PORT if port_text is None else int(port_text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{_DEFAULT_DB_PORT_SECRET} must be an integer.") from exc
    dsn = build_postgres_dsn_from_parts(
        host=host,
        port=port,
        name=name,
        user=user,
        password=password,
        sslmode=sslmode,
    )
    return database_settings_from_dsn(dsn)


def load_database_settings(*, database_url_override: Optional[str] = None) -> DatabaseSettings:
    override = str(database_url_override or "").strip()
    if override:
        return database_settings_from_dsn(override)

    direct_dsn = _clean_secret(_DEFAULT_DB_SECRET)
    if direct_dsn is not None:
        return database_settings_from_dsn(direct_dsn)

    settings = _database_settings_from_split_secrets()
    if settings is not None:
        return settings

    raise _required_settings_error()
