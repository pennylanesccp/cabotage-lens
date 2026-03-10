#!/usr/bin/env python3
# scripts/normalize_sqlite_place_names.py
# -*- coding: utf-8 -*-

"""
One-shot SQLite maintenance script.

Normalizes place-name text to ASCII across known analytics/cache tables and
removes duplicates created by accent variants.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.addressing.text import ascii_place_text
from modules.infra.database_manager import DEFAULT_DB_PATH
from modules.infra.log_manager import get_logger, init_logging
from modules.infra.db.road_cache import normalize_profile
from modules.multimodal.scenario_keys import build_bulk_scenario_key, normalize_bulk_place_input

_log = get_logger("normalize_sqlite_place_names")

_PLACE_COLUMNS = ("origin_name", "destiny_name", "input_origin", "input_destiny")
_BULK_SCENARIO_FIELDS = (
    "input_origin",
    "input_destiny",
    "cargo_t",
    "truck_key",
    "ors_profile",
    "vessel_class",
    "include_hoteling",
    "hoteling_hours_per_call",
    "port_calls",
    "include_port_ops",
    "port_moves_per_call",
    "cargo_teu",
    "t_per_teu_default",
    "allocation_mode",
    "allocation_load_factor",
    "full_call_mode",
    "port_ops_scenario",
)


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _backup_database(db_path: Path, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_path)
    _log.info("SQLite backup created: %s", backup_path)


def _list_target_tables(conn: sqlite3.Connection, selected: Iterable[str] | None = None) -> list[str]:
    selected_set = {str(name).strip() for name in (selected or []) if str(name).strip()}
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    tables = [str(row[0]) for row in rows]
    if not selected_set:
        return tables
    return [table for table in tables if table in selected_set]


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({_quote_ident(table_name)})").fetchall()
    return [str(row[1]) for row in rows]


def _row_sort_key(row: Dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row.get("updated_timestamp") or ""),
        str(row.get("insertion_timestamp") or ""),
        int(row.get("__rowid__") or 0),
    )


def _detect_strategy(columns: set[str]) -> str:
    if {"origin_name", "destiny_name", "profile_requested"}.issubset(columns):
        return "routes"
    if {"scenario_key", "input_origin", "input_destiny", "truck_key", "ors_profile", "cargo_t"}.issubset(columns):
        return "bulk"
    if {"origin_name", "destiny_name", "cargo_t"}.issubset(columns):
        return "multimodal"
    if any(column in columns for column in _PLACE_COLUMNS):
        return "generic"
    return "skip"


def _row_value(row: Dict[str, Any], normalized: Dict[str, Any], column: str) -> Any:
    return normalized[column] if column in normalized else row.get(column)


def _normalize_row(row: Dict[str, Any], columns: set[str], strategy: str) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}

    for column in _PLACE_COLUMNS:
        if column not in columns:
            continue
        raw_value = row.get(column)
        if raw_value is None:
            continue
        new_value = (
            normalize_bulk_place_input(raw_value)
            if column in {"input_origin", "input_destiny"}
            else ascii_place_text(raw_value)
        )
        if new_value != raw_value:
            normalized[column] = new_value

    if strategy == "routes" and "profile_requested" in columns:
        raw_profile = row.get("profile_requested")
        new_profile = normalize_profile(None if raw_profile is None else str(raw_profile))
        if new_profile != raw_profile:
            normalized["profile_requested"] = new_profile

    if strategy == "bulk":
        payload = {
            field: _row_value(row, normalized, field)
            for field in _BULK_SCENARIO_FIELDS
            if field in columns
        }
        new_scenario_key = build_bulk_scenario_key(payload)
        if new_scenario_key != row.get("scenario_key"):
            normalized["scenario_key"] = new_scenario_key

    return normalized


def _dedupe_key(row: Dict[str, Any], normalized: Dict[str, Any], strategy: str) -> tuple[Any, ...] | None:
    if strategy == "routes":
        return (
            "routes",
            _row_value(row, normalized, "origin_name"),
            _row_value(row, normalized, "destiny_name"),
            normalize_profile(_row_value(row, normalized, "profile_requested")),
        )

    if strategy == "bulk":
        return ("bulk", _row_value(row, normalized, "scenario_key"))

    if strategy == "multimodal":
        return ("multimodal", _row_value(row, normalized, "destiny_name"))

    return None


def _delete_rows(conn: sqlite3.Connection, table_name: str, rowids: list[int]) -> None:
    if not rowids:
        return
    sql = f"DELETE FROM {_quote_ident(table_name)} WHERE rowid = ?"
    conn.executemany(sql, [(int(rowid),) for rowid in rowids])


def _update_rows(conn: sqlite3.Connection, table_name: str, updates: dict[int, Dict[str, Any]]) -> None:
    for rowid, changed in updates.items():
        set_clause = ", ".join(f"{_quote_ident(column)} = ?" for column in changed.keys())
        sql = f"UPDATE {_quote_ident(table_name)} SET {set_clause} WHERE rowid = ?"
        params = [changed[column] for column in changed.keys()]
        params.append(int(rowid))
        conn.execute(sql, params)


def process_table(conn: sqlite3.Connection, table_name: str, *, dry_run: bool) -> Dict[str, Any]:
    columns = set(_table_columns(conn, table_name))
    strategy = _detect_strategy(columns)
    if strategy == "skip":
        return {
            "table": table_name,
            "strategy": strategy,
            "rows": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": True,
        }

    try:
        rows = [dict(row) for row in conn.execute(f"SELECT rowid AS __rowid__, * FROM {_quote_ident(table_name)}")]
    except sqlite3.OperationalError as exc:
        _log.warning("Skipping table without rowid access: %s (%s)", table_name, exc)
        return {
            "table": table_name,
            "strategy": "skip",
            "rows": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": True,
        }

    rows.sort(key=_row_sort_key, reverse=True)

    seen_keys: dict[tuple[Any, ...], int] = {}
    rowids_to_delete: list[int] = []
    updates_by_rowid: dict[int, Dict[str, Any]] = {}

    for row in rows:
        rowid = int(row["__rowid__"])
        normalized = _normalize_row(row, columns, strategy)
        dedupe_key = _dedupe_key(row, normalized, strategy)

        if dedupe_key is not None and dedupe_key in seen_keys:
            rowids_to_delete.append(rowid)
            continue

        if dedupe_key is not None:
            seen_keys[dedupe_key] = rowid

        if normalized:
            updates_by_rowid[rowid] = normalized

    if not dry_run:
        _delete_rows(conn, table_name, rowids_to_delete)
        _update_rows(conn, table_name, updates_by_rowid)

    return {
        "table": table_name,
        "strategy": strategy,
        "rows": len(rows),
        "updated": len(updates_by_rowid),
        "deleted": len(rowids_to_delete),
        "skipped": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize accented place names in SQLite and remove duplicates.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Target SQLite database path")
    parser.add_argument("--table", action="append", dest="tables", help="Optional specific table(s) to process")
    parser.add_argument("--dry-run", action="store_true", help="Inspect changes without modifying the database")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating a backup copy before modifying the DB")
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()
    init_logging(level=args.log_level)

    db_path = Path(args.db_path).resolve()
    if not db_path.exists():
        _log.critical("Database file not found: %s", db_path)
        return 1

    if not args.dry_run and not args.no_backup:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_name(f"{db_path.stem}.backup-{stamp}{db_path.suffix}")
        _backup_database(db_path, backup_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        tables = _list_target_tables(conn, args.tables)
        if not tables:
            _log.warning("No matching tables found.")
            return 0

        _log.info("Processing %d table(s) in %s", len(tables), db_path)

        total_rows = 0
        total_updates = 0
        total_deleted = 0
        processed = 0

        for table_name in tables:
            stats = process_table(conn, table_name, dry_run=bool(args.dry_run))
            if stats["skipped"]:
                continue
            processed += 1
            total_rows += int(stats["rows"])
            total_updates += int(stats["updated"])
            total_deleted += int(stats["deleted"])
            _log.info(
                "Table %s: strategy=%s rows=%d updated=%d deleted=%d",
                stats["table"],
                stats["strategy"],
                stats["rows"],
                stats["updated"],
                stats["deleted"],
            )

        if args.dry_run:
            conn.rollback()
            _log.info(
                "Dry run complete. tables=%d rows=%d updates=%d duplicates=%d",
                processed,
                total_rows,
                total_updates,
                total_deleted,
            )
        else:
            conn.commit()
            _log.info(
                "Normalization complete. tables=%d rows=%d updates=%d duplicates_removed=%d",
                processed,
                total_rows,
                total_updates,
                total_deleted,
            )

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
