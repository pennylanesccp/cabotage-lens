from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from modules.core.secrets import get_secret

DEFAULT_SQLITE_DB_PATH = Path("data/processed/database/carbon_footprint.sqlite")
_VALID_BACKENDS = {"sqlite", "postgres"}
_POSTGRES_BACKEND = "postgres"


def _clean_secret(name: str) -> Optional[str]:
    value = get_secret(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _default_backend() -> str:
    explicit = (_clean_secret("CARBON_DB_BACKEND") or "").lower()
    if explicit == "sqlite":
        raise RuntimeError(
            "SQLite is no longer supported in the main runtime. "
            "Remove CARBON_DB_BACKEND=sqlite and configure Supabase Postgres secrets instead."
        )
    if explicit == _POSTGRES_BACKEND:
        return _POSTGRES_BACKEND
    return _POSTGRES_BACKEND


def _build_postgres_dsn(
    *,
    host: str,
    port: int,
    name: str,
    user: str,
    password: str,
    sslmode: str,
) -> str:
    return f"postgresql://{user}:{password}@{host}:{port}/{name}?sslmode={sslmode}"


@dataclass(frozen=True)
class DatabaseSettings:
    backend: str
    sqlite_path: Optional[Path]
    postgres_dsn: Optional[str]
    host: Optional[str]
    port: int
    name: Optional[str]
    user: Optional[str]
    password: Optional[str]
    sslmode: str

    @property
    def is_postgres(self) -> bool:
        return self.backend == "postgres"

    @property
    def display_target(self) -> str:
        if self.is_postgres:
            if self.host and self.name and self.user:
                return f"postgresql://{self.user}:***@{self.host}:{self.port}/{self.name}?sslmode={self.sslmode}"
            return "postgresql://***"
        return str(self.sqlite_path or DEFAULT_SQLITE_DB_PATH)


def load_database_settings(*, backend_override: Optional[str] = None) -> DatabaseSettings:
    backend = str(backend_override).strip().lower() if backend_override is not None else _default_backend()
    if backend not in _VALID_BACKENDS:
        raise ValueError(f"Unsupported database backend: {backend}")

    sqlite_path = Path(_clean_secret("CARBON_DB_PATH") or DEFAULT_SQLITE_DB_PATH) if backend == "sqlite" else None
    dsn = _clean_secret("SUPABASE_DB_URL") or _clean_secret("DATABASE_URL")

    host = _clean_secret("SUPABASE_DB_HOST")
    port_text = _clean_secret("SUPABASE_DB_PORT") or "5432"
    name = _clean_secret("SUPABASE_DB_NAME") or "postgres"
    user = _clean_secret("SUPABASE_DB_USER") or "postgres"
    password = _clean_secret("SUPABASE_DB_PASSWORD")
    sslmode = _clean_secret("SUPABASE_DB_SSLMODE") or "require"

    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError(f"Invalid SUPABASE_DB_PORT: {port_text}") from exc

    postgres_dsn = dsn
    if backend == _POSTGRES_BACKEND and not postgres_dsn and all((host, name, user, password)):
        postgres_dsn = _build_postgres_dsn(
            host=str(host),
            port=port,
            name=str(name),
            user=str(user),
            password=str(password),
            sslmode=sslmode,
        )

    return DatabaseSettings(
        backend=backend,
        sqlite_path=sqlite_path,
        postgres_dsn=postgres_dsn,
        host=host,
        port=port,
        name=name,
        user=user,
        password=password,
        sslmode=sslmode,
    )
