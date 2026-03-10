#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
One-time SQLite to Supabase Postgres migration.

This script inspects the source SQLite schema at runtime, migrates relevant
route-cache and analytical tables, skips duplicates already present in
Supabase, and logs per-table row accounting.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.infra.database_manager import DEFAULT_BULK_RESULTS_TABLE, DEFAULT_DB_PATH, connection_target_summary
from modules.infra.db.bulk_results import ensure_results_table as ensure_bulk_results_table
from modules.infra.db.bulk_results import upsert_result as upsert_bulk_result
from modules.infra.db.core import db_session, safe_table_name
from modules.infra.db.multimodal import ensure_results_table as ensure_multimodal_results_table
from modules.infra.db.multimodal import upsert_result as upsert_multimodal_result
from modules.infra.db.road_cache import DEFAULT_TABLE as DEFAULT_ROUTES_TABLE
from modules.infra.db.road_cache import ensure_main_table, get_run, normalize_profile, upsert_run
from modules.infra.db.settings import load_database_settings
from modules.infra.log_manager import get_logger, init_logging

_log = get_logger("migrate_sqlite_to_supabase")


@dataclass
class MigrationStats:
    found: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_invalid: int = 0
    failed: int = 0


@dataclass(frozen=True)
class SourceTable:
    name: str
    kind: str
    row_count: int
    columns: tuple[str, ...]


def _sqlite_tables(conn: sqlite3.Connection) -> list[str]:
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


def _sqlite_columns(conn: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    table = safe_table_name(table_name)
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return tuple(str(row[1]) for row in rows)


def _sqlite_row_count(conn: sqlite3.Connection, table_name: str) -> int:
    table = safe_table_name(table_name)
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _is_route_table(columns: set[str]) -> bool:
    required = {"origin_name", "destiny_name", "distance_km"}
    return required.issubset(columns) and ("profile_requested" in columns or "is_hgv" in columns)


def _is_bulk_table(columns: set[str]) -> bool:
    required = {"scenario_key", "input_origin", "input_destiny", "status"}
    return required.issubset(columns)


def _is_analysis_table(columns: set[str]) -> bool:
    required = {"origin_name", "destiny_name", "cargo_t", "delta_cost_r"}
    return required.issubset(columns) and "scenario_key" not in columns and "distance_km" not in columns


def _classify_table(name: str, columns: tuple[str, ...]) -> str:
    column_set = set(columns)
    if name == "http_cache":
        return "http_cache"
    if _is_bulk_table(column_set) or name == DEFAULT_BULK_RESULTS_TABLE:
        return "bulk"
    if _is_route_table(column_set) or name in {"routes", "heatmap_runs"}:
        return "routes"
    if _is_analysis_table(column_set):
        return "analysis"
    return "skip"


def inspect_source_tables(conn: sqlite3.Connection, selected: Optional[Iterable[str]] = None) -> list[SourceTable]:
    selected_set = {safe_table_name(name) for name in selected or []}
    tables: list[SourceTable] = []
    for name in _sqlite_tables(conn):
        if selected_set and name not in selected_set:
            continue
        columns = _sqlite_columns(conn, name)
        row_count = _sqlite_row_count(conn, name)
        kind = _classify_table(name, columns)
        tables.append(SourceTable(name=name, kind=kind, row_count=row_count, columns=columns))
    return tables


def _row_value(row: sqlite3.Row, columns: set[str], key: str, default: Any = None) -> Any:
    if key not in columns:
        return default
    value = row[key]
    return default if value == "" else value


def _table_exists_row(conn: Any, table_name: str, where_col: str, where_value: Any) -> bool:
    table = safe_table_name(table_name)
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE {where_col} = ? LIMIT 1",
        (where_value,),
    ).fetchone()
    return bool(row)


def _open_savepoint(conn: Any, name: str) -> None:
    conn.execute(f"SAVEPOINT {name}")


def _rollback_savepoint(conn: Any, name: str) -> None:
    conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
    conn.execute(f"RELEASE SAVEPOINT {name}")


def _release_savepoint(conn: Any, name: str) -> None:
    conn.execute(f"RELEASE SAVEPOINT {name}")


