# modules/multimodal/port_ops.py
# -*- coding: utf-8 -*-

"""
Moves-based port operations model (terminal handling).

Runtime consumes processed params from:
    data/processed/cabotage_data/port_ops_params_santos.json
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from modules.fuel.emissions import estimate_fuel_emissions
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORT_OPS_PARAMS_PATH = (
    _REPO_ROOT / "data" / "processed" / "cabotage_data" / "port_ops_params_santos.json"
)
DEFAULT_PORT_OPS_SCENARIO = "santos_diesel_heavy"
DEFAULT_T_PER_TEU = 14.0

_STAT_KEYS: tuple[str, ...] = ("p10", "median", "p90")


@dataclass(frozen=True)
class PortOpsScenarioSelection:
    requested_scenario: str
    resolved_scenario: str
    source_path: Path
    default_port_calls: int
    default_port_moves_per_call: dict[str, float]
    t_per_teu_default: float
    diesel_density_kg_per_l: float
    diesel_fuel_type: str
    electricity_kg_co2e_per_kwh: float
    electricity_price_brl_per_kwh: float
    equipment: dict[str, Any]


@lru_cache(maxsize=4)
def _load_payload_cached(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"Port ops params artifact not found: {path}. "
            "Run 'python calcs/port_ops_params_builder.py' first."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "scenarios" not in payload:
        raise ValueError(f"Invalid port ops params payload: {path}")
    return payload


def _resolve_payload(params_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = Path(params_path or DEFAULT_PORT_OPS_PARAMS_PATH).resolve()
    payload = _load_payload_cached(str(path))
    return path, payload


def _float_or(default: float, value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(out)


def _stats_or_default(stats: Any, default: float) -> dict[str, float]:
    if not isinstance(stats, dict):
        return {"p10": default, "median": default, "p90": default}

    return {
        "p10": _float_or(default, stats.get("p10", default)),
        "median": _float_or(default, stats.get("median", default)),
        "p90": _float_or(default, stats.get("p90", default)),
    }


def _pick_stat(stats: Any, stat_key: str) -> float:
    norm = str(stat_key or "median").strip().lower()
    if norm not in _STAT_KEYS:
        norm = "median"

    if not isinstance(stats, dict):
        return 0.0

    return max(_float_or(0.0, stats.get(norm, 0.0)), 0.0)


def _resolve_cargo_teu(cargo_t: float | None, cargo_teu: float | None, t_per_teu_default: float) -> int | None:
    if cargo_teu is not None:
        try:
            teu = float(cargo_teu)
        except (TypeError, ValueError):
            teu = 0.0
        if teu > 0:
            return max(int(math.ceil(teu)), 1)

    if cargo_t is not None:
        try:
            mass_t = float(cargo_t)
        except (TypeError, ValueError):
            mass_t = 0.0
        if mass_t > 0 and t_per_teu_default > 0:
            return max(int(math.ceil(mass_t / t_per_teu_default)), 1)

    return None


def list_port_ops_scenarios(params_path: Path | None = None) -> tuple[str, ...]:
    try:
        _, payload = _resolve_payload(params_path)
        scenarios = payload.get("scenarios") or {}
        if isinstance(scenarios, dict) and scenarios:
            out = list(scenarios.keys())
            if DEFAULT_PORT_OPS_SCENARIO in out:
                out.remove(DEFAULT_PORT_OPS_SCENARIO)
                out.insert(0, DEFAULT_PORT_OPS_SCENARIO)
            return tuple(out)
    except Exception:
        pass
    return (DEFAULT_PORT_OPS_SCENARIO,)


def resolve_port_ops_scenario(
    scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    *,
    params_path: Path | None = None,
) -> PortOpsScenarioSelection:
    source_path, payload = _resolve_payload(params_path)

    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), dict) else {}
    if not scenarios:
        raise ValueError(f"No scenarios found in port ops params: {source_path}")

    requested = str(scenario or "").strip().lower() or DEFAULT_PORT_OPS_SCENARIO

    candidates: list[str] = [requested]
    if DEFAULT_PORT_OPS_SCENARIO not in candidates:
        candidates.append(DEFAULT_PORT_OPS_SCENARIO)
    for key in scenarios.keys():
        if isinstance(key, str) and key not in candidates:
            candidates.append(key)

    chosen_name: str | None = None
    chosen_payload: dict[str, Any] | None = None
    for name in candidates:
        obj = scenarios.get(name)
        if isinstance(obj, dict):
            chosen_name = name
            chosen_payload = obj
            break

    if chosen_name is None or chosen_payload is None:
        raise ValueError(f"Could not resolve any valid scenario in: {source_path}")

    if chosen_name != requested:
        _log.warning(
            "Port ops scenario '%s' unavailable in %s. Falling back to '%s'.",
            requested,
            source_path,
            chosen_name,
        )

    default_moves_stats = _stats_or_default(defaults.get("default_port_moves_per_call"), 0.0)

    return PortOpsScenarioSelection(
        requested_scenario=requested,
        resolved_scenario=chosen_name,
        source_path=source_path,
        default_port_calls=max(int(_float_or(2, defaults.get("default_port_calls", 2))), 0),
        default_port_moves_per_call=default_moves_stats,
        t_per_teu_default=max(_float_or(DEFAULT_T_PER_TEU, defaults.get("t_per_teu_default", DEFAULT_T_PER_TEU)), 0.1),
        diesel_density_kg_per_l=max(_float_or(0.85, defaults.get("diesel_density_kg_per_l", 0.85)), 0.0),
        diesel_fuel_type=str(defaults.get("diesel_fuel_type") or "diesel").strip().lower() or "diesel",
        electricity_kg_co2e_per_kwh=max(
            _float_or(0.0, defaults.get("electricity_kg_co2e_per_kwh", 0.0)),
            0.0,
        ),
        electricity_price_brl_per_kwh=max(
            _float_or(0.0, defaults.get("electricity_price_brl_per_kwh", 0.0)),
            0.0,
        ),
        equipment=chosen_payload.get("equipment") if isinstance(chosen_payload.get("equipment"), dict) else {},
    )


def estimate_port_ops(
    *,
    scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    port_calls: int,
    port_moves_per_call: float | None = None,
    cargo_t: float | None = None,
    cargo_teu: float | None = None,
    t_per_teu_default: float | None = None,
    full_call_mode: bool = False,
    stat_key: str = "median",
    diesel_price_per_l: float | None = None,
    params_path: Path | None = None,
) -> dict[str, Any]:
    """
    Estimate port operations fuel/energy/emissions using a moves-based method.

    `port_moves_per_call` is interpreted as quay-side container moves per call.
    Equipment-specific movement multipliers convert this into RTG/TT/STS moves.
    """
    selection = resolve_port_ops_scenario(scenario=scenario, params_path=params_path)

    calls = max(int(port_calls), 0)

    requested_moves = None if port_moves_per_call is None else max(float(port_moves_per_call), 0.0)

    t_per_teu = float(t_per_teu_default) if t_per_teu_default is not None else float(selection.t_per_teu_default)
    if t_per_teu <= 0:
        t_per_teu = float(selection.t_per_teu_default)

    cargo_teu_resolved = _resolve_cargo_teu(cargo_t=cargo_t, cargo_teu=cargo_teu, t_per_teu_default=t_per_teu)

    if full_call_mode:
        if requested_moves is None or requested_moves <= 0.0:
            moves_per_call = float(selection.default_port_moves_per_call.get("median", 0.0))
            moves_source = "scenario_default_full_call"
        else:
            moves_per_call = requested_moves
            moves_source = "explicit_override"
    else:
        if requested_moves is not None and requested_moves > 0.0:
            moves_per_call = requested_moves
            moves_source = "explicit_override"
        elif cargo_teu_resolved is not None:
            moves_per_call = float(cargo_teu_resolved)
            moves_source = "cargo_teu_derived"
        else:
            moves_per_call = float(selection.default_port_moves_per_call.get("median", 0.0))
            moves_source = "scenario_default_fallback"

    quay_moves_total = moves_per_call * float(calls)

    totals = {
        "diesel_liters": 0.0,
        "fuel_kg": 0.0,
        "electricity_kwh": 0.0,
        "co2e_kg": 0.0,
        "cost_brl": 0.0,
    }

    equipment_breakdown: dict[str, dict[str, Any]] = {}

    for equipment_name, equipment_cfg in selection.equipment.items():
        if not isinstance(equipment_cfg, dict):
            continue

        moves_per_container = max(_float_or(0.0, equipment_cfg.get("moves_per_container", 0.0)), 0.0)
        equipment_moves_total = quay_moves_total * moves_per_container

        diesel_l_per_move = _pick_stat(equipment_cfg.get("diesel_l_per_move"), stat_key)
        electric_kwh_per_move = _pick_stat(equipment_cfg.get("electricity_kwh_per_move"), stat_key)

        diesel_liters = equipment_moves_total * diesel_l_per_move
        fuel_kg = diesel_liters * selection.diesel_density_kg_per_l

        if fuel_kg > 0:
            diesel_emissions = estimate_fuel_emissions(
                fuel_mass_kg=fuel_kg,
                fuel_type=selection.diesel_fuel_type,
            )
            fuel_co2e_kg = float(diesel_emissions.get("co2e_kg") or 0.0)
        else:
            fuel_co2e_kg = 0.0

        electricity_kwh = equipment_moves_total * electric_kwh_per_move
        electricity_co2e_kg = electricity_kwh * selection.electricity_kg_co2e_per_kwh

        diesel_cost_brl = diesel_liters * float(diesel_price_per_l) if diesel_price_per_l is not None else 0.0
        electricity_cost_brl = electricity_kwh * selection.electricity_price_brl_per_kwh
        total_cost_brl = diesel_cost_brl + electricity_cost_brl

        equipment_result = {
            "moves_per_container": float(moves_per_container),
            "moves_total": float(equipment_moves_total),
            "diesel_l_per_move": float(diesel_l_per_move),
            "diesel_liters": float(diesel_liters),
            "fuel_kg": float(fuel_kg),
            "electricity_kwh_per_move": float(electric_kwh_per_move),
            "electricity_kwh": float(electricity_kwh),
            "co2e_kg_fuel": float(fuel_co2e_kg),
            "co2e_kg_electricity": float(electricity_co2e_kg),
            "co2e_kg": float(fuel_co2e_kg + electricity_co2e_kg),
            "cost_brl_fuel": float(diesel_cost_brl),
            "cost_brl_electricity": float(electricity_cost_brl),
            "cost_brl": float(total_cost_brl),
        }
        equipment_breakdown[equipment_name] = equipment_result

        totals["diesel_liters"] += diesel_liters
        totals["fuel_kg"] += fuel_kg
        totals["electricity_kwh"] += electricity_kwh
        totals["co2e_kg"] += fuel_co2e_kg + electricity_co2e_kg
        totals["cost_brl"] += total_cost_brl

    return {
        "requested_scenario": selection.requested_scenario,
        "resolved_scenario": selection.resolved_scenario,
        "source_path": str(selection.source_path),
        "stat_key": stat_key if stat_key in _STAT_KEYS else "median",
        "full_call_mode": bool(full_call_mode),
        "port_calls": int(calls),
        "cargo_t_input": None if cargo_t is None else float(cargo_t),
        "cargo_teu_input": None if cargo_teu is None else float(cargo_teu),
        "cargo_teu_resolved": None if cargo_teu_resolved is None else int(cargo_teu_resolved),
        "t_per_teu_default": float(t_per_teu),
        "port_moves_per_call": float(moves_per_call),
        "port_moves_source": moves_source,
        "quay_moves_total": float(quay_moves_total),
        "default_port_moves_per_call": selection.default_port_moves_per_call,
        "diesel_fuel_type": selection.diesel_fuel_type,
        "diesel_density_kg_per_l": float(selection.diesel_density_kg_per_l),
        "electricity_kg_co2e_per_kwh": float(selection.electricity_kg_co2e_per_kwh),
        "equipment": equipment_breakdown,
        "totals": {k: float(v) for k, v in totals.items()},
    }
