from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.database_manager import (
    BulkRunSelector,
    db_session,
    find_place_point,
    get_latest_completed_run,
    list_bulk_results_for_origin_scenario,
    list_bulk_results,
    list_bulk_run_results,
    list_bulk_run_cargo_values,
    list_bulk_run_origins,
    list_cached_place_points,
    list_multimodal_heatmap_results,
    load_database_settings,
    summarize_bulk_results,
)
from modules.infra.db.bulk_runs import selector_hash
from modules.infra.log_manager import bind_log_context, get_logger
from modules.multimodal.bulk import load_destinations, run_bulk_evaluation
from modules.multimodal.scenario_keys import normalize_bulk_place_input

from app.heatmap.config import (
    HEATMAP_DESTINATION_SET_ID,
    heatmap_destination_label,
    resolve_heatmap_destination_path,
)
from app.heatmap.types import (
    HeatmapDataset,
    HeatmapDatasetDiagnostics,
    HeatmapFailureRecord,
    HeatmapPoint,
    HeatmapRunInfo,
    HeatmapScenario,
)
from app.main.utils.constants import DEFAULTS

_log = get_logger(__name__)
_COMPARE_SINGLE_RESULTS_TABLE = "analysis_results"


class HeatmapConfigurationError(RuntimeError):
    pass


class HeatmapDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class _LoadedHeatmapRow:
    source_kind: str
    source_detail: Optional[str]
    input_destiny: str
    destiny_name: str
    destiny_lat: Optional[float]
    destiny_lon: Optional[float]
    destiny_uf: Optional[str]
    port_destiny_name: Optional[str]
    road_cost_r: Optional[float]
    multimodal_cost_r: Optional[float]
    cost_delta_r: Optional[float]
    cost_savings_pct: Optional[float]
    road_emissions_kg: Optional[float]
    multimodal_emissions_kg: Optional[float]
    emissions_delta_kg: Optional[float]
    emissions_savings_pct: Optional[float]
    road_distance_km: Optional[float]
    sea_km: Optional[float]
    updated_timestamp: Any


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


def _resolve_destination_set_id(destination_set_id: str | None = None) -> str:
    try:
        return resolve_heatmap_destination_path(destination_set_id).name
    except FileNotFoundError as exc:
        raise HeatmapConfigurationError(str(exc)) from exc


def _destination_label(destination_set_id: str) -> str:
    return heatmap_destination_label(destination_set_id)


@lru_cache(maxsize=16)
def _heatmap_destinations(destination_set_id: str = HEATMAP_DESTINATION_SET_ID) -> tuple[str, ...]:
    destination_path = resolve_heatmap_destination_path(destination_set_id)
    destinations = _dedupe_preserve_order(load_destinations(destination_path))
    return tuple(destinations)


def _require_postgres() -> None:
    settings = load_database_settings()
    if not settings.is_postgres or not settings.postgres_dsn:
        raise HeatmapConfigurationError(
            "Heatmap storage requires Supabase Postgres. Configure SUPABASE_DB_URL or the split secrets "
            "SUPABASE_DB_HOST, SUPABASE_DB_PORT, SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, "
            "and SUPABASE_DB_SSLMODE."
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
    destination_set_id: str,
    row_count: int,
    success_count: int,
    fail_count: int,
    failed_destination_count: int,
    latest_updated_timestamp: Any,
    latest_run_id: Optional[str],
    duration_s: Optional[float],
    completed_timestamp: Any,
) -> HeatmapRunInfo:
    destination_count = len(_heatmap_destinations(destination_set_id))
    found_count = max(min(int(row_count), destination_count), 0)
    success_total = max(min(int(success_count), destination_count), 0)
    fail_total = max(min(int(fail_count), destination_count), 0)
    missing_count = max(destination_count - found_count, 0)
    failed_total = max(min(int(failed_destination_count), destination_count), 0)
    pending_count = max(min(missing_count + failed_total, destination_count), 0)
    return HeatmapRunInfo(
        run_id=latest_run_id,
        origin_name=scenario.origin_name,
        cargo_t=float(scenario.cargo_t),
        destination_count=destination_count,
        found_count=found_count,
        success_count=success_total,
        fail_count=fail_total,
        missing_count=missing_count,
        pending_count=pending_count,
        duration_s=duration_s,
        completed_timestamp=completed_timestamp,
        updated_timestamp=latest_updated_timestamp,
        destination_set_id=destination_set_id,
    )


