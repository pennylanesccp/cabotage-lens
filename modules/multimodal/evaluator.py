# modules/multimodal/evaluator.py
# -*- coding: utf-8 -*-

"""
Multimodal Evaluator.
=====================

Takes the geometric path (from builder.py) and applies:
1. Truck specifications (fuel consumption curves).
2. Fuel prices (Diesel/Bunker).
3. Emission factors.

Returns a complete financial and environmental assessment.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Path Bootstrap
if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger
from modules.core.config import Config
from modules.fuel.road_fuel_model import estimate_leg_liters
from modules.fuel.truck_specs import get_truck_spec
from modules.costs.diesel_prices import get_average_price
from modules.costs.ship_fuel_prices import get_bunker_price

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Core Logic
# ────────────────────────────────────────────────────────────────────────────────

def evaluate_path(
      path_data: Dict[str, Any]
    , cargo_t: float
    , truck_key: str = "semi_27t"
    , diesel_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Assess the costs and emissions for a given path geometry.

    Parameters
    ----------
    path_data : Dict
        Output from `builder.build_path_geometry`.
    cargo_t : float
        Amount of cargo in tonnes.
    truck_key : str
        Truck profile key (e.g., 'semi_27t').
    diesel_price : float, optional
        Override for diesel price. If None, looks up state average.
    """
    if not path_data or path_data.get("status") != "ok":
        _log.warning("Cannot evaluate invalid path geometry.")
        return {}

    # 1. Resolve Parameters
    truck_spec = get_truck_spec(truck_key)
    
    # Determine diesel price
    # path_data["origin"] is a dict like {'label': '...', 'lat': ..., 'lon': ...}
    # It might not have 'uf' key directly if not geocoded with that info
    # We can try to infer UF from the label string if needed, but for now fallback to defaults
    # Ideally, builder.py should return 'uf' in origin/destiny
    
    # Extract UF if present, or default to "SP" for price lookup
    origin_uf = "SP" 
    destiny_uf = "SP"
    
    # If builder returns UF (which the fixed resolver does!), use it
    if path_data["origin"].get("uf"):
        origin_uf = path_data["origin"]["uf"]
    if path_data["destiny"].get("uf"):
        destiny_uf = path_data["destiny"]["uf"]

    price_meta = get_average_price(origin_uf, destiny_uf)
    price_l = diesel_price or price_meta.get("price_r_per_l", 6.0)
    
    _log.debug(f"Evaluator: Cargo={cargo_t}t, Truck={truck_key}, Diesel=R${price_l:.2f}/L")

    # 2. Evaluate Road Legs
    def _calc_road(leg: Dict[str, Any]) -> Dict[str, Any]:
        dist = leg.get("distance_km")
        if not dist: 
            return {"liters": 0.0, "cost": 0.0, "co2e": 0.0}
            
        liters, _, _, trips, _, _ = estimate_leg_liters(
            distance_km=dist,
            cargo_t=cargo_t,
            spec=truck_spec,
            empty_backhaul_share=0.0 # Simplifying assumption for now
        )
        
        cost = liters * price_l
        co2e = liters * 2.68 # Diesel EF (kg CO2e/L)
        
        return {
            "distance_km": dist,
            "trips": trips,
            "liters": liters,
            "cost": cost,
            "co2e": co2e
        }

    res_direct = _calc_road(path_data["road_direct"])
    res_first = _calc_road(path_data["first_mile"])
    res_last = _calc_road(path_data["last_mile"])

    # 3. Evaluate Sea Leg
    sea_dist = path_data["sea_leg"]["distance_km"]
    
    # Get real bunker price (VLSFO)
    bunker_price_ton = get_bunker_price(default_price_brl_mt=3500.0)
    
    # Simple Sea Model (linear k factor)
    SEA_FUEL_INTENSITY = 0.0025 # kg fuel / t*km
    BUNKER_EF = 3.2 # kg CO2e / kg fuel
    
    sea_fuel_kg = sea_dist * cargo_t * SEA_FUEL_INTENSITY
    sea_cost = (sea_fuel_kg / 1000.0) * bunker_price_ton
    sea_co2e = sea_fuel_kg * BUNKER_EF

    res_sea = {
        "distance_km": sea_dist,
        "fuel_kg": sea_fuel_kg,
        "cost": sea_cost,
        "co2e": sea_co2e
    }

    # 4. Aggregation
    mm_cost = res_first["cost"] + res_last["cost"] + res_sea["cost"]
    mm_co2e = res_first["co2e"] + res_last["co2e"] + res_sea["co2e"]
    
    road_cost = res_direct["cost"]
    road_co2e = res_direct["co2e"]

    return {
        "inputs": {
            "cargo_t": cargo_t,
            "truck": truck_key,
            "diesel_price": price_l,
            "bunker_price": bunker_price_ton
        },
        "road_only": res_direct,
        "multimodal": {
            "first_mile": res_first,
            "sea": res_sea,
            "last_mile": res_last,
            "total_cost": mm_cost,
            "total_co2e": mm_co2e
        },
        "comparison": {
            "delta_cost": mm_cost - road_cost,
            "delta_co2e": mm_co2e - road_co2e,
            "savings_pct": (1 - (mm_cost / road_cost)) * 100 if road_cost > 0 else 0
        }
    }

# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging
    import json
    
    init_logging(level="DEBUG")
    print("--- Evaluator Smoke Test ---")
    
    # Dummy geometry for testing
    geo_dummy = {
        "status": "ok",
        "origin": {"uf": "SP"},
        "destiny": {"uf": "AM"},
        "road_direct": {"distance_km": 4000.0},
        "first_mile": {"distance_km": 100.0},
        "last_mile": {"distance_km": 50.0},
        "sea_leg": {"distance_km": 3500.0}
    }
    
    res = evaluate_path(geo_dummy, cargo_t=27.0)
    print(json.dumps(res, indent=2))
    print("--- Done ---")