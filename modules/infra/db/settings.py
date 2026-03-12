from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from modules.core.secrets import get_secret

DEFAULT_SQLITE_DB_PATH = Path("data/processed/database/carbon_footprint.sqlite")
_VALID_BACKENDS = {"sqlite", "postgres"}
_POSTGRES_BACKEND = "postgres"
_DEFAULT_POSTGRES_PORT = 5432
_DEFAULT_POSTGRES_NAME = "postgres"
_DEFAULT_POSTGRES_USER = "postgres"
_DEFAULT_POSTGRES_SSLMODE = "require"


def _clean_secret(name: str) -> Optional[str]:
    value = get_secret(name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _default_backend() -> str:
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
    user_text = quote(str(user), safe="")
    password_text = quote(str(password), safe="")
    return f"postgresql://{user_text}:{password_text}@{host}:{port}/{name}?sslmode={sslmode}"


def _default_postgres_host(*, project_ref: str | None, port: int) -> str | None:
    if not project_ref:
        return None
    if port == 6543:
        raise RuntimeError(
            "SUPABASE_DB_PORT=6543 cannot be derived from SUPABASE_PROJECT_REF alone. "
            "Use SUPABASE_DB_PORT=5432 for the direct host, or set SUPABASE_DB_HOST explicitly for a pooler host."
        )
    return f"db.{project_ref}.supabase.co"


def _default_postgres_user(*, project_ref: str | None, port: int) -> str:
    if port == 6543 and project_ref:
        return f"postgres.{project_ref}"
    return _DEFAULT_POSTGRES_USER


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
    project_ref = _clean_secret("SUPABASE_PROJECT_REF")
    port_text = _clean_secret("SUPABASE_DB_PORT") or str(_DEFAULT_POSTGRES_PORT)
    name = _clean_secret("SUPABASE_DB_NAME") or _DEFAULT_POSTGRES_NAME
    password = _clean_secret("SUPABASE_DB_PASSWORD")
    sslmode = _clean_secret("SUPABASE_DB_SSLMODE") or _DEFAULT_POSTGRES_SSLMODE

    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError(f"Invalid SUPABASE_DB_PORT: {port_text}") from exc

    host = _clean_secret("SUPABASE_DB_HOST")
    user = _clean_secret("SUPABASE_DB_USER")
    postgres_dsn = None
    if backend == _POSTGRES_BACKEND:
        host = host or _default_postgres_host(project_ref=project_ref, port=port)
        user = user or _default_postgres_user(project_ref=project_ref, port=port)

    if backend == _POSTGRES_BACKEND and all((host, name, user, password)):
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