def _to_point(record: Any) -> Optional[HeatmapPoint]:
    if record.destiny_lat is None or record.destiny_lon is None:
        return None
    if record.road_cost_r is None or record.multimodal_cost_r is None:
        return None
    if record.road_emissions_kg is None or record.multimodal_emissions_kg is None:
        return None
    return HeatmapPoint(
        destiny_name=record.destiny_name,
        destiny_lat=float(record.destiny_lat),
        destiny_lon=float(record.destiny_lon),
        destiny_uf=record.destiny_uf,
        port_destiny_name=record.port_destiny_name,
        road_cost_r=float(record.road_cost_r),
        multimodal_cost_r=float(record.multimodal_cost_r),
        cost_delta_r=float(record.cost_delta_r or 0.0),
        cost_savings_pct=record.cost_savings_pct,
        road_emissions_kg=float(record.road_emissions_kg),
        multimodal_emissions_kg=float(record.multimodal_emissions_kg),
        emissions_delta_kg=float(record.emissions_delta_kg or 0.0),
        emissions_savings_pct=record.emissions_savings_pct,
        road_distance_km=record.road_distance_km,
        sea_km=record.sea_km,
        updated_timestamp=record.updated_timestamp,
    )


def _point_rejection_reason(record: Any) -> Optional[str]:
    if record.destiny_lat is None or record.destiny_lon is None:
        return "missing_coordinates"
    if record.road_cost_r is None or record.multimodal_cost_r is None:
        return "missing_costs"
    if record.road_emissions_kg is None or record.multimodal_emissions_kg is None:
        return "missing_emissions"
    return None


def _failure_record_from_run_result(record: Any) -> Optional[HeatmapFailureRecord]:
    status = str(getattr(record, "status", "")).strip().lower()
    if status == "ok":
        return None
    destination = str(getattr(record, "destiny_name", "") or getattr(record, "input_destiny", "")).strip()
    return HeatmapFailureRecord(
        destination=destination or str(getattr(record, "input_destiny", "")).strip() or "<unknown>",
        failed_leg=getattr(record, "failed_leg", None),
        failed_step=getattr(record, "failed_step", None),
        failure_reason=getattr(record, "failure_reason", None),
        failure_detail=getattr(record, "failure_detail", None) or getattr(record, "error_message", None),
        port_origin=getattr(record, "port_origin_name", None),
        port_destiny=getattr(record, "port_destiny_name", None),
        retryable=bool(getattr(record, "retryable", False)),
        provider=getattr(record, "failure_provider", None),
        provider_operation=getattr(record, "failure_provider_operation", None),
    )


def _load_failed_destinations(conn: Any, *, run_id: Optional[str]) -> List[HeatmapFailureRecord]:
    if not str(run_id or "").strip():
        return []
    records = list_bulk_run_results(conn, run_id=str(run_id), only_success=False)
    failures = [failure for failure in (_failure_record_from_run_result(record) for record in records) if failure is not None]
    return sorted(failures, key=lambda item: (item.destination.casefold(), item.destination))


def _origin_name_variants(origin_name: str) -> List[str]:
    return _dedupe_preserve_order(
        [
            ascii_place_text(origin_name),
            _canonical_origin_name(origin_name),
        ]
    )


