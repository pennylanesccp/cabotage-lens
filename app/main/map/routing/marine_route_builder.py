from __future__ import annotations

from functools import lru_cache

from app.main.map.routing.water_validation import build_leg_reference_path
from app.main.map.routing.marine_master_route import load_master_route_ports
from modules.plot.maritime_arc_geometry import build_port_to_port_arc


@lru_cache(maxsize=1)
def _peer_port_latlons() -> tuple[tuple[float, float], ...]:
    return tuple((float(port.latlon[0]), float(port.latlon[1])) for port in load_master_route_ports())


def build_marine_route_polyline(
    *,
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    n_points: int = 100,
    smooth_window: int = 7,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
) -> list[list[float]]:
    del smooth_window, style, curvature

    reference_path_latlon = build_leg_reference_path(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=origin_latlon,
        dest_latlon=dest_latlon,
    )
    geometry = build_port_to_port_arc(
        port_a_latlon=origin_latlon,
        port_b_latlon=dest_latlon,
        reference_path_latlon=reference_path_latlon,
        clutter_points_latlon=_peer_port_latlons(),
        n_points=max(int(n_points), 2),
    )
    return [[float(lon), float(lat)] for lat, lon in geometry.arc_points_latlon]
