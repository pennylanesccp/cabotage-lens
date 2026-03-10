from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.database_manager import (
    BulkRunSelector,
    db_session,
    get_latest_completed_run,
    list_bulk_run_cargo_values,
    list_bulk_run_origins,
    list_bulk_run_results,
    load_database_settings,
)
from modules.infra.log_manager import get_logger
from modules.multimodal.bulk import load_destinations, run_bulk_evaluation

from app.heatmap.config import HEATMAP_DESTINATION_LABEL, HEATMAP_DESTINATION_SET_ID, HEATMAP_DESTINATIONS_PATH
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapRunInfo, HeatmapScenario
from app.main.utils.constants import DEFAULTS

_log = get_logger(__name__)


class HeatmapConfigurationError(RuntimeError):
    pass


class HeatmapDataError(RuntimeError):
    pass



def _require_postgres() -> None:
    settings = load_database_settings()
    if not settings.is_postgres or not settings.postgres_dsn:
        raise HeatmapConfigurationError(
            "Heatmap storage requires Supabase Postgres. Configure SUPABASE_DB_URL "
            "or the component-based SUPABASE_DB_* Streamlit secrets first."
        )



def _hidden_defaults() -> Dict[str, Any]:
    cargo_teu_raw = float(DEFAULTS.get("cargo_teu_input", 0.0))
    port_moves_raw = float(DEFAULTS.get("port_moves_per_call_input", 0.0))
    allocation_mode = str(DEFAULTS.get("allocation_mode", "auto")).strip().lower()
    return {
        "truck_key": str(DEFAULTS["truck_key"]),
        "profile": str(DEFAULTS["profile"]),
        "vessel_class": str(DEFAULTS["vessel_class"]),
        "include_hoteling": bool(DEFAULTS["include_hoteling"]),
        "hoteling_hours_per_call": float(DEFAULTS["hoteling_hours_per_call"]),
        "port_calls": int(DEFAULTS["port_calls"]),
        "include_port_ops": bool(DEFAULTS["include_port_ops"]),
        "port_moves_per_call": (None if port_moves_raw <= 0.0 else port_moves_raw),
        "cargo_teu": (None if cargo_teu_raw <= 0.0 else cargo_teu_raw),
        "t_per_teu_default": float(DEFAULTS["t_per_teu_default"]),
        "allocation_mode": (None if allocation_mode == "auto" else allocation_mode),
        "allocation_load_factor": float(DEFAULTS["allocation_load_factor"]),
        "full_call_mode": bool(DEFAULTS["full_call_mode"]),
        "port_ops_scenario": str(DEFAULTS["port_ops_scenario"]),
        "destination_set_id": HEATMAP_DESTINATION_SET_ID,
    }



def _build_selector(origin_name: str, cargo_t: float) -> BulkRunSelector:
    defaults = _hidden_defaults()
    return BulkRunSelector(
        origin_key=ascii_place_key(origin_name),
        cargo_t=float(cargo_t),
        truck_key=str(defaults["truck_key"]),
        ors_profile=str(defaults["profile"]),
        vessel_class=str(defaults["vessel_class"]),
        include_hoteling=bool(defaults["include_hoteling"]),
        hoteling_hours_per_call=float(defaults["hoteling_hours_per_call"]),
        port_calls=int(defaults["port_calls"]),
        include_port_ops=bool(defaults["include_port_ops"]),
        port_moves_per_call=defaults["port_moves_per_call"],
        cargo_teu=defaults["cargo_teu"],
        t_per_teu_default=float(defaults["t_per_teu_default"]),
        allocation_mode=defaults["allocation_mode"],
        allocation_load_factor=float(defaults["allocation_load_factor"]),
        full_call_mode=bool(defaults["full_call_mode"]),
        port_ops_scenario=str(defaults["port_ops_scenario"]),
        destination_set_id=str(defaults["destination_set_id"]),
    )