def _loaded_row_from_bulk(record: Any) -> _LoadedHeatmapRow:
    return _LoadedHeatmapRow(
        source_kind="bulk",
        source_detail=str(getattr(record, "destination_set_id", "")).strip() or None,
        input_destiny=str(getattr(record, "input_destiny", "") or getattr(record, "destiny_name", "")).strip(),
        destiny_name=str(getattr(record, "destiny_name", "")).strip(),
        destiny_lat=getattr(record, "destiny_lat", None),
        destiny_lon=getattr(record, "destiny_lon", None),
        destiny_uf=getattr(record, "destiny_uf", None),
        port_destiny_name=getattr(record, "port_destiny_name", None),
        road_cost_r=getattr(record, "road_cost_r", None),
        multimodal_cost_r=getattr(record, "multimodal_cost_r", None),
        cost_delta_r=getattr(record, "cost_delta_r", None),
        cost_savings_pct=getattr(record, "cost_savings_pct", None),
        road_emissions_kg=getattr(record, "road_emissions_kg", None),
        multimodal_emissions_kg=getattr(record, "multimodal_emissions_kg", None),
        emissions_delta_kg=getattr(record, "emissions_delta_kg", None),
        emissions_savings_pct=getattr(record, "emissions_savings_pct", None),
        road_distance_km=getattr(record, "road_distance_km", None),
        sea_km=getattr(record, "sea_km", None),
        updated_timestamp=getattr(record, "updated_timestamp", None),
    )


def _loaded_row_from_single_compare(record: Any, cached_point: Optional[Dict[str, Any]]) -> _LoadedHeatmapRow:
    return _LoadedHeatmapRow(
        source_kind="single_compare",
        source_detail=_COMPARE_SINGLE_RESULTS_TABLE,
        input_destiny=str(getattr(record, "destiny_name", "")).strip(),
        destiny_name=ascii_place_text((cached_point or {}).get("label") or getattr(record, "destiny_name", "")),
        destiny_lat=(None if cached_point is None else cached_point.get("lat")),
        destiny_lon=(None if cached_point is None else cached_point.get("lon")),
        destiny_uf=(None if cached_point is None else cached_point.get("uf")),
        port_destiny_name=getattr(record, "port_destiny_name", None),
        road_cost_r=getattr(record, "road_cost_r", None),
        multimodal_cost_r=getattr(record, "multimodal_cost_r", None),
        cost_delta_r=getattr(record, "cost_delta_r", None),
        cost_savings_pct=getattr(record, "cost_savings_pct", None),
        road_emissions_kg=getattr(record, "road_emissions_kg", None),
        multimodal_emissions_kg=getattr(record, "multimodal_emissions_kg", None),
        emissions_delta_kg=getattr(record, "emissions_delta_kg", None),
        emissions_savings_pct=getattr(record, "emissions_savings_pct", None),
        road_distance_km=getattr(record, "road_distance_km", None),
        sea_km=getattr(record, "sea_km", None),
        updated_timestamp=getattr(record, "updated_timestamp", None),
    )


def _loaded_row_key(record: _LoadedHeatmapRow) -> str:
    return normalize_bulk_place_input(record.input_destiny or record.destiny_name).casefold()


def _timestamp_sort_key(value: Any) -> tuple[int, str]:
    text = str(value).strip() if value is not None else ""
    return (1, text) if text else (0, "")


def _row_preference_key(record: _LoadedHeatmapRow) -> tuple[Any, ...]:
    rejection_reason = _point_rejection_reason(record)
    return (
        1 if rejection_reason is None else 0,
        1 if record.destiny_lat is not None and record.destiny_lon is not None else 0,
        1 if record.road_cost_r is not None and record.multimodal_cost_r is not None else 0,
        1 if record.road_emissions_kg is not None and record.multimodal_emissions_kg is not None else 0,
        _timestamp_sort_key(record.updated_timestamp),
        1 if record.source_kind == "bulk" else 0,
    )


