# modules/multimodal/builder.py
# -*- coding: utf-8 -*-

"""
Multimodal geometry builder.

Builds the geometric inputs required by the evaluator:
- direct road leg,
- first-mile road leg,
- sea leg,
- last-mile road leg.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict, cast

if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.addressing.coords import parse_lat_lon_string
from modules.addressing.resolver import resolve_point_null_safe
from modules.addressing.text import ascii_place_text
from modules.cabotage.sea_matrix import SeaMatrix
from modules.core.secrets import get_secret
from modules.infra.database_manager import db_session, find_place_point
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


class LegResult(TypedDict, total=False):
    origin_name: str
    destiny_name: str
    distance_km: Optional[float]
    is_hgv: Optional[bool]
    profile_requested: str
    profile_used: Optional[str]
    cached: bool
    source: str


class SeaResult(TypedDict):
    distance_km: float
    source: str


class PathGeometry(TypedDict):
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


def load_routing_assets(
    *,
    ports_json_path: Optional[Path] = None,
    sea_matrix_path: Optional[Path] = None,
    db_path: Optional[Path | str] = None,
) -> tuple[ORSClient, list[Dict[str, Any]], SeaMatrix, Optional[Path | str]]:
    """Load reusable routing dependencies for one or many evaluations."""
    p_json = _resolve_path(ports_json_path, _DEFAULT_PORTS_JSON)
    s_json = _resolve_path(sea_matrix_path, _DEFAULT_SEA_MATRIX_JSON)

    ors = _cached_ors_client(str(get_secret("ORS_API_KEY", "")))
    ports = _cached_ports(str(p_json))
    sea_matrix = _cached_sea_matrix(str(s_json))
    return ors, ports, sea_matrix, db_path


def _cached_point_for_geometry(value: Any, *, db_path: Optional[Path | str] = None) -> Optional[Point]:
    if hasattr(value, "lat") and hasattr(value, "lon"):
        return None

    query: Optional[str] = None
    if isinstance(value, dict):
        lat = value.get("lat") or value.get("latitude")
        lon = value.get("lon") or value.get("longitude")
        if lat is not None and lon is not None:
            return None
        query = value.get("label") or value.get("input")
    else:
        candidate = str(value).strip()
        if not candidate or parse_lat_lon_string(candidate):
            return None
        query = candidate

    query_text = ascii_place_text(query)
    if not query_text:
        return None

    try:
        with db_session(db_path) as conn:
            cached_point = find_place_point(conn, place=query_text)
    except Exception as exc:
        _log.debug("Routes-table point lookup failed for %s: %s", query_text, exc)
        return None

    if not cached_point or cached_point.get("lat") is None or cached_point.get("lon") is None:
        return None

    _log.info(
        "Using cached coordinates for %s from routes table role=%s",
        query_text,
        cached_point.get("role") or "<unknown>",
    )
    return {
        "label": ascii_place_text(cached_point.get("label") or query_text),
        "lat": float(cached_point["lat"]),
        "lon": float(cached_point["lon"]),
        "uf": None,
    }


def resolve_point_for_geometry(
    value: Any,
    ors: ORSClient,
    *,
    db_path: Optional[Path | str] = None,
) -> Optional[Point]:
    """Resolve one origin/destination input into the normalized geometry shape."""
    cached_point = _cached_point_for_geometry(value, db_path=db_path)
    if cached_point is not None:
        return cached_point

    point = resolve_point_null_safe(value, ors, _log)
    if not point:
        return None
    return {
        "label": ascii_place_text(point.label),
        "lat": point.lat,
        "lon": point.lon,
        "uf": point.uf,
    }


def build_port_node(port_data: Dict[str, Any]) -> Dict[str, Any]:
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


def build_path_geometry_from_resolved(
    origin_pt: Point,
    destiny_pt: Point,
    *,
    ors: ORSClient,
    ports: list[Dict[str, Any]],
    sea_matrix: SeaMatrix,
    ors_profile: str = "driving-hgv",
    overwrite_road: bool = False,
    db_path: Optional[Path | str] = None,
    port_origin: Optional[Dict[str, Any]] = None,
    first_mile_leg: Optional[Dict[str, Any]] = None,
) -> Optional[PathGeometry]:
    """Build geometry from already resolved endpoints and shared routing assets."""

    po_data = port_origin or find_nearest_port(origin_pt["lat"], origin_pt["lon"], ports)
    pd_data = find_nearest_port(destiny_pt["lat"], destiny_pt["lon"], ports)
    _log.info("Ports selected: %s (origin) -> %s (destiny)", po_data["name"], pd_data["name"])

    po_node = build_port_node(po_data)
    pd_node = build_port_node(pd_data)

    leg_direct = get_or_create_leg(
        ors,
        origin_pt,
        destiny_pt,
        profile=ors_profile,
        overwrite=overwrite_road,
        db_path=db_path,
    )
    leg_first = first_mile_leg or get_or_create_leg(
        ors,
        origin_pt,
        po_node,
        profile=ors_profile,
        overwrite=overwrite_road,
        db_path=db_path,
    )
    leg_last = get_or_create_leg(
        ors,
        pd_node,
        destiny_pt,
        profile=ors_profile,
        overwrite=overwrite_road,
        db_path=db_path,
    )

    sea_dist, sea_src = sea_matrix.km_with_source(
        {"lat": po_data["lat"], "lon": po_data["lon"], "name": po_data["name"]},
        {"lat": pd_data["lat"], "lon": pd_data["lon"], "name": pd_data["name"]},
    )

    return {
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


def build_path_geometry(
    origin_input: Any,
    destiny_input: Any,
    *,
    ors_profile: str = "driving-hgv",
    overwrite_road: bool = False,
    ports_json_path: Optional[Path] = None,
    sea_matrix_path: Optional[Path] = None,
    db_path: Optional[Path | str] = None,
) -> Optional[PathGeometry]:
    """Resolve and compute all legs needed for multimodal comparison."""
    ors, ports, sea_matrix, _ = load_routing_assets(
        ports_json_path=ports_json_path,
        sea_matrix_path=sea_matrix_path,
        db_path=db_path,
    )

    _log.debug("Resolving endpoints: %r -> %r", origin_input, destiny_input)
    origin_pt = resolve_point_for_geometry(origin_input, ors, db_path=db_path)
    destiny_pt = resolve_point_for_geometry(destiny_input, ors, db_path=db_path)

    if not origin_pt or not destiny_pt:
        _log.error("Failed to geocode one or both endpoints. Aborting geometry build.")
        return None

    return build_path_geometry_from_resolved(
        origin_pt,
        destiny_pt,
        ors=ors,
        ports=ports,
        sea_matrix=sea_matrix,
        ors_profile=ors_profile,
        overwrite_road=overwrite_road,
        db_path=db_path,
    )


if __name__ == "__main__":
    from modules.infra.log_manager import init_logging

    init_logging(level="INFO")
    print("--- Geometry Builder Smoke Test ---")

    result = build_path_geometry(
        "Avenida Professor Luciano Gualberto, Sao Paulo",
        "Manaus, AM",
        ors_profile="driving-hgv",
    )

    if result:
        print("\nGeometry built successfully")
        print(f"  Direct road: {result['road_direct']['distance_km']} km")
        print(f"  First mile:  {result['first_mile']['distance_km']} km")
        print(f"  Sea leg:     {result['sea_leg']['distance_km']} km")
        print(f"  Last mile:   {result['last_mile']['distance_km']} km")
    else:
        print("\nGeometry build failed")

    print("--- Done ---")
