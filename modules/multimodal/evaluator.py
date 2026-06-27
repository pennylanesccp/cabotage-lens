# modules/multimodal/evaluator.py
# -*- coding: utf-8 -*-

"""
Multimodal evaluator.

Consumes path geometry and produces cost/emissions comparison between:
- direct road,
- multimodal (first mile + sea leg + last mile).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Path bootstrap
if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.costs.diesel_prices import (
    DieselPriceLookup,
    build_price_lookup,
    get_average_price,
    get_average_price_from_lookup,
    normalize_uf,
)
from modules.costs.ship_fuel_prices import get_bunker_price
from modules.fuel.emissions import get_ef_kg_per_kg
from modules.fuel.road_fuel_model import estimate_leg_liters
from modules.fuel.truck_specs import get_truck_spec
from modules.infra.log_manager import get_logger
from modules.multimodal.container_efficiency import (
    DEFAULT_VESSEL_CLASS,
    VesselClassEfficiency,
    resolve_vessel_class_efficiency,
)
from modules.multimodal.hoteling import HotelingRateSelection, resolve_hoteling_rate
from modules.multimodal.port_ops import (
    DEFAULT_PORT_OPS_SCENARIO,
    PortOpsScenarioSelection,
    estimate_port_ops,
    resolve_port_ops_scenario,
)

_log = get_logger(__name__)

_DIESEL_EF_KG_CO2E_PER_L = 2.68
_MARINE_FUEL_TYPE = "vlsfo"
_BUNKER_EF_KG_CO2E_PER_KG = float(get_ef_kg_per_kg(_MARINE_FUEL_TYPE))
_NM_TO_KM = 1.852
_KG_PER_TONNE = 1000.0
_DEFAULT_TEU_LOAD_FACTOR = 0.80


@dataclass(frozen=True)
class PreparedEvaluationContext:
    """Scenario-wide evaluator inputs prepared once and reused across many paths."""

    truck_spec: Dict[str, Any]
    diesel_lookup: DieselPriceLookup | None
    diesel_price_override: float | None
    bunker_price_ton: float
    vessel_eff: VesselClassEfficiency
    hoteling_sel: HotelingRateSelection | None
    port_ops_selection: PortOpsScenarioSelection | None


def _resolve_uf_from_point(point: Dict[str, Any]) -> str:
    """Resolve UF code from structured point data or from the point label tail."""
    uf = normalize_uf(str(point.get("uf") or ""))
    if uf:
        return uf

    label = str(point.get("label") or "").strip()
    if "," in label:
        uf = normalize_uf(label.split(",")[-1].strip())
        if uf:
            return uf

    return ""


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


def _positive_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0.0 else None


def _resolve_cargo_teu(cargo_t: float, cargo_teu: float | None, t_per_teu_default: float) -> int:
    if cargo_teu is not None:
        try:
            teu = float(cargo_teu)
        except (TypeError, ValueError):
            teu = 0.0
        if teu > 0:
            return max(int(math.ceil(teu)), 1)

    cargo_t = max(float(cargo_t), 0.0)
    t_per_teu_default = max(float(t_per_teu_default), 0.1)
    if cargo_t <= 0.0:
        return 0
    return max(int(math.ceil(cargo_t / t_per_teu_default)), 1)


def _cargo_allocation_share_dwt(cargo_t: float, size_proxy_t_median: float | None) -> float:
    if size_proxy_t_median is None or size_proxy_t_median <= 0:
        return 1.0
    share = float(cargo_t) / float(size_proxy_t_median)
    if share < 0:
        return 0.0
    return min(share, 1.0)


def compute_cargo_allocation_share(
    inputs: Dict[str, Any],
    vessel_meta: Dict[str, Any],
) -> tuple[float, Dict[str, Any]]:
    """
    Compute cargo allocation share for maritime fuel attribution.

    Supported modes:
    - dwt_share: legacy mass proxy share (cargo_t / size_proxy_t_median)
    - teu_share: cargo TEU share over operational loaded TEU capacity
    """
    cargo_t = max(float(inputs.get("cargo_t") or 0.0), 0.0)
    cargo_teu = inputs.get("cargo_teu")
    t_per_teu_default = max(float(inputs.get("t_per_teu_default") or 14.0), 0.1)

    requested_mode_raw = str(inputs.get("allocation_mode") or "").strip().lower()
    requested_mode = requested_mode_raw if requested_mode_raw in {"dwt_share", "teu_share"} else None

    load_factor_requested = inputs.get("load_factor")
    try:
        load_factor = float(load_factor_requested) if load_factor_requested is not None else _DEFAULT_TEU_LOAD_FACTOR
    except (TypeError, ValueError):
        load_factor = _DEFAULT_TEU_LOAD_FACTOR
    if load_factor <= 0:
        load_factor = _DEFAULT_TEU_LOAD_FACTOR
    load_factor = _clamp(float(load_factor), 0.01, 1.0)

    vessel_class = str(vessel_meta.get("vessel_class") or "").strip().lower()

    size_proxy_t_median_raw = vessel_meta.get("size_proxy_t_median")
    try:
        size_proxy_t_median = float(size_proxy_t_median_raw) if size_proxy_t_median_raw is not None else None
    except (TypeError, ValueError):
        size_proxy_t_median = None
    if isinstance(size_proxy_t_median, float) and size_proxy_t_median <= 0:
        size_proxy_t_median = None

    teu_capacity_raw = vessel_meta.get("teu_capacity")
    try:
        teu_capacity = float(teu_capacity_raw) if teu_capacity_raw is not None else None
    except (TypeError, ValueError):
        teu_capacity = None
    if isinstance(teu_capacity, float) and teu_capacity <= 0:
        teu_capacity = None

    lightship_raw = vessel_meta.get("lightship_t")
    try:
        lightship_t = float(lightship_raw) if lightship_raw is not None else None
    except (TypeError, ValueError):
        lightship_t = None
    if isinstance(lightship_t, float) and lightship_t <= 0:
        lightship_t = None

    cargo_teu_resolved = _resolve_cargo_teu(
        cargo_t=cargo_t,
        cargo_teu=cargo_teu,
        t_per_teu_default=t_per_teu_default,
    )

    share_old_dwt = _cargo_allocation_share_dwt(
        cargo_t=cargo_t,
        size_proxy_t_median=size_proxy_t_median,
    )

    teu_loaded = None
    share_new_teu = share_old_dwt
    if teu_capacity is not None and teu_capacity > 0:
        teu_loaded = teu_capacity * load_factor
        if teu_loaded > 0:
            share_new_teu = _clamp(float(cargo_teu_resolved) / float(teu_loaded), 0.0, 1.0)

    default_mode = "teu_share" if vessel_class.startswith("container") else "dwt_share"
    mode_used = requested_mode or default_mode

    if mode_used == "teu_share" and not (isinstance(teu_loaded, (int, float)) and teu_loaded > 0):
        mode_used = "dwt_share"

    share_used = share_new_teu if mode_used == "teu_share" else share_old_dwt
    ratio_new_vs_old = (share_new_teu / share_old_dwt) if share_old_dwt > 0 else None

    debug: Dict[str, Any] = {
        "allocation_mode_requested": requested_mode,
        "allocation_mode_default": default_mode,
        "allocation_mode_used": mode_used,
        "teu_capacity": teu_capacity,
        "load_factor": load_factor,
        "teu_loaded": teu_loaded,
        "cargo_teu_resolved": int(cargo_teu_resolved),
        "share_old_dwt": float(share_old_dwt),
        "share_new_teu": float(share_new_teu),
        "ratio_new_vs_old": (None if ratio_new_vs_old is None else float(ratio_new_vs_old)),
    }

    if (
        lightship_t is not None
        and cargo_teu_resolved > 0
        and isinstance(teu_loaded, (int, float))
        and teu_loaded > 0
    ):
        debug["eff_t_per_teu"] = (cargo_t / float(cargo_teu_resolved)) + (lightship_t / float(teu_loaded))

    return float(share_used), debug


def prepare_evaluation_context(
    *,
    truck_key: str = "semi_27t",
    diesel_price: Optional[float] = None,
    diesel_default_price_r_per_l: float = 6.0,
    diesel_csv_path: Optional[Path] = None,
    vessel_class: str = DEFAULT_VESSEL_CLASS,
    vessel_efficiency_path: Optional[Path] = None,
    include_hoteling: bool = True,
    hoteling_hours_per_call: float = 14.0,
    port_calls: int = 2,
    hoteling_rate_path: Optional[Path] = None,
    include_port_ops: bool = True,
    port_ops_scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    port_ops_params_path: Optional[Path] = None,
    bunker_price_brl_mt: float = 3500.0,
) -> PreparedEvaluationContext:
    """Prepare scenario-wide evaluator inputs once for reuse across many destinations."""
    hoteling_hours_total = max(float(hoteling_hours_per_call), 0.0) * max(int(port_calls), 0)

    vessel_eff = resolve_vessel_class_efficiency(
        vessel_class=vessel_class,
        efficiency_json_path=vessel_efficiency_path,
    )
    uses_transport_work_intensity = bool(
        isinstance(vessel_eff.fuel_g_per_tnm, (int, float)) and float(vessel_eff.fuel_g_per_tnm) > 0.0
    )

    hoteling_sel = None
    if bool(include_hoteling) and hoteling_hours_total > 0 and not uses_transport_work_intensity:
        hoteling_sel = resolve_hoteling_rate(
            vessel_class=vessel_eff.vessel_class,
            hoteling_rate_path=hoteling_rate_path,
        )

    port_ops_selection = None
    if bool(include_port_ops) and max(int(port_calls), 0) > 0:
        port_ops_selection = resolve_port_ops_scenario(
            scenario=port_ops_scenario,
            params_path=port_ops_params_path,
        )

    diesel_lookup = None
    diesel_price_override = None if diesel_price is None else float(diesel_price)
    if diesel_price_override is None:
        diesel_lookup = build_price_lookup(
            default_price_r_per_l=diesel_default_price_r_per_l,
            csv_path=diesel_csv_path,
        )

    context = PreparedEvaluationContext(
        truck_spec=get_truck_spec(truck_key),
        diesel_lookup=diesel_lookup,
        diesel_price_override=diesel_price_override,
        bunker_price_ton=float(get_bunker_price(default_price_brl_mt=bunker_price_brl_mt)),
        vessel_eff=vessel_eff,
        hoteling_sel=hoteling_sel,
        port_ops_selection=port_ops_selection,
    )

    _log.info(
        (
            "Prepared evaluation context: truck=%s vessel_class=%s diesel_mode=%s "
            "diesel_rows=%d bunker_price=R$ %.2f/mt hoteling=%s port_ops=%s"
        ),
        truck_key,
        vessel_eff.vessel_class,
        ("explicit_override" if diesel_price_override is not None else "lookup"),
        (0 if diesel_lookup is None else diesel_lookup.row_count),
        context.bunker_price_ton,
        bool(hoteling_sel is not None),
        bool(port_ops_selection is not None),
    )
    return context


def evaluate_path(
    path_data: Dict[str, Any],
    cargo_t: float,
    truck_key: str = "semi_27t",
    diesel_price: Optional[float] = None,
    vessel_class: str = DEFAULT_VESSEL_CLASS,
    vessel_efficiency_path: Optional[Path] = None,
    include_hoteling: bool = True,
    hoteling_hours_per_call: float = 14.0,
    port_calls: int = 2,
    hoteling_rate_path: Optional[Path] = None,
    include_port_ops: bool = True,
    port_moves_per_call: Optional[float] = None,
    cargo_teu: Optional[float] = None,
    t_per_teu_default: float = 14.0,
    allocation_mode: Optional[str] = None,
    allocation_load_factor: Optional[float] = None,
    full_call_mode: bool = False,
    port_ops_scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    port_ops_params_path: Optional[Path] = None,
    port_ops_stat_key: str = "median",
    prepared_context: PreparedEvaluationContext | None = None,
    diesel_default_price_r_per_l: float = 6.0,
    diesel_csv_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Assess costs and emissions for a path geometry payload."""
    if not path_data or path_data.get("status") != "ok":
        _log.warning("Cannot evaluate invalid path geometry.")
        return {}

    include_hoteling = bool(include_hoteling)
    include_port_ops = bool(include_port_ops)
    hoteling_hours_per_call = max(float(hoteling_hours_per_call), 0.0)
    port_calls = max(int(port_calls), 0)
    hoteling_hours_total_requested = hoteling_hours_per_call * float(port_calls) if include_hoteling else 0.0

    try:
        context = prepared_context or prepare_evaluation_context(
            truck_key=truck_key,
            diesel_price=diesel_price,
            diesel_default_price_r_per_l=diesel_default_price_r_per_l,
            diesel_csv_path=diesel_csv_path,
            vessel_class=vessel_class,
            vessel_efficiency_path=vessel_efficiency_path,
            include_hoteling=include_hoteling,
            hoteling_hours_per_call=hoteling_hours_per_call,
            port_calls=port_calls,
            hoteling_rate_path=hoteling_rate_path,
            include_port_ops=include_port_ops,
            port_ops_scenario=port_ops_scenario,
            port_ops_params_path=port_ops_params_path,
        )
    except Exception as exc:
        _log.error("Failed to prepare evaluation context: %s", exc)
        return {}

    cargo_t = float(cargo_t)
    truck_spec = context.truck_spec
    vessel_eff = context.vessel_eff
    hoteling_sel = context.hoteling_sel

    origin_uf = _resolve_uf_from_point(path_data.get("origin", {}))
    destiny_uf = _resolve_uf_from_point(path_data.get("destiny", {}))

    if diesel_price is not None:
        diesel_meta = {
            "price_r_per_l": float(diesel_price),
            "source": "explicit_override",
            "uf_origin": origin_uf or None,
            "uf_destiny": destiny_uf or None,
            "fallback_used": False,
            "csv_path": None,
        }
        price_l = float(diesel_price)
        diesel_source = "explicit_override"
    elif context.diesel_price_override is not None:
        diesel_meta = {
            "price_r_per_l": float(context.diesel_price_override),
            "source": "explicit_override",
            "uf_origin": origin_uf or None,
            "uf_destiny": destiny_uf or None,
            "fallback_used": False,
            "csv_path": None,
        }
        price_l = float(context.diesel_price_override)
        diesel_source = "explicit_override"
    elif context.diesel_lookup is not None:
        diesel_meta = get_average_price_from_lookup(origin_uf, destiny_uf, context.diesel_lookup)
        price_l = float(diesel_meta.get("price_r_per_l", diesel_default_price_r_per_l))
        diesel_source = str(diesel_meta.get("source", "latest_diesel_prices_csv"))
    else:
        diesel_meta = get_average_price(
            origin_uf,
            destiny_uf,
            default_price_r_per_l=diesel_default_price_r_per_l,
            csv_path=diesel_csv_path,
        )
        price_l = float(diesel_meta.get("price_r_per_l", diesel_default_price_r_per_l))
        diesel_source = str(diesel_meta.get("source", "latest_diesel_prices_csv"))

    _log.debug(
        (
            "Evaluator inputs: cargo_t=%.3f truck=%s diesel=R$ %.4f/L uf_o=%s uf_d=%s "
            "vessel_class=%s include_hoteling=%s include_port_ops=%s"
        ),
        cargo_t,
        truck_key,
        price_l,
        origin_uf or "<missing>",
        destiny_uf or "<missing>",
        vessel_eff.vessel_class,
        include_hoteling,
        include_port_ops,
    )

    def _calc_road(leg: Dict[str, Any]) -> Dict[str, Any]:
        dist_raw = leg.get("distance_km")
        dist_km = float(dist_raw) if dist_raw is not None else 0.0
        if dist_km <= 0.0:
            return {
                "distance_km": dist_km,
                "trips": 0,
                "liters": 0.0,
                "cost": 0.0,
                "co2e": 0.0,
            }

        liters, _, _, trips, _, _ = estimate_leg_liters(
            distance_km=dist_km,
            cargo_t=cargo_t,
            spec=truck_spec,
            empty_backhaul_share=0.0,
        )

        liters = float(liters)
        cost = liters * price_l
        co2e = liters * _DIESEL_EF_KG_CO2E_PER_L

        return {
            "distance_km": dist_km,
            "trips": int(trips),
            "liters": liters,
            "cost": float(cost),
            "co2e": float(co2e),
        }

    res_direct = _calc_road(path_data.get("road_direct", {}))
    res_first = _calc_road(path_data.get("first_mile", {}))
    res_last = _calc_road(path_data.get("last_mile", {}))

    route_quality_warnings = [
        dict(item)
        for item in (path_data.get("route_quality_warnings") or [])
        if isinstance(item, dict)
    ]
    sea_leg_data = path_data.get("sea_leg", {}) if isinstance(path_data.get("sea_leg"), dict) else {}
    sea_dist_km = float(sea_leg_data.get("distance_km") or 0.0)
    sea_dist_nm = sea_dist_km / _NM_TO_KM if sea_dist_km > 0 else 0.0
    bunker_price_ton = float(context.bunker_price_ton)

    cargo_share, allocation_debug = compute_cargo_allocation_share(
        inputs={
            "cargo_t": cargo_t,
            "cargo_teu": cargo_teu,
            "t_per_teu_default": t_per_teu_default,
            "allocation_mode": allocation_mode,
            "load_factor": allocation_load_factor,
        },
        vessel_meta={
            "vessel_class": vessel_eff.vessel_class,
            "size_proxy_t_median": vessel_eff.size_proxy_t_median,
            "teu_capacity": vessel_eff.teu_capacity,
            "lightship_t": vessel_eff.lightship_t,
        },
    )

    sea_leg_fuel_g_per_tnm = _positive_float_or_none(sea_leg_data.get("fuel_g_per_tnm"))
    vessel_fuel_g_per_tnm = _positive_float_or_none(vessel_eff.fuel_g_per_tnm)
    fuel_g_per_tnm = sea_leg_fuel_g_per_tnm if sea_leg_fuel_g_per_tnm is not None else vessel_fuel_g_per_tnm
    sea_fuel_g_per_tnm_source = (
        str(sea_leg_data.get("fuel_g_per_tnm_source") or "").strip()
        if sea_leg_fuel_g_per_tnm is not None
        else ("vessel_class_transport_work_intensity" if vessel_fuel_g_per_tnm is not None else "")
    ) or None
    sailing_fuel_mode = (
        "sea_matrix_directional_transport_work_intensity"
        if sea_leg_fuel_g_per_tnm is not None
        else "transport_work_intensity"
    )
    hoteling_disabled_for_transport_work = bool(
        include_hoteling
        and hoteling_hours_total_requested > 0
        and isinstance(fuel_g_per_tnm, (int, float))
        and float(fuel_g_per_tnm) > 0.0
    )
    if isinstance(fuel_g_per_tnm, (int, float)) and fuel_g_per_tnm > 0:
        # Preferred MRV metric: g fuel/(t*nm) allocated directly to cargo and distance.
        sea_fuel_sailing_kg = (float(fuel_g_per_tnm) * cargo_t * sea_dist_nm) / _KG_PER_TONNE
    else:
        # Fallback uses vessel-level kg/nm scaled by cargo share proxy.
        ship_fuel_kg = sea_dist_nm * vessel_eff.fuel_per_nm
        sea_fuel_sailing_kg = ship_fuel_kg * cargo_share
        sailing_fuel_mode = "vessel_fuel_share_fallback"

    hoteling_effective = bool(include_hoteling) and not hoteling_disabled_for_transport_work
    hoteling_hours_total = hoteling_hours_total_requested if hoteling_effective else 0.0
    hoteling_exclusion_reason: str | None = None
    if hoteling_disabled_for_transport_work:
        hoteling_exclusion_reason = "included_in_transport_work_intensity"
        _log.info(
            "Skipping separate hoteling because MRV transport-work intensity is available for vessel class '%s'.",
            vessel_eff.vessel_class,
        )
    elif not include_hoteling:
        hoteling_exclusion_reason = "disabled_by_user"

    hoteling_rate_t_per_h = 0.0
    hoteling_ratio_used = 0.0
    hoteling_aux_main_ratio = 0.0
    hoteling_fuel_kg = 0.0
    hoteling_fuel_ship_kg = 0.0
    hoteling_source_path: str | None = None
    hoteling_vessel_class = vessel_eff.vessel_class

    if hoteling_effective and hoteling_hours_total > 0 and hoteling_sel is not None:
        hoteling_rate_t_per_h = float(hoteling_sel.fuel_rate_hoteling_t_per_h)
        hoteling_ratio_used = float(hoteling_sel.ratio_used)
        hoteling_aux_main_ratio = float(hoteling_sel.aux_main_ratio)
        hoteling_source_path = str(hoteling_sel.source_path)
        hoteling_vessel_class = hoteling_sel.vessel_class
        if hoteling_vessel_class != vessel_eff.vessel_class:
            _log.warning(
                "Hoteling class fallback differs from sea efficiency class: sea=%s hoteling=%s",
                vessel_eff.vessel_class,
                hoteling_vessel_class,
            )
        hoteling_fuel_ship_kg = hoteling_hours_total * hoteling_rate_t_per_h * _KG_PER_TONNE
        hoteling_fuel_kg = hoteling_fuel_ship_kg * cargo_share

    sea_fuel_marine_kg = sea_fuel_sailing_kg + hoteling_fuel_kg
    sea_cost_marine = (sea_fuel_marine_kg / _KG_PER_TONNE) * bunker_price_ton
    sea_co2e_marine = sea_fuel_marine_kg * _BUNKER_EF_KG_CO2E_PER_KG

    port_ops_payload: Dict[str, Any] | None = None
    port_ops_fuel_kg = 0.0
    port_ops_co2e_kg = 0.0
    port_ops_cost_brl = 0.0

    if include_port_ops and port_calls > 0:
        try:
            port_ops_payload = estimate_port_ops(
                scenario=port_ops_scenario,
                port_calls=port_calls,
                port_moves_per_call=port_moves_per_call,
                cargo_t=cargo_t,
                cargo_teu=cargo_teu,
                t_per_teu_default=t_per_teu_default,
                full_call_mode=full_call_mode,
                stat_key=port_ops_stat_key,
                diesel_price_per_l=price_l,
                params_path=port_ops_params_path,
                selection=context.port_ops_selection,
            )
            totals = port_ops_payload.get("totals", {}) if isinstance(port_ops_payload, dict) else {}
            port_ops_fuel_kg = float(totals.get("fuel_kg") or 0.0)
            port_ops_co2e_kg = float(totals.get("co2e_kg") or 0.0)
            port_ops_cost_brl = float(totals.get("cost_brl") or 0.0)
        except Exception as exc:
            _log.error("Failed to resolve/evaluate port-ops artifact: %s", exc)
            return {}

    sea_fuel_total_kg = sea_fuel_marine_kg + port_ops_fuel_kg
    sea_cost_total = sea_cost_marine + port_ops_cost_brl
    sea_co2e_total = sea_co2e_marine + port_ops_co2e_kg

    res_sea = {
        "distance_km": float(sea_dist_km),
        "distance_nm": float(sea_dist_nm),
        "distance_source": sea_leg_data.get("source"),
        "distance_provenance": sea_leg_data.get("distance_provenance"),
        "vessel_class": vessel_eff.vessel_class,
        "fuel_per_nm_kg": float(vessel_eff.fuel_per_nm),
        "fuel_g_per_tnm": (None if fuel_g_per_tnm is None else float(fuel_g_per_tnm)),
        "fuel_g_per_tnm_source": sea_fuel_g_per_tnm_source,
        "route_fuel_g_per_tnm": (None if sea_leg_fuel_g_per_tnm is None else float(sea_leg_fuel_g_per_tnm)),
        "vessel_class_fuel_g_per_tnm": (None if vessel_fuel_g_per_tnm is None else float(vessel_fuel_g_per_tnm)),
        "route_match_rate_segments": _positive_float_or_none(sea_leg_data.get("match_rate_segments")),
        "route_match_rate_tonne_nm": _positive_float_or_none(sea_leg_data.get("match_rate_tonne_nm")),
        "route_segment_count": int(sea_leg_data.get("segment_count") or 0),
        "route_matched_segment_count": int(sea_leg_data.get("matched_segment_count") or 0),
        "route_voyage_count": int(sea_leg_data.get("voyage_count") or 0),
        "route_matched_voyage_count": int(sea_leg_data.get("matched_voyage_count") or 0),
        "route_unique_imo_count": int(sea_leg_data.get("unique_imo_count") or 0),
        "route_matched_imo_count": int(sea_leg_data.get("matched_imo_count") or 0),
        "route_corridor_leg_count": int(sea_leg_data.get("corridor_leg_count") or 0),
        "route_corridor_port_path": list(sea_leg_data.get("corridor_port_path") or []),
        "size_proxy_t_median": (
            None if vessel_eff.size_proxy_t_median is None else float(vessel_eff.size_proxy_t_median)
        ),
        "teu_capacity": allocation_debug.get("teu_capacity"),
        "allocation_mode_used": allocation_debug.get("allocation_mode_used"),
        "load_factor": allocation_debug.get("load_factor"),
        "teu_loaded": allocation_debug.get("teu_loaded"),
        "cargo_teu_resolved": allocation_debug.get("cargo_teu_resolved"),
        "share_old_dwt": allocation_debug.get("share_old_dwt"),
        "share_new_teu": allocation_debug.get("share_new_teu"),
        "ratio_new_vs_old": allocation_debug.get("ratio_new_vs_old"),
        "eff_t_per_teu": allocation_debug.get("eff_t_per_teu"),
        "cargo_allocation_share": float(cargo_share),
        "sailing_fuel_calc_mode": sailing_fuel_mode,
        "fuel_kg_sailing": float(sea_fuel_sailing_kg),
        "hoteling_requested": bool(include_hoteling),
        "hoteling_included": bool(hoteling_effective),
        "hoteling_exclusion_reason": hoteling_exclusion_reason,
        "hoteling_hours_per_call": float(hoteling_hours_per_call),
        "port_calls": int(port_calls),
        "hoteling_hours_total": float(hoteling_hours_total),
        "hoteling_hours_total_requested": float(hoteling_hours_total_requested),
        "hoteling_rate_t_per_h": float(hoteling_rate_t_per_h),
        "hoteling_fuel_ship_kg": float(hoteling_fuel_ship_kg),
        "hoteling_fuel_kg": float(hoteling_fuel_kg),
        "hoteling_vessel_class": hoteling_vessel_class,
        "hoteling_ratio_used": float(hoteling_ratio_used),
        "hoteling_aux_main_ratio": float(hoteling_aux_main_ratio),
        "fuel_kg_marine": float(sea_fuel_marine_kg),
        "cost_marine": float(sea_cost_marine),
        "co2e_marine": float(sea_co2e_marine),
        "port_ops_included": bool(include_port_ops),
        "port_ops_scenario_requested": str(port_ops_scenario),
        "port_ops_stat_key": str(port_ops_stat_key),
        "cargo_teu_requested": (None if cargo_teu is None else float(max(float(cargo_teu), 0.0))),
        "t_per_teu_default": float(t_per_teu_default),
        "full_call_mode": bool(full_call_mode),
        "port_moves_per_call_requested": (
            None if port_moves_per_call is None else float(max(float(port_moves_per_call), 0.0))
        ),
        "port_ops_fuel_kg": float(port_ops_fuel_kg),
        "port_ops_cost": float(port_ops_cost_brl),
        "port_ops_co2e": float(port_ops_co2e_kg),
        "port_ops": port_ops_payload,
        "fuel_kg": float(sea_fuel_total_kg),
        "cost": float(sea_cost_total),
        "co2e": float(sea_co2e_total),
    }

    mm_cost = res_first["cost"] + res_last["cost"] + res_sea["cost"]
    mm_co2e = res_first["co2e"] + res_last["co2e"] + res_sea["co2e"]

    road_cost = float(res_direct["cost"])
    road_co2e = float(res_direct["co2e"])

    return {
        "inputs": {
            "cargo_t": cargo_t,
            "truck": truck_key,
            "diesel_price": price_l,
            "diesel_price_source": diesel_source,
            "diesel_price_meta": diesel_meta,
            "bunker_price": bunker_price_ton,
            "marine_fuel_type": _MARINE_FUEL_TYPE,
            "marine_ef_kg_per_kg": _BUNKER_EF_KG_CO2E_PER_KG,
            "uf_origin": origin_uf or None,
            "uf_destiny": destiny_uf or None,
            "vessel_class_requested": vessel_eff.requested_class,
            "vessel_class": vessel_eff.vessel_class,
            "sea_fuel_per_nm_kg": float(vessel_eff.fuel_per_nm),
            "sea_fuel_g_per_tnm": (None if fuel_g_per_tnm is None else float(fuel_g_per_tnm)),
            "sea_fuel_g_per_tnm_source": sea_fuel_g_per_tnm_source,
            "sea_route_fuel_g_per_tnm": (
                None if sea_leg_fuel_g_per_tnm is None else float(sea_leg_fuel_g_per_tnm)
            ),
            "sea_vessel_class_fuel_g_per_tnm": (
                None if vessel_fuel_g_per_tnm is None else float(vessel_fuel_g_per_tnm)
            ),
            "sea_route_match_rate_segments": _positive_float_or_none(sea_leg_data.get("match_rate_segments")),
            "sea_route_match_rate_tonne_nm": _positive_float_or_none(sea_leg_data.get("match_rate_tonne_nm")),
            "sea_route_segment_count": int(sea_leg_data.get("segment_count") or 0),
            "sea_route_matched_segment_count": int(sea_leg_data.get("matched_segment_count") or 0),
            "sea_route_voyage_count": int(sea_leg_data.get("voyage_count") or 0),
            "sea_route_matched_voyage_count": int(sea_leg_data.get("matched_voyage_count") or 0),
            "sea_route_unique_imo_count": int(sea_leg_data.get("unique_imo_count") or 0),
            "sea_route_matched_imo_count": int(sea_leg_data.get("matched_imo_count") or 0),
            "sea_route_corridor_leg_count": int(sea_leg_data.get("corridor_leg_count") or 0),
            "sea_route_corridor_port_path": list(sea_leg_data.get("corridor_port_path") or []),
            "size_proxy_t_median": (
                None if vessel_eff.size_proxy_t_median is None else float(vessel_eff.size_proxy_t_median)
            ),
            "teu_capacity": allocation_debug.get("teu_capacity"),
            "allocation_mode_requested": allocation_debug.get("allocation_mode_requested"),
            "allocation_mode_used": allocation_debug.get("allocation_mode_used"),
            "allocation_load_factor": allocation_debug.get("load_factor"),
            "teu_loaded": allocation_debug.get("teu_loaded"),
            "share_old_dwt": allocation_debug.get("share_old_dwt"),
            "share_new_teu": allocation_debug.get("share_new_teu"),
            "ratio_new_vs_old": allocation_debug.get("ratio_new_vs_old"),
            "eff_t_per_teu": allocation_debug.get("eff_t_per_teu"),
            "cargo_allocation_share": float(cargo_share),
            "sailing_fuel_calc_mode": sailing_fuel_mode,
            "vessel_sample_size": int(vessel_eff.sample_size),
            "vessel_efficiency_source": str(vessel_eff.source_path),
            "include_hoteling": bool(hoteling_effective),
            "hoteling_requested": bool(include_hoteling),
            "hoteling_exclusion_reason": hoteling_exclusion_reason,
            "hoteling_hours_per_call": float(hoteling_hours_per_call),
            "port_calls": int(port_calls),
            "hoteling_hours_total": float(hoteling_hours_total),
            "hoteling_hours_total_requested": float(hoteling_hours_total_requested),
            "hoteling_rate_t_per_h": float(hoteling_rate_t_per_h),
            "hoteling_vessel_class": hoteling_vessel_class,
            "hoteling_ratio_used": float(hoteling_ratio_used),
            "hoteling_aux_main_ratio": float(hoteling_aux_main_ratio),
            "hoteling_source": hoteling_source_path,
            "include_port_ops": bool(include_port_ops),
            "port_ops_scenario_requested": str(port_ops_scenario),
            "port_ops_stat_key": str(port_ops_stat_key),
            "cargo_teu_requested": (None if cargo_teu is None else float(max(float(cargo_teu), 0.0))),
            "t_per_teu_default": float(t_per_teu_default),
            "full_call_mode": bool(full_call_mode),
            "port_moves_per_call_requested": (
                None if port_moves_per_call is None else float(max(float(port_moves_per_call), 0.0))
            ),
            "port_ops_source": (
                None
                if not isinstance(port_ops_payload, dict)
                else str(port_ops_payload.get("source_path") or "")
            ),
            "port_ops_scenario_resolved": (
                None
                if not isinstance(port_ops_payload, dict)
                else str(port_ops_payload.get("resolved_scenario") or "")
            ),
            "port_moves_per_call_resolved": (
                None
                if not isinstance(port_ops_payload, dict)
                else float(port_ops_payload.get("port_moves_per_call") or 0.0)
            ),
            "cargo_teu_resolved": int(allocation_debug.get("cargo_teu_resolved") or 0),
            "cargo_teu_resolved_port_ops": (
                None
                if not isinstance(port_ops_payload, dict)
                else int(port_ops_payload.get("cargo_teu_resolved") or 0)
            ),
            "route_quality_warning_count": len(route_quality_warnings),
        },
        "route_quality_warnings": route_quality_warnings,
        "road_only": res_direct,
        "multimodal": {
            "first_mile": res_first,
            "sea": res_sea,
            "last_mile": res_last,
            "total_cost": float(mm_cost),
            "total_co2e": float(mm_co2e),
        },
        "comparison": {
            "delta_cost": float(mm_cost - road_cost),
            "delta_co2e": float(mm_co2e - road_co2e),
            "savings_pct": float((1 - (mm_cost / road_cost)) * 100) if road_cost > 0 else 0.0,
        },
    }


if __name__ == "__main__":
    import json

    from modules.infra.log_manager import init_logging

    init_logging(level="DEBUG")
    print("--- Evaluator Smoke Test ---")

    geo_dummy = {
        "status": "ok",
        "origin": {"uf": "SP"},
        "destiny": {"uf": "AM"},
        "road_direct": {"distance_km": 4000.0},
        "first_mile": {"distance_km": 100.0},
        "last_mile": {"distance_km": 50.0},
        "sea_leg": {"distance_km": 3500.0},
    }

    res = evaluate_path(geo_dummy, cargo_t=27.0)
    print(json.dumps(res, indent=2))
    print("--- Done ---")
