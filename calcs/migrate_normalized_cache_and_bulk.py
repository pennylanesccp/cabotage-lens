from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.db.bulk_runs import BulkRunSelector, insert_run_result, upsert_run as upsert_bulk_run
from modules.infra.db.core import connect, table_columns, table_exists
from modules.infra.db.locations import find_point, upsert_alias_point
from modules.infra.db.road_cache import upsert_run as upsert_route_run
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal.scenario_keys import normalize_bulk_place_input
from modules.ports.ports_index import load_ports

_log = get_logger(__name__)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PORTS_JSON = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"

_OLD_PLACE_POINTS = "place_points"
_OLD_ROUTES = "routes"
_OLD_BULK_RUNS = "bulk_evaluation_runs"
_OLD_BULK_RUN_RESULTS = "bulk_evaluation_run_results"
_OLD_BULK_RESULTS = "bulk_evaluation_results"


@dataclass
class PhaseStats:
    name: str
    rows_read: int = 0
    rows_migrated: int = 0
    rows_skipped: int = 0
    conflicts_handled: int = 0
    anomalies_found: int = 0


@dataclass
class MigrationReport:
    phases: dict[str, PhaseStats] = field(default_factory=dict)

    def phase(self, name: str) -> PhaseStats:
        if name not in self.phases:
            self.phases[name] = PhaseStats(name=name)
        return self.phases[name]

    def to_dict(self) -> dict[str, Any]:
        return {
            name: {
                "rows_read": stats.rows_read,
                "rows_migrated": stats.rows_migrated,
                "rows_skipped": stats.rows_skipped,
                "conflicts_handled": stats.conflicts_handled,
                "anomalies_found": stats.anomalies_found,
            }
            for name, stats in sorted(self.phases.items())
        }


def _read_dict_rows(
    conn: Any,
    table_name: str,
    *,
    columns: Iterable[str],
    where_sql: str = "",
    params: Optional[Iterable[Any]] = None,
    order_by_sql: str = "",
) -> list[dict[str, Any]]:
    table = str(table_name).strip()
    available = table_columns(conn, table)
    selected = [column for column in columns if column in available]
    if not selected:
        return []

    query = f"SELECT {', '.join(selected)} FROM {table}"
    if where_sql:
        query += f" WHERE {where_sql}"
    if order_by_sql:
        query += f" ORDER BY {order_by_sql}"

    cursor = conn.execute(query, tuple(params or ()))
    rows = cursor.fetchall()
    description = getattr(cursor, "description", None) or []
    names = [str(col[0]) for col in description]
    if not names:
        names = selected
    return [dict(zip(names, row)) for row in rows]


def _port_lookup(path: Path = _DEFAULT_PORTS_JSON) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for port in load_ports(str(path)):
        keys = [ascii_place_key(port.get("name"))]
        keys.extend(ascii_place_key(alias) for alias in port.get("aliases") or [])
        for key in keys:
            if key:
                lookup[key] = port
    return lookup


def _find_port(port_index: dict[str, dict[str, Any]], name: Any) -> Optional[dict[str, Any]]:
    key = ascii_place_key(name)
    if not key:
        return None
    return port_index.get(key)


def _resolve_location_id_from_aliases(conn: Any, *candidates: Any) -> Optional[int]:
    for candidate in candidates:
        point = find_point(conn, place=candidate)
        if point and point.get("location_id") is not None:
            return int(point["location_id"])
    return None


def _selector_from_legacy_row(row: dict[str, Any], *, origin_location_id: int) -> BulkRunSelector:
    return BulkRunSelector(
        origin_location_id=int(origin_location_id),
        cargo_t=float(row.get("cargo_t") or 0.0),
        truck_key=str(row.get("truck_key") or ""),
        ors_profile=str(row.get("ors_profile") or "driving-hgv"),
        vessel_class=(None if row.get("vessel_class") in (None, "") else str(row.get("vessel_class"))),
        include_hoteling=bool(row.get("include_hoteling", True)),
        hoteling_hours_per_call=float(row.get("hoteling_hours_per_call") or 0.0),
        port_calls=int(row.get("port_calls") or 0),
        include_port_ops=bool(row.get("include_port_ops", True)),
        port_moves_per_call=(None if row.get("port_moves_per_call") in (None, "") else float(row["port_moves_per_call"])),
        cargo_teu=(None if row.get("cargo_teu") in (None, "") else float(row["cargo_teu"])),
        t_per_teu_default=float(row.get("t_per_teu_default") or 0.0),
        allocation_mode=(None if row.get("allocation_mode") in (None, "") else str(row.get("allocation_mode"))),
        allocation_load_factor=float(row.get("allocation_load_factor") or 0.0),
        full_call_mode=bool(row.get("full_call_mode", False)),
        port_ops_scenario=str(row.get("port_ops_scenario") or ""),
        destination_set_id=str(row.get("destination_set_id") or "legacy"),
    )


