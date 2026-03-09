# modules/multimodal/persistence.py
# -*- coding: utf-8 -*-

"""
Helpers for flattening multimodal evaluation payloads for persistence.
"""

from __future__ import annotations

from typing import Any, Dict

_DIESEL_DENSITY_KG_PER_L = 0.84


def flatten_evaluation_for_db(origin_name: str, destiny_name: str, res: Dict[str, Any]) -> Dict[str, Any]:
    """Convert nested evaluator output into a flat analytical payload."""
    road_only = res.get("road_only", {})
    mm = res.get("multimodal", {})

    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})
    comp = res.get("comparison", {})

    road_liters = float(road_only.get("liters") or 0.0)
    road_fuel_kg = float(road_only.get("fuel_kg") or (road_liters * _DIESEL_DENSITY_KG_PER_L))

    mm_road_liters = float(first.get("liters") or 0.0) + float(last.get("liters") or 0.0)
    mm_road_kg = float(first.get("fuel_kg") or 0.0) + float(last.get("fuel_kg") or 0.0)
    if mm_road_kg <= 0.0 and mm_road_liters > 0.0:
        mm_road_kg = mm_road_liters * _DIESEL_DENSITY_KG_PER_L

    sea_fuel_kg = float(sea.get("fuel_kg") or 0.0)

    return {
        "origin_name": origin_name,
        "destiny_name": destiny_name,
        "cargo_t": res["inputs"]["cargo_t"],
        "road_distance_km": road_only.get("distance_km"),
        "road_fuel_liters": road_liters,
        "road_fuel_kg": road_fuel_kg,
        "road_fuel_cost_r": road_only.get("cost"),
        "road_co2e_kg": road_only.get("co2e"),
        "mm_road_fuel_liters": mm_road_liters,
        "mm_road_fuel_kg": mm_road_kg,
        "mm_road_fuel_cost_r": float(first.get("cost") or 0.0) + float(last.get("cost") or 0.0),
        "mm_road_co2e_kg": float(first.get("co2e") or 0.0) + float(last.get("co2e") or 0.0),
        "sea_km": sea.get("distance_km"),
        "sea_fuel_kg": sea_fuel_kg,
        "sea_fuel_cost_r": sea.get("cost"),
        "sea_co2e_kg": sea.get("co2e"),
        "total_fuel_kg": mm_road_kg + sea_fuel_kg,
        "total_fuel_cost_r": mm.get("total_cost"),
        "total_co2e_kg": mm.get("total_co2e"),
        "delta_cost_r": comp.get("delta_cost"),
        "delta_co2e_kg": comp.get("delta_co2e"),
    }
