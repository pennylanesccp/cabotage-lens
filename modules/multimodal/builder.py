# modules/multimodal/builder.py
# -*- coding: utf-8 -*-

"""
Multimodal geometry builder.

Builds the physical path for an O-D scenario:
- direct road leg,
- first-mile road leg (origin -> origin port),
- sea leg (origin port -> destiny port),
- last-mile road leg (destiny port -> destiny).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict, cast

# Path bootstrap for direct execution smoke tests.
if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.addressing.resolver import resolve_point_null_safe
from modules.cabotage.sea_matrix import SeaMatrix
from modules.infra.database_manager import DEFAULT_DB_PATH
from modules.infra.log_manager import get_logger
from modules.ports.ports_index import load_ports
from modules.ports.ports_nearest import find_nearest_port
from modules.road.router import ORSClient, ORSConfig, get_or_create_leg

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PORTS_JSON = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"
_DEFAULT_SEA_MATRIX_JSON = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "sea_matrix.json"


class Point(TypedDict):
    label: str
    lat: float
    lon: float
    uf: Optional[str]


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
    """Complete geometric definition for a comparison scenario."""

    origin: Point
    destiny: Point
    port_origin: Dict[str, Any]
    port_destiny: Dict[str, Any]
    road_direct: LegResult
    first_mile: LegResult
    last_mile: LegResult
    sea_leg: SeaResult
    status: str


@lru_cache(maxsize=4)
def _cached_ors_client(api_key: str) -> ORSClient:
    return ORSClient(ORSConfig(api_key=api_key or None))


@lru_cache(maxsize=8)
def _cached_ports(path_str: str) -> list[Dict[str, Any]]:
    return load_ports(path=path_str)


@lru_cache(maxsize=8)
def _cached_sea_matrix(path_str: str) -> SeaMatrix:
    return SeaMatrix.from_json_path(path_str)


def _resolve_path(candidate: Optional[Path], default: Path) -> Path:
    return Path(candidate).resolve() if candidate is not None else default.resolve()


def build_path_geometry(
    origin_input: Any,
    destiny_input: Any,
    *,
    ors_profile: str = "driving-hgv",
    overwrite_road: bool = False,
    ports_json_path: Optional[Path] = None,
    sea_matrix_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Optional[PathGeometry]:
    """Resolve and compute all legs needed for multimodal comparison."""

    p_json = _resolve_path(ports_json_path, _DEFAULT_PORTS_JSON)
    s_json = _resolve_path(sea_matrix_path, _DEFAULT_SEA_MATRIX_JSON)
    d_path = Path(db_path).resolve() if db_path is not None else Path(DEFAULT_DB_PATH).resolve()

    ors = _cached_ors_client(os.getenv("ORS_API_KEY", ""))
    ports = _cached_ports(str(p_json))
    sea_matrix = _cached_sea_matrix(str(s_json))

    _log.debug("Resolving endpoints: %r -> %r", origin_input, destiny_input)
    p_origin = resolve_point_null_safe(origin_input, ors, _log)
    p_destiny = resolve_point_null_safe(destiny_input, ors, _log)

    if not p_origin or not p_destiny:
        _log.error("Failed to geocode one or both endpoints. Aborting geometry build.")
        return None

    origin_pt: Point = {
        "label": p_origin.label,
        "lat": p_origin.lat,
        "lon": p_origin.lon,
        "uf": p_origin.uf,
    }
    destiny_pt: Point = {
        "label": p_destiny.label,
        "lat": p_destiny.lat,
        "lon": p_destiny.lon,
        "uf": p_destiny.uf,
    }

    po_data = find_nearest_port(origin_pt["lat"], origin_pt["lon"], ports)
    pd_data = find_nearest_port(destiny_pt["lat"], destiny_pt["lon"], ports)
    _log.info("Ports selected: %s (origin) -> %s (destiny)", po_data["name"], pd_data["name"])

    def _port_node(port_data: Dict[str, Any]) -> Dict[str, Any]:
        gate = port_data.get("gate")
        if gate:
            return {
                "lat": gate["lat"],
                "lon": gate["lon"],
                "label": f"{port_data['name']} ({gate.get('label', 'gate')})",
            }
        return {
            "lat": port_data["lat"],
            "lon": port_data["lon"],
            "label": port_data["name"],
        }

    po_node = _port_node(po_data)
    pd_node = _port_node(pd_data)

    leg_direct = get_or_create_leg(
        ors,
        origin_pt,
        destiny_pt,
        profile=ors_profile,
        overwrite=overwrite_road,
        db_path=d_path,
    )
    leg_first = get_or_create_leg(
        ors,
        origin_pt,
        po_node,
        profile=ors_profile,
        overwrite=overwrite_road,
        db_path=d_path,
    )
    leg_last = get_or_create_leg(
        ors,
        pd_node,
        destiny_pt,
        profile=ors_profile,
        overwrite=overwrite_road,
        db_path=d_path,
    )

    sea_dist, sea_src = sea_matrix.km_with_source(
        {"lat": po_data["lat"], "lon": po_data["lon"], "name": po_data["name"]},
        {"lat": pd_data["lat"], "lon": pd_data["lon"], "name": pd_data["name"]},
    )

    result: PathGeometry = {
        "origin": origin_pt,
        "destiny": destiny_pt,
        "port_origin": po_data,
        "port_destiny": pd_data,
        "road_direct": cast(LegResult, leg_direct),
        "first_mile": cast(LegResult, leg_first),
        "last_mile": cast(LegResult, leg_last),
        "sea_leg": {"distance_km": float(sea_dist), "source": sea_src},
        "status": "ok",
    }
    return result


if __name__ == "__main__":
    import json

    from modules.infra.log_manager import init_logging

    init_logging(level="INFO")
    print("--- Geometry Builder Smoke Test ---")

    res = build_path_geometry(
        "Avenida Professor Luciano Gualberto, Sao Paulo",
        "Manaus, AM",
        ors_profile="driving-hgv",
    )

    if res:
        print("\nGeometry built successfully")
        print(f"  Direct road: {res['road_direct']['distance_km']} km")
        print(f"  First mile:  {res['first_mile']['distance_km']} km")
        print(f"  Sea leg:     {res['sea_leg']['distance_km']} km")
        print(f"  Last mile:   {res['last_mile']['distance_km']} km")
    else:
        print("\nGeometry build failed")

    print("--- Done ---")
