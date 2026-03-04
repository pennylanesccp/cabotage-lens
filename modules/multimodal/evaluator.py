# modules/multimodal/evaluator.py
# -*- coding: utf-8 -*-

"""
Multimodal evaluator.

Consumes path geometry and produces cost/emissions comparison between:
- direct road,
- multimodal (first mile + sea leg + last mile).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

# Path bootstrap
if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.costs.diesel_prices import get_average_price, normalize_uf
from modules.costs.ship_fuel_prices import get_bunker_price
from modules.fuel.road_fuel_model import estimate_leg_liters
from modules.fuel.truck_specs import get_truck_spec
from modules.infra.log_manager import get_logger
from modules.multimodal.container_efficiency import (
    DEFAULT_VESSEL_CLASS,
    resolve_vessel_class_efficiency,
)
from modules.multimodal.hoteling import resolve_hoteling_rate

_log = get_logger(__name__)

_DIESEL_EF_KG_CO2E_PER_L = 2.68
_BUNKER_EF_KG_CO2E_PER_KG = 3.2
_NM_TO_KM = 1.852
_KG_PER_TONNE = 1000.0


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
) -> Dict[str, Any]:
    """Assess costs and emissions for a path geometry payload."""
    if not path_data or path_data.get("status") != "ok":
        _log.warning("Cannot evaluate invalid path geometry.")
        return {}

    include_hoteling = bool(include_hoteling)
    hoteling_hours_per_call = max(float(hoteling_hours_per_call), 0.0)
    port_calls = max(int(port_calls), 0)
    hoteling_hours_total = hoteling_hours_per_call * float(port_calls) if include_hoteling else 0.0

    try:
        vessel_eff = resolve_vessel_class_efficiency(
            vessel_class=vessel_class,
            efficiency_json_path=vessel_efficiency_path,
        )
    except Exception as exc:
        _log.error("Failed to resolve vessel class efficiency: %s", exc)
        return {}

    hoteling_sel = None
    if include_hoteling and hoteling_hours_total > 0:
        try:
            hoteling_sel = resolve_hoteling_rate(
                vessel_class=vessel_class,
                hoteling_rate_path=hoteling_rate_path,
            )
        except Exception as exc:
            _log.error("Failed to resolve hoteling-rate artifact: %s", exc)
            return {}

    cargo_t = float(cargo_t)
    truck_spec = get_truck_spec(truck_key)

    origin_uf = _resolve_uf_from_point(path_data.get("origin", {}))
    destiny_uf = _resolve_uf_from_point(path_data.get("destiny", {}))

    diesel_meta = get_average_price(origin_uf, destiny_uf)
    if diesel_price is not None:
        price_l = float(diesel_price)
        diesel_source = "explicit_override"
    else:
        price_l = float(diesel_meta.get("price_r_per_l", 6.0))
        diesel_source = str(diesel_meta.get("source", "latest_diesel_prices_csv"))

    _log.debug(
        "Evaluator inputs: cargo_t=%.3f truck=%s diesel=R$ %.4f/L uf_o=%s uf_d=%s vessel_class=%s include_hoteling=%s",
        cargo_t,
        truck_key,
        price_l,
        origin_uf or "<missing>",
        destiny_uf or "<missing>",
        vessel_eff.vessel_class,
        include_hoteling,
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

    sea_dist_km = float(path_data.get("sea_leg", {}).get("distance_km") or 0.0)
    sea_dist_nm = sea_dist_km / _NM_TO_KM if sea_dist_km > 0 else 0.0
    bunker_price_ton = float(get_bunker_price(default_price_brl_mt=3500.0))

    # MRV class medians are ship-level kg fuel / n mile.
    sea_fuel_sailing_kg = sea_dist_nm * vessel_eff.fuel_per_nm

    hoteling_rate_t_per_h = 0.0
    hoteling_ratio_used = 0.0
    hoteling_aux_main_ratio = 0.0
    hoteling_fuel_kg = 0.0
    hoteling_source_path: str | None = None

    if include_hoteling and hoteling_hours_total > 0 and hoteling_sel is not None:
        hoteling_rate_t_per_h = float(hoteling_sel.fuel_rate_hoteling_t_per_h)
        hoteling_ratio_used = float(hoteling_sel.ratio_used)
        hoteling_aux_main_ratio = float(hoteling_sel.aux_main_ratio)
        hoteling_source_path = str(hoteling_sel.source_path)
        hoteling_fuel_kg = hoteling_hours_total * hoteling_rate_t_per_h * _KG_PER_TONNE

    sea_fuel_total_kg = sea_fuel_sailing_kg + hoteling_fuel_kg
    sea_cost = (sea_fuel_total_kg / _KG_PER_TONNE) * bunker_price_ton
    sea_co2e = sea_fuel_total_kg * _BUNKER_EF_KG_CO2E_PER_KG

    res_sea = {
        "distance_km": float(sea_dist_km),
        "distance_nm": float(sea_dist_nm),
        "vessel_class": vessel_eff.vessel_class,
        "fuel_per_nm_kg": float(vessel_eff.fuel_per_nm),
        "fuel_kg_sailing": float(sea_fuel_sailing_kg),
        "hoteling_included": bool(include_hoteling),
        "hoteling_hours_per_call": float(hoteling_hours_per_call),
        "port_calls": int(port_calls),
        "hoteling_hours_total": float(hoteling_hours_total),
        "hoteling_rate_t_per_h": float(hoteling_rate_t_per_h),
        "hoteling_fuel_kg": float(hoteling_fuel_kg),
        "hoteling_ratio_used": float(hoteling_ratio_used),
        "hoteling_aux_main_ratio": float(hoteling_aux_main_ratio),
        "fuel_kg": float(sea_fuel_total_kg),
        "cost": float(sea_cost),
        "co2e": float(sea_co2e),
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
            "uf_origin": origin_uf or None,
            "uf_destiny": destiny_uf or None,
            "vessel_class_requested": vessel_eff.requested_class,
            "vessel_class": vessel_eff.vessel_class,
            "sea_fuel_per_nm_kg": float(vessel_eff.fuel_per_nm),
            "vessel_sample_size": int(vessel_eff.sample_size),
            "vessel_efficiency_source": str(vessel_eff.source_path),
            "include_hoteling": bool(include_hoteling),
            "hoteling_hours_per_call": float(hoteling_hours_per_call),
            "port_calls": int(port_calls),
            "hoteling_hours_total": float(hoteling_hours_total),
            "hoteling_rate_t_per_h": float(hoteling_rate_t_per_h),
            "hoteling_ratio_used": float(hoteling_ratio_used),
            "hoteling_aux_main_ratio": float(hoteling_aux_main_ratio),
            "hoteling_source": hoteling_source_path,
        },
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
