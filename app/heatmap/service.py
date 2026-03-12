from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from typing import Any, Dict, List, Optional

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.database_manager import (
    BulkRunSelector,
    db_session,
    find_place_point,
    get_latest_completed_run,
    list_bulk_results,
    list_bulk_run_cargo_values,
    list_bulk_run_origins,
    load_database_settings,
    summarize_bulk_results,
)
from modules.infra.log_manager import get_logger
from modules.multimodal.bulk import load_destinations, run_bulk_evaluation
from modules.multimodal.scenario_keys import normalize_bulk_place_input

from app.heatmap.config import HEATMAP_DESTINATION_LABEL, HEATMAP_DESTINATION_SET_ID, HEATMAP_DESTINATIONS_PATH
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapRunInfo, HeatmapScenario
from app.main.utils.constants import DEFAULTS

_log = get_logger(__name__)


class HeatmapConfigurationError(RuntimeError):
    pass


class HeatmapDataError(RuntimeError):
    pass


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


@lru_cache(maxsize=1)
def _heatmap_destinations() -> tuple[str, ...]:
    destination_path = HEATMAP_DESTINATIONS_PATH.resolve()
    destinations = _dedupe_preserve_order(load_destinations(destination_path))
    return tuple(destinations)


def _require_postgres() -> None:
    settings = load_database_settings()
    if not settings.is_postgres or not settings.postgres_dsn:
        raise HeatmapConfigurationError(
            "Heatmap storage requires Supabase Postgres. Configure SUPABASE_PROJECT_REF, "
            "SUPABASE_DB_PASSWORD, and SUPABASE_DB_PORT first."
        )


