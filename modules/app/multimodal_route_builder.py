#!/usr/bin/env python3
# modules/app/multimodal_route_builder.py
# -*- coding: utf-8 -*-

"""
Multimodal Route Builder.
=========================

Orchestrates the comparison between a Direct Road route and a Cabotage route.
1. Resolves coordinates.
2. Selects nearest ports.
3. Delegates leg calculations to `modules.road.router`.
4. Delegates sea distance to `modules.cabotage.sea_matrix`.
5. Assembles the final JSON payload.
"""

from __future__ import annotations

from pathlib import Path
import sys
import json
import argparse
from typing import Any, Dict

# Path Bootstrap
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Imports from "Mother Modules" ---
from modules.infra.log_manager import init_logging, get_logger
# UPDATED: Import everything related to road/routing from the router module
from modules.road.router import get_or_create_leg, ORSClient, ORSConfig
from modules.addressing.resolver import resolve_point_null_safe
from modules.ports.ports_index import load_ports
from modules.ports.ports_nearest import find_nearest_port
from modules.cabotage.sea_matrix import SeaMatrix
from modules.infra.database_manager import DEFAULT_DB_PATH

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Configuration Defaults
# ────────────────────────────────────────────────────────────────────────────────
DEFAULT_PORTS_JSON = ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"
DEFAULT_SEA_JSON   = ROOT / "data" / "processed" / "cabotage_data" / "sea_matrix.json"


# ────────────────────────────────────────────────────────────────────────────────
# Orchestration Logic
# ────────────────────────────────────────────────────────────────────────────────

def build_multimodal_route(
      origin_raw: str
    , destiny_raw: str
    , *
    , ors_profile: str = "driving-hgv"
    , overwrite: bool = False
    , ports_path: Path = DEFAULT_PORTS_JSON
    , sea_path: Path = DEFAULT_SEA_JSON
    , db_path: Path = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """
    Main business logic.
    """
    # 1. Initialize Services
    ors = ORSClient(ORSConfig())
    ports = load_ports(path=str(ports_path))
    sea_matrix = SeaMatrix.from_json_path(sea_path)

    # 2. Geocode Origin/Destiny
    #    resolve_point_null_safe returns a GeoPoint (lat, lon, label)
    p_origin = resolve_point_null_safe(origin_raw, ors, _log)
    p_destiny = resolve_point_null_safe(destiny_raw, ors, _log)

    if not p_origin or not p_destiny:
        _log.error("Geocoding failed for one or both endpoints.")
        return {"status": "geocode_failed", "inputs": {"origin": origin_raw, "destiny": destiny_raw}}

    # Convert GeoPoints to simple dicts for the router
    # This ensures we pass explicit coords, not just strings
    origin_dict = {"lat": p_origin.lat, "lon": p_origin.lon, "label": p_origin.label}
    destiny_dict = {"lat": p_destiny.lat, "lon": p_destiny.lon, "label": p_destiny.label}

    # 3. Identify Ports
    #    find_nearest_port returns a dict with metadata + best 'gate' coords
    port_origin = find_nearest_port(p_origin.lat, p_origin.lon, ports)
    port_destiny = find_nearest_port(p_destiny.lat, p_destiny.lon, ports)

    # Helper to get the "Gate" coordinates for routing
    def _get_gate_coords(p: Dict[str, Any]) -> Dict[str, Any]:
        # Use gate if available, else centroid
        if p.get("gate"):
            return {
                "lat": p["gate"]["lat"],
                "lon": p["gate"]["lon"],
                "label": f"{p['name']} ({p['gate']['label']})"
            }
        return {
            "lat": p["lat"],
            "lon": p["lon"],
            "label": p["name"]
        }

    po_node = _get_gate_coords(port_origin)
    pd_node = _get_gate_coords(port_destiny)

    # 4. Calculate Legs (Using the Router Module)
    
    # A) Direct Road (Origin -> Destiny)
    leg_direct = get_or_create_leg(
        ors, origin_dict, destiny_dict, 
        profile=ors_profile, overwrite=overwrite, db_path=db_path
    )

    # B) First Mile (Origin -> Origin Port)
    leg_first_mile = get_or_create_leg(
        ors, origin_dict, po_node,
        profile=ors_profile, overwrite=overwrite, db_path=db_path
    )

    # C) Last Mile (Destiny Port -> Destiny)
    leg_last_mile = get_or_create_leg(
        ors, pd_node, destiny_dict,
        profile=ors_profile, overwrite=overwrite, db_path=db_path
    )

    # D) Sea Leg (Port -> Port)
    #    SeaMatrix needs {lat, lon, name} dicts
    sea_km, sea_source = sea_matrix.km_with_source(
        {"lat": port_origin["lat"], "lon": port_origin["lon"], "name": port_origin["name"]},
        {"lat": port_destiny["lat"], "lon": port_destiny["lon"], "name": port_destiny["name"]}
    )

    # 5. Assemble Result
    return {
        "status": "ok",
        "origin": origin_dict,
        "destiny": destiny_dict,
        "ports": {
            "origin_port": port_origin,
            "destiny_port": port_destiny
        },
        "legs": {
            "road_direct": leg_direct,
            "road_first_mile": leg_first_mile,
            "road_last_mile": leg_last_mile,
            "sea": {
                "distance_km": float(sea_km),
                "source": sea_source
            }
        }
    }


# ────────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Multimodal Route Builder")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destiny", required=True)
    parser.add_argument("--ors-profile", default="driving-hgv")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--ports-json", default=DEFAULT_PORTS_JSON, type=Path)
    parser.add_argument("--sea-matrix-json", default=DEFAULT_SEA_JSON, type=Path)
    
    args = parser.parse_args()
    init_logging(level=args.log_level)

    result = build_multimodal_route(
        args.origin, args.destiny,
        ors_profile=args.ors_profile,
        overwrite=args.overwrite,
        ports_path=args.ports_json,
        sea_path=args.sea_matrix_json
    )

    if args.pretty:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))

    return 0

if __name__ == "__main__":
    raise SystemExit(main())