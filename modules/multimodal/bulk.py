from __future__ import annotations

import copy
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from modules.addressing.text import ascii_place_key
from modules.infra.database_manager import (
    DEFAULT_BULK_RESULTS_TABLE,
    DEFAULT_BULK_RUN_RESULTS_TABLE,
    DEFAULT_BULK_RUNS_TABLE,
    BulkRunSelector,
    db_session,
    finish_bulk_run,
    insert_bulk_run_result,
    start_bulk_run,
    upsert_bulk_result,
)
from modules.infra.log_manager import get_logger
from modules.multimodal.builder import (
    build_path_geometry_from_resolved,
    build_port_node,
    load_routing_assets,
    resolve_point_for_geometry,
)
from modules.multimodal.evaluator import evaluate_path, prepare_evaluation_context
from modules.multimodal.persistence import flatten_evaluation_for_db
from modules.multimodal.scenario_keys import build_bulk_scenario_key, normalize_bulk_place_input
from modules.ports.ports_nearest import find_nearest_port, haversine_km
from modules.road.router import get_or_create_leg

_log = get_logger(__name__)
ProgressCallback = Callable[[Dict[str, Any]], None]

_APPROX_ROUTE_SOURCE = "nearest_exact_delta_straight_line"
_MIN_APPROX_ROAD_DISTANCE_KM = 1.0


@dataclass(frozen=True)
class ExactRoadReference:
    destiny_name: str
    destiny_lat: float
    destiny_lon: float
    road_distance_km: float


@dataclass(frozen=True)
class ApproximationMetadata:
    route_source: str
    reference_destiny: str
    reference_distance_km: float
    delta_straight_line_km: float
    notes: str


@dataclass(frozen=True)
class PendingApproximation:
    index: int
    destiny_input: str
    destiny_name: str
    scenario_key: str
    scenario_payload: Dict[str, Any]
    geo: Dict[str, Any]
    failure_status: str
    error_message: str


def load_destinations(path: Path) -> List[str]:
    """Read clean non-empty destination lines from a text file."""
    if not path.exists():
        raise FileNotFoundError(f"Destinations file not found: {path}")

    destinations: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = str(line).strip().lstrip("\ufeff")
            if text and not text.startswith("#"):
                destinations.append(text)
    return destinations


