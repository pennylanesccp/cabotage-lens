from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Optional

from modules.infra.db.settings import DatabaseSettings, load_database_settings
from modules.infra.log_manager import get_logger

try:
    import psycopg
except Exception:  # pragma: no cover - dependency is installed in supported environments
    psycopg = None  # type: ignore[assignment]

_log = get_logger(__name__)
_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SCHEMA_READY: set[tuple[str, str, str]] = set()


class DBConnection:
    """Thin wrapper that keeps repository SQL portable within psycopg."""

    def __init__(self, raw: Any, *, target: str, reconnect_dsn: str | None = None) -> None:
        self._raw = raw
        self.backend = "postgres"
        self.target = target
        self._reconnect_dsn = reconnect_dsn

    def _adapt_sql(self, sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> Any:
        statement = self._adapt_sql(sql)
        if params is None:
            return self._raw.execute(statement)
        return self._raw.execute(statement, tuple(params))

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]) -> Any:
        statement = self._adapt_sql(sql)
        rows = [tuple(row) for row in seq_of_params]
        if hasattr(self._raw, "executemany"):
            return self._raw.executemany(statement, rows)
        cursor = self._raw.cursor()
        try:
            cursor.executemany(statement, rows)
        except Exception:
            cursor.close()
            raise
        return cursor

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def cursor(self) -> Any:
        return self._raw.cursor()

    def ping(self) -> None:
        cursor = self._raw.execute("SELECT 1")
        if hasattr(cursor, "fetchone"):
            cursor.fetchone()

    def reconnect(self) -> None:
        if not self._reconnect_dsn:
            raise RuntimeError("This DB connection cannot be reconnected.")
        try:
            self._raw.close()
        except Exception:
            pass
        self._raw = _open_raw_connection(self._reconnect_dsn)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)


def to_float(v: Any) -> Optional[float]:
    """Safely coerce to float, returning None for None/empty strings."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        _log.warning("Failed to convert %r to float; returning None.", v)
        return None


def bool_to_int(v: Optional[bool]) -> Optional[int]:
    return 1 if v else 0 if v is not None else None


def int_to_bool(v: Any) -> Optional[bool]:
    return bool(v) if v is not None else None


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


def _resolve_settings(database_url: str | None = None) -> DatabaseSettings:
    return load_database_settings(database_url_override=database_url)


def connection_target_summary(database_url: str | None = None) -> str:
    return _resolve_settings(database_url).display_target


def table_exists(conn: DBConnection, table_name: str) -> bool:
    table = safe_table_name(table_name)
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


def table_columns(conn: DBConnection, table_name: str) -> set[str]:
    table = safe_table_name(table_name)
    if not table_exists(conn, table):
        return set()

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


def list_tables(conn: DBConnection) -> list[str]:
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


def _open_raw_connection(postgres_dsn: str) -> Any:
    return psycopg.connect(
        postgres_dsn,
        connect_timeout=10,
        prepare_threshold=None,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=3,
    )


def connect(database_url: str | None = None) -> DBConnection:
    """Open a Supabase Postgres connection."""
    settings = _resolve_settings(database_url)
    if psycopg is None:
        raise RuntimeError("Supabase Postgres requires psycopg.")

    _log.debug("Connecting to Postgres: %s", settings.display_target)
    raw = _open_raw_connection(settings.postgres_dsn)
    return DBConnection(raw, target=settings.display_target, reconnect_dsn=settings.postgres_dsn)


@contextmanager
def db_session(database_url: str | None = None) -> Generator[DBConnection, None, None]:
    """Transactional context manager for Supabase Postgres."""
    conn = connect(database_url)
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        _log.error("DB transaction failed: %s -> rolling back.", exc)
        try:
            conn.rollback()
        except Exception as rollback_exc:
            _log.warning("DB rollback failed after transaction error: %s", rollback_exc)
        raise
    finally:
        try:
            conn.close()
        except Exception as close_exc:
            _log.warning("DB connection close failed: %s", close_exc)
