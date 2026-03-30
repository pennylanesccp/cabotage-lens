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
from typing import Any, Callable, Dict, MutableMapping, Optional, TypedDict, cast

if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.addressing.coords import parse_lat_lon_string
from modules.addressing.resolver import resolve_point_null_safe
from modules.addressing.text import ascii_place_text
from modules.cabotage.sea_matrix import SeaMatrix
from modules.infra.database_manager import db_session, find_place_point, upsert_place_point
from modules.infra.log_manager import get_logger
from modules.ports.ports_index import load_ports
from modules.ports.ports_nearest import find_nearest_port
from modules.road.locationiq.structures import get_configured_locationiq_api_keys
from modules.road.ors.structures import get_configured_ors_api_keys
from modules.road.router import ORSClient, ORSConfig, get_or_create_leg

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PORTS_JSON = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"
_DEFAULT_SEA_MATRIX_JSON = _REPO_ROOT / "data" / "sea_matrix.json"


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


class SeaResult(TypedDict, total=False):
    distance_km: float
    source: str
    fuel_g_per_tnm: float
    fuel_g_per_tnm_source: str
    corridor_leg_count: int
    corridor_port_path: list[str]
    fuel_g_per_tnm_mean: float
    fuel_g_per_tnm_median: float
    segment_count: int
    matched_segment_count: int
    voyage_count: int
    matched_voyage_count: int
    unique_imo_count: int
    matched_imo_count: int
    match_rate_segments: float
    match_rate_tonne_nm: float


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
def _cached_ors_client(api_keys: tuple[str, ...], locationiq_api_keys: tuple[str, ...]) -> ORSClient:
    primary_key = api_keys[0] if api_keys else ""
    del locationiq_api_keys
    return ORSClient(ORSConfig(api_key=primary_key or None))


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

    ors = _cached_ors_client(
        tuple(get_configured_ors_api_keys()),
        tuple(get_configured_locationiq_api_keys()),
    )
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
        "Using cached coordinates for %s from the canonical location cache role=%s",
        query_text,
        cached_point.get("role") or "<unknown>",
    )
    return {
        "label": ascii_place_text(cached_point.get("label") or query_text),
        "lat": float(cached_point["lat"]),
        "lon": float(cached_point["lon"]),
        "uf": cached_point.get("uf"),
    }


