# modules/infra/db/core.py
# -*- coding: utf-8 -*-

"""
Core SQLite infrastructure.
===========================

Handles:
- Database connection lifecycle.
- Transaction management (context manager).
- Low-level type conversions (Boolean/Float handling).
- PRAGMA configurations for performance/safety.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Optional, Generator

# Path Bootstrap: Add repo root to sys.path so we can import 'modules.*'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

DEFAULT_DB_PATH = Path("data/processed/database/carbon_footprint.sqlite")


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
    """Convert Python bool to SQLite int (0/1)."""
    return 1 if v else 0 if v is not None else None


def int_to_bool(v: Any) -> Optional[bool]:
    """Convert SQLite int back to Python bool."""
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


# ────────────────────────────────────────────────────────────────────────────────
# Connection Managers
# ────────────────────────────────────────────────────────────────────────────────

def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Open a raw SQLite connection.
    """
    path = Path(db_path)
    _ensure_parent(path)
    
    _log.debug(f"Connecting to SQLite: {path}")
    conn = sqlite3.connect(str(path))
    _configure_pragmas(conn)
    return conn


@contextmanager
def db_session(db_path: Path | str = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Transactional context manager.
    
    Automatically commits on success, rolls back on exception, and closes connection.
    
    Usage
    -----
    with db_session() as conn:
        conn.execute(...)
    """
    conn = connect(db_path)
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
    with db_session("smoke_test.db") as c:
        c.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
        c.execute("INSERT INTO test DEFAULT VALUES")
        print("Inserted row.")
    
    # Cleanup
    Path("smoke_test.db").unlink(missing_ok=True)
    print("--- Done ---")