def migrate_route_cache_table(source_conn: sqlite3.Connection, target_conn: Any, table: SourceTable) -> MigrationStats:
    stats = MigrationStats()
    columns = set(table.columns)
    ensure_main_table(target_conn, DEFAULT_ROUTES_TABLE)
    src_table = safe_table_name(table.name)

    for idx, row in enumerate(source_conn.execute(f"SELECT * FROM {src_table}"), start=1):
        stats.found += 1
        origin_name = str(_row_value(row, columns, "origin_name", "") or "").strip()
        destiny_name = str(_row_value(row, columns, "destiny_name", "") or "").strip()
        distance_km = _row_value(row, columns, "distance_km")
        requested = normalize_profile(_row_value(row, columns, "profile_requested"))
        used = _row_value(row, columns, "profile_used")

        if not origin_name or not destiny_name or distance_km in (None, ""):
            stats.skipped_invalid += 1
            continue

        if get_run(
            target_conn,
            origin=origin_name,
            destiny=destiny_name,
            profile_requested=requested,
            table_name=DEFAULT_ROUTES_TABLE,
        ):
            stats.skipped_existing += 1
            continue

        savepoint = f"route_{idx}"
        _open_savepoint(target_conn, savepoint)
        try:
            upsert_run(
                target_conn,
                origin=origin_name,
                destiny=destiny_name,
                origin_lat=_row_value(row, columns, "origin_lat"),
                origin_lon=_row_value(row, columns, "origin_lon"),
                destiny_lat=_row_value(row, columns, "destiny_lat"),
                destiny_lon=_row_value(row, columns, "destiny_lon"),
                distance_km=distance_km,
                profile_requested=requested,
                profile_used=used,
                lookup_mode=str(_row_value(row, columns, "lookup_mode", "label") or "label"),
                source=str(_row_value(row, columns, "source", "ors") or "ors"),
                is_hgv=bool(_row_value(row, columns, "is_hgv")) if "is_hgv" in columns else None,
                table_name=DEFAULT_ROUTES_TABLE,
            )
            _release_savepoint(target_conn, savepoint)
            stats.inserted += 1
        except Exception as exc:
            _rollback_savepoint(target_conn, savepoint)
            stats.failed += 1
            _log.error("Route row failed from source table %s: %s", table.name, exc)

    return stats


