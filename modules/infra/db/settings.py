from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlsplit, urlunsplit

from modules.core.secrets import get_secret

_DEFAULT_DB_SECRET = "SUPABASE_DB_URL"
_VALID_SCHEMES = {"postgres", "postgresql"}


def _clean_secret(name: str) -> Optional[str]:
    value = get_secret(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def load_database_settings(*, database_url_override: Optional[str] = None) -> DatabaseSettings:
    dsn = str(database_url_override or _clean_secret(_DEFAULT_DB_SECRET) or "").strip()
    return database_settings_from_dsn(dsn)