def _merge_loaded_rows(rows: List[_LoadedHeatmapRow]) -> List[_LoadedHeatmapRow]:
    latest_by_destiny: dict[str, _LoadedHeatmapRow] = {}
    for row in rows:
        destiny_key = _loaded_row_key(row)
        if not destiny_key:
            continue
        current = latest_by_destiny.get(destiny_key)
        if current is None or _row_preference_key(row) > _row_preference_key(current):
            latest_by_destiny[destiny_key] = row
    return sorted(latest_by_destiny.values(), key=lambda item: (item.destiny_name.casefold(), item.destiny_name))


def default_cargo_options() -> List[float]:
    return [float(DEFAULTS["cargo_t"])]


@lru_cache(maxsize=256)
def _canonical_origin_name(origin_name: str) -> str:
    candidate = normalize_bulk_place_input(origin_name)
    if not candidate:
        return ""

    try:
        with db_session() as conn:
            cached_point = find_place_point(conn, place=candidate)
    except Exception as exc:
        _log.debug("Heatmap origin canonicalization skipped for %s: %s", candidate, exc)
        return candidate

    resolved = ascii_place_text((cached_point or {}).get("label") or candidate)
    if resolved != candidate:
        _log.info("Canonicalized heatmap origin selector %s -> %s", candidate, resolved)
    return resolved or candidate


def _origin_location_id(origin_name: str) -> Optional[int]:
    candidate = _canonical_origin_name(origin_name)
    if not candidate:
        return None
    try:
        with db_session() as conn:
            cached_point = find_place_point(conn, place=candidate)
    except Exception as exc:
        _log.debug("Heatmap origin location lookup skipped for %s: %s", candidate, exc)
        return None
    if not cached_point or cached_point.get("location_id") is None:
        return None
    return int(cached_point["location_id"])


def _build_selector_for_origin_location(
    scenario: HeatmapScenario,
    origin_location_id: Optional[int],
    destination_set_id: str,
) -> BulkRunSelector:
    return BulkRunSelector(
        origin_location_id=origin_location_id,
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
        destination_set_id=destination_set_id,
    )


def _selector_log_details(selector: BulkRunSelector) -> str:
    return (
        f"selector_hash={selector_hash(selector)} "
        f"origin_location_id={selector.origin_location_id} "
        f"cargo_t={selector.cargo_t:.3f} "
        f"truck_key={selector.truck_key} "
        f"ors_profile={selector.ors_profile} "
        f"vessel_class={selector.vessel_class} "
        f"include_hoteling={selector.include_hoteling} "
        f"include_port_ops={selector.include_port_ops} "
        f"allocation_mode={selector.allocation_mode or 'auto'} "
        f"destination_set={selector.destination_set_id}"
    )


def _failed_destination_count(records: List[Any]) -> int:
    return sum(1 for record in records if str(getattr(record, "status", "")).strip().lower() != "ok")


def _pending_destination_list(records: List[Any], *, destination_set_id: str) -> List[str]:
    latest_statuses: dict[str, str] = {}
    for record in records:
        normalized_input = normalize_bulk_place_input(getattr(record, "input_destiny", ""))
        if not normalized_input:
            continue
        latest_statuses[normalized_input.casefold()] = str(getattr(record, "status", "")).strip().lower()

    pending: list[str] = []
    for destination in _heatmap_destinations(destination_set_id):
        normalized_input = normalize_bulk_place_input(destination).casefold()
        status = latest_statuses.get(normalized_input)
        if status is None or status != "ok":
            pending.append(destination)
    return pending