def migrate_bulk_results_table(source_conn: sqlite3.Connection, target_conn: Any, table: SourceTable) -> MigrationStats:
    stats = MigrationStats()
    columns = set(table.columns)
    target_table = safe_table_name(table.name)
    ensure_bulk_results_table(target_conn, target_table)
    src_table = safe_table_name(table.name)

    for idx, row in enumerate(source_conn.execute(f"SELECT * FROM {src_table}"), start=1):
        stats.found += 1
        scenario_key = str(_row_value(row, columns, "scenario_key", "") or "").strip()
        origin_name = str(_row_value(row, columns, "origin_name", "") or "").strip()
        destiny_name = str(_row_value(row, columns, "destiny_name", "") or "").strip()
        input_origin = str(_row_value(row, columns, "input_origin", origin_name) or origin_name).strip()
        input_destiny = str(_row_value(row, columns, "input_destiny", destiny_name) or destiny_name).strip()

        if not scenario_key or not origin_name or not destiny_name:
            stats.skipped_invalid += 1
            continue

        if _table_exists_row(target_conn, target_table, "scenario_key", scenario_key):
            stats.skipped_existing += 1
            continue

        savepoint = f"bulk_{idx}"
        _open_savepoint(target_conn, savepoint)
        try:
            upsert_bulk_result(
                target_conn,
                table_name=target_table,
                scenario_key=scenario_key,
                origin_name=origin_name,
                destiny_name=destiny_name,
                input_origin=input_origin,
                input_destiny=input_destiny,
                cargo_t=float(_row_value(row, columns, "cargo_t", 0.0) or 0.0),
                truck_key=str(_row_value(row, columns, "truck_key", "semi_27t") or "semi_27t"),
                ors_profile=str(_row_value(row, columns, "ors_profile", "driving-hgv") or "driving-hgv"),
                vessel_class=_row_value(row, columns, "vessel_class"),
                include_hoteling=bool(_row_value(row, columns, "include_hoteling", 1)),
                hoteling_hours_per_call=_row_value(row, columns, "hoteling_hours_per_call"),
                port_calls=_row_value(row, columns, "port_calls"),
                include_port_ops=bool(_row_value(row, columns, "include_port_ops", 1)),
                port_moves_per_call=_row_value(row, columns, "port_moves_per_call"),
                cargo_teu=_row_value(row, columns, "cargo_teu"),
                t_per_teu_default=_row_value(row, columns, "t_per_teu_default"),
                allocation_mode=_row_value(row, columns, "allocation_mode"),
                allocation_load_factor=_row_value(row, columns, "allocation_load_factor"),
                full_call_mode=bool(_row_value(row, columns, "full_call_mode", 0)),
                port_ops_scenario=_row_value(row, columns, "port_ops_scenario"),
                status=str(_row_value(row, columns, "status", "ok") or "ok"),
                error_message=_row_value(row, columns, "error_message"),
                geometry_status=_row_value(row, columns, "geometry_status"),
                road_direct_source=_row_value(row, columns, "road_direct_source"),
                first_mile_source=_row_value(row, columns, "first_mile_source"),
                last_mile_source=_row_value(row, columns, "last_mile_source"),
                road_direct_profile_used=_row_value(row, columns, "road_direct_profile_used"),
                first_mile_profile_used=_row_value(row, columns, "first_mile_profile_used"),
                last_mile_profile_used=_row_value(row, columns, "last_mile_profile_used"),
                road_distance_km=_row_value(row, columns, "road_distance_km"),
                road_fuel_liters=_row_value(row, columns, "road_fuel_liters"),
                road_fuel_kg=_row_value(row, columns, "road_fuel_kg"),
                road_fuel_cost_r=_row_value(row, columns, "road_fuel_cost_r"),
                road_co2e_kg=_row_value(row, columns, "road_co2e_kg"),
                mm_road_fuel_liters=_row_value(row, columns, "mm_road_fuel_liters"),
                mm_road_fuel_kg=_row_value(row, columns, "mm_road_fuel_kg"),
                mm_road_fuel_cost_r=_row_value(row, columns, "mm_road_fuel_cost_r"),
                mm_road_co2e_kg=_row_value(row, columns, "mm_road_co2e_kg"),
                sea_km=_row_value(row, columns, "sea_km"),
                sea_fuel_kg=_row_value(row, columns, "sea_fuel_kg"),
                sea_fuel_cost_r=_row_value(row, columns, "sea_fuel_cost_r"),
                sea_co2e_kg=_row_value(row, columns, "sea_co2e_kg"),
                total_fuel_kg=_row_value(row, columns, "total_fuel_kg"),
                total_fuel_cost_r=_row_value(row, columns, "total_fuel_cost_r"),
                total_co2e_kg=_row_value(row, columns, "total_co2e_kg"),
                delta_cost_r=_row_value(row, columns, "delta_cost_r"),
                delta_co2e_kg=_row_value(row, columns, "delta_co2e_kg"),
                savings_pct=_row_value(row, columns, "savings_pct"),
                diesel_price_r_per_l=_row_value(row, columns, "diesel_price_r_per_l"),
                diesel_price_source=_row_value(row, columns, "diesel_price_source"),
                bunker_price_r_per_t=_row_value(row, columns, "bunker_price_r_per_t"),
            )
            _release_savepoint(target_conn, savepoint)
            stats.inserted += 1
        except Exception as exc:
            _rollback_savepoint(target_conn, savepoint)
            stats.failed += 1
            _log.error("Bulk row failed from source table %s scenario_key=%s: %s", table.name, scenario_key, exc)

    return stats


def migrate_analysis_table(source_conn: sqlite3.Connection, target_conn: Any, table: SourceTable) -> MigrationStats:
    stats = MigrationStats()
    columns = set(table.columns)
    target_table = safe_table_name(table.name)
    ensure_multimodal_results_table(target_conn, target_table)
    src_table = safe_table_name(table.name)

    for idx, row in enumerate(source_conn.execute(f"SELECT * FROM {src_table}"), start=1):
        stats.found += 1
        origin_name = str(_row_value(row, columns, "origin_name", "") or "").strip()
        destiny_name = str(_row_value(row, columns, "destiny_name", "") or "").strip()
        cargo_t = _row_value(row, columns, "cargo_t")

        if not origin_name or not destiny_name or cargo_t in (None, ""):
            stats.skipped_invalid += 1
            continue

        if _table_exists_row(target_conn, target_table, "destiny_name", destiny_name):
            stats.skipped_existing += 1
            continue

        savepoint = f"analysis_{idx}"
        _open_savepoint(target_conn, savepoint)
        try:
            upsert_multimodal_result(
                target_conn,
                target_table,
                origin_name=origin_name,
                destiny_name=destiny_name,
                cargo_t=float(cargo_t or 0.0),
                road_distance_km=_row_value(row, columns, "road_distance_km"),
                road_fuel_liters=_row_value(row, columns, "road_fuel_liters"),
                road_fuel_kg=_row_value(row, columns, "road_fuel_kg"),
                road_fuel_cost_r=_row_value(row, columns, "road_fuel_cost_r"),
                road_co2e_kg=_row_value(row, columns, "road_co2e_kg"),
                mm_road_fuel_liters=_row_value(row, columns, "mm_road_fuel_liters"),
                mm_road_fuel_kg=_row_value(row, columns, "mm_road_fuel_kg"),
                mm_road_fuel_cost_r=_row_value(row, columns, "mm_road_fuel_cost_r"),
                mm_road_co2e_kg=_row_value(row, columns, "mm_road_co2e_kg"),
                sea_km=_row_value(row, columns, "sea_km"),
                sea_fuel_kg=_row_value(row, columns, "sea_fuel_kg"),
                sea_fuel_cost_r=_row_value(row, columns, "sea_fuel_cost_r"),
                sea_co2e_kg=_row_value(row, columns, "sea_co2e_kg"),
                total_fuel_kg=_row_value(row, columns, "total_fuel_kg"),
                total_fuel_cost_r=_row_value(row, columns, "total_fuel_cost_r"),
                total_co2e_kg=_row_value(row, columns, "total_co2e_kg"),
                delta_cost_r=_row_value(row, columns, "delta_cost_r"),
                delta_co2e_kg=_row_value(row, columns, "delta_co2e_kg"),
            )
            _release_savepoint(target_conn, savepoint)
            stats.inserted += 1
        except Exception as exc:
            _rollback_savepoint(target_conn, savepoint)
            stats.failed += 1
            _log.error("Analysis row failed from source table %s destiny=%s: %s", table.name, destiny_name, exc)

    return stats


