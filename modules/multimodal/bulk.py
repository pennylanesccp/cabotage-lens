from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
from modules.multimodal.evaluator import evaluate_path
from modules.multimodal.persistence import flatten_evaluation_for_db
from modules.multimodal.scenario_keys import build_bulk_scenario_key, normalize_bulk_place_input
from modules.ports.ports_nearest import find_nearest_port
from modules.road.router import get_or_create_leg

_log = get_logger(__name__)
ProgressCallback = Callable[[Dict[str, Any]], None]


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



def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    duplicates = 0

    for value in values:
        key = str(value).strip()
        if not key:
            continue
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        ordered.append(key)

    if duplicates:
        _log.warning("Skipped %d duplicated destination entries in bulk input.", duplicates)

    return ordered



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

    if "road distance is unavailable" in lowered:
        return "no_road_route", message, False
    if "failed to resolve destination" in lowered:
        return "geocode_failed", message, False

    return "error", message, True



def _build_summary_row(destiny_input: str, geo: Dict[str, Any], res: Dict[str, Any], flat: Dict[str, Any]) -> Dict[str, Any]:
    inputs = res.get("inputs", {})
    comparison = res.get("comparison", {})

    return {
        "destiny_input": destiny_input,
        "destiny_name": geo["destiny"]["label"],
        "status": "ok",
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
            road_direct_profile_used=(None if not isinstance(geo, dict) else geo.get("road_direct", {}).get("profile_used")),
            first_mile_profile_used=(None if not isinstance(geo, dict) else geo.get("first_mile", {}).get("profile_used")),
            last_mile_profile_used=(None if not isinstance(geo, dict) else geo.get("last_mile", {}).get("profile_used")),
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
) -> Dict[str, Any]:
    """Run the bulk comparison flow and persist analytical outputs."""
    deduped_destinations = _dedupe_preserve_order(dest_list)
    if not deduped_destinations:
        return {"summary_rows": [], "success_count": 0, "fail_count": 0, "duration_s": 0.0, "run_id": None}

    t0_global = time.time()
    summary_rows: List[Dict[str, Any]] = []
    success_count = 0
    fail_count = 0
    run_id: Optional[str] = None

    _log.info(
        "Starting bulk evaluation: origin=%r destinations=%d destination_set=%s",
        origin,
        len(deduped_destinations),
        destination_set_id,
    )
    _emit_progress(
        progress_callback,
        phase="start",
        current=0,
        total=len(deduped_destinations),
        message="Preparing routing assets...",
    )

    ors, ports, sea_matrix, resolved_db_path = load_routing_assets(db_path=db_path)
    origin_pt = resolve_point_for_geometry(origin, ors)
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

    with db_session(resolved_db_path) as conn:
        run_id = start_bulk_run(
            conn,
            selector=run_selector,
            origin_name=origin_pt["label"],
            input_origin=origin_input_norm,
            destination_count=len(deduped_destinations),
            table_name=runs_table,
        )

    try:
        for index, destiny_input in enumerate(deduped_destinations, start=1):
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
            res: Optional[Dict[str, Any]] = None
            flat: Optional[Dict[str, Any]] = None

            _log.info("[%d/%d] Processing destination: %s", index, len(deduped_destinations), destiny_input)
            t0 = time.time()
            _emit_progress(
                progress_callback,
                phase="progress",
                current=index - 1,
                total=len(deduped_destinations),
                destination=str(destiny_input),
                message=f"Processing {destiny_input} ({index}/{len(deduped_destinations)})",
            )

            try:
                destiny_pt = resolve_point_for_geometry(destiny_input, ors)
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

                _require_distance(geo["road_direct"], "road_direct")
                _require_distance(geo["last_mile"], "last_mile")

                _log.info(
                    "Leg sources for %s: direct=%s first=%s last=%s",
                    destiny_name,
                    geo["road_direct"].get("source"),
                    geo["first_mile"].get("source"),
                    geo["last_mile"].get("source"),
                )

                res = evaluate_path(
                    geo,
                    cargo_t=cargo_t,
                    truck_key=truck_key,
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
                )
                if not res:
                    raise RuntimeError("Path evaluation failed")

                flat = flatten_evaluation_for_db(origin_pt["label"], destiny_name, res)
                try:
                    _persist_bulk_outcome(
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
                        status="ok",
                        geo=geo,
                        res=res,
                        flat=flat,
                    )
                except Exception as persist_exc:
                    _log.error(
                        "Failed to persist bulk success outcome for %s: %s",
                        destiny_input,
                        persist_exc,
                        exc_info=True,
                    )

                summary_rows.append(_build_summary_row(str(destiny_input), geo, res, flat))
                success_count += 1
                _log.info(
                    "Completed %s in %.2fs savings_pct=%.2f",
                    destiny_name,
                    time.time() - t0,
                    float(res.get("comparison", {}).get("savings_pct") or 0.0),
                )
            except Exception as exc:
                fail_count += 1
                failure_status, failure_message, log_trace = _classify_failure(exc)
                if log_trace:
                    _log.error("Bulk destination failed: %s", failure_message, exc_info=True)
                else:
                    _log.warning("Bulk destination skipped: %s (%s)", destiny_input, failure_message)
                try:
                    _persist_bulk_outcome(
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
                        status=failure_status,
                        error_message=failure_message,
                        geo=geo,
                        res=res,
                        flat=flat,
                    )
                except Exception as persist_exc:
                    _log.error(
                        "Failed to persist bulk error outcome for %s: %s",
                        destiny_input,
                        persist_exc,
                        exc_info=True,
                    )
                summary_rows.append(
                    {
                        "destiny_input": str(destiny_input),
                        "destiny_name": destiny_name,
                        "status": failure_status,
                        "error_msg": failure_message,
                    }
                )
            finally:
                _emit_progress(
                    progress_callback,
                    phase="progress",
                    current=index,
                    total=len(deduped_destinations),
                    destination=str(destiny_input),
                    success_count=success_count,
                    fail_count=fail_count,
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
            total=len(deduped_destinations),
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
        current=len(deduped_destinations),
        total=len(deduped_destinations),
        success_count=success_count,
        fail_count=fail_count,
        duration_s=duration,
        run_id=run_id,
        message="Bulk evaluation finished.",
    )
    _log.info(
        "Bulk evaluation complete: success=%d fail=%d duration_s=%.2f run_id=%s",
        success_count,
        fail_count,
        duration,
        run_id,
    )
    return {
        "summary_rows": summary_rows,
        "success_count": success_count,
        "fail_count": fail_count,
        "duration_s": duration,
        "run_id": run_id,
    }
