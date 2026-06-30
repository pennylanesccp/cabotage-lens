from __future__ import annotations

import math
from typing import Any, Callable, Dict, Mapping, Tuple

from modules.infra.log_manager import get_logger
from modules.multimodal import build_path_geometry, evaluate_path

from app.main.utils.state import resolve_runtime_db_target

_log = get_logger("streamlit_app")
_ProgressCallback = Callable[[dict[str, Any]], None]


def build_scenario_payload(session_state: Mapping[str, Any]) -> Dict[str, Any]:
    cargo_teu_value = float(session_state.get("cargo_teu_input", 0.0))
    t_per_teu_default = max(float(session_state.get("t_per_teu_default", 14.0)), 0.1)
    allocation_mode = str(session_state.get("allocation_mode", "auto")).strip().lower()
    allocation_load_factor = min(max(float(session_state.get("allocation_load_factor", 0.8)), 0.01), 1.0)

    payload = {
        "origin": str(session_state.get("origin", "")).strip(),
        "destiny": str(session_state.get("destiny", "")).strip(),
        "cargo_t": float(session_state.get("cargo_t", 0.0)),
        "cargo_teu": None if cargo_teu_value <= 0.0 else cargo_teu_value,
        "t_per_teu_default": t_per_teu_default,
        "allocation_mode": None if allocation_mode == "auto" else allocation_mode,
        "allocation_load_factor": allocation_load_factor,
        "truck_key": str(session_state.get("truck_key", "")),
        "ors_profile": "driving-car",
        "overwrite_road": bool(session_state.get("overwrite_road", False)),
        "vessel_class": str(session_state.get("vessel_class", "")),
        "include_hoteling": bool(session_state.get("include_hoteling", True)),
        "hoteling_hours_per_call": float(session_state.get("hoteling_hours_per_call", 14.0)),
        "port_calls": int(session_state.get("port_calls", 2)),
        "include_port_ops": bool(session_state.get("include_port_ops", True)),
        "full_call_mode": bool(session_state.get("full_call_mode", False)),
        "port_moves_per_call": (
            None
            if float(session_state.get("port_moves_per_call_input", 0.0)) <= 0.0
            else float(session_state.get("port_moves_per_call_input", 0.0))
        ),
        "port_ops_scenario": str(session_state.get("port_ops_scenario", "")),
    }

    observed_ports = session_state.get("port_ops_observed_ports")
    if observed_ports:
        payload["port_ops_observed_ports"] = observed_ports

    return payload


def resolve_cargo_teu(payload: Mapping[str, Any]) -> int:
    cargo_teu = payload.get("cargo_teu")
    if isinstance(cargo_teu, (int, float)) and float(cargo_teu) > 0:
        return max(int(math.ceil(float(cargo_teu))), 1)
    cargo_t = max(float(payload.get("cargo_t") or 0.0), 0.0)
    t_per_teu_default = max(float(payload.get("t_per_teu_default") or 14.0), 0.1)
    return max(int(math.ceil(cargo_t / t_per_teu_default)), 1) if cargo_t > 0 else 0


def run_analysis(
    payload: Mapping[str, Any],
    *,
    progress_callback: _ProgressCallback | None = None,
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None, str | None, str]:
    total_steps = 3

    def _emit_progress(message: str, *, current: int, phase: str = "working") -> None:
        if progress_callback is None:
            return
        progress_callback(
            {
                "phase": phase,
                "message": message,
                "current": current,
                "total": total_steps,
            }
        )

    _log.info(
        (
            "Single analysis start origin=%s destiny=%s cargo_t=%.3f truck=%s profile=%s "
            "allocation_mode=%s"
        ),
        payload["origin"],
        payload["destiny"],
        payload["cargo_t"],
        payload["truck_key"],
        payload["ors_profile"],
        payload["allocation_mode"] or "auto",
    )
    _emit_progress("Preparing router analysis...", current=0)

    db_target = resolve_runtime_db_target()

    _emit_progress("Building route geometry...", current=0)
    geo = build_path_geometry(
        payload["origin"],
        payload["destiny"],
        ors_profile=payload["ors_profile"],
        overwrite_road=payload["overwrite_road"],
        cooldown_callback=progress_callback,
    )
    if not geo or geo.get("status") != "ok":
        _log.error("Failed to build route geometry.")
        _emit_progress("Failed to build route geometry.", current=0, phase="error")
        return None, None, "Failed to build route geometry. Check inputs and API key.", str(db_target)
    _emit_progress("Route geometry ready.", current=1)

    _log.info(
        (
            "Single analysis geometry origin=%s destiny=%s direct_source=%s first_mile_source=%s "
            "last_mile_source=%s"
        ),
        geo["origin"]["label"],
        geo["destiny"]["label"],
        geo["road_direct"].get("source"),
        geo["first_mile"].get("source"),
        geo["last_mile"].get("source"),
    )

    _log.info("Calculating costs and emissions...")
    _emit_progress("Calculating costs and emissions...", current=1)
    results = evaluate_path(
        geo,
        cargo_t=payload["cargo_t"],
        truck_key=payload["truck_key"],
        vessel_class=payload["vessel_class"],
        include_hoteling=payload["include_hoteling"],
        hoteling_hours_per_call=payload["hoteling_hours_per_call"],
        port_calls=payload["port_calls"],
        include_port_ops=payload["include_port_ops"],
        port_moves_per_call=payload["port_moves_per_call"],
        cargo_teu=payload["cargo_teu"],
        t_per_teu_default=payload["t_per_teu_default"],
        allocation_mode=payload["allocation_mode"],
        allocation_load_factor=payload["allocation_load_factor"],
        full_call_mode=payload["full_call_mode"],
        port_ops_scenario=payload["port_ops_scenario"],
        port_ops_observed_ports=payload.get("port_ops_observed_ports"),
    )
    if not results:
        _log.error("Failed to evaluate route.")
        _emit_progress("Failed to evaluate route.", current=1, phase="error")
        return (
            geo,
            None,
            "Failed to evaluate route. Ensure the required cabotage data assets are available locally or in Supabase Storage.",
            str(db_target),
        )
    _emit_progress("Route evaluation completed.", current=2)

    comparison = results.get("comparison", {})
    road_only = results.get("road_only", {})
    multimodal = results.get("multimodal", {})
    emissions_savings_pct = None
    road_total_co2e = road_only.get("co2e")
    multimodal_total_co2e = multimodal.get("total_co2e")
    if isinstance(road_total_co2e, (int, float)) and float(road_total_co2e) > 0 and isinstance(
        multimodal_total_co2e,
        (int, float),
    ):
        emissions_savings_pct = (1.0 - (float(multimodal_total_co2e) / float(road_total_co2e))) * 100.0
    _log.info(
        (
            "Single analysis complete road_km=%s sea_km=%s cost_savings_pct=%s emissions_savings_pct=%s "
            "db_target=%s"
        ),
        geo["road_direct"].get("distance_km"),
        geo["sea_leg"].get("distance_km"),
        comparison.get("savings_pct"),
        emissions_savings_pct,
        db_target,
    )
    _emit_progress("Router analysis completed.", current=3, phase="complete")
    return geo, results, None, str(db_target)
