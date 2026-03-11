from __future__ import annotations

import math
from functools import lru_cache
from typing import Sequence

from app.main.map.routing.geometry_utils import dedupe_latlon_path, densify_latlon_path, path_length_km, smooth_lonlat_path
from app.main.map.routing.marine_master_route import load_master_route_ports
from modules.infra.log_manager import get_logger
from modules.plot.port_arc_geometry import PortArcGeometry, generate_port_arc_geometry

_log = get_logger(__name__)

MIN_LEG_ARC_SAMPLES = 9


@lru_cache(maxsize=1)
def _peer_port_latlons() -> tuple[tuple[float, float], ...]:
    return tuple((float(port.latlon[0]), float(port.latlon[1])) for port in load_master_route_ports())


def build_corridor_leg_points(
    *,
    start_name: str,
    end_name: str,
    anchor_path_latlon: Sequence[tuple[float, float]],
    n_points: int = 100,
    smooth_window: int = 7,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
) -> list[tuple[float, float]]:
    anchor_path = dedupe_latlon_path(anchor_path_latlon)
    if len(anchor_path) < 2:
        return []

    combined_path = list(anchor_path)
    if len(anchor_path) >= 3:
        origin_arc = _build_port_arc(
            port_name=start_name,
            port_latlon=anchor_path[0],
            corridor_latlon=anchor_path[1:],
        )
        dest_arc = _build_port_arc(
            port_name=end_name,
            port_latlon=anchor_path[-1],
            corridor_latlon=list(reversed(anchor_path[:-1])),
        )
        combined_path = _combine_anchor_and_port_arcs(anchor_path, origin_arc, dest_arc)

    dense_points = max(int(n_points), _adaptive_point_target(combined_path))
    dense_lonlat = densify_latlon_path(combined_path, n_points=dense_points + 2)
    smooth_lonlat = smooth_lonlat_path(
        dense_lonlat,
        smooth_window=_resolve_smooth_window(
            base_window=smooth_window,
            style=style,
            curvature=curvature,
        ),
    )
    smooth_latlon = [(float(point[1]), float(point[0])) for point in smooth_lonlat]
    smooth_latlon[0] = (float(anchor_path[0][0]), float(anchor_path[0][1]))
    smooth_latlon[-1] = (float(anchor_path[-1][0]), float(anchor_path[-1][1]))
    return smooth_latlon[1:-1]


def _build_port_arc(
    *,
    port_name: str,
    port_latlon: tuple[float, float],
    corridor_latlon: Sequence[tuple[float, float]],
) -> PortArcGeometry | None:
    if not corridor_latlon:
        return None
    geometry = generate_port_arc_geometry(
        port_name=port_name,
        port_latlon=port_latlon,
        corridor_latlon=corridor_latlon,
        peer_port_latlons=_peer_port_latlons(),
        sample_count=MIN_LEG_ARC_SAMPLES,
    )
    _log.debug(
        (
            "Corridor leg port arc port=%s radius_km=%.3f target_arc_km=%.3f visible_deg=%.2f "
            "anchor=(%.6f, %.6f) midpoint_to_corridor_km=%.3f"
        ),
        port_name,
        geometry.radius_km,
        geometry.target_arc_length_km,
        math.degrees(geometry.visible_angle_rad),
        geometry.corridor_anchor_latlon[0],
        geometry.corridor_anchor_latlon[1],
        geometry.midpoint_distance_to_corridor_km,
    )
    return geometry


def _combine_anchor_and_port_arcs(
    anchor_path: Sequence[tuple[float, float]],
    origin_arc: PortArcGeometry | None,
    dest_arc: PortArcGeometry | None,
) -> list[tuple[float, float]]:
    combined: list[tuple[float, float]] = [(float(anchor_path[0][0]), float(anchor_path[0][1]))]
    if origin_arc is not None:
        combined.extend(origin_arc.route_ordered_arc_points_latlon)
        combined.append(origin_arc.corridor_anchor_latlon)
    combined.extend((float(point[0]), float(point[1])) for point in anchor_path[1:-1])
    if dest_arc is not None:
        combined.append(dest_arc.corridor_anchor_latlon)
        combined.extend(reversed(dest_arc.route_ordered_arc_points_latlon))
    combined.append((float(anchor_path[-1][0]), float(anchor_path[-1][1])))
    return dedupe_latlon_path(combined)


def _adaptive_point_target(path_latlon: Sequence[tuple[float, float]]) -> int:
    length_km = path_length_km(path_latlon)
    return max(60, min(220, int(math.ceil(length_km / 10.0))))


def _resolve_smooth_window(*, base_window: int, style: str, curvature: float) -> int:
    window = max(int(base_window), 5)
    if window % 2 == 0:
        window += 1
    if str(style) == "Arc (pretty)":
        window += 2
    if float(curvature) >= 0.3:
        window += 2
    return window
