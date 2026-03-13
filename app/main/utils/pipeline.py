from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Tuple

from modules.infra.log_manager import get_logger
from modules.multimodal import build_path_geometry, evaluate_path

from app.main.utils.state import resolve_runtime_db_target

_log = get_logger("streamlit_app")


def build_scenario_payload(session_state: Mapping[str, Any]) -> Dict[str, Any]:
    cargo_teu_value = float(session_state.get("cargo_teu_input", 0.0))
    t_per_teu_default = max(float(session_state.get("t_per_teu_default", 14.0)), 0.1)
    allocation_mode = str(session_state.get("allocation_mode", "auto")).strip().lower()
    allocation_load_factor = min(max(float(session_state.get("allocation_load_factor", 0.8)), 0.01), 1.0)

    return {
        "origin": str(session_state.get("origin", "")).strip(),
        "destiny": str(session_state.get("destiny", "")).strip(),
        "cargo_t": float(session_state.get("cargo_t", 0.0)),
        "cargo_teu": None if cargo_teu_value <= 0.0 else cargo_teu_value,
        "t_per_teu_default": t_per_teu_default,
        "allocation_mode": None if allocation_mode == "auto" else allocation_mode,
        "allocation_load_factor": allocation_load_factor,
        "truck_key": str(session_state.get("truck_key", "")),
        "ors_profile": str(session_state.get("profile", "driving-hgv")),
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


def resolve_cargo_teu(payload: Mapping[str, Any]) -> int:
    cargo_teu = payload.get("cargo_teu")
    if isinstance(cargo_teu, (int, float)) and float(cargo_teu) > 0:
        return max(int(math.ceil(float(cargo_teu))), 1)
    cargo_t = max(float(payload.get("cargo_t") or 0.0), 0.0)
    t_per_teu_default = max(float(payload.get("t_per_teu_default") or 14.0), 0.1)
    return max(int(math.ceil(cargo_t / t_per_teu_default)), 1) if cargo_t > 0 else 0


def run_analysis(
    payload: Mapping[str, Any],
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None, str | None, str]:
    _log.info("Routing: %s -> %s (%.3ft)", payload["origin"], payload["destiny"], payload["cargo_t"])

    db_target = resolve_runtime_db_target()

    geo = build_path_geometry(
        payload["origin"],
        payload["destiny"],
        ors_profile=payload["ors_profile"],
        overwrite_road=payload["overwrite_road"],
    )
    if not geo or geo.get("status") != "ok":
        _log.error("Failed to build route geometry.")
        return None, None, "Failed to build route geometry. Check inputs and API key.", str(db_target)

    _log.info("Calculating costs and emissions...")
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
    )
    if not results:
        _log.error("Failed to evaluate route.")
        return (
            geo,
            None,
            "Failed to evaluate route. Ensure processed artifacts exist in data/processed/cabotage_data.",
            str(db_target),
        )

    _log.info("Analysis finished.")
    return geo, results, None, str(db_target)
