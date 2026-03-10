# modules/infra/db/core.py
# -*- coding: utf-8 -*-

"""
Core database infrastructure.
=============================

Handles:
- Database backend selection (Supabase Postgres in the main runtime, with
  legacy SQLite kept only for tests and maintenance tools).
- Connection lifecycle and transaction management.
- Low-level type conversions.
- Safe identifier validation and schema introspection helpers.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Optional

# Path Bootstrap: Add repo root to sys.path so we can import 'modules.*'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.db.settings import DEFAULT_SQLITE_DB_PATH, DatabaseSettings, load_database_settings
from modules.infra.log_manager import get_logger

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency until postgres backend is enabled
    psycopg = None  # type: ignore[assignment]

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = DEFAULT_SQLITE_DB_PATH
_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SCHEMA_READY: set[tuple[str, str, str]] = set()


class DBConnection:
    """Small wrapper that exposes a consistent API across SQLite and Postgres."""

    def __init__(self, raw: Any, *, backend: str, target: str) -> None:
        self._raw = raw
        self.backend = backend
        self.target = target

    def _adapt_sql(self, sql: str) -> str:
        if self.backend == "postgres":
            return sql.replace("?", "%s")
        return sql

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> Any:
        statement = self._adapt_sql(sql)
        if params is None:
            return self._raw.execute(statement)
        return self._raw.execute(statement, tuple(params))

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> Any:
        statement = self._adapt_sql(sql)
        rows = [tuple(row) for row in seq_of_params]
        return self._raw.executemany(statement, rows)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def cursor(self) -> Any:
        return self._raw.cursor()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)


# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────

def to_float(v: Any) -> Optional[float]:
    """Safely coerce to float, returning None for None/Empty strings."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        _log.warning(f"Failed to convert '{v}' to float; returning None.")
        return None


def bool_to_int(v: Optional[bool]) -> Optional[int]:
    """Convert Python bool to portable integer storage (0/1)."""
    return 1 if v else 0 if v is not None else None


def int_to_bool(v: Any) -> Optional[bool]:
    """Convert portable int/bool storage back to Python bool."""
    return bool(v) if v is not None else None


def _ensure_parent(path: Path) -> None:
    if not path.parent.exists():
        _log.debug(f"Creating directory for DB: {path.parent}")
        path.parent.mkdir(parents=True, exist_ok=True)


def _configure_pragmas(conn: sqlite3.Connection) -> None:
    """Apply performance and integrity settings."""
    conn.execute("PRAGMA journal_mode=WAL;")  # Write-Ahead Logging for concurrency
    conn.execute("PRAGMA synchronous=NORMAL;") # Balance speed/safety
    conn.execute("PRAGMA foreign_keys=ON;")    # Enforce constraints
    conn.execute("PRAGMA busy_timeout=5000;")  # Wait 5s before lock error


def safe_table_name(name: str) -> str:
    text = str(name or "").strip()
    if not _VALID_IDENTIFIER_RE.fullmatch(text):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return text


def current_timestamp_sql() -> str:
    return "CURRENT_TIMESTAMP"


def schema_is_ready(conn: DBConnection, namespace: str, table_name: str) -> bool:
    table = safe_table_name(table_name)
    return (conn.backend, conn.target, f"{namespace}:{table}") in _SCHEMA_READY


def mark_schema_ready(conn: DBConnection, namespace: str, table_name: str) -> None:
    table = safe_table_name(table_name)
    _SCHEMA_READY.add((conn.backend, conn.target, f"{namespace}:{table}"))


def _default_path_aliases() -> set[str]:
    default_path = str(DEFAULT_DB_PATH)
    return {default_path, str(Path(default_path)), ""}


def _resolve_settings(db_path: Path | str | None = None, *, backend: Optional[str] = None) -> DatabaseSettings:
    settings = load_database_settings(backend_override=backend)
    if settings.backend == "sqlite":
        explicit = "" if db_path is None else str(db_path).strip()
        if explicit and explicit not in _default_path_aliases():
            return DatabaseSettings(
                backend="sqlite",
                sqlite_path=Path(explicit),
                postgres_dsn=settings.postgres_dsn,
                host=settings.host,
                port=settings.port,
                name=settings.name,
                user=settings.user,
                password=settings.password,
                sslmode=settings.sslmode,
            )
    elif db_path not in (None, "", DEFAULT_DB_PATH, str(DEFAULT_DB_PATH)):
        _log.debug("Ignoring explicit db_path because backend=%s target=%s", settings.backend, settings.display_target)
    return settings


def connection_target_summary(db_path: Path | str | None = None, *, backend: Optional[str] = None) -> str:
    return _resolve_settings(db_path, backend=backend).display_target


def table_exists(conn: DBConnection, table_name: str) -> bool:
    table = safe_table_name(table_name)
    if conn.backend == "postgres":
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = ?
            LIMIT 1
            """,
            (table,),
        ).fetchone()
        return bool(row)

    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table,),
    ).fetchone()
    return bool(row)


def table_columns(conn: DBConnection, table_name: str) -> set[str]:
    table = safe_table_name(table_name)
    if not table_exists(conn, table):
        return set()

    if conn.backend == "postgres":
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table,),
        ).fetchall()
        return {str(row[0]) for row in rows}

    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def list_tables(conn: DBConnection) -> list[str]:
    if conn.backend == "postgres":
        rows = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()
        return [str(row[0]) for row in rows]

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


# ────────────────────────────────────────────────────────────────────────────────
# Connection Managers
# ────────────────────────────────────────────────────────────────────────────────

def connect(db_path: Path | str | None = DEFAULT_DB_PATH, *, backend: Optional[str] = None) -> DBConnection:
    """Open a backend-aware database connection."""
    settings = _resolve_settings(db_path, backend=backend)

    if settings.backend == "postgres":
        if psycopg is None:
            raise RuntimeError("Postgres backend requested but psycopg is not installed.")
        if not settings.postgres_dsn:
            raise RuntimeError(
                "Supabase Postgres is required for the main runtime. "
                "Set SUPABASE_DB_URL or the SUPABASE_DB_HOST/SUPABASE_DB_NAME/"
                "SUPABASE_DB_USER/SUPABASE_DB_PASSWORD secrets."
            )
        _log.debug("Connecting to Postgres: %s", settings.display_target)
        raw = psycopg.connect(str(settings.postgres_dsn), connect_timeout=10)
        return DBConnection(raw, backend="postgres", target=settings.display_target)

    path = Path(settings.sqlite_path)
    _ensure_parent(path)
    _log.debug("Connecting to SQLite: %s", path)
    raw = sqlite3.connect(str(path))
    _configure_pragmas(raw)
    return DBConnection(raw, backend="sqlite", target=str(path))


@contextmanager
def db_session(
    db_path: Path | str | None = DEFAULT_DB_PATH,
    *,
    backend: Optional[str] = None,
) -> Generator[DBConnection, None, None]:
    """
    Transactional context manager.
    
    Automatically commits on success, rolls back on exception, and closes connection.
    
    Usage
    -----
    with db_session() as conn:
        conn.execute(...)
    """
    conn = connect(db_path, backend=backend)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        _log.error(f"DB Transaction Error: {e} -> Rolling back.")
        conn.rollback()
        raise
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("--- Core DB Smoke Test ---")
    with db_session("smoke_test.db", backend="sqlite") as c:
        c.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        c.execute("INSERT INTO test DEFAULT VALUES")
        print("Inserted row.")
    
    # Cleanup
    Path("smoke_test.db").unlink(missing_ok=True)
    print("--- Done ---")