def _select_active_selector(
    conn: Any,
    scenario: HeatmapScenario,
    destination_set_id: str,
) -> tuple[BulkRunSelector, Any, Any]:
    selector = _build_selector_for_origin_location(
        scenario,
        _origin_location_id(scenario.origin_name),
        destination_set_id,
    )
    _log.info(
        "Resolved heatmap selector origin=%s cargo_t=%.3f %s",
        scenario.origin_name,
        scenario.cargo_t,
        _selector_log_details(selector),
    )
    summary = summarize_bulk_results(conn, selector=selector)
    latest_completed = get_latest_completed_run(conn, selector=selector)
    return selector, summary, latest_completed


def _load_bulk_rows_for_map(
    conn: Any,
    scenario: HeatmapScenario,
    destination_set_id: str,
) -> List[_LoadedHeatmapRow]:
    selector = _build_selector_for_origin_location(
        scenario,
        _origin_location_id(scenario.origin_name),
        destination_set_id,
    )
    records = list_bulk_results_for_origin_scenario(
        conn,
        selector=selector,
        only_success=True,
        include_all_destination_sets=True,
    )
    return [_loaded_row_from_bulk(record) for record in records]


def _load_single_compare_rows_for_map(conn: Any, scenario: HeatmapScenario) -> List[_LoadedHeatmapRow]:
    origin_variants = _origin_name_variants(scenario.origin_name)
    if not origin_variants:
        return []

    records = list_multimodal_heatmap_results(
        conn,
        origin_names=origin_variants,
        cargo_t=float(scenario.cargo_t),
        table_name=_COMPARE_SINGLE_RESULTS_TABLE,
    )
    if not records:
        return []

    cached_points = list_cached_place_points(conn, places=[record.destiny_name for record in records])
    rows: list[_LoadedHeatmapRow] = []
    for record in records:
        cached_point = cached_points.get(ascii_place_key(record.destiny_name))
        rows.append(_loaded_row_from_single_compare(record, cached_point))
    return rows


def _load_map_rows(
    conn: Any,
    scenario: HeatmapScenario,
    destination_set_id: str,
) -> List[_LoadedHeatmapRow]:
    bulk_rows = _load_bulk_rows_for_map(conn, scenario, destination_set_id)
    single_compare_rows = _load_single_compare_rows_for_map(conn, scenario)
    merged_rows = _merge_loaded_rows([*bulk_rows, *single_compare_rows])
    _log.info(
        (
            "Resolved aggregated heatmap rows origin=%s cargo_t=%.3f selected_destination_set=%s "
            "bulk_rows=%d single_compare_rows=%d merged_rows=%d"
        ),
        scenario.origin_name,
        scenario.cargo_t,
        destination_set_id,
        len(bulk_rows),
        len(single_compare_rows),
        len(merged_rows),
    )
    return merged_rows


def list_origin_options(*, destination_set_id: str | None = None) -> List[str]:
    _require_postgres()
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
    _log.info("Loading heatmap origins destination_set=%s", resolved_destination_set_id)
    with db_session() as conn:
        origins = list_bulk_run_origins(
            conn,
            destination_set_id=resolved_destination_set_id,
            limit=2_000,
        )
    normalized = _dedupe_preserve_order([ascii_place_text(origin) for origin in origins])
    _log.info(
        "Loaded heatmap origins destination_set=%s raw=%d normalized=%d",
        resolved_destination_set_id,
        len(origins),
        len(normalized),
    )
    return normalized


