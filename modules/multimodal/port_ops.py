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
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.fuel.emissions import estimate_fuel_emissions
from modules.infra.data_assets import resolve_data_asset_path
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORT_OPS_PARAMS_PATH = (
    _REPO_ROOT / "data" / "processed" / "cabotage_data" / "port_ops_params_santos.json"
)
DEFAULT_PORT_OPS_SCENARIO = "santos_diesel_heavy"
DEFAULT_T_PER_TEU = 14.0

_STAT_KEYS: tuple[str, ...] = ("p10", "median", "p90")
_SOURCE_OBSERVED = "observed"
_SOURCE_ESTIMATED_AVERAGE = "estimated_port_average"
_SOURCE_LITERATURE_DEFAULT = "literature_default"
_SOURCE_UNAVAILABLE = "unavailable"
_SOURCE_ZERO_ACTIVITY = "zero_activity"
_SOURCE_LEVELS: tuple[str, ...] = (
    _SOURCE_ZERO_ACTIVITY,
    _SOURCE_OBSERVED,
    _SOURCE_ESTIMATED_AVERAGE,
    _SOURCE_LITERATURE_DEFAULT,
    _SOURCE_UNAVAILABLE,
)

_METRIC_UNITS = {
    "fuel_kg": "kg_fuel",
    "co2e_kg": "kg_co2e",
}

_METRIC_ALIASES = {
    "fuel_kg": (
        "fuel_kg",
        "port_ops_fuel_kg",
        "total_fuel_kg",
        "hoteling_fuel_kg",
        "value",
    ),
    "co2e_kg": (
        "co2e_kg",
        "port_ops_co2e_kg",
        "emissions_kg",
        "emissions_kg_co2e",
        "kg_co2e",
        "value",
    ),
}

_DENOMINATOR_ALIASES = {
    "teu": (
        "observed_teu",
        "cargo_teu",
        "handled_teu",
        "total_teu",
        "teu",
    ),
    "tonne": (
        "observed_cargo_tons",
        "observed_cargo_tonnes",
        "cargo_t",
        "cargo_tons",
        "cargo_tonnes",
        "handled_t",
        "total_handled_t",
        "tons",
        "tonnes",
    ),
    "move": (
        "observed_moves",
        "quay_moves",
        "port_moves",
        "moves",
    ),
}
_GENERIC_DENOMINATOR_ALIASES = ("denominator", "activity_denominator")
_DENOMINATOR_UNIT_ALIASES = {
    "teu": "teu",
    "teus": "teu",
    "container": "teu",
    "containers": "teu",
    "tonne": "tonne",
    "tonnes": "tonne",
    "ton": "tonne",
    "tons": "tonne",
    "t": "tonne",
    "metric_ton": "tonne",
    "metric_tons": "tonne",
    "metric_tonne": "tonne",
    "metric_tonnes": "tonne",
    "move": "move",
    "moves": "move",
    "quay_move": "move",
    "quay_moves": "move",
}
_DENOMINATOR_UNIT_KEYS = (
    "denominator_unit",
    "activity_unit",
    "throughput_unit",
    "cargo_unit",
)

_INTENSITY_ALIASES = {
    ("fuel_kg", "teu"): ("kg_fuel_per_teu", "fuel_kg_per_teu"),
    ("fuel_kg", "tonne"): ("kg_fuel_per_tonne", "kg_fuel_per_t", "fuel_kg_per_tonne"),
    ("fuel_kg", "move"): ("kg_fuel_per_move", "fuel_kg_per_move"),
    ("co2e_kg", "teu"): ("kg_co2e_per_teu", "co2e_kg_per_teu"),
    ("co2e_kg", "tonne"): ("kg_co2e_per_tonne", "kg_co2e_per_t", "co2e_kg_per_tonne"),
    ("co2e_kg", "move"): ("kg_co2e_per_move", "co2e_kg_per_move"),
}


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
    observed_port_ops: tuple[dict[str, Any], ...] = ()


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
    path = resolve_data_asset_path(params_path or DEFAULT_PORT_OPS_PARAMS_PATH)
    payload = _load_payload_cached(str(path))
    return path, payload