def _max_abs(values: List[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(abs(value) for value in values)
    index = max(int(round((len(ordered) - 1) * 0.9)), 0)
    candidate = ordered[index]
    return candidate if candidate > 0 else 1.0


def _to_run_info(
    scenario: HeatmapScenario,
    *,
    row_count: int,
    success_count: int,
    fail_count: int,
    latest_updated_timestamp: Any,
    latest_run_id: Optional[str],
    duration_s: Optional[float],
    completed_timestamp: Any,
) -> HeatmapRunInfo:
    destination_count = len(_heatmap_destinations())
    found_count = min(int(row_count), destination_count)
    return HeatmapRunInfo(
        run_id=latest_run_id,
        origin_name=scenario.origin_name,
        cargo_t=float(scenario.cargo_t),
        destination_count=destination_count,
        found_count=found_count,
        success_count=int(success_count),
        fail_count=int(fail_count),
        missing_count=max(destination_count - found_count, 0),
        duration_s=duration_s,
        completed_timestamp=completed_timestamp,
        updated_timestamp=latest_updated_timestamp,
        destination_set_id=HEATMAP_DESTINATION_SET_ID,
    )


def _to_point(record: Any) -> Optional[HeatmapPoint]:
    if record.destiny_lat is None or record.destiny_lon is None:
        return None
    if record.road_fuel_cost_r is None or record.total_fuel_cost_r is None:
        return None
    if record.road_co2e_kg is None or record.total_co2e_kg is None:
        return None
    return HeatmapPoint(
        destiny_name=record.destiny_name,
        destiny_lat=float(record.destiny_lat),
        destiny_lon=float(record.destiny_lon),
        destiny_uf=record.destiny_uf,
        port_destiny_name=record.port_destiny_name,
        road_cost_r=float(record.road_fuel_cost_r),
        multimodal_cost_r=float(record.total_fuel_cost_r),
        cost_delta_r=float(record.delta_cost_r or 0.0),
        cost_savings_pct=record.savings_pct,
        road_emissions_kg=float(record.road_co2e_kg),
        multimodal_emissions_kg=float(record.total_co2e_kg),
        emissions_delta_kg=float(record.delta_co2e_kg or 0.0),
        emissions_savings_pct=record.emissions_savings_pct,
        road_distance_km=record.road_distance_km,
        sea_km=record.sea_km,
        updated_timestamp=record.updated_timestamp,
    )


def _point_rejection_reason(record: Any) -> Optional[str]:
    if record.destiny_lat is None or record.destiny_lon is None:
        return "missing_coordinates"
    if record.road_fuel_cost_r is None or record.total_fuel_cost_r is None:
        return "missing_costs"
    if record.road_co2e_kg is None or record.total_co2e_kg is None:
        return "missing_emissions"
    return None


def default_cargo_options() -> List[float]:
    return [float(DEFAULTS["cargo_t"])]


@lru_cache(maxsize=256)
def _canonical_origin_name(origin_name: str) -> str:
    candidate = normalize_bulk_place_input(origin_name)
    if not candidate:
        return ""

    try:
        with db_session(backend="postgres") as conn:
            cached_point = find_place_point(conn, place=candidate)
    except Exception as exc:
        _log.debug("Heatmap origin canonicalization skipped for %s: %s", candidate, exc)
        return candidate

    resolved = ascii_place_text((cached_point or {}).get("label") or candidate)
    if resolved != candidate:
        _log.info("Canonicalized heatmap origin selector %s -> %s", candidate, resolved)
    return resolved or candidate


def _build_selector(scenario: HeatmapScenario) -> BulkRunSelector:
    canonical_origin_name = _canonical_origin_name(scenario.origin_name)
    return BulkRunSelector(
        origin_key=ascii_place_key(canonical_origin_name),
        cargo_t=float(scenario.cargo_t),
        truck_key=str(scenario.truck_key),
        ors_profile=str(scenario.ors_profile),
        vessel_class=str(scenario.vessel_class),
        include_hoteling=bool(scenario.include_hoteling),
        hoteling_hours_per_call=float(scenario.hoteling_hours_per_call),
        port_calls=int(scenario.port_calls),
        include_port_ops=bool(scenario.include_port_ops),
        port_moves_per_call=scenario.port_moves_per_call,
        cargo_teu=scenario.cargo_teu,
        t_per_teu_default=float(scenario.t_per_teu_default),
        allocation_mode=scenario.allocation_mode,
        allocation_load_factor=float(scenario.allocation_load_factor),
        full_call_mode=bool(scenario.full_call_mode),
        port_ops_scenario=str(scenario.port_ops_scenario),
        destination_set_id=HEATMAP_DESTINATION_SET_ID,
    )


def list_origin_options() -> List[str]:
    _require_postgres()
    _log.info("Loading heatmap origins destination_set=%s", HEATMAP_DESTINATION_SET_ID)
    with db_session(backend="postgres") as conn:
        origins = list_bulk_run_origins(
            conn,
            destination_set_id=HEATMAP_DESTINATION_SET_ID,
            limit=2_000,
        )
    normalized = _dedupe_preserve_order([ascii_place_text(origin) for origin in origins])
    _log.info(
        "Loaded heatmap origins destination_set=%s raw=%d normalized=%d",
        HEATMAP_DESTINATION_SET_ID,
        len(origins),
        len(normalized),
    )
    return normalized


def list_cargo_options(origin_name: str) -> List[float]:
    _require_postgres()
    default_values = default_cargo_options()
    if not str(origin_name).strip():
        _log.info(
            "Using default heatmap cargo options because no origin is selected values=%s",
            ",".join(f"{value:.3f}" for value in default_values),
        )
        return default_values

    _log.info(
        "Loading heatmap cargo options origin=%s destination_set=%s",
        origin_name,
        HEATMAP_DESTINATION_SET_ID,
    )
    with db_session(backend="postgres") as conn:
        stored = list_bulk_run_cargo_values(
            conn,
            origin_key=ascii_place_key(origin_name),
            destination_set_id=HEATMAP_DESTINATION_SET_ID,
            limit=100,
        )

    merged = {float(value) for value in default_values}
    merged.update(float(value) for value in stored)
    values = sorted(merged)
    _log.info(
        "Loaded heatmap cargo options origin=%s count=%d values=%s",
        origin_name,
        len(values),
        ",".join(f"{value:.3f}" for value in values),
    )
    return values


def get_heatmap_status(scenario: HeatmapScenario) -> HeatmapRunInfo:
    _require_postgres()
    selector = _build_selector(scenario)
    _log.info(
        "Querying heatmap comparison status origin=%s cargo_t=%.3f destination_set=%s",
        scenario.origin_name,
        scenario.cargo_t,
        HEATMAP_DESTINATION_SET_ID,
    )
    with db_session(backend="postgres") as conn:
        summary = summarize_bulk_results(conn, selector=selector)
        latest_completed = get_latest_completed_run(conn, selector=selector)

    status = _to_run_info(
        scenario,
        row_count=summary.row_count,
        success_count=summary.success_count,
        fail_count=summary.fail_count,
        latest_updated_timestamp=(
            summary.latest_updated_timestamp
            or (None if latest_completed is None else latest_completed.updated_timestamp)
        ),
        latest_run_id=summary.latest_run_id or (None if latest_completed is None else latest_completed.run_id),
        duration_s=None if latest_completed is None else latest_completed.duration_s,
        completed_timestamp=None if latest_completed is None else latest_completed.completed_timestamp,
    )
    _log.info(
        (
            "Heatmap comparison status origin=%s cargo_t=%.3f found=%d success=%d fail=%d "
            "missing=%d latest_run_id=%s"
        ),
        scenario.origin_name,
        scenario.cargo_t,
        status.found_count,
        status.success_count,
        status.fail_count,
        status.missing_count,
        status.run_id or "<none>",
    )
    return status


def get_latest_run_info(scenario: HeatmapScenario) -> Optional[HeatmapRunInfo]:
    status = get_heatmap_status(scenario)
    return status if status.updated_timestamp is not None else None


def _existing_destination_inputs(scenario: HeatmapScenario) -> set[str]:
    selector = _build_selector(scenario)
    with db_session(backend="postgres") as conn:
        rows = list_bulk_results(conn, selector=selector, only_success=None)
    return {
        normalize_bulk_place_input(row.input_destiny).casefold()
        for row in rows
        if str(row.input_destiny).strip()
    }


def pending_destinations(scenario: HeatmapScenario) -> List[str]:
    existing = _existing_destination_inputs(scenario)
    pending = [
        destination
        for destination in _heatmap_destinations()
        if normalize_bulk_place_input(destination).casefold() not in existing
    ]
    _log.info(
        "Computed pending heatmap destinations origin=%s cargo_t=%.3f pending=%d total=%d",
        scenario.origin_name,
        scenario.cargo_t,
        len(pending),
        len(_heatmap_destinations()),
    )
    return pending


def load_current_dataset(scenario: HeatmapScenario) -> Optional[HeatmapDataset]:
    status = get_heatmap_status(scenario)
    if status.found_count <= 0:
        return None

    selector = _build_selector(scenario)
    _log.info("Loading heatmap comparison rows origin=%s cargo_t=%.3f", scenario.origin_name, scenario.cargo_t)
    with db_session(backend="postgres") as conn:
        rows = list_bulk_results(conn, selector=selector, only_success=True)

    points: List[HeatmapPoint] = []
    skipped_missing_coordinates = 0
    skipped_missing_costs = 0
    skipped_missing_emissions = 0
    for row in rows:
        rejection_reason = _point_rejection_reason(row)
        if rejection_reason == "missing_coordinates":
            skipped_missing_coordinates += 1
            continue
        if rejection_reason == "missing_costs":
            skipped_missing_costs += 1
            continue
        if rejection_reason == "missing_emissions":
            skipped_missing_emissions += 1
            continue
        point = _to_point(row)
        if point is not None:
            points.append(point)

    if not points:
        _log.warning(
            "Heatmap comparison rows are not plottable origin=%s cargo_t=%.3f success_rows=%d skipped_missing_coordinates=%d skipped_missing_costs=%d skipped_missing_emissions=%d",
            scenario.origin_name,
            scenario.cargo_t,
            len(rows),
            skipped_missing_coordinates,
            skipped_missing_costs,
            skipped_missing_emissions,
        )
        raise HeatmapDataError(
            "Stored comparison rows were found, but none of them have plottable map values. Use rerun to refresh the comparison table."
        )

    dataset = HeatmapDataset(
        scenario=scenario,
        run=status,
        points=points,
        max_abs_cost_delta=_max_abs([point.cost_delta_r for point in points]),
        max_abs_emissions_delta=_max_abs([point.emissions_delta_kg for point in points]),
    )
    _log.info(
        "Loaded heatmap dataset origin=%s cargo_t=%.3f plotted_rows=%d success_rows=%d missing=%d",
        scenario.origin_name,
        scenario.cargo_t,
        len(points),
        len(rows),
        status.missing_count,
    )
    return dataset


def load_latest_dataset(scenario: HeatmapScenario) -> Optional[HeatmapDataset]:
    return load_current_dataset(scenario)


def run_heatmap(
    scenario: HeatmapScenario,
    *,
    rerun: bool,
    progress_callback: Optional[Any] = None,
) -> HeatmapDataset:
    _require_postgres()
    all_destinations = list(_heatmap_destinations())
    if not all_destinations:
        raise HeatmapDataError(f"Heatmap destinations file is empty: {HEATMAP_DESTINATIONS_PATH.resolve()}")

    if rerun:
        destinations_to_process = all_destinations
        mode_label = "rerun"
    else:
        destinations_to_process = pending_destinations(scenario)
        mode_label = "missing-only run"

    if not destinations_to_process:
        _log.info(
            "Heatmap %s skipped because no destinations need processing origin=%s cargo_t=%.3f",
            mode_label,
            scenario.origin_name,
            scenario.cargo_t,
        )
        dataset = load_current_dataset(scenario)
        if dataset is None:
            raise HeatmapDataError(
                f"No stored heatmap rows were found for {HEATMAP_DESTINATION_LABEL}. Use rerun to populate the comparison table."
            )
        return dataset

    _log.info(
        "Starting heatmap %s origin=%s cargo_t=%.3f destination_set=%s destinations=%d overwrite_road=%s",
        mode_label,
        scenario.origin_name,
        scenario.cargo_t,
        HEATMAP_DESTINATION_SET_ID,
        len(destinations_to_process),
        False,
    )
    bulk_summary = run_bulk_evaluation(
        origin=scenario.origin_name,
        dest_list=destinations_to_process,
        cargo_t=float(scenario.cargo_t),
        truck_key=str(scenario.truck_key),
        profile=str(scenario.ors_profile),
        overwrite_road=False,
        vessel_class=str(scenario.vessel_class),
        include_hoteling=bool(scenario.include_hoteling),
        hoteling_hours_per_call=float(scenario.hoteling_hours_per_call),
        port_calls=int(scenario.port_calls),
        include_port_ops=bool(scenario.include_port_ops),
        port_moves_per_call=scenario.port_moves_per_call,
        cargo_teu=scenario.cargo_teu,
        t_per_teu_default=float(scenario.t_per_teu_default),
        allocation_mode=scenario.allocation_mode,
        allocation_load_factor=float(scenario.allocation_load_factor),
        full_call_mode=bool(scenario.full_call_mode),
        port_ops_scenario=str(scenario.port_ops_scenario),
        destination_set_id=HEATMAP_DESTINATION_SET_ID,
        progress_callback=progress_callback,
    )
    _log.info(
        (
            "Heatmap %s bulk summary origin=%s cargo_t=%.3f success=%d fail=%d "
            "exact_success=%d approximated_success=%d run_id=%s"
        ),
        mode_label,
        scenario.origin_name,
        scenario.cargo_t,
        int(bulk_summary.get("success_count") or 0),
        int(bulk_summary.get("fail_count") or 0),
        int(bulk_summary.get("exact_success_count") or 0),
        int(bulk_summary.get("approximated_success_count") or 0),
        bulk_summary.get("run_id") or "<none>",
    )
    dataset = load_current_dataset(scenario)
    if dataset is None:
        post_status = get_heatmap_status(scenario)
        _log.error(
            (
                "Heatmap %s finished without readable comparison rows origin=%s cargo_t=%.3f "
                "bulk_success=%d bulk_fail=%d post_found=%d post_success=%d post_fail=%d post_run_id=%s"
            ),
            mode_label,
            scenario.origin_name,
            scenario.cargo_t,
            int(bulk_summary.get("success_count") or 0),
            int(bulk_summary.get("fail_count") or 0),
            post_status.found_count,
            post_status.success_count,
            post_status.fail_count,
            post_status.run_id or "<none>",
        )
        raise HeatmapDataError(
            f"The heatmap {mode_label} finished but no comparison rows were found for {HEATMAP_DESTINATION_LABEL}."
        )
    _log.info(
        "Heatmap %s loaded dataset origin=%s cargo_t=%.3f points=%d",
        mode_label,
        scenario.origin_name,
        scenario.cargo_t,
        len(dataset.points),
    )
    return dataset


def rerun_heatmap(
    scenario: HeatmapScenario,
    *,
    progress_callback: Optional[Any] = None,
) -> HeatmapDataset:
    return run_heatmap(scenario, rerun=True, progress_callback=progress_callback)


def describe_hidden_defaults() -> Dict[str, Any]:
    return dict(DEFAULTS)


def scenario_to_dict(scenario: HeatmapScenario) -> Dict[str, Any]:
    return asdict(scenario)