def list_cargo_options(origin_name: str, *, destination_set_id: str | None = None) -> List[float]:
    _require_postgres()
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
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
        resolved_destination_set_id,
    )
    origin_location_id = _origin_location_id(origin_name)
    if origin_location_id is None:
        return default_values
    with db_session() as conn:
        stored = list_bulk_run_cargo_values(
            conn,
            origin_location_id=int(origin_location_id),
            destination_set_id=resolved_destination_set_id,
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


def get_heatmap_status(
    scenario: HeatmapScenario,
    *,
    destination_set_id: str | None = None,
) -> HeatmapRunInfo:
    _require_postgres()
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
    with bind_log_context(origin=scenario.origin_name, destination_set_id=resolved_destination_set_id, ors_profile=scenario.ors_profile, entrypoint="heatmap"):
        _log.info(
            "Querying heatmap comparison status origin=%s cargo_t=%.3f destination_set=%s",
            scenario.origin_name,
            scenario.cargo_t,
            resolved_destination_set_id,
        )
        with db_session() as conn:
            selector, summary, latest_completed = _select_active_selector(conn, scenario, resolved_destination_set_id)
            latest_rows = list_bulk_results(conn, selector=selector, only_success=None)

        failed_destination_count = _failed_destination_count(latest_rows)
        status = _to_run_info(
            scenario,
            destination_set_id=resolved_destination_set_id,
            row_count=summary.row_count,
            success_count=summary.success_count,
            fail_count=summary.fail_count,
            failed_destination_count=failed_destination_count,
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
                "missing=%d failed_latest=%d pending=%d latest_run_id=%s selector_hash=%s"
            ),
            scenario.origin_name,
            scenario.cargo_t,
            status.found_count,
            status.success_count,
            status.fail_count,
            status.missing_count,
            failed_destination_count,
            status.pending_count,
            status.run_id or "<none>",
            selector_hash(selector),
        )
        return status


def get_latest_run_info(
    scenario: HeatmapScenario,
    *,
    destination_set_id: str | None = None,
) -> Optional[HeatmapRunInfo]:
    status = get_heatmap_status(scenario, destination_set_id=destination_set_id)
    return status if status.updated_timestamp is not None else None


def pending_destinations(
    scenario: HeatmapScenario,
    *,
    destination_set_id: str | None = None,
) -> List[str]:
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
    with db_session() as conn:
        selector = _build_selector_for_origin_location(
            scenario,
            _origin_location_id(scenario.origin_name),
            resolved_destination_set_id,
        )
        latest_rows = list_bulk_results(conn, selector=selector, only_success=None)

    pending = _pending_destination_list(latest_rows, destination_set_id=resolved_destination_set_id)
    failed_destinations = _failed_destination_count(latest_rows)
    missing_count = max(len(_heatmap_destinations(resolved_destination_set_id)) - len(latest_rows), 0)
    _log.info(
        (
            "Computed pending heatmap destinations origin=%s cargo_t=%.3f pending=%d missing=%d "
            "failed=%d total=%d"
        ),
        scenario.origin_name,
        scenario.cargo_t,
        len(pending),
        missing_count,
        failed_destinations,
        len(_heatmap_destinations(resolved_destination_set_id)),
    )
    return pending


def list_failed_destinations(
    scenario: HeatmapScenario,
    *,
    destination_set_id: str | None = None,
    run_id: str | None = None,
) -> List[HeatmapFailureRecord]:
    _require_postgres()
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
    selected_run_id = str(run_id or "").strip() or None
    with db_session() as conn:
        if selected_run_id is None:
            selector, summary, latest_completed = _select_active_selector(conn, scenario, resolved_destination_set_id)
            del selector
            selected_run_id = summary.latest_run_id or (None if latest_completed is None else latest_completed.run_id)
        failures = _load_failed_destinations(conn, run_id=selected_run_id)
    _log.info(
        "Loaded heatmap failed destinations origin=%s cargo_t=%.3f destination_set=%s run_id=%s failures=%d",
        scenario.origin_name,
        scenario.cargo_t,
        resolved_destination_set_id,
        selected_run_id or "<none>",
        len(failures),
    )
    return failures