def _max_abs(values: List[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(abs(value) for value in values)
    index = max(int(round((len(ordered) - 1) * 0.9)), 0)
    candidate = ordered[index]
    return candidate if candidate > 0 else 1.0



def _to_run_info(record: Any) -> HeatmapRunInfo:
    return HeatmapRunInfo(
        run_id=record.run_id,
        origin_name=record.origin_name,
        cargo_t=float(record.cargo_t),
        destination_count=int(record.destination_count),
        success_count=int(record.success_count),
        fail_count=int(record.fail_count),
        duration_s=record.duration_s,
        completed_timestamp=record.completed_timestamp,
        updated_timestamp=record.updated_timestamp,
        destination_set_id=record.destination_set_id,
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



def default_cargo_options() -> List[float]:
    return [float(DEFAULTS["cargo_t"])]



def list_origin_options() -> List[str]:
    _require_postgres()
    with db_session(backend="postgres") as conn:
        origins = list_bulk_run_origins(
            conn,
            destination_set_id=HEATMAP_DESTINATION_SET_ID,
            limit=2_000,
        )
    return [ascii_place_text(origin) for origin in origins]



def list_cargo_options(origin_name: str) -> List[float]:
    _require_postgres()
    default_values = default_cargo_options()
    if not str(origin_name).strip():
        return default_values

    with db_session(backend="postgres") as conn:
        stored = list_bulk_run_cargo_values(
            conn,
            origin_key=ascii_place_key(origin_name),
            destination_set_id=HEATMAP_DESTINATION_SET_ID,
            limit=100,
        )

    merged = {float(value) for value in default_values}
    merged.update(float(value) for value in stored)
    return sorted(merged)



def get_latest_run_info(scenario: HeatmapScenario) -> Optional[HeatmapRunInfo]:
    _require_postgres()
    selector = _build_selector(scenario.origin_name, scenario.cargo_t)
    with db_session(backend="postgres") as conn:
        record = get_latest_completed_run(conn, selector=selector)
    if record is None:
        return None
    _log.info(
        "Latest heatmap run found: run_id=%s origin=%s cargo_t=%.3f success=%d fail=%d",
        record.run_id,
        record.origin_name,
        record.cargo_t,
        record.success_count,
        record.fail_count,
    )
    return _to_run_info(record)



def load_latest_dataset(scenario: HeatmapScenario) -> Optional[HeatmapDataset]:
    run_info = get_latest_run_info(scenario)
    if run_info is None:
        return None

    with db_session(backend="postgres") as conn:
        rows = list_bulk_run_results(conn, run_id=run_info.run_id, only_success=True)

    points: List[HeatmapPoint] = []
    for row in rows:
        point = _to_point(row)
        if point is not None:
            points.append(point)

    if not points:
        raise HeatmapDataError(
            "The latest run was found, but none of its rows have map coordinates. Run the heatmap again to refresh the dataset."
        )

    dataset = HeatmapDataset(
        run=run_info,
        points=points,
        max_abs_cost_delta=_max_abs([point.cost_delta_r for point in points]),
        max_abs_emissions_delta=_max_abs([point.emissions_delta_kg for point in points]),
    )
    _log.info(
        "Loaded heatmap dataset: run_id=%s rows=%d destination_set=%s",
        run_info.run_id,
        len(points),
        run_info.destination_set_id,
    )
    return dataset



def rerun_heatmap(
    scenario: HeatmapScenario,
    *,
    overwrite_road: bool = False,
    progress_callback: Optional[Any] = None,
) -> HeatmapDataset:
    _require_postgres()
    destination_path = HEATMAP_DESTINATIONS_PATH.resolve()
    destinations = load_destinations(destination_path)
    if not destinations:
        raise HeatmapDataError(f"Heatmap destinations file is empty: {destination_path}")

    defaults = _hidden_defaults()
    _log.info(
        "Starting heatmap rerun: origin=%s cargo_t=%.3f destination_set=%s destinations=%d",
        scenario.origin_name,
        scenario.cargo_t,
        HEATMAP_DESTINATION_SET_ID,
        len(destinations),
    )
    run_bulk_evaluation(
        origin=scenario.origin_name,
        dest_list=destinations,
        cargo_t=float(scenario.cargo_t),
        truck_key=str(defaults["truck_key"]),
        profile=str(defaults["profile"]),
        overwrite_road=bool(overwrite_road),
        vessel_class=str(defaults["vessel_class"]),
        include_hoteling=bool(defaults["include_hoteling"]),
        hoteling_hours_per_call=float(defaults["hoteling_hours_per_call"]),
        port_calls=int(defaults["port_calls"]),
        include_port_ops=bool(defaults["include_port_ops"]),
        port_moves_per_call=defaults["port_moves_per_call"],
        cargo_teu=defaults["cargo_teu"],
        t_per_teu_default=float(defaults["t_per_teu_default"]),
        allocation_mode=defaults["allocation_mode"],
        allocation_load_factor=float(defaults["allocation_load_factor"]),
        full_call_mode=bool(defaults["full_call_mode"]),
        port_ops_scenario=str(defaults["port_ops_scenario"]),
        destination_set_id=HEATMAP_DESTINATION_SET_ID,
        progress_callback=progress_callback,
    )
    dataset = load_latest_dataset(scenario)
    if dataset is None:
        raise HeatmapDataError(
            f"The rerun finished but no completed batch was found for {HEATMAP_DESTINATION_LABEL}."
        )
    return dataset



def describe_hidden_defaults() -> Dict[str, Any]:
    return dict(_hidden_defaults())



def scenario_to_dict(scenario: HeatmapScenario) -> Dict[str, Any]:
    return asdict(scenario)