def _synthetic_run_id(row: dict[str, Any], *, origin_location_id: int) -> str:
    selector = _selector_from_legacy_row(row, origin_location_id=origin_location_id)
    payload = {
        "origin_location_id": selector.origin_location_id,
        "input_origin": normalize_bulk_place_input(row.get("input_origin") or row.get("origin_name") or ""),
        "destination_set_id": selector.destination_set_id,
        "cargo_t": selector.cargo_t,
        "truck_key": selector.truck_key,
        "ors_profile": selector.ors_profile,
        "vessel_class": selector.vessel_class,
        "include_hoteling": selector.include_hoteling,
        "hoteling_hours_per_call": selector.hoteling_hours_per_call,
        "port_calls": selector.port_calls,
        "include_port_ops": selector.include_port_ops,
        "port_moves_per_call": selector.port_moves_per_call,
        "cargo_teu": selector.cargo_teu,
        "t_per_teu_default": selector.t_per_teu_default,
        "allocation_mode": selector.allocation_mode,
        "allocation_load_factor": selector.allocation_load_factor,
        "full_call_mode": selector.full_call_mode,
        "port_ops_scenario": selector.port_ops_scenario,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]
    return f"legacy-{digest}"


def _migrate_place_points(conn: Any, *, dry_run: bool, report: MigrationReport) -> None:
    stats = report.phase("place_points")
    if not table_exists(conn, _OLD_PLACE_POINTS):
        return
    rows = _read_dict_rows(
        conn,
        _OLD_PLACE_POINTS,
        columns=(
            "place_key",
            "label",
            "lat",
            "lon",
            "uf",
            "provider",
            "source",
            "insertion_timestamp",
            "updated_timestamp",
        ),
        order_by_sql="updated_timestamp ASC NULLS LAST, insertion_timestamp ASC NULLS LAST",
    )
    stats.rows_read = len(rows)
    for row in rows:
        if row.get("lat") is None or row.get("lon") is None:
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            continue
        if dry_run:
            stats.rows_migrated += 1
            continue
        upsert_alias_point(
            conn,
            place=row.get("place_key") or row.get("label"),
            label=row.get("label") or row.get("place_key"),
            lat=row.get("lat"),
            lon=row.get("lon"),
            uf=row.get("uf"),
            provider=row.get("provider"),
            source=str(row.get("source") or "legacy_place_points"),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        stats.rows_migrated += 1


def _migrate_routes(conn: Any, *, dry_run: bool, report: MigrationReport) -> None:
    stats = report.phase("routes")
    if not table_exists(conn, _OLD_ROUTES):
        return
    rows = _read_dict_rows(
        conn,
        _OLD_ROUTES,
        columns=(
            "origin_key",
            "origin_name",
            "origin_lat",
            "origin_lon",
            "destiny_key",
            "destiny_name",
            "destiny_lat",
            "destiny_lon",
            "profile_requested",
            "profile_used",
            "source",
            "distance_km",
            "insertion_timestamp",
            "updated_timestamp",
        ),
        order_by_sql="updated_timestamp ASC NULLS LAST, insertion_timestamp ASC NULLS LAST",
    )
    stats.rows_read = len(rows)
    for row in rows:
        if None in (row.get("origin_lat"), row.get("origin_lon"), row.get("destiny_lat"), row.get("destiny_lon")):
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            continue
        if dry_run:
            stats.rows_migrated += 1
            continue
        origin = upsert_alias_point(
            conn,
            place=row.get("origin_key") or row.get("origin_name"),
            label=row.get("origin_name") or row.get("origin_key"),
            lat=row.get("origin_lat"),
            lon=row.get("origin_lon"),
            source="legacy_routes",
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        destiny = upsert_alias_point(
            conn,
            place=row.get("destiny_key") or row.get("destiny_name"),
            label=row.get("destiny_name") or row.get("destiny_key"),
            lat=row.get("destiny_lat"),
            lon=row.get("destiny_lon"),
            source="legacy_routes",
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        upsert_route_run(
            conn,
            origin=str(row.get("origin_name") or row.get("origin_key") or ""),
            origin_lat=row.get("origin_lat"),
            origin_lon=row.get("origin_lon"),
            destiny=str(row.get("destiny_name") or row.get("destiny_key") or ""),
            destiny_lat=row.get("destiny_lat"),
            destiny_lon=row.get("destiny_lon"),
            profile_requested=row.get("profile_requested"),
            profile_used=row.get("profile_used"),
            source=str(row.get("source") or "legacy_routes"),
            distance_km=row.get("distance_km"),
            origin_location_id=(None if origin is None else origin.get("location_id")),
            destiny_location_id=(None if destiny is None else destiny.get("location_id")),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        stats.rows_migrated += 1


def _ensure_run_header(
    conn: Any,
    *,
    row: dict[str, Any],
    run_id: str,
    origin_location_id: int,
    destination_count: int,
    success_count: int,
    fail_count: int,
    started_timestamp: Any,
    completed_timestamp: Any,
    updated_timestamp: Any,
    status: str,
) -> None:
    selector = _selector_from_legacy_row(row, origin_location_id=origin_location_id)
    upsert_bulk_run(
        conn,
        run_id=run_id,
        selector=selector,
        origin_name=str(row.get("origin_name") or row.get("input_origin") or row.get("origin_key") or ""),
        input_origin=str(row.get("input_origin") or row.get("origin_name") or ""),
        destination_count=destination_count,
        success_count=success_count,
        fail_count=fail_count,
        status=status,
        error_message=row.get("error_message"),
        duration_s=row.get("duration_s"),
        started_timestamp=started_timestamp,
        completed_timestamp=completed_timestamp,
        updated_timestamp=updated_timestamp,
        origin_location_id=origin_location_id,
    )


def _migrate_run_items(
    conn: Any,
    rows: list[dict[str, Any]],
    *,
    port_index: dict[str, dict[str, Any]],
    dry_run: bool,
    report: MigrationReport,
    phase_name: str,
) -> None:
    stats = report.phase(phase_name)
    for row in rows:
        stats.rows_read += 1
        if dry_run:
            stats.rows_migrated += 1
            continue
        port_origin = _find_port(port_index, row.get("port_origin_name"))
        port_destiny = _find_port(port_index, row.get("port_destiny_name"))
        insert_run_result(
            conn,
            run_id=str(row.get("run_id")),
            scenario_key=str(row.get("scenario_key")),
            input_destiny=str(row.get("input_destiny") or row.get("destiny_name") or ""),
            destiny_name=row.get("destiny_name"),
            destiny_lat=row.get("destiny_lat"),
            destiny_lon=row.get("destiny_lon"),
            destiny_uf=row.get("destiny_uf"),
            port_origin_name=row.get("port_origin_name"),
            port_origin_lat=(None if port_origin is None else port_origin.get("lat")),
            port_origin_lon=(None if port_origin is None else port_origin.get("lon")),
            port_destiny_name=row.get("port_destiny_name"),
            port_destiny_lat=(None if port_destiny is None else port_destiny.get("lat")),
            port_destiny_lon=(None if port_destiny is None else port_destiny.get("lon")),
            status=str(row.get("status") or "ok"),
            error_message=row.get("error_message"),
            road_cost_r=row.get("road_cost_r"),
            multimodal_cost_r=row.get("multimodal_cost_r"),
            cost_delta_r=row.get("cost_delta_r"),
            cost_savings_pct=row.get("cost_savings_pct"),
            road_emissions_kg=row.get("road_emissions_kg"),
            multimodal_emissions_kg=row.get("multimodal_emissions_kg"),
            emissions_delta_kg=row.get("emissions_delta_kg"),
            emissions_savings_pct=row.get("emissions_savings_pct"),
            road_distance_km=row.get("road_distance_km"),
            sea_km=row.get("sea_km"),
            is_approximation=bool(row.get("is_approximation", False)),
            route_source=row.get("route_source"),
            approximation_reference_destiny=row.get("approximation_reference_destiny"),
            approximation_reference_distance_km=row.get("approximation_reference_distance_km"),
            approximation_delta_straight_line_km=row.get("approximation_delta_straight_line_km"),
            approximation_notes=row.get("approximation_notes"),
            ors_profile=str(row.get("ors_profile") or "driving-hgv"),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        stats.rows_migrated += 1


def _migrate_bulk_runs(conn: Any, *, port_index: dict[str, dict[str, Any]], dry_run: bool, report: MigrationReport) -> None:
    if table_exists(conn, _OLD_BULK_RUNS):
        run_rows = _read_dict_rows(
            conn,
            _OLD_BULK_RUNS,
            columns=(
                "run_id",
                "origin_key",
                "origin_name",
                "input_origin",
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
                "destination_set_id",
                "destination_count",
                "success_count",
                "fail_count",
                "status",
                "error_message",
                "duration_s",
                "started_timestamp",
                "completed_timestamp",
                "updated_timestamp",
            ),
            order_by_sql="started_timestamp ASC NULLS LAST, updated_timestamp ASC NULLS LAST",
        )
        stats = report.phase("bulk_runs")
        stats.rows_read = len(run_rows)
        for row in run_rows:
            origin_location_id = _resolve_location_id_from_aliases(
                conn,
                row.get("origin_key"),
                row.get("origin_name"),
                row.get("input_origin"),
            )
            if origin_location_id is None:
                stats.rows_skipped += 1
                stats.anomalies_found += 1
                continue
            if not dry_run:
                _ensure_run_header(
                    conn,
                    row=row,
                    run_id=str(row.get("run_id")),
                    origin_location_id=origin_location_id,
                    destination_count=int(row.get("destination_count") or 0),
                    success_count=int(row.get("success_count") or 0),
                    fail_count=int(row.get("fail_count") or 0),
                    started_timestamp=row.get("started_timestamp"),
                    completed_timestamp=row.get("completed_timestamp"),
                    updated_timestamp=row.get("updated_timestamp"),
                    status=str(row.get("status") or "completed"),
                )
            stats.rows_migrated += 1

    if table_exists(conn, _OLD_BULK_RUN_RESULTS):
        item_rows = _read_dict_rows(
            conn,
            _OLD_BULK_RUN_RESULTS,
            columns=(
                "run_id",
                "scenario_key",
                "input_destiny",
                "destiny_name",
                "destiny_lat",
                "destiny_lon",
                "destiny_uf",
                "port_origin_name",
                "port_destiny_name",
                "status",
                "error_message",
                "road_cost_r",
                "multimodal_cost_r",
                "cost_delta_r",
                "cost_savings_pct",
                "road_emissions_kg",
                "multimodal_emissions_kg",
                "emissions_delta_kg",
                "emissions_savings_pct",
                "road_distance_km",
                "sea_km",
                "is_approximation",
                "route_source",
                "approximation_reference_destiny",
                "approximation_reference_distance_km",
                "approximation_delta_straight_line_km",
                "approximation_notes",
                "ors_profile",
                "insertion_timestamp",
                "updated_timestamp",
            ),
            order_by_sql="updated_timestamp ASC NULLS LAST, insertion_timestamp ASC NULLS LAST",
        )
        _migrate_run_items(
            conn,
            item_rows,
            port_index=port_index,
            dry_run=dry_run,
            report=report,
            phase_name="bulk_run_items",
        )


def _migrate_legacy_bulk_results(conn: Any, *, port_index: dict[str, dict[str, Any]], dry_run: bool, report: MigrationReport) -> None:
    if not table_exists(conn, _OLD_BULK_RESULTS):
        return
    rows = _read_dict_rows(
        conn,
        _OLD_BULK_RESULTS,
        columns=(
            "run_id",
            "scenario_key",
            "destination_set_id",
            "origin_key",
            "origin_name",
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
            "port_origin_name",
            "port_destiny_name",
            "destiny_name",
            "destiny_lat",
            "destiny_lon",
            "destiny_uf",
            "status",
            "error_message",
            "road_distance_km",
            "road_fuel_cost_r",
            "total_fuel_cost_r",
            "delta_cost_r",
            "savings_pct",
            "road_co2e_kg",
            "total_co2e_kg",
            "delta_co2e_kg",
            "emissions_savings_pct",
            "is_approximation",
            "route_source",
            "approximation_reference_destiny",
            "approximation_reference_distance_km",
            "approximation_delta_straight_line_km",
            "approximation_notes",
            "sea_km",
            "insertion_timestamp",
            "updated_timestamp",
        ),
        order_by_sql="updated_timestamp ASC NULLS LAST, insertion_timestamp ASC NULLS LAST",
    )
    stats = report.phase("legacy_bulk_results")
    grouped: dict[str, list[dict[str, Any]]] = {}
    header_row_by_run: dict[str, dict[str, Any]] = {}
    for row in rows:
        stats.rows_read += 1
        origin_location_id = _resolve_location_id_from_aliases(
            conn,
            row.get("origin_key"),
            row.get("origin_name"),
            row.get("input_origin"),
        )
        if origin_location_id is None:
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            continue
        run_id = str(row.get("run_id") or _synthetic_run_id(row, origin_location_id=origin_location_id))
        row["_resolved_origin_location_id"] = origin_location_id
        row["run_id"] = run_id
        grouped.setdefault(run_id, []).append(row)
        header_row_by_run.setdefault(run_id, row)

    for run_id, group in grouped.items():
        header = header_row_by_run[run_id]
        success_count = sum(1 for row in group if str(row.get("status") or "") == "ok")
        fail_count = len(group) - success_count
        if not dry_run:
            _ensure_run_header(
                conn,
                row=header,
                run_id=run_id,
                origin_location_id=int(header["_resolved_origin_location_id"]),
                destination_count=len(group),
                success_count=success_count,
                fail_count=fail_count,
                started_timestamp=min((row.get("insertion_timestamp") for row in group), default=None),
                completed_timestamp=max((row.get("updated_timestamp") for row in group), default=None),
                updated_timestamp=max((row.get("updated_timestamp") for row in group), default=None),
                status="completed",
            )
        stats.conflicts_handled += 1 if len(group) > 1 else 0

    normalized_items = []
    for group in grouped.values():
        for row in group:
            normalized_items.append(
                {
                    "run_id": row.get("run_id"),
                    "scenario_key": row.get("scenario_key"),
                    "input_destiny": row.get("input_destiny"),
                    "destiny_name": row.get("destiny_name"),
                    "destiny_lat": row.get("destiny_lat"),
                    "destiny_lon": row.get("destiny_lon"),
                    "destiny_uf": row.get("destiny_uf"),
                    "port_origin_name": row.get("port_origin_name"),
                    "port_destiny_name": row.get("port_destiny_name"),
                    "status": row.get("status"),
                    "error_message": row.get("error_message"),
                    "road_cost_r": row.get("road_fuel_cost_r"),
                    "multimodal_cost_r": row.get("total_fuel_cost_r"),
                    "cost_delta_r": row.get("delta_cost_r"),
                    "cost_savings_pct": row.get("savings_pct"),
                    "road_emissions_kg": row.get("road_co2e_kg"),
                    "multimodal_emissions_kg": row.get("total_co2e_kg"),
                    "emissions_delta_kg": row.get("delta_co2e_kg"),
                    "emissions_savings_pct": row.get("emissions_savings_pct"),
                    "road_distance_km": row.get("road_distance_km"),
                    "sea_km": row.get("sea_km"),
                    "is_approximation": row.get("is_approximation"),
                    "route_source": row.get("route_source"),
                    "approximation_reference_destiny": row.get("approximation_reference_destiny"),
                    "approximation_reference_distance_km": row.get("approximation_reference_distance_km"),
                    "approximation_delta_straight_line_km": row.get("approximation_delta_straight_line_km"),
                    "approximation_notes": row.get("approximation_notes"),
                    "ors_profile": row.get("ors_profile"),
                    "insertion_timestamp": row.get("insertion_timestamp"),
                    "updated_timestamp": row.get("updated_timestamp"),
                }
            )
    _migrate_run_items(
        conn,
        normalized_items,
        port_index=port_index,
        dry_run=dry_run,
        report=report,
        phase_name="legacy_bulk_result_items",
    )


def run_migration(*, dry_run: bool) -> MigrationReport:
    report = MigrationReport()
    port_index = _port_lookup()
    conn = connect()
    try:
        _migrate_place_points(conn, dry_run=dry_run, report=report)
        _migrate_routes(conn, dry_run=dry_run, report=report)
        _migrate_bulk_runs(conn, port_index=port_index, dry_run=dry_run, report=report)
        _migrate_legacy_bulk_results(conn, port_index=port_index, dry_run=dry_run, report=report)
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
        return report
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy cache and bulk rows into the normalized Postgres schema.")
    parser.add_argument("--dry-run", action="store_true", help="Read and transform rows without committing writes.")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    init_logging(level=args.log_level)
    report = run_migration(dry_run=bool(args.dry_run))
    _log.info("Normalized migration report: %s", json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