def load_current_dataset(
    scenario: HeatmapScenario,
    *,
    status: HeatmapRunInfo | None = None,
    destination_set_id: str | None = None,
) -> Optional[HeatmapDataset]:
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
    status = status or get_heatmap_status(scenario, destination_set_id=resolved_destination_set_id)
    if status.found_count <= 0:
        with db_session() as conn:
            aggregated_rows = _load_map_rows(conn, scenario, resolved_destination_set_id)
        if not aggregated_rows:
            return None
    else:
        aggregated_rows = []

    _log.info(
        "Loading aggregated heatmap comparison rows origin=%s cargo_t=%.3f selected_destination_set=%s",
        scenario.origin_name,
        scenario.cargo_t,
        resolved_destination_set_id,
    )
    with db_session() as conn:
        if not aggregated_rows:
            aggregated_rows = _load_map_rows(conn, scenario, resolved_destination_set_id)
        failed_destinations = _load_failed_destinations(conn, run_id=status.run_id)

    if not aggregated_rows:
        return None

    _log.info(
        (
            "Heatmap dataset row load origin=%s cargo_t=%.3f selected_destination_set=%s "
            "selected_found=%d selected_success=%d selected_fail=%d loaded_rows=%d"
        ),
        scenario.origin_name,
        scenario.cargo_t,
        resolved_destination_set_id,
        status.found_count,
        status.success_count,
        status.fail_count,
        len(aggregated_rows),
    )
    if len(aggregated_rows) != status.success_count:
        _log.info(
            (
                "Heatmap dataset selected-summary differs from aggregated load origin=%s cargo_t=%.3f "
                "selected_success=%d loaded_rows=%d"
            ),
            scenario.origin_name,
            scenario.cargo_t,
            status.success_count,
            len(aggregated_rows),
        )

    points: List[HeatmapPoint] = []
    skipped_missing_coordinates = 0
    skipped_missing_costs = 0
    skipped_missing_emissions = 0
    for row in aggregated_rows:
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

    loaded_bulk_rows = sum(1 for row in aggregated_rows if row.source_kind == "bulk")
    loaded_single_compare_rows = sum(1 for row in aggregated_rows if row.source_kind == "single_compare")
    if not points:
        _log.warning(
            (
                "Aggregated heatmap comparison rows are not plottable origin=%s cargo_t=%.3f rows=%d "
                "bulk_rows=%d single_compare_rows=%d skipped_missing_coordinates=%d "
                "skipped_missing_costs=%d skipped_missing_emissions=%d"
            ),
            scenario.origin_name,
            scenario.cargo_t,
            len(aggregated_rows),
            loaded_bulk_rows,
            loaded_single_compare_rows,
            skipped_missing_coordinates,
            skipped_missing_costs,
            skipped_missing_emissions,
        )
        raise HeatmapDataError(
            "Stored comparison rows were found across the available sources, but none of them have plottable map values. Use rerun to refresh the comparison table."
        )

    diagnostics = HeatmapDatasetDiagnostics(
        successful_rows=len(aggregated_rows),
        plottable_points=len(points),
        skipped_missing_coordinates=skipped_missing_coordinates,
        skipped_missing_costs=skipped_missing_costs,
        skipped_missing_emissions=skipped_missing_emissions,
        loaded_bulk_rows=loaded_bulk_rows,
        loaded_single_compare_rows=loaded_single_compare_rows,
        failed_destinations=failed_destinations,
    )
    dataset = HeatmapDataset(
        scenario=scenario,
        run=status,
        points=points,
        max_abs_cost_delta=_max_abs([point.cost_delta_r for point in points]),
        max_abs_emissions_delta=_max_abs([point.emissions_delta_kg for point in points]),
        diagnostics=diagnostics,
    )
    _log.info(
        (
            "Loaded aggregated heatmap dataset origin=%s cargo_t=%.3f selected_destination_set=%s "
            "loaded_rows=%d bulk_rows=%d single_compare_rows=%d plottable_points=%d "
            "skipped_missing_coordinates=%d skipped_missing_costs=%d skipped_missing_emissions=%d "
            "failed_destinations=%d selected_missing=%d"
        ),
        scenario.origin_name,
        scenario.cargo_t,
        resolved_destination_set_id,
        diagnostics.successful_rows,
        diagnostics.loaded_bulk_rows,
        diagnostics.loaded_single_compare_rows,
        diagnostics.plottable_points,
        diagnostics.skipped_missing_coordinates,
        diagnostics.skipped_missing_costs,
        diagnostics.skipped_missing_emissions,
        len(diagnostics.failed_destinations),
        status.missing_count,
    )
    return dataset


