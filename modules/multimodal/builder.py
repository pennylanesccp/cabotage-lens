# modules/multimodal/builder.py
# -*- coding: utf-8 -*-

"""
Multimodal Geometry Builder.
============================

This module is the "Geospatial Engine" of the multimodal assessment.
It is responsible for resolving the physical path for a shipment:

1.  **Resolution:** Geocodes the origin and destination.
2.  **Network Selection:** Finds the optimal entry/exit ports.
3.  **Routing:** Calculates the three critical road legs:
    * Direct Road (O -> D)
    * First Mile (O -> Port Origin)
    * Last Mile (Port Destiny -> D)
4.  **Sea Leg:** Looks up the maritime distance.

It delegates raw road routing to `modules.road.router` (which handles caching)
and sea distances to `modules.cabotage.sea_matrix`.

Usage
-----
    from modules.multimodal.builder import build_path_geometry

    path = build_path_geometry("Sao Paulo", "Manaus")
    print(path.legs.road_direct.distance_km)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict, cast
from pathlib import Path

# Path Bootstrap (for direct execution smoke tests)
if __name__ == "__main__":
    import sys
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger
from modules.core.config import Config
from modules.road.router import get_or_create_leg, ORSClient, ORSConfig
from modules.addressing.resolver import resolve_point_null_safe
from modules.ports.ports_index import load_ports
from modules.ports.ports_nearest import find_nearest_port
from modules.cabotage.sea_matrix import SeaMatrix

_log = get_logger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Data Models (TypedDicts for clean structure)
# ────────────────────────────────────────────────────────────────────────────────

class Point(TypedDict):
    label: str
    lat: float
    lon: float

class LegResult(TypedDict):
    origin_name: str
    destiny_name: str
    distance_km: Optional[float]
    is_hgv: Optional[bool]
    profile_used: Optional[str]
    cached: bool

class SeaResult(TypedDict):
    distance_km: float
    source: str

class PathGeometry(TypedDict):
    """The complete geometric definition of the comparison."""
    origin: Point
    destiny: Point
    port_origin: Dict[str, Any]
    port_destiny: Dict[str, Any]
    road_direct: LegResult
    first_mile: LegResult
    last_mile: LegResult
    sea_leg: SeaResult
    status: str


# ────────────────────────────────────────────────────────────────────────────────
# Core Logic
# ────────────────────────────────────────────────────────────────────────────────

def build_path_geometry(
      origin_input: Any
    , destiny_input: Any
    , *
    , ors_profile: str = "driving-hgv"
    , overwrite_road: bool = False
    , ports_json_path: Optional[Path] = None
    , sea_matrix_path: Optional[Path] = None
    , db_path: Optional[Path] = None
) -> Optional[PathGeometry]:
    """
    Resolve coordinates and calculate all road/sea legs for a comparison.

    This function orchestrates `addressing`, `ports`, `road`, and `cabotage`
    modules to create a single geometric "truth" for the shipment.

    Parameters
    ----------
    origin_input, destiny_input : str or Dict
        Addresses, CEPs, or lat/lon dicts.
    ors_profile : str
        Routing profile for truck legs (default: 'driving-hgv').
    overwrite_road : bool
        If True, ignores road cache and forces fresh API calls.

    Returns
    -------
    PathGeometry dict or None if geocoding fails.
    """
    # 1. Setup Infrastructure
    #    We load these fresh or relies on module-level caching if implemented.
    #    For production, you might want to pass these in, but loading here keeps API simple.
    cfg = Config() # Assuming a global config helper exists or uses defaults
    
    p_json = ports_json_path or Path("data/processed/cabotage_data/ports_br.json")
    s_json = sea_matrix_path or Path("data/processed/cabotage_data/sea_matrix.json")
    d_path = db_path or Path("data/processed/database/carbon_footprint.sqlite")

    ors = ORSClient(ORSConfig())
    ports = load_ports(path=str(p_json))
    sea_matrix = SeaMatrix.from_json_path(s_json)

    # 2. Geocode Endpoints
    #    We use the null_safe resolver which handles exceptions internally.
    _log.debug(f"Resolving endpoints: '{origin_input}' -> '{destiny_input}'")
    p_origin = resolve_point_null_safe(origin_input, ors, _log)
    p_destiny = resolve_point_null_safe(destiny_input, ors, _log)

    if not p_origin or not p_destiny:
        _log.error("Failed to geocode one or both endpoints. Aborting geometry build.")
        return None

    # Convert to strict Point dicts for consistency
    origin_pt: Point = {"label": p_origin.label, "lat": p_origin.lat, "lon": p_origin.lon}
    destiny_pt: Point = {"label": p_destiny.label, "lat": p_destiny.lat, "lon": p_destiny.lon}

    # 3. Select Ports
    #    Find the geographically closest ports to O and D.
    _log.debug("Selecting optimal ports...")
    po_data = find_nearest_port(origin_pt["lat"], origin_pt["lon"], ports)
    pd_data = find_nearest_port(destiny_pt["lat"], destiny_pt["lon"], ports)

    _log.info(f"Ports Selected: {po_data['name']} (Origin) -> {pd_data['name']} (Destiny)")

    # 4. Routing - Preparation
    #    Extract "Gate" coordinates for the ports to ensure accurate truck routing.
    def _get_node(p_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract routing target from port data (Gate > Centroid)."""
        if p_data.get("gate"):
            return {
                "lat": p_data["gate"]["lat"],
                "lon": p_data["gate"]["lon"],
                "label": f"{p_data['name']} ({p_data['gate']['label']})"
            }
        return {
            "lat": p_data["lat"],
            "lon": p_data["lon"],
            "label": p_data["name"]
        }

    po_node = _get_node(po_data)
    pd_node = _get_node(pd_data)

    # 5. Routing - Execution (Road)
    #    We use the road router facade to get/cache these legs.
    _log.debug(f"Calculating road legs (Profile: {ors_profile})...")

    # A) Direct Road (Reference Baseline)
    leg_direct = get_or_create_leg(
        ors, origin_pt, destiny_pt,
        profile=ors_profile, overwrite=overwrite_road, db_path=d_path
    )

    # B) First Mile (Origin -> Origin Port)
    leg_first = get_or_create_leg(
        ors, origin_pt, po_node,
        profile=ors_profile, overwrite=overwrite_road, db_path=d_path
    )

    # C) Last Mile (Destiny Port -> Destiny)
    leg_last = get_or_create_leg(
        ors, pd_node, destiny_pt,
        profile=ors_profile, overwrite=overwrite_road, db_path=d_path
    )

    # 6. Routing - Execution (Sea)
    #    SeaMatrix requires {lat, lon, name} to perform lookups or haversine fallback.
    #    We use the port centroids for sea distance (standard practice), not gates.
    sea_dist, sea_src = sea_matrix.km_with_source(
        {"lat": po_data["lat"], "lon": po_data["lon"], "name": po_data["name"]},
        {"lat": pd_data["lat"], "lon": pd_data["lon"], "name": pd_data["name"]}
    )

    # 7. Assembly
    result: PathGeometry = {
        "origin": origin_pt,
        "destiny": destiny_pt,
        "port_origin": po_data,
        "port_destiny": pd_data,
        "road_direct": cast(LegResult, leg_direct),
        "first_mile": cast(LegResult, leg_first),
        "last_mile": cast(LegResult, leg_last),
        "sea_leg": {"distance_km": float(sea_dist), "source": sea_src},
        "status": "ok"
    }
    
    return result


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging
    import json

    init_logging(level="INFO")
    print("--- Geometry Builder Smoke Test ---")

    # Test Route: USP (SP) -> UFAM (Manaus)
    # This forces a complex route: Truck -> Santos -> Ship -> Manaus -> Truck -> UFAM
    res = build_path_geometry(
        "Avenida Professor Luciano Gualberto, São Paulo",
        "Manaus, AM",
        ors_profile="driving-hgv"
    )

    if res:
        print("\n✅ Geometry Built Successfully!")
        print(f"   • Direct Road: {res['road_direct']['distance_km']} km")
        print(f"   • First Mile:  {res['first_mile']['distance_km']} km (to {res['port_origin']['name']})")
        print(f"   • Sea Leg:     {res['sea_leg']['distance_km']} km")
        print(f"   • Last Mile:   {res['last_mile']['distance_km']} km (from {res['port_destiny']['name']})")
        
        # Optional: Dump to verify JSON serialization
        # print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Geometry Build Failed.")
    
    print("--- Done ---")