def _float_or(default: float, value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    return float(out)


def _float_or_none(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return float(out)


def _nonnegative_float_or_none(value: Any) -> float | None:
    out = _float_or_none(value)
    if out is None or out < 0.0:
        return None
    return out


def _positive_float_or_none(value: Any) -> float | None:
    out = _float_or_none(value)
    if out is None or out <= 0.0:
        return None
    return out


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(ascii_text.split())


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _first_present_item(mapping: Mapping[str, Any], keys: Sequence[str]) -> tuple[str | None, Any]:
    for key in keys:
        if key in mapping:
            return key, mapping.get(key)
    return None, None


def _record_port_label(record: Mapping[str, Any]) -> str:
    for key in ("port_name", "port", "name", "city"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_denominator_unit(value: Any) -> str | None:
    text = _normalize_text(value).replace(" ", "_")
    if not text:
        return None
    return _DENOMINATOR_UNIT_ALIASES.get(text)


def _record_declared_denominator_unit(record: Mapping[str, Any]) -> str | None:
    return _normalize_denominator_unit(_first_present(record, _DENOMINATOR_UNIT_KEYS))


def _record_supports_denominator_unit(record: Mapping[str, Any], denominator_unit: str) -> bool:
    declared = _record_declared_denominator_unit(record)
    return declared is None or declared == denominator_unit


def _coerce_observed_records(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()

    records: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            records.append(dict(item))
    return tuple(records)


def _observed_records_from_payload(payload: Mapping[str, Any], scenario_payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    for source in (
        scenario_payload.get("observed_port_ops"),
        scenario_payload.get("observed_ports"),
        scenario_payload.get("port_observations"),
        payload.get("observed_port_ops"),
        payload.get("observed_ports"),
        payload.get("port_observations"),
    ):
        records = _coerce_observed_records(source)
        if records:
            return records
    return ()


def _metric_unit(metric_key: str) -> str:
    return _METRIC_UNITS.get(metric_key, str(metric_key))


def _intensity_unit(metric_key: str, denominator_unit: str) -> str:
    return f"{_metric_unit(metric_key)}_per_{denominator_unit}"


def _record_metric_numerator(record: Mapping[str, Any], metric_key: str) -> float | None:
    for key in _METRIC_ALIASES.get(metric_key, (metric_key,)):
        if key not in record:
            continue
        if key == "value":
            declared_metric = _normalize_text(
                _first_present(record, ("metric_key", "metric", "value_metric", "value_unit"))
            )
            accepted = {
                _normalize_text(metric_key),
                _normalize_text(_metric_unit(metric_key)),
            }
            if declared_metric and declared_metric not in accepted:
                continue
        return _nonnegative_float_or_none(record.get(key))
    return None


def _record_denominator(record: Mapping[str, Any], denominator_unit: str) -> float | None:
    if not _record_supports_denominator_unit(record, denominator_unit):
        return None

    keys = _DENOMINATOR_ALIASES.get(denominator_unit, (denominator_unit,))
    value = _positive_float_or_none(_first_present(record, keys))
    if value is not None:
        return value

    generic_key, generic_value = _first_present_item(record, _GENERIC_DENOMINATOR_ALIASES)
    if generic_key is None:
        return None

    # A generic denominator is ambiguous without an explicit unit declaration.
    declared = _record_declared_denominator_unit(record)
    if declared != denominator_unit:
        return None
    return _positive_float_or_none(generic_value)


def _record_intensity(record: Mapping[str, Any], metric_key: str, denominator_unit: str) -> float | None:
    if not _record_supports_denominator_unit(record, denominator_unit):
        return None

    aliases = _INTENSITY_ALIASES.get((metric_key, denominator_unit), ())
    direct = _nonnegative_float_or_none(_first_present(record, aliases))
    if direct is not None:
        return direct

    numerator = _record_metric_numerator(record, metric_key)
    denominator = _record_denominator(record, denominator_unit)
    if numerator is None or denominator is None:
        return None
    return numerator / denominator


def _observed_samples(
    observed_port_ops: Sequence[Mapping[str, Any]],
    *,
    metric_key: str,
    denominator_unit: str,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for record in observed_port_ops:
        if not isinstance(record, Mapping):
            continue

        label = _record_port_label(record)
        intensity = _record_intensity(record, metric_key, denominator_unit)
        if intensity is None:
            continue

        denominator = _record_denominator(record, denominator_unit)
        numerator = _record_metric_numerator(record, metric_key)
        if numerator is None and denominator is not None:
            numerator = intensity * denominator

        samples.append(
            {
                "port_name": label,
                "port_key": _normalize_text(label),
                "intensity": float(intensity),
                "metric_key": metric_key,
                "denominator_unit": denominator_unit,
                "numerator": None if numerator is None else float(numerator),
                "denominator": None if denominator is None else float(denominator),
            }
        )
    return samples


def resolve_port_ops_intensity(
    *,
    port_name: str,
    denominator: float,
    denominator_unit: str,
    observed_port_ops: Sequence[Mapping[str, Any]] | None = None,
    metric_key: str = "fuel_kg",
    literature_default_intensity: float | None = None,
    literature_default_basis: str | None = None,
) -> dict[str, Any]:
    """
    Resolve a port-operation or hoteling intensity with explicit provenance.

    Hierarchy:
    1) port-specific observed intensity,
    2) weighted average from observed peer ports,
    3) existing documented/literature default,
    4) explicit unavailable result.
    """
    unit = str(denominator_unit or "").strip().lower()
    if unit not in _DENOMINATOR_ALIASES:
        unit = "teu"

    metric = str(metric_key or "fuel_kg").strip().lower()
    if metric not in _METRIC_ALIASES:
        metric = "fuel_kg"

    activity = max(_float_or(0.0, denominator), 0.0)
    value_unit = _metric_unit(metric)
    intensity_unit = _intensity_unit(metric, unit)
    observed_records = tuple(observed_port_ops or ())
    port_key = _normalize_text(port_name)

    base = {
        "value": None,
        "unit": value_unit,
        "intensity": None,
        "intensity_unit": intensity_unit,
        "source_level": _SOURCE_UNAVAILABLE,
        "basis": None,
        "port_name": str(port_name or ""),
        "denominator": float(activity),
        "denominator_unit": unit,
        "observed_ports_used": 0,
        "total_denominator": 0.0,
        "ports_included": [],
        "warning": None,
        "zero_activity": False,
        "excluded_from_total": True,
        "available": False,
        "observed_record_count": len(observed_records),
        "valid_observed_sample_count": 0,
    }

    if activity == 0.0:
        out = dict(base)
        out.update(
            {
                "value": 0.0,
                "intensity": 0.0,
                "source_level": _SOURCE_ZERO_ACTIVITY,
                "basis": "zero_activity",
                "zero_activity": True,
                "excluded_from_total": False,
                "available": True,
            }
        )
        return out

    samples = _observed_samples(observed_records, metric_key=metric, denominator_unit=unit)
    base["valid_observed_sample_count"] = len(samples)

    for sample in samples:
        if port_key and sample["port_key"] == port_key:
            intensity = float(sample["intensity"])
            out = dict(base)
            out.update(
                {
                    "value": float(intensity * activity),
                    "intensity": intensity,
                    "source_level": _SOURCE_OBSERVED,
                    "basis": "port_specific_observed_intensity",
                    "observed_ports_used": 1,
                    "total_denominator": float(sample["denominator"] or 0.0),
                    "ports_included": [sample["port_name"]] if sample["port_name"] else [],
                    "excluded_from_total": False,
                    "available": True,
                }
            )
            return out

    weighted_samples = [
        sample
        for sample in samples
        if sample.get("numerator") is not None and (sample.get("denominator") or 0.0) > 0.0
    ]
    if weighted_samples:
        total_numerator = sum(float(sample["numerator"]) for sample in weighted_samples)
        total_denominator = sum(float(sample["denominator"]) for sample in weighted_samples)
        if total_denominator > 0.0:
            intensity = total_numerator / total_denominator
            ports_included = [
                str(sample["port_name"])
                for sample in weighted_samples
                if str(sample.get("port_name") or "").strip()
            ]
            out = dict(base)
            out.update(
                {
                    "value": float(intensity * activity),
                    "intensity": float(intensity),
                    "source_level": _SOURCE_ESTIMATED_AVERAGE,
                    "basis": "weighted_average_observed_ports",
                    "observed_ports_used": len(weighted_samples),
                    "total_denominator": float(total_denominator),
                    "ports_included": ports_included,
                    "warning": (
                        "Port-specific observed port-ops data missing; "
                        f"used {unit}-weighted average from observed peer ports."
                    ),
                    "excluded_from_total": False,
                    "available": True,
                }
            )
            return out

    default_intensity = _nonnegative_float_or_none(literature_default_intensity)
    if default_intensity is not None and default_intensity > 0.0:
        out = dict(base)
        out.update(
            {
                "value": float(default_intensity * activity),
                "intensity": float(default_intensity),
                "source_level": _SOURCE_LITERATURE_DEFAULT,
                "basis": literature_default_basis or "documented_literature_default",
                "warning": (
                    "Observed port-ops data were unavailable for this basis; "
                    "used existing documented default intensity."
                ),
                "excluded_from_total": False,
                "available": True,
            }
        )
        return out

    out = dict(base)
    out.update(
        {
            "basis": "no_observed_or_documented_default",
            "warning": (
                "Port-specific observed port-ops data missing and no valid "
                "observed peer or documented default intensity is available."
            ),
            "excluded_from_total": True,
            "available": False,
        }
    )
    return out


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
        observed_port_ops=_observed_records_from_payload(payload, chosen_payload),
    )


def _resolve_port_call_names(port_names: Sequence[str] | None, calls: int) -> list[str]:
    names = [str(name).strip() for name in (port_names or []) if str(name or "").strip()]
    if not names:
        names = [f"port_call_{index}" for index in range(1, calls + 1)]
    if len(names) >= calls:
        return names[:calls]
    while len(names) < calls:
        names.append(f"port_call_{len(names) + 1}")
    return names


def _equipment_zero_warning(
    *,
    equipment_name: str,
    moves_total: float,
    diesel_l_per_move: float,
    electric_kwh_per_move: float,
    diesel_stats: Any,
    electricity_stats: Any,
) -> str | None:
    if moves_total <= 0.0 or (diesel_l_per_move > 0.0 or electric_kwh_per_move > 0.0):
        return None

    source_text = " ".join(
        str(stats.get("source") or "")
        for stats in (diesel_stats, electricity_stats)
        if isinstance(stats, dict)
    ).lower()
    if "no explicit" in source_text or "not identified" in source_text:
        return (
            f"{equipment_name} has movement activity but no explicit energy factor in the "
            "documented artifact; its contribution is marked unavailable instead of inferred as zero."
        )
    return None


def _summarize_source_levels(port_calls: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {level: 0 for level in _SOURCE_LEVELS}
    for call in port_calls:
        source_level = str(call.get("source_level") or _SOURCE_UNAVAILABLE)
        if source_level not in counts:
            source_level = _SOURCE_UNAVAILABLE
        counts[source_level] += 1
    return {key: value for key, value in counts.items() if value > 0}


def _summarize_mapping_source_levels(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {level: 0 for level in _SOURCE_LEVELS}
    for item in items:
        source_level = str(item.get("source_level") or _SOURCE_UNAVAILABLE)
        if source_level not in counts:
            source_level = _SOURCE_UNAVAILABLE
        counts[source_level] += 1
    return {key: value for key, value in counts.items() if value > 0}


def _source_count(counts: Mapping[str, int], source_level: str) -> int:
    value = counts.get(source_level)
    return int(value) if isinstance(value, (int, float)) and int(value) > 0 else 0


def _overall_source_level(source_counts: Mapping[str, int]) -> str:
    if source_counts.get(_SOURCE_UNAVAILABLE):
        return _SOURCE_UNAVAILABLE
    if source_counts.get(_SOURCE_ESTIMATED_AVERAGE):
        return _SOURCE_ESTIMATED_AVERAGE
    if source_counts.get(_SOURCE_LITERATURE_DEFAULT):
        return _SOURCE_LITERATURE_DEFAULT
    if source_counts.get(_SOURCE_OBSERVED):
        return _SOURCE_OBSERVED
    if source_counts.get(_SOURCE_ZERO_ACTIVITY):
        return _SOURCE_ZERO_ACTIVITY
    return _SOURCE_UNAVAILABLE


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
    selection: PortOpsScenarioSelection | None = None,
    port_names: Sequence[str] | None = None,
    observed_port_ops: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Estimate port operations fuel/energy/emissions using a moves-based method.

    `port_moves_per_call` is interpreted as quay-side container moves per call.
    Equipment-specific movement multipliers convert this into RTG/TT/STS moves.

    When observed per-port records are supplied through the params artifact or
    `observed_port_ops`, port-call values use the explicit fallback hierarchy:
    observed port data, weighted observed peer average, documented scenario
    default, then explicit unavailable metadata. Missing data is not converted
    to an unmarked zero.
    """
    selection = selection or resolve_port_ops_scenario(scenario=scenario, params_path=params_path)

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

    scenario_totals = {
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

        diesel_stats = equipment_cfg.get("diesel_l_per_move")
        electricity_stats = equipment_cfg.get("electricity_kwh_per_move")
        diesel_l_per_move = _pick_stat(diesel_stats, stat_key)
        electric_kwh_per_move = _pick_stat(electricity_stats, stat_key)

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
        zero_warning = _equipment_zero_warning(
            equipment_name=str(equipment_name),
            moves_total=equipment_moves_total,
            diesel_l_per_move=diesel_l_per_move,
            electric_kwh_per_move=electric_kwh_per_move,
            diesel_stats=diesel_stats,
            electricity_stats=electricity_stats,
        )
        equipment_zero_activity = equipment_moves_total <= 0.0
        equipment_available = bool(equipment_zero_activity or not zero_warning)
        if equipment_zero_activity:
            equipment_source_level = _SOURCE_ZERO_ACTIVITY
        elif zero_warning:
            equipment_source_level = _SOURCE_UNAVAILABLE
        else:
            equipment_source_level = _SOURCE_LITERATURE_DEFAULT

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
            "source_level": equipment_source_level,
            "available": equipment_available,
            "excluded_from_total": not equipment_available,
            "zero_activity": equipment_zero_activity,
            "warning": zero_warning,
        }
        equipment_breakdown[equipment_name] = equipment_result

        scenario_totals["diesel_liters"] += diesel_liters
        scenario_totals["fuel_kg"] += fuel_kg
        scenario_totals["electricity_kwh"] += electricity_kwh
        scenario_totals["co2e_kg"] += fuel_co2e_kg + electricity_co2e_kg
        scenario_totals["cost_brl"] += total_cost_brl

    observed_records = tuple(observed_port_ops) if observed_port_ops is not None else tuple(selection.observed_port_ops)
    port_call_names = _resolve_port_call_names(port_names, calls)
    denominator_unit = "move" if full_call_mode or moves_source == "explicit_override" else "teu"
    total_denominator = float(quay_moves_total)
    literature_fuel_intensity = (
        float(scenario_totals["fuel_kg"]) / total_denominator
        if total_denominator > 0.0 and scenario_totals["fuel_kg"] > 0.0
        else None
    )
    literature_co2e_intensity = (
        float(scenario_totals["co2e_kg"]) / total_denominator
        if total_denominator > 0.0 and scenario_totals["co2e_kg"] > 0.0
        else None
    )

    port_call_breakdown: list[dict[str, Any]] = []
    warnings: list[str] = []
    totals = {k: float(v) for k, v in scenario_totals.items()}
    calculation_basis = "documented_moves_based_scenario"

    zero_activity = calls == 0 or moves_per_call <= 0.0 or quay_moves_total <= 0.0
    if zero_activity:
        calculation_basis = "zero_activity"
        totals = {
            "diesel_liters": 0.0,
            "fuel_kg": 0.0,
            "electricity_kwh": 0.0,
            "co2e_kg": 0.0,
            "cost_brl": 0.0,
        }
        if calls > 0:
            for port_name in port_call_names:
                port_call_breakdown.append(
                    {
                        "port_name": str(port_name),
                        "activity_value": float(moves_per_call),
                        "activity_unit": denominator_unit,
                        "fuel_kg": 0.0,
                        "co2e_kg": 0.0,
                        "diesel_liters": 0.0,
                        "cost_brl": 0.0,
                        "source_level": _SOURCE_ZERO_ACTIVITY,
                        "basis": "zero_activity",
                        "fuel_available": True,
                        "co2e_available": True,
                        "available": True,
                        "excluded_from_total": False,
                        "zero_activity": True,
                        "warning": None,
                    }
                )
    elif observed_records:
        calculation_basis = "observed_port_ops_hierarchy"
        totals = {
            "diesel_liters": 0.0,
            "fuel_kg": 0.0,
            "electricity_kwh": 0.0,
            "co2e_kg": 0.0,
            "cost_brl": 0.0,
        }

        for port_name in port_call_names:
            fuel_resolution = resolve_port_ops_intensity(
                port_name=port_name,
                denominator=moves_per_call,
                denominator_unit=denominator_unit,
                observed_port_ops=observed_records,
                metric_key="fuel_kg",
                literature_default_intensity=literature_fuel_intensity,
                literature_default_basis="documented_moves_based_scenario",
            )
            co2e_resolution = resolve_port_ops_intensity(
                port_name=port_name,
                denominator=moves_per_call,
                denominator_unit=denominator_unit,
                observed_port_ops=observed_records,
                metric_key="co2e_kg",
                literature_default_intensity=literature_co2e_intensity,
                literature_default_basis="documented_moves_based_scenario",
            )

            fuel_value = fuel_resolution.get("value")
            co2e_value = co2e_resolution.get("value")
            fuel_kg = 0.0 if fuel_value is None else float(fuel_value)

            if co2e_value is None and fuel_value is not None:
                co2e_from_fuel = estimate_fuel_emissions(
                    fuel_mass_kg=fuel_kg,
                    fuel_type=selection.diesel_fuel_type,
                )
                co2e_kg = float(co2e_from_fuel.get("co2e_kg") or 0.0)
                co2e_resolution = {
                    **co2e_resolution,
                    "value": co2e_kg,
                    "unit": "kg_co2e",
                    "source_level": str(fuel_resolution.get("source_level") or _SOURCE_UNAVAILABLE),
                    "basis": "converted_from_resolved_fuel_kg",
                    "warning": fuel_resolution.get("warning"),
                    "available": True,
                    "excluded_from_total": False,
                }
            else:
                co2e_kg = 0.0 if co2e_value is None else float(co2e_value)

            diesel_liters = fuel_kg / selection.diesel_density_kg_per_l if selection.diesel_density_kg_per_l > 0 else 0.0
            diesel_cost_brl = diesel_liters * float(diesel_price_per_l) if diesel_price_per_l is not None else 0.0

            source_level = str(fuel_resolution.get("source_level") or _SOURCE_UNAVAILABLE)
            if source_level == _SOURCE_UNAVAILABLE and str(co2e_resolution.get("source_level")) != _SOURCE_UNAVAILABLE:
                source_level = str(co2e_resolution.get("source_level"))

            call_warnings = list(
                dict.fromkeys(
                    str(item)
                    for item in (fuel_resolution.get("warning"), co2e_resolution.get("warning"))
                    if str(item or "").strip()
                )
            )
            call_warning = "; ".join(call_warnings) if call_warnings else None
            warnings.extend(call_warnings)

            port_call_breakdown.append(
                {
                    "port_name": str(port_name),
                    "activity_value": float(moves_per_call),
                    "activity_unit": denominator_unit,
                    "fuel_kg": None if fuel_value is None else float(fuel_kg),
                    "co2e_kg": None if co2e_value is None and fuel_value is None else float(co2e_kg),
                    "diesel_liters": float(diesel_liters),
                    "cost_brl": float(diesel_cost_brl),
                    "source_level": source_level,
                    "fuel_available": fuel_value is not None,
                    "co2e_available": co2e_value is not None or fuel_value is not None,
                    "available": fuel_value is not None or co2e_value is not None,
                    "excluded_from_total": fuel_value is None and co2e_value is None,
                    "fuel_resolution": fuel_resolution,
                    "co2e_resolution": co2e_resolution,
                    "warning": call_warning,
                }
            )

            totals["diesel_liters"] += diesel_liters
            totals["fuel_kg"] += fuel_kg
            totals["co2e_kg"] += co2e_kg
            totals["cost_brl"] += diesel_cost_brl
    else:
        if calls > 0:
            for port_name in port_call_names:
                call_share = (moves_per_call / total_denominator) if total_denominator > 0.0 else 0.0
                call_available = scenario_totals["fuel_kg"] > 0.0 or scenario_totals["co2e_kg"] > 0.0
                port_call_breakdown.append(
                    {
                        "port_name": str(port_name),
                        "activity_value": float(moves_per_call),
                        "activity_unit": denominator_unit,
                        "fuel_kg": float(scenario_totals["fuel_kg"] * call_share) if call_available else None,
                        "co2e_kg": float(scenario_totals["co2e_kg"] * call_share) if call_available else None,
                        "diesel_liters": float(scenario_totals["diesel_liters"] * call_share),
                        "cost_brl": float(scenario_totals["cost_brl"] * call_share),
                        "source_level": _SOURCE_LITERATURE_DEFAULT if call_available else _SOURCE_UNAVAILABLE,
                        "basis": "documented_moves_based_scenario",
                        "fuel_available": scenario_totals["fuel_kg"] > 0.0,
                        "co2e_available": scenario_totals["co2e_kg"] > 0.0,
                        "available": call_available,
                        "excluded_from_total": not call_available,
                        "warning": (
                            "No port-specific observed port-ops records were available; "
                            "used documented moves-based scenario."
                        )
                        if call_available
                        else "No observed port-ops records or valid documented positive default were available.",
                    }
                )
        if scenario_totals["fuel_kg"] > 0.0 or scenario_totals["co2e_kg"] > 0.0:
            warnings.append(
                "No port-specific observed port-ops records were available; used documented moves-based scenario."
            )
        elif calls > 0:
            warnings.append("No observed port-ops records or valid documented positive default were available.")

    equipment_warnings = [
        str(item.get("warning"))
        for item in equipment_breakdown.values()
        if isinstance(item, dict) and item.get("warning")
    ]
    source_counts = _summarize_source_levels(port_call_breakdown)
    equipment_source_counts = _summarize_mapping_source_levels(list(equipment_breakdown.values()))
    source_level = _overall_source_level(source_counts)
    if zero_activity and not source_counts:
        source_level = _SOURCE_ZERO_ACTIVITY
    uses_documented_scenario_values = (
        not observed_records
        or _source_count(source_counts, _SOURCE_LITERATURE_DEFAULT) > 0
        or source_level == _SOURCE_LITERATURE_DEFAULT
    ) and not zero_activity
    if uses_documented_scenario_values:
        warnings.extend(equipment_warnings)
    deduped_warnings = list(dict.fromkeys(warnings))
    unavailable_port_call_count = _source_count(source_counts, _SOURCE_UNAVAILABLE)
    unavailable_equipment_count = (
        _source_count(equipment_source_counts, _SOURCE_UNAVAILABLE)
        if uses_documented_scenario_values
        else 0
    )
    has_unavailable_port_ops = bool(unavailable_port_call_count > 0 or unavailable_equipment_count > 0)

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
        "source_level": source_level,
        "source_level_counts": source_counts,
        "equipment_source_level_counts": equipment_source_counts,
        "calculation_basis": calculation_basis,
        "observed_port_ops_record_count": len(observed_records),
        "fallback_denominator_unit": denominator_unit,
        "fallback_total_denominator": float(total_denominator),
        "unavailable_port_call_count": unavailable_port_call_count,
        "unavailable_equipment_count": unavailable_equipment_count,
        "equipment_unavailable_affects_totals": bool(uses_documented_scenario_values and unavailable_equipment_count > 0),
        "has_unavailable_port_ops": has_unavailable_port_ops,
        "totals_complete": not has_unavailable_port_ops,
        "zero_activity": bool(zero_activity),
        "missing_value_policy": "unavailable_values_excluded_from_numeric_totals_with_warning",
        "port_call_breakdown": port_call_breakdown,
        "warnings": deduped_warnings,
        "equipment": equipment_breakdown,
        "totals": {k: float(v) for k, v in totals.items()},
    }