def _persist_point_for_geometry(
    query_text: str,
    resolved_point: Dict[str, Any],
    *,
    db_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    if not query_text:
        return dict(resolved_point)

    try:
        with db_session(db_path) as conn:
            cached_point = upsert_place_point(
                conn,
                place=query_text,
                label=resolved_point.get("label") or query_text,
                lat=resolved_point.get("lat"),
                lon=resolved_point.get("lon"),
                uf=resolved_point.get("uf"),
                source="provider",
            )
            if hasattr(conn, "commit"):
                conn.commit()
    except Exception as exc:
        _log.debug("Failed to persist resolved point for %s: %s", query_text, exc)
        return dict(resolved_point)

    if not cached_point:
        return dict(resolved_point)

    persisted_point = {
        "label": ascii_place_text(cached_point.get("label") or resolved_point.get("label") or query_text),
        "lat": float(cached_point.get("lat") or resolved_point["lat"]),
        "lon": float(cached_point.get("lon") or resolved_point["lon"]),
        "uf": cached_point.get("uf", resolved_point.get("uf")),
    }
    if cached_point.get("location_id") is not None:
        persisted_point["location_id"] = int(cached_point["location_id"])
    return persisted_point


def resolve_point_for_geometry(
    value: Any,
    ors: ORSClient,
    *,
    db_path: Optional[Path | str] = None,
    point_cache: Optional[MutableMapping[str, Point]] = None,
) -> Optional[Point]:
    """Resolve one origin/destination input into the normalized geometry shape."""
    cache_key = ascii_place_text((value or {}).get("label")) if isinstance(value, dict) else ascii_place_text(value)
    if point_cache is not None and cache_key and cache_key in point_cache:
        return dict(point_cache[cache_key])

    cached_point = _cached_point_for_geometry(value, db_path=db_path)
    if cached_point is not None:
        if point_cache is not None and cache_key:
            point_cache[cache_key] = dict(cached_point)
        return cached_point

    point = resolve_point_null_safe(value, ors, _log)
    if not point:
        return None
    resolved_point = {
        "label": ascii_place_text(point.label),
        "lat": point.lat,
        "lon": point.lon,
        "uf": point.uf,
    }
    if cache_key:
        resolved_point = _persist_point_for_geometry(cache_key, resolved_point, db_path=db_path)
    if point_cache is not None and cache_key:
        point_cache[cache_key] = dict(resolved_point)
    return resolved_point


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


def _point_label(point: Dict[str, Any]) -> str:
    return str(point.get("label") or point.get("name") or "<unknown>")


def _resolve_route_leg(
    resolve_leg: Callable[[Dict[str, Any], Dict[str, Any], str], Dict[str, Any]],
    start: Dict[str, Any],
    end: Dict[str, Any],
    leg_name: str,
) -> Dict[str, Any]:
    _log.info(
        "Resolving route leg %s: %s -> %s (cache first, provider on miss)",
        leg_name,
        _point_label(start),
        _point_label(end),
    )
    return resolve_leg(start, end, leg_name)


def build_path_geometry_from_resolved(
    origin_pt: Point,
    destiny_pt: Point,
    *,
    ors: ORSClient,
    ports: list[Dict[str, Any]],
    sea_matrix: SeaMatrix,
    ors_profile: str = "driving-car",
    overwrite_road: bool = False,
    db_path: Optional[Path | str] = None,
    port_origin: Optional[Dict[str, Any]] = None,
    port_destiny: Optional[Dict[str, Any]] = None,
    first_mile_leg: Optional[Dict[str, Any]] = None,
    route_resolver: Optional[Callable[[Dict[str, Any], Dict[str, Any], str], Dict[str, Any]]] = None,
) -> Optional[PathGeometry]:
    """Build geometry from already resolved endpoints and shared routing assets."""

    po_data = port_origin or find_nearest_port(origin_pt["lat"], origin_pt["lon"], ports)
    pd_data = port_destiny or find_nearest_port(destiny_pt["lat"], destiny_pt["lon"], ports)
    _log.info("Ports selected: %s (origin) -> %s (destiny)", po_data["name"], pd_data["name"])

    po_node = build_port_node(po_data)
    pd_node = build_port_node(pd_data)
    resolve_leg = route_resolver or (
        lambda start, end, _leg_name: get_or_create_leg(
            ors,
            start,
            end,
            profile=ors_profile,
            overwrite=overwrite_road,
            db_path=db_path,
        )
    )

    leg_direct = _resolve_route_leg(
        resolve_leg,
        origin_pt,
        destiny_pt,
        "road_direct",
    )
    if first_mile_leg is not None:
        _log.info(
            "Reusing pre-resolved route leg first_mile: %s -> %s",
            _point_label(origin_pt),
            _point_label(po_node),
        )
        leg_first = first_mile_leg
    else:
        leg_first = _resolve_route_leg(
            resolve_leg,
            origin_pt,
            po_node,
            "first_mile",
        )
    leg_last = _resolve_route_leg(
        resolve_leg,
        pd_node,
        destiny_pt,
        "last_mile",
    )

    sea_dist, sea_src = sea_matrix.km_with_source(
        {"lat": po_data["lat"], "lon": po_data["lon"], "name": po_data["name"]},
        {"lat": pd_data["lat"], "lon": pd_data["lon"], "name": pd_data["name"]},
    )

    sea_leg: SeaResult = {"distance_km": float(sea_dist), "source": sea_src}
    directional_stats = sea_matrix.best_directional_stats(po_data["name"], pd_data["name"])
    if directional_stats:
        corridor_leg_count = int(directional_stats.get("corridor_leg_count") or 0)
        route_distance_km = directional_stats.get("distance_km")
        if isinstance(route_distance_km, (int, float)) and float(route_distance_km) > 0.0:
            sea_leg["distance_km"] = float(route_distance_km)
            sea_leg["source"] = str(directional_stats.get("distance_source") or sea_src)
        weighted_mean = directional_stats.get("fuel_g_per_tnm_weighted_mean")
        if isinstance(weighted_mean, (int, float)) and float(weighted_mean) > 0.0:
            sea_leg["fuel_g_per_tnm"] = float(weighted_mean)
            sea_leg["fuel_g_per_tnm_source"] = (
                "sea_matrix_directional_corridor_weighted_mean"
                if corridor_leg_count > 1
                else "sea_matrix_directional_weighted_mean"
            )
        if corridor_leg_count > 0:
            sea_leg["corridor_leg_count"] = corridor_leg_count
        corridor_port_path = directional_stats.get("corridor_port_path")
        if isinstance(corridor_port_path, list) and corridor_port_path:
            sea_leg["corridor_port_path"] = [str(item) for item in corridor_port_path]
        for key in (
            "fuel_g_per_tnm_mean",
            "fuel_g_per_tnm_median",
            "segment_count",
            "matched_segment_count",
            "voyage_count",
            "matched_voyage_count",
            "unique_imo_count",
            "matched_imo_count",
            "match_rate_segments",
            "match_rate_tonne_nm",
        ):
            value = directional_stats.get(key)
            if isinstance(value, (int, float)):
                sea_leg[key] = float(value) if "rate" in key or "fuel" in key else int(value)
        _log.info(
            (
                "Sea leg matched route KPI %s -> %s fuel_g_per_tnm=%.4f source=%s "
                "corridor_legs=%s matched_segments=%s match_rate_tonne_nm=%s"
            ),
            po_data["name"],
            pd_data["name"],
            float(sea_leg.get("fuel_g_per_tnm") or 0.0),
            sea_leg.get("fuel_g_per_tnm_source"),
            sea_leg.get("corridor_leg_count"),
            sea_leg.get("matched_segment_count"),
            sea_leg.get("match_rate_tonne_nm"),
        )

    return {
        "origin": origin_pt,
        "destiny": destiny_pt,
        "port_origin": po_data,
        "port_destiny": pd_data,
        "road_direct": cast(LegResult, leg_direct),
        "first_mile": cast(LegResult, leg_first),
        "last_mile": cast(LegResult, leg_last),
        "sea_leg": sea_leg,
        "status": "ok",
    }


def build_path_geometry(
    origin_input: Any,
    destiny_input: Any,
    *,
    ors_profile: str = "driving-car",
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
    if hasattr(ors, "reset_metrics"):
        ors.reset_metrics()

    _log.debug("Resolving endpoints: %r -> %r", origin_input, destiny_input)
    origin_pt = resolve_point_for_geometry(origin_input, ors, db_path=db_path)
    destiny_pt = resolve_point_for_geometry(destiny_input, ors, db_path=db_path)

    if not origin_pt or not destiny_pt:
        _log.error("Failed to geocode one or both endpoints. Aborting geometry build.")
        return None

    try:
        geometry = build_path_geometry_from_resolved(
            origin_pt,
            destiny_pt,
            ors=ors,
            ports=ports,
            sea_matrix=sea_matrix,
            ors_profile=ors_profile,
            overwrite_road=overwrite_road,
            db_path=db_path,
        )
    except Exception as exc:
        _log.error("Failed to build route geometry for %r -> %r: %s", origin_input, destiny_input, exc)
        return None

    if geometry and geometry.get("status") == "ok":
        provider_calls = ors.metrics_snapshot() if hasattr(ors, "metrics_snapshot") else {}
        _log.info(
            (
                "Single-route geometry summary origin=%s destiny=%s direct_source=%s "
                "first_mile_source=%s last_mile_source=%s providers=%s"
            ),
            geometry["origin"]["label"],
            geometry["destiny"]["label"],
            geometry["road_direct"].get("source"),
            geometry["first_mile"].get("source"),
            geometry["last_mile"].get("source"),
            provider_calls,
        )
    return geometry


if __name__ == "__main__":
    from modules.infra.log_manager import init_logging

    init_logging(level="INFO")
    print("--- Geometry Builder Smoke Test ---")

    result = build_path_geometry(
        "Avenida Professor Luciano Gualberto, Sao Paulo",
        "Manaus, AM",
        ors_profile="driving-car",
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