def load_latest_dataset(
    scenario: HeatmapScenario,
    *,
    destination_set_id: str | None = None,
) -> Optional[HeatmapDataset]:
    return load_current_dataset(scenario, destination_set_id=destination_set_id)


def run_heatmap(
    scenario: HeatmapScenario,
    *,
    rerun: bool,
    progress_callback: Optional[Any] = None,
    destination_set_id: str | None = None,
) -> HeatmapDataset:
    _require_postgres()
    resolved_destination_set_id = _resolve_destination_set_id(destination_set_id)
    destination_label = _destination_label(resolved_destination_set_id)
    destination_path = resolve_heatmap_destination_path(resolved_destination_set_id)
    all_destinations = list(_heatmap_destinations(resolved_destination_set_id))
    if not all_destinations:
        raise HeatmapDataError(f"Heatmap destinations file is empty: {destination_path}")

    if rerun:
        destinations_to_process = all_destinations
        mode_label = "rerun"
    else:
        destinations_to_process = pending_destinations(scenario, destination_set_id=resolved_destination_set_id)
        mode_label = "run-missing"

    if not destinations_to_process:
        _log.info(
            "Heatmap %s skipped because no destinations are missing or failed origin=%s cargo_t=%.3f",
            mode_label,
            scenario.origin_name,
            scenario.cargo_t,
        )
        dataset = load_current_dataset(scenario, destination_set_id=resolved_destination_set_id)
        if dataset is None:
            raise HeatmapDataError(
                f"No stored heatmap rows were found for {destination_label}. Use rerun to populate the comparison table."
            )
        return dataset

    with bind_log_context(origin=scenario.origin_name, destination_set_id=resolved_destination_set_id, ors_profile=scenario.ors_profile, entrypoint="heatmap"):
        _log.info(
            "Starting heatmap %s origin=%s cargo_t=%.3f destination_set=%s destinations=%d overwrite_road=%s",
            mode_label,
            scenario.origin_name,
            scenario.cargo_t,
            resolved_destination_set_id,
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
            destination_set_id=resolved_destination_set_id,
            progress_callback=progress_callback,
            max_geocode_workers=1,
            max_route_workers=2,
        )
        _log.info(
            (
                "Heatmap %s bulk summary origin=%s cargo_t=%.3f success=%d fail=%d "
                "exact_success=%d approximated_success=%d run_id=%s selector_hash=%s"
            ),
            mode_label,
            scenario.origin_name,
            scenario.cargo_t,
            int(bulk_summary.get("success_count") or 0),
            int(bulk_summary.get("fail_count") or 0),
            int(bulk_summary.get("exact_success_count") or 0),
            int(bulk_summary.get("approximated_success_count") or 0),
            bulk_summary.get("run_id") or "<none>",
            bulk_summary.get("selector_hash") or "<none>",
        )
    dataset = load_current_dataset(scenario, destination_set_id=resolved_destination_set_id)
    if dataset is None:
        post_status = get_heatmap_status(scenario, destination_set_id=resolved_destination_set_id)
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
            f"The heatmap {mode_label} finished but no comparison rows were found for {destination_label}."
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
    destination_set_id: str | None = None,
) -> HeatmapDataset:
    return run_heatmap(
        scenario,
        rerun=True,
        progress_callback=progress_callback,
        destination_set_id=destination_set_id,
    )


def describe_hidden_defaults() -> Dict[str, Any]:
    return dict(DEFAULTS)


def scenario_to_dict(scenario: HeatmapScenario) -> Dict[str, Any]:
    return asdict(scenario)