def _log_inspection(tables: list[SourceTable]) -> None:
    if not tables:
        _log.warning("No source tables matched the requested scope.")
        return
    for table in tables:
        _log.info(
            "SQLite table detected: name=%s kind=%s rows=%d columns=%s",
            table.name,
            table.kind,
            table.row_count,
            ", ".join(table.columns),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate local SQLite persistence into Supabase Postgres.")
    parser.add_argument("--sqlite-path", type=Path, default=DEFAULT_DB_PATH, help="Source SQLite database path")
    parser.add_argument("--table", action="append", default=None, help="Optional specific source table to migrate")
    parser.add_argument(
        "--include-analysis-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also migrate legacy single-run analytical result tables when detected.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Inspect and classify source tables without writing to Supabase")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    init_logging(level=args.log_level, write_to_file=False)

    source_path = Path(args.sqlite_path).expanduser().resolve()
    if not source_path.exists():
        _log.critical("Source SQLite database not found: %s", source_path)
        return 1

    target_settings = load_database_settings(backend_override="postgres")
    _log.info("Target backend: %s", target_settings.display_target)
    _log.info("Source SQLite path: %s", source_path)
    _log.info("Target connection summary: %s", connection_target_summary(backend="postgres"))

    source_conn = sqlite3.connect(str(source_path))
    source_conn.row_factory = sqlite3.Row
    try:
        tables = inspect_source_tables(source_conn, selected=args.table)
        _log_inspection(tables)
        if args.dry_run:
            _log.info("Dry run complete. No rows were written.")
            return 0

        overall: dict[str, MigrationStats] = {}
        with db_session(backend="postgres") as target_conn:
            for table in tables:
                if table.kind == "routes":
                    stats = migrate_route_cache_table(source_conn, target_conn, table)
                elif table.kind == "bulk":
                    stats = migrate_bulk_results_table(source_conn, target_conn, table)
                elif table.kind == "analysis" and bool(args.include_analysis_tables):
                    stats = migrate_analysis_table(source_conn, target_conn, table)
                else:
                    _log.info("Skipping source table %s kind=%s", table.name, table.kind)
                    continue

                overall[table.name] = stats
                _log.info(
                    "Migrated %s kind=%s found=%d inserted=%d skipped_existing=%d skipped_invalid=%d failed=%d",
                    table.name,
                    table.kind,
                    stats.found,
                    stats.inserted,
                    stats.skipped_existing,
                    stats.skipped_invalid,
                    stats.failed,
                )

        total = MigrationStats()
        for stats in overall.values():
            total.found += stats.found
            total.inserted += stats.inserted
            total.skipped_existing += stats.skipped_existing
            total.skipped_invalid += stats.skipped_invalid
            total.failed += stats.failed

        _log.info(
            "Migration finished. found=%d inserted=%d skipped_existing=%d skipped_invalid=%d failed=%d",
            total.found,
            total.inserted,
            total.skipped_existing,
            total.skipped_invalid,
            total.failed,
        )
        return 0 if total.failed == 0 else 2
    finally:
        source_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