def _dedupe_preserve_order(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    duplicates = 0

    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = normalize_bulk_place_input(text).casefold()
        if not key:
            continue
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        ordered.append(text)

    if duplicates:
        _log.warning("Skipped %d duplicated destination entries in bulk input.", duplicates)

    return ordered


def _shuffle_destinations(
    values: Sequence[str],
    *,
    enabled: bool,
    seed: Optional[int],
) -> tuple[List[str], Optional[int]]:
    ordered = list(values)
    if not enabled:
        return ordered, None

    seed_used = int(seed) if seed is not None else random.SystemRandom().randrange(0, 2**32)
    if len(ordered) > 1:
        random.Random(seed_used).shuffle(ordered)
    return ordered, seed_used


def _require_distance(leg: Dict[str, Any], leg_name: str) -> None:
    if leg.get("distance_km") is None:
        raise RuntimeError(f"{leg_name} road distance is unavailable")


def _classify_failure(exc: Exception) -> tuple[str, str, bool]:
    """
    Classify expected per-destination failures so they are logged cleanly and
    persisted with a more useful status.
    """
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if "last_mile road distance is unavailable" in lowered:
        return "last_mile_no_road_route", message, False
    if "road_direct road distance is unavailable" in lowered or "road distance is unavailable" in lowered:
        return "no_road_route", message, False
    if "failed to resolve destination" in lowered:
        return "geocode_failed", message, False
    if "geometry build failed" in lowered:
        return "geometry_failed", message, False
    if "path evaluation failed" in lowered:
        return "evaluation_failed", message, False

    return "error", message, True


def _route_source_for_result(
    geo: Optional[Dict[str, Any]],
    *,
    is_approximation: bool,
) -> Optional[str]:
    if not isinstance(geo, dict):
        return None
    direct_leg = geo.get("road_direct", {})
    if not isinstance(direct_leg, dict):
        return None
    source = str(direct_leg.get("source") or "").strip()
    if not source:
        return None
    if is_approximation:
        return source
    if source == "api":
        return "ors_exact"
    if source == "cache":
        return "cache_exact"
    if source.endswith("_exact"):
        return source
    return f"{source}_exact"


def _build_success_summary_row(
    destiny_input: str,
    geo: Dict[str, Any],
    res: Dict[str, Any],
    flat: Dict[str, Any],
    *,
    is_approximation: bool,
    route_source: Optional[str],
    approximation_meta: Optional[ApproximationMetadata],
) -> Dict[str, Any]:
    inputs = res.get("inputs", {})
    comparison = res.get("comparison", {})

    return {
        "destiny_input": destiny_input,
        "destiny_name": geo["destiny"]["label"],
        "status": "ok",
        "is_approximation": bool(is_approximation),
        "route_source": route_source,
        "approximation_reference_destiny": (
            None if approximation_meta is None else approximation_meta.reference_destiny
        ),
        "approximation_reference_distance_km": (
            None if approximation_meta is None else approximation_meta.reference_distance_km
        ),
        "approximation_delta_straight_line_km": (
            None if approximation_meta is None else approximation_meta.delta_straight_line_km
        ),
        "approximation_notes": None if approximation_meta is None else approximation_meta.notes,
        "road_direct_source": geo["road_direct"].get("source"),
        "first_mile_source": geo["first_mile"].get("source"),
        "last_mile_source": geo["last_mile"].get("source"),
        "road_direct_profile_used": geo["road_direct"].get("profile_used"),
        "first_mile_profile_used": geo["first_mile"].get("profile_used"),
        "last_mile_profile_used": geo["last_mile"].get("profile_used"),
        "road_cost": flat.get("road_fuel_cost_r"),
        "mm_cost": flat.get("total_fuel_cost_r"),
        "delta_cost": flat.get("delta_cost_r"),
        "savings_pct": comparison.get("savings_pct"),
        "road_co2e": flat.get("road_co2e_kg"),
        "mm_co2e": flat.get("total_co2e_kg"),
        "diesel_price_source": inputs.get("diesel_price_source"),
        "port_ops_scenario": inputs.get("port_ops_scenario_resolved"),
        "allocation_mode_used": inputs.get("allocation_mode_used"),
    }


def _build_failure_summary_row(
    destiny_input: str,
    destiny_name: str,
    *,
    status: str,
    error_message: str,
    route_source: Optional[str] = None,
    approximation_notes: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "destiny_input": destiny_input,
        "destiny_name": destiny_name,
        "status": status,
        "is_approximation": False,
        "route_source": route_source,
        "approximation_reference_destiny": None,
        "approximation_reference_distance_km": None,
        "approximation_delta_straight_line_km": None,
        "approximation_notes": approximation_notes,
        "error_msg": error_message,
    }


def _build_run_selector(
    *,
    origin_name: str,
    cargo_t: float,
    truck_key: str,
    profile: str,
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    port_moves_per_call: Optional[float],
    cargo_teu: Optional[float],
    t_per_teu_default: float,
    allocation_mode: Optional[str],
    allocation_load_factor: float,
    full_call_mode: bool,
    port_ops_scenario: str,
    destination_set_id: str,
) -> BulkRunSelector:
    return BulkRunSelector(
        origin_key=ascii_place_key(origin_name),
        cargo_t=float(cargo_t),
        truck_key=str(truck_key),
        ors_profile=str(profile),
        vessel_class=str(vessel_class),
        include_hoteling=bool(include_hoteling),
        hoteling_hours_per_call=float(hoteling_hours_per_call),
        port_calls=int(port_calls),
        include_port_ops=bool(include_port_ops),
        port_moves_per_call=(None if port_moves_per_call is None else float(port_moves_per_call)),
        cargo_teu=(None if cargo_teu is None else float(cargo_teu)),
        t_per_teu_default=float(t_per_teu_default),
        allocation_mode=allocation_mode,
        allocation_load_factor=float(allocation_load_factor),
        full_call_mode=bool(full_call_mode),
        port_ops_scenario=str(port_ops_scenario),
        destination_set_id=str(destination_set_id),
    )


def _emissions_savings_pct(flat: Dict[str, Any]) -> Optional[float]:
    road_co2e = float(flat.get("road_co2e_kg") or 0.0)
    multimodal_co2e = float(flat.get("total_co2e_kg") or 0.0)
    if road_co2e <= 0.0:
        return None
    return float((1 - (multimodal_co2e / road_co2e)) * 100.0)


def _emit_progress(progress_callback: Optional[ProgressCallback], **payload: Any) -> None:
    if progress_callback is None:
        return
    try:
        progress_callback(payload)
    except Exception as exc:
        _log.warning("Bulk progress callback failed: %s", exc)


def _point_coords(point: Optional[Dict[str, Any]]) -> Optional[tuple[float, float]]:
    if not isinstance(point, dict):
        return None
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _make_exact_reference(geo: Dict[str, Any], flat: Dict[str, Any]) -> Optional[ExactRoadReference]:
    destiny = geo.get("destiny", {})
    coords = _point_coords(destiny)
    road_distance_km = flat.get("road_distance_km")
    if coords is None or road_distance_km is None:
        return None
    return ExactRoadReference(
        destiny_name=str(destiny.get("label") or geo.get("destiny_name") or ""),
        destiny_lat=coords[0],
        destiny_lon=coords[1],
        road_distance_km=float(road_distance_km),
    )


def _select_nearest_exact_reference(
    destiny_point: Dict[str, Any],
    exact_references: Sequence[ExactRoadReference],
) -> Optional[ExactRoadReference]:
    coords = _point_coords(destiny_point)
    if coords is None or not exact_references:
        return None
    lat, lon = coords
    return min(
        exact_references,
        key=lambda candidate: haversine_km(lat, lon, candidate.destiny_lat, candidate.destiny_lon),
    )


def _estimate_road_distance_from_reference(
    origin_point: Dict[str, Any],
    destiny_point: Dict[str, Any],
    reference: ExactRoadReference,
) -> tuple[float, ApproximationMetadata]:
    origin_coords = _point_coords(origin_point)
    destiny_coords = _point_coords(destiny_point)
    if origin_coords is None:
        raise RuntimeError("Approximation fallback unavailable: origin coordinates are missing")
    if destiny_coords is None:
        raise RuntimeError("Approximation fallback unavailable: destination coordinates are missing")

    origin_lat, origin_lon = origin_coords
    destiny_lat, destiny_lon = destiny_coords

    straight_origin_to_missing_km = haversine_km(origin_lat, origin_lon, destiny_lat, destiny_lon)
    straight_origin_to_reference_km = haversine_km(
        origin_lat,
        origin_lon,
        reference.destiny_lat,
        reference.destiny_lon,
    )
    delta_straight_line_km = straight_origin_to_missing_km - straight_origin_to_reference_km
    raw_estimated_distance_km = reference.road_distance_km + delta_straight_line_km
    estimated_distance_km = max(raw_estimated_distance_km, _MIN_APPROX_ROAD_DISTANCE_KM)

    notes = "Approximate direct-road distance from the nearest exact destination in the same bulk run."
    if estimated_distance_km != raw_estimated_distance_km:
        notes = (
            f"{notes} Clamped from {raw_estimated_distance_km:.3f} km "
            f"to {_MIN_APPROX_ROAD_DISTANCE_KM:.3f} km."
        )

    return float(estimated_distance_km), ApproximationMetadata(
        route_source=_APPROX_ROUTE_SOURCE,
        reference_destiny=reference.destiny_name,
        reference_distance_km=float(reference.road_distance_km),
        delta_straight_line_km=float(delta_straight_line_km),
        notes=notes,
    )


def _build_approximated_geometry(geo: Dict[str, Any], estimated_distance_km: float) -> Dict[str, Any]:
    approx_geo = copy.deepcopy(geo)
    approx_geo.setdefault("road_direct", {})
    approx_geo["road_direct"]["distance_km"] = float(estimated_distance_km)
    approx_geo["road_direct"]["cached"] = False
    approx_geo["road_direct"]["is_hgv"] = None
    approx_geo["road_direct"]["profile_used"] = None
    approx_geo["road_direct"]["source"] = _APPROX_ROUTE_SOURCE
    return approx_geo


def _evaluate_and_flatten(
    geo: Dict[str, Any],
    *,
    origin_name: str,
    destiny_name: str,
    evaluation_kwargs: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    res = evaluate_path(geo, **evaluation_kwargs)
    if not res:
        raise RuntimeError("Path evaluation failed")
    flat = flatten_evaluation_for_db(origin_name, destiny_name, res)
    return res, flat


def _safe_persist_bulk_outcome(
    destiny_input: str,
    *,
    status: str,
    **kwargs: Any,
) -> None:
    try:
        _persist_bulk_outcome(status=status, **kwargs)
    except Exception as persist_exc:
        kind = "success" if status == "ok" else "error"
        _log.error(
            "Failed to persist bulk %s outcome for %s: %s",
            kind,
            destiny_input,
            persist_exc,
            exc_info=True,
        )


def _persist_bulk_outcome(
    *,
    db_path: Path | str | None,
    table_name: str,
    run_results_table: str,
    run_id: str,
    destination_set_id: str,
    scenario_key: str,
    input_origin: str,
    input_destiny: str,
    origin_name: str,
    destiny_name: str,
    truck_key: str,
    ors_profile: str,
    cargo_t: float,
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    port_moves_per_call: Optional[float],
    cargo_teu: Optional[float],
    t_per_teu_default: float,
    allocation_mode: Optional[str],
    allocation_load_factor: float,
    full_call_mode: bool,
    port_ops_scenario: str,
    status: str,
    error_message: Optional[str] = None,
    geo: Optional[Dict[str, Any]] = None,
    res: Optional[Dict[str, Any]] = None,
    flat: Optional[Dict[str, Any]] = None,
    is_approximation: bool = False,
    route_source: Optional[str] = None,
    approximation_reference_destiny: Optional[str] = None,
    approximation_reference_distance_km: Optional[float] = None,
    approximation_delta_straight_line_km: Optional[float] = None,
    approximation_notes: Optional[str] = None,
) -> None:
    inputs = res.get("inputs", {}) if isinstance(res, dict) else {}
    flat = flat or {}
    origin_point = geo.get("origin", {}) if isinstance(geo, dict) else {}
    destiny_point = geo.get("destiny", {}) if isinstance(geo, dict) else {}
    port_origin = geo.get("port_origin", {}) if isinstance(geo, dict) else {}
    port_destiny = geo.get("port_destiny", {}) if isinstance(geo, dict) else {}

    road_cost_r = flat.get("road_fuel_cost_r")
    multimodal_cost_r = flat.get("total_fuel_cost_r")
    road_emissions_kg = flat.get("road_co2e_kg")
    multimodal_emissions_kg = flat.get("total_co2e_kg")
    emissions_savings_pct = _emissions_savings_pct(flat)
    resolved_route_source = route_source or _route_source_for_result(geo, is_approximation=is_approximation)

    cost_delta_r = None
    if road_cost_r is not None and multimodal_cost_r is not None:
        cost_delta_r = float(road_cost_r) - float(multimodal_cost_r)

    emissions_delta_kg = None
    if road_emissions_kg is not None and multimodal_emissions_kg is not None:
        emissions_delta_kg = float(road_emissions_kg) - float(multimodal_emissions_kg)

    with db_session(db_path) as conn:
        upsert_bulk_result(
            conn,
            table_name=table_name,
            scenario_key=scenario_key,
            run_id=run_id,
            destination_set_id=destination_set_id,
            origin_key=ascii_place_key(origin_name),
            origin_name=origin_name,
            origin_lat=origin_point.get("lat"),
            origin_lon=origin_point.get("lon"),
            origin_uf=origin_point.get("uf"),
            destiny_key=ascii_place_key(destiny_name),
            destiny_name=destiny_name,
            destiny_lat=destiny_point.get("lat"),
            destiny_lon=destiny_point.get("lon"),
            destiny_uf=destiny_point.get("uf"),
            input_origin=input_origin,
            input_destiny=input_destiny,
            cargo_t=cargo_t,
            truck_key=truck_key,
            ors_profile=ors_profile,
            vessel_class=vessel_class,
            include_hoteling=include_hoteling,
            hoteling_hours_per_call=hoteling_hours_per_call,
            port_calls=port_calls,
            include_port_ops=include_port_ops,
            port_moves_per_call=port_moves_per_call,
            cargo_teu=cargo_teu,
            t_per_teu_default=t_per_teu_default,
            allocation_mode=allocation_mode,
            allocation_load_factor=allocation_load_factor,
            full_call_mode=full_call_mode,
            port_ops_scenario=port_ops_scenario,
            port_origin_name=(None if not isinstance(port_origin, dict) else port_origin.get("name")),
            port_destiny_name=(None if not isinstance(port_destiny, dict) else port_destiny.get("name")),
            status=status,
            error_message=error_message,
            geometry_status=(None if not isinstance(geo, dict) else geo.get("status")),
            road_direct_source=(None if not isinstance(geo, dict) else geo.get("road_direct", {}).get("source")),
            first_mile_source=(None if not isinstance(geo, dict) else geo.get("first_mile", {}).get("source")),
            last_mile_source=(None if not isinstance(geo, dict) else geo.get("last_mile", {}).get("source")),
            road_direct_profile_used=(
                None if not isinstance(geo, dict) else geo.get("road_direct", {}).get("profile_used")
            ),
            first_mile_profile_used=(
                None if not isinstance(geo, dict) else geo.get("first_mile", {}).get("profile_used")
            ),
            last_mile_profile_used=(
                None if not isinstance(geo, dict) else geo.get("last_mile", {}).get("profile_used")
            ),
            is_approximation=is_approximation,
            route_source=resolved_route_source,
            approximation_reference_destiny=approximation_reference_destiny,
            approximation_reference_distance_km=approximation_reference_distance_km,
            approximation_delta_straight_line_km=approximation_delta_straight_line_km,
            approximation_notes=approximation_notes,
            road_distance_km=flat.get("road_distance_km"),
            road_fuel_liters=flat.get("road_fuel_liters"),
            road_fuel_kg=flat.get("road_fuel_kg"),
            road_fuel_cost_r=road_cost_r,
            road_co2e_kg=road_emissions_kg,
            mm_road_fuel_liters=flat.get("mm_road_fuel_liters"),
            mm_road_fuel_kg=flat.get("mm_road_fuel_kg"),
            mm_road_fuel_cost_r=flat.get("mm_road_fuel_cost_r"),
            mm_road_co2e_kg=flat.get("mm_road_co2e_kg"),
            sea_km=flat.get("sea_km"),
            sea_fuel_kg=flat.get("sea_fuel_kg"),
            sea_fuel_cost_r=flat.get("sea_fuel_cost_r"),
            sea_co2e_kg=flat.get("sea_co2e_kg"),
            total_fuel_kg=flat.get("total_fuel_kg"),
            total_fuel_cost_r=multimodal_cost_r,
            total_co2e_kg=multimodal_emissions_kg,
            delta_cost_r=flat.get("delta_cost_r"),
            delta_co2e_kg=flat.get("delta_co2e_kg"),
            savings_pct=(None if not isinstance(res, dict) else res.get("comparison", {}).get("savings_pct")),
            emissions_savings_pct=emissions_savings_pct,
            diesel_price_r_per_l=inputs.get("diesel_price"),
            diesel_price_source=inputs.get("diesel_price_source"),
            bunker_price_r_per_t=inputs.get("bunker_price"),
        )
        insert_bulk_run_result(
            conn,
            table_name=run_results_table,
            run_id=run_id,
            scenario_key=scenario_key,
            origin_key=ascii_place_key(origin_name),
            origin_name=origin_name,
            origin_lat=origin_point.get("lat"),
            origin_lon=origin_point.get("lon"),
            origin_uf=origin_point.get("uf"),
            destiny_key=ascii_place_key(destiny_name),
            destiny_name=destiny_name,
            destiny_lat=destiny_point.get("lat"),
            destiny_lon=destiny_point.get("lon"),
            destiny_uf=destiny_point.get("uf"),
            input_origin=input_origin,
            input_destiny=input_destiny,
            destination_set_id=destination_set_id,
            port_origin_name=(None if not isinstance(port_origin, dict) else port_origin.get("name")),
            port_destiny_name=(None if not isinstance(port_destiny, dict) else port_destiny.get("name")),
            status=status,
            error_message=error_message,
            road_cost_r=road_cost_r,
            multimodal_cost_r=multimodal_cost_r,
            cost_delta_r=cost_delta_r,
            cost_savings_pct=(None if not isinstance(res, dict) else res.get("comparison", {}).get("savings_pct")),
            road_emissions_kg=road_emissions_kg,
            multimodal_emissions_kg=multimodal_emissions_kg,
            emissions_delta_kg=emissions_delta_kg,
            emissions_savings_pct=emissions_savings_pct,
            road_distance_km=flat.get("road_distance_km"),
            sea_km=flat.get("sea_km"),
            is_approximation=is_approximation,
            route_source=resolved_route_source,
            approximation_reference_destiny=approximation_reference_destiny,
            approximation_reference_distance_km=approximation_reference_distance_km,
            approximation_delta_straight_line_km=approximation_delta_straight_line_km,
            approximation_notes=approximation_notes,
        )


def run_bulk_evaluation(
    origin: str,
    dest_list: List[str],
    *,
    cargo_t: float,
    truck_key: str,
    profile: str,
    overwrite_road: bool = False,
    db_path: Path | str | None = None,
    results_table: str = DEFAULT_BULK_RESULTS_TABLE,
    runs_table: str = DEFAULT_BULK_RUNS_TABLE,
    run_results_table: str = DEFAULT_BULK_RUN_RESULTS_TABLE,
    destination_set_id: str = "ad_hoc",
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    port_moves_per_call: Optional[float],
    cargo_teu: Optional[float],
    t_per_teu_default: float,
    allocation_mode: Optional[str],
    allocation_load_factor: float,
    full_call_mode: bool,
    port_ops_scenario: str,
    progress_callback: Optional[ProgressCallback] = None,
    shuffle_destinations: bool = True,
    shuffle_seed: Optional[int] = None,
    approximation_fallback: bool = True,
) -> Dict[str, Any]:
    """Run the bulk comparison flow with exact routing first and bulk-only approximation fallback."""
    deduped_destinations = _dedupe_preserve_order(dest_list)
    if not deduped_destinations:
        return {
            "summary_rows": [],
            "success_count": 0,
            "fail_count": 0,
            "exact_success_count": 0,
            "approximated_success_count": 0,
            "unresolved_fail_count": 0,
            "duration_s": 0.0,
            "run_id": None,
            "shuffle_seed_used": None,
        }

    shuffled_destinations, shuffle_seed_used = _shuffle_destinations(
        deduped_destinations,
        enabled=shuffle_destinations,
        seed=shuffle_seed,
    )

    t0_global = time.time()
    summary_rows: List[Dict[str, Any]] = []
    pending_approximations: List[PendingApproximation] = []
    exact_references: List[ExactRoadReference] = []
    exact_success_count = 0
    approximated_success_count = 0
    unresolved_fail_count = 0
    success_count = 0
    fail_count = 0
    run_id: Optional[str] = None

    _log.info(
        (
            "Starting bulk evaluation: origin=%r destinations=%d destination_set=%s "
            "shuffle=%s shuffle_seed=%s approximation_fallback=%s"
        ),
        origin,
        len(shuffled_destinations),
        destination_set_id,
        shuffle_destinations,
        (shuffle_seed_used if shuffle_seed_used is not None else "disabled"),
        approximation_fallback,
    )
    _emit_progress(
        progress_callback,
        phase="start",
        current=0,
        total=len(shuffled_destinations),
        shuffle_seed_used=shuffle_seed_used,
        approximation_fallback=approximation_fallback,
        message="Preparing routing assets...",
    )

    ors, ports, sea_matrix, resolved_db_path = load_routing_assets(db_path=db_path)
    origin_pt = resolve_point_for_geometry(origin, ors, db_path=resolved_db_path)
    if not origin_pt:
        raise RuntimeError(f"Failed to resolve bulk origin: {origin}")
    origin_input_norm = normalize_bulk_place_input(origin)

    origin_port = find_nearest_port(origin_pt["lat"], origin_pt["lon"], ports)
    origin_port_node = build_port_node(origin_port)
    first_mile_leg = get_or_create_leg(
        ors,
        origin_pt,
        origin_port_node,
        profile=profile,
        overwrite=overwrite_road,
        db_path=resolved_db_path,
    )
    _require_distance(first_mile_leg, "first_mile")

    run_selector = _build_run_selector(
        origin_name=origin_pt["label"],
        cargo_t=cargo_t,
        truck_key=truck_key,
        profile=profile,
        vessel_class=vessel_class,
        include_hoteling=include_hoteling,
        hoteling_hours_per_call=hoteling_hours_per_call,
        port_calls=port_calls,
        include_port_ops=include_port_ops,
        port_moves_per_call=port_moves_per_call,
        cargo_teu=cargo_teu,
        t_per_teu_default=t_per_teu_default,
        allocation_mode=allocation_mode,
        allocation_load_factor=allocation_load_factor,
        full_call_mode=full_call_mode,
        port_ops_scenario=port_ops_scenario,
        destination_set_id=destination_set_id,
    )

    evaluation_kwargs = {
        "cargo_t": cargo_t,
        "truck_key": truck_key,
        "vessel_class": vessel_class,
        "include_hoteling": include_hoteling,
        "hoteling_hours_per_call": hoteling_hours_per_call,
        "port_calls": port_calls,
        "include_port_ops": include_port_ops,
        "port_moves_per_call": port_moves_per_call,
        "cargo_teu": cargo_teu,
        "t_per_teu_default": t_per_teu_default,
        "allocation_mode": allocation_mode,
        "allocation_load_factor": allocation_load_factor,
        "full_call_mode": full_call_mode,
        "port_ops_scenario": port_ops_scenario,
    }
    evaluation_kwargs["prepared_context"] = prepare_evaluation_context(
        truck_key=truck_key,
        vessel_class=vessel_class,
        include_hoteling=include_hoteling,
        hoteling_hours_per_call=hoteling_hours_per_call,
        port_calls=port_calls,
        include_port_ops=include_port_ops,
        port_ops_scenario=port_ops_scenario,
    )
    _log.info(
        (
            "Bulk evaluation context ready: origin=%s truck=%s vessel_class=%s "
            "hoteling=%s port_ops=%s"
        ),
        origin_pt["label"],
        truck_key,
        vessel_class,
        include_hoteling,
        include_port_ops,
    )

    with db_session(resolved_db_path) as conn:
        run_id = start_bulk_run(
            conn,
            selector=run_selector,
            origin_name=origin_pt["label"],
            input_origin=origin_input_norm,
            destination_count=len(shuffled_destinations),
            table_name=runs_table,
        )

    try:
        for index, destiny_input in enumerate(shuffled_destinations, start=1):
            scenario_payload = {
                "input_origin": origin_input_norm,
                "input_destiny": normalize_bulk_place_input(destiny_input),
                "cargo_t": float(cargo_t),
                "truck_key": str(truck_key),
                "ors_profile": str(profile),
                "vessel_class": str(vessel_class),
                "include_hoteling": bool(include_hoteling),
                "hoteling_hours_per_call": float(hoteling_hours_per_call),
                "port_calls": int(port_calls),
                "include_port_ops": bool(include_port_ops),
                "port_moves_per_call": port_moves_per_call,
                "cargo_teu": cargo_teu,
                "t_per_teu_default": float(t_per_teu_default),
                "allocation_mode": allocation_mode,
                "allocation_load_factor": float(allocation_load_factor),
                "full_call_mode": bool(full_call_mode),
                "port_ops_scenario": str(port_ops_scenario),
            }
            scenario_key = build_bulk_scenario_key(scenario_payload)
            destiny_name = str(destiny_input).strip()
            geo: Optional[Dict[str, Any]] = None

            _log.info("[%d/%d] Exact routing attempt for destination: %s", index, len(shuffled_destinations), destiny_input)
            t0 = time.time()
            _emit_progress(
                progress_callback,
                phase="progress",
                pass_name="exact",
                current=index - 1,
                total=len(shuffled_destinations),
                destination=str(destiny_input),
                success_count=success_count,
                fail_count=fail_count,
                exact_success_count=exact_success_count,
                approximated_success_count=approximated_success_count,
                message=f"Exact routing for {destiny_input} ({index}/{len(shuffled_destinations)})",
            )

            try:
                destiny_pt = resolve_point_for_geometry(destiny_input, ors, db_path=resolved_db_path)
                if not destiny_pt:
                    raise RuntimeError(f"Failed to resolve destination: {destiny_input}")

                destiny_name = destiny_pt["label"]
                geo = build_path_geometry_from_resolved(
                    origin_pt,
                    destiny_pt,
                    ors=ors,
                    ports=ports,
                    sea_matrix=sea_matrix,
                    ors_profile=profile,
                    overwrite_road=overwrite_road,
                    db_path=resolved_db_path,
                    port_origin=origin_port,
                    first_mile_leg=first_mile_leg,
                )
                if not geo or geo.get("status") != "ok":
                    raise RuntimeError("Geometry build failed")

                _require_distance(geo["last_mile"], "last_mile")

                if geo["road_direct"].get("distance_km") is None:
                    if approximation_fallback:
                        pending_approximations.append(
                            PendingApproximation(
                                index=index,
                                destiny_input=str(destiny_input),
                                destiny_name=destiny_name,
                                scenario_key=scenario_key,
                                scenario_payload=scenario_payload,
                                geo=geo,
                                failure_status="no_road_route",
                                error_message="road_direct road distance is unavailable",
                            )
                        )
                        _log.warning(
                            "Exact road route unavailable for %s; queued for approximation pass.",
                            destiny_name,
                        )
                        continue
                    raise RuntimeError("road_direct road distance is unavailable")

                _log.info(
                    "Leg sources for %s: direct=%s first=%s last=%s",
                    destiny_name,
                    geo["road_direct"].get("source"),
                    geo["first_mile"].get("source"),
                    geo["last_mile"].get("source"),
                )

                res, flat = _evaluate_and_flatten(
                    geo,
                    origin_name=origin_pt["label"],
                    destiny_name=destiny_name,
                    evaluation_kwargs=evaluation_kwargs,
                )
                route_source = _route_source_for_result(geo, is_approximation=False)
                _safe_persist_bulk_outcome(
                    str(destiny_input),
                    status="ok",
                    db_path=resolved_db_path,
                    table_name=results_table,
                    run_results_table=run_results_table,
                    run_id=str(run_id),
                    destination_set_id=destination_set_id,
                    scenario_key=scenario_key,
                    input_origin=scenario_payload["input_origin"],
                    input_destiny=scenario_payload["input_destiny"],
                    origin_name=origin_pt["label"],
                    destiny_name=destiny_name,
                    truck_key=truck_key,
                    ors_profile=profile,
                    cargo_t=cargo_t,
                    vessel_class=vessel_class,
                    include_hoteling=include_hoteling,
                    hoteling_hours_per_call=hoteling_hours_per_call,
                    port_calls=port_calls,
                    include_port_ops=include_port_ops,
                    port_moves_per_call=port_moves_per_call,
                    cargo_teu=cargo_teu,
                    t_per_teu_default=t_per_teu_default,
                    allocation_mode=allocation_mode,
                    allocation_load_factor=allocation_load_factor,
                    full_call_mode=full_call_mode,
                    port_ops_scenario=port_ops_scenario,
                    geo=geo,
                    res=res,
                    flat=flat,
                    is_approximation=False,
                    route_source=route_source,
                )

                reference = _make_exact_reference(geo, flat)
                if reference is None:
                    _log.warning(
                        "Exact bulk success for %s is missing coordinates or road distance and will not be used as an approximation reference.",
                        destiny_name,
                    )
                else:
                    exact_references.append(reference)

                summary_rows.append(
                    _build_success_summary_row(
                        str(destiny_input),
                        geo,
                        res,
                        flat,
                        is_approximation=False,
                        route_source=route_source,
                        approximation_meta=None,
                    )
                )
                success_count += 1
                exact_success_count += 1
                _log.info(
                    "Completed exact route for %s in %.2fs savings_pct=%.2f route_source=%s",
                    destiny_name,
                    time.time() - t0,
                    float(res.get("comparison", {}).get("savings_pct") or 0.0),
                    route_source or "<missing>",
                )
            except Exception as exc:
                fail_count += 1
                unresolved_fail_count += 1
                failure_status, failure_message, log_trace = _classify_failure(exc)
                if log_trace:
                    _log.error("Bulk destination failed: %s", failure_message, exc_info=True)
                else:
                    _log.warning("Bulk destination skipped: %s (%s)", destiny_input, failure_message)
                _safe_persist_bulk_outcome(
                    str(destiny_input),
                    status=failure_status,
                    db_path=resolved_db_path,
                    table_name=results_table,
                    run_results_table=run_results_table,
                    run_id=str(run_id),
                    destination_set_id=destination_set_id,
                    scenario_key=scenario_key,
                    input_origin=scenario_payload["input_origin"],
                    input_destiny=scenario_payload["input_destiny"],
                    origin_name=origin_pt["label"],
                    destiny_name=destiny_name,
                    truck_key=truck_key,
                    ors_profile=profile,
                    cargo_t=cargo_t,
                    vessel_class=vessel_class,
                    include_hoteling=include_hoteling,
                    hoteling_hours_per_call=hoteling_hours_per_call,
                    port_calls=port_calls,
                    include_port_ops=include_port_ops,
                    port_moves_per_call=port_moves_per_call,
                    cargo_teu=cargo_teu,
                    t_per_teu_default=t_per_teu_default,
                    allocation_mode=allocation_mode,
                    allocation_load_factor=allocation_load_factor,
                    full_call_mode=full_call_mode,
                    port_ops_scenario=port_ops_scenario,
                    error_message=failure_message,
                    geo=geo,
                    is_approximation=False,
                )
                summary_rows.append(
                    _build_failure_summary_row(
                        str(destiny_input),
                        destiny_name,
                        status=failure_status,
                        error_message=failure_message,
                    )
                )
            finally:
                _emit_progress(
                    progress_callback,
                    phase="progress",
                    pass_name="exact",
                    current=index,
                    total=len(shuffled_destinations),
                    destination=str(destiny_input),
                    success_count=success_count,
                    fail_count=fail_count,
                    exact_success_count=exact_success_count,
                    approximated_success_count=approximated_success_count,
                    pending_approximations=len(pending_approximations),
                )

        _log.info(
            (
                "Bulk exact pass complete: total=%d exact_success=%d queued_for_approximation=%d "
                "unresolved_failures=%d"
            ),
            len(shuffled_destinations),
            exact_success_count,
            len(pending_approximations),
            unresolved_fail_count,
        )

        if pending_approximations:
            _emit_progress(
                progress_callback,
                phase="approximation_start",
                current=0,
                total=len(pending_approximations),
                success_count=success_count,
                fail_count=fail_count,
                exact_success_count=exact_success_count,
                approximated_success_count=approximated_success_count,
                message="Starting approximation fallback pass.",
            )

        for approx_index, pending in enumerate(pending_approximations, start=1):
            approximation_message = (
                f"Approximation pass for {pending.destiny_input} ({approx_index}/{len(pending_approximations)})"
            )
            _emit_progress(
                progress_callback,
                phase="progress",
                pass_name="approximation",
                current=approx_index - 1,
                total=len(pending_approximations),
                destination=pending.destiny_input,
                success_count=success_count,
                fail_count=fail_count,
                exact_success_count=exact_success_count,
                approximated_success_count=approximated_success_count,
                message=approximation_message,
            )

            try:
                if not exact_references:
                    raise RuntimeError(
                        "Approximation fallback unavailable: no exact successful road routes were solved in this bulk run"
                    )

                destiny_point = pending.geo.get("destiny", {})
                reference = _select_nearest_exact_reference(destiny_point, exact_references)
                if reference is None:
                    raise RuntimeError(
                        "Approximation fallback unavailable: destination coordinates are missing for nearest-reference selection"
                    )

                estimated_distance_km, approximation_meta = _estimate_road_distance_from_reference(
                    origin_pt,
                    destiny_point,
                    reference,
                )
                approx_geo = _build_approximated_geometry(pending.geo, estimated_distance_km)
                res, flat = _evaluate_and_flatten(
                    approx_geo,
                    origin_name=origin_pt["label"],
                    destiny_name=pending.destiny_name,
                    evaluation_kwargs=evaluation_kwargs,
                )

                _safe_persist_bulk_outcome(
                    pending.destiny_input,
                    status="ok",
                    db_path=resolved_db_path,
                    table_name=results_table,
                    run_results_table=run_results_table,
                    run_id=str(run_id),
                    destination_set_id=destination_set_id,
                    scenario_key=pending.scenario_key,
                    input_origin=pending.scenario_payload["input_origin"],
                    input_destiny=pending.scenario_payload["input_destiny"],
                    origin_name=origin_pt["label"],
                    destiny_name=pending.destiny_name,
                    truck_key=truck_key,
                    ors_profile=profile,
                    cargo_t=cargo_t,
                    vessel_class=vessel_class,
                    include_hoteling=include_hoteling,
                    hoteling_hours_per_call=hoteling_hours_per_call,
                    port_calls=port_calls,
                    include_port_ops=include_port_ops,
                    port_moves_per_call=port_moves_per_call,
                    cargo_teu=cargo_teu,
                    t_per_teu_default=t_per_teu_default,
                    allocation_mode=allocation_mode,
                    allocation_load_factor=allocation_load_factor,
                    full_call_mode=full_call_mode,
                    port_ops_scenario=port_ops_scenario,
                    geo=approx_geo,
                    res=res,
                    flat=flat,
                    is_approximation=True,
                    route_source=approximation_meta.route_source,
                    approximation_reference_destiny=approximation_meta.reference_destiny,
                    approximation_reference_distance_km=approximation_meta.reference_distance_km,
                    approximation_delta_straight_line_km=approximation_meta.delta_straight_line_km,
                    approximation_notes=approximation_meta.notes,
                )

                summary_rows.append(
                    _build_success_summary_row(
                        pending.destiny_input,
                        approx_geo,
                        res,
                        flat,
                        is_approximation=True,
                        route_source=approximation_meta.route_source,
                        approximation_meta=approximation_meta,
                    )
                )
                success_count += 1
                approximated_success_count += 1
                _log.info(
                    (
                        "Approximated %s using reference=%s reference_distance_km=%.3f "
                        "signed_delta_km=%+.3f estimated_road_distance_km=%.3f"
                    ),
                    pending.destiny_name,
                    approximation_meta.reference_destiny,
                    approximation_meta.reference_distance_km,
                    approximation_meta.delta_straight_line_km,
                    estimated_distance_km,
                )
            except Exception as exc:
                fail_count += 1
                unresolved_fail_count += 1
                approximation_failure = str(exc).strip() or "Approximation fallback failed"
                combined_error = f"{pending.error_message}; {approximation_failure}"
                _log.warning("Approximation unavailable for %s: %s", pending.destiny_input, approximation_failure)
                _safe_persist_bulk_outcome(
                    pending.destiny_input,
                    status=pending.failure_status,
                    db_path=resolved_db_path,
                    table_name=results_table,
                    run_results_table=run_results_table,
                    run_id=str(run_id),
                    destination_set_id=destination_set_id,
                    scenario_key=pending.scenario_key,
                    input_origin=pending.scenario_payload["input_origin"],
                    input_destiny=pending.scenario_payload["input_destiny"],
                    origin_name=origin_pt["label"],
                    destiny_name=pending.destiny_name,
                    truck_key=truck_key,
                    ors_profile=profile,
                    cargo_t=cargo_t,
                    vessel_class=vessel_class,
                    include_hoteling=include_hoteling,
                    hoteling_hours_per_call=hoteling_hours_per_call,
                    port_calls=port_calls,
                    include_port_ops=include_port_ops,
                    port_moves_per_call=port_moves_per_call,
                    cargo_teu=cargo_teu,
                    t_per_teu_default=t_per_teu_default,
                    allocation_mode=allocation_mode,
                    allocation_load_factor=allocation_load_factor,
                    full_call_mode=full_call_mode,
                    port_ops_scenario=port_ops_scenario,
                    error_message=combined_error,
                    geo=pending.geo,
                    is_approximation=False,
                    approximation_notes=approximation_failure,
                )
                summary_rows.append(
                    _build_failure_summary_row(
                        pending.destiny_input,
                        pending.destiny_name,
                        status=pending.failure_status,
                        error_message=combined_error,
                        approximation_notes=approximation_failure,
                    )
                )
            finally:
                _emit_progress(
                    progress_callback,
                    phase="progress",
                    pass_name="approximation",
                    current=approx_index,
                    total=len(pending_approximations),
                    destination=pending.destiny_input,
                    success_count=success_count,
                    fail_count=fail_count,
                    exact_success_count=exact_success_count,
                    approximated_success_count=approximated_success_count,
                )
    except Exception as exc:
        duration = time.time() - t0_global
        if run_id is not None:
            with db_session(resolved_db_path) as conn:
                finish_bulk_run(
                    conn,
                    run_id=str(run_id),
                    status="failed",
                    success_count=success_count,
                    fail_count=fail_count,
                    duration_s=duration,
                    error_message=str(exc),
                    table_name=runs_table,
                )
        _emit_progress(
            progress_callback,
            phase="error",
            current=success_count + fail_count,
            total=len(shuffled_destinations),
            success_count=success_count,
            fail_count=fail_count,
            exact_success_count=exact_success_count,
            approximated_success_count=approximated_success_count,
            message=str(exc),
        )
        raise

    duration = time.time() - t0_global
    if run_id is not None:
        with db_session(resolved_db_path) as conn:
            finish_bulk_run(
                conn,
                run_id=str(run_id),
                status="completed",
                success_count=success_count,
                fail_count=fail_count,
                duration_s=duration,
                error_message=None,
                table_name=runs_table,
            )
    _emit_progress(
        progress_callback,
        phase="complete",
        current=len(shuffled_destinations),
        total=len(shuffled_destinations),
        success_count=success_count,
        fail_count=fail_count,
        exact_success_count=exact_success_count,
        approximated_success_count=approximated_success_count,
        unresolved_fail_count=unresolved_fail_count,
        duration_s=duration,
        run_id=run_id,
        shuffle_seed_used=shuffle_seed_used,
        message="Bulk evaluation finished.",
    )
    _log.info(
        (
            "Bulk evaluation complete: total=%d exact_success=%d approximated_success=%d "
            "unresolved_failures=%d duration_s=%.2f run_id=%s"
        ),
        len(shuffled_destinations),
        exact_success_count,
        approximated_success_count,
        unresolved_fail_count,
        duration,
        run_id,
    )
    return {
        "summary_rows": summary_rows,
        "success_count": success_count,
        "fail_count": fail_count,
        "exact_success_count": exact_success_count,
        "approximated_success_count": approximated_success_count,
        "unresolved_fail_count": unresolved_fail_count,
        "duration_s": duration,
        "run_id": run_id,
        "shuffle_seed_used": shuffle_seed_used,
    }
