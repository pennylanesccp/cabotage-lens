from __future__ import annotations

from functools import lru_cache

from app.main.map.routing.water_validation import build_leg_reference_path
from app.main.map.routing.marine_master_route import load_master_route_ports, resolve_master_route_slice
from modules.plot.maritime_arc_geometry import RouteArcPort, build_route_arc_path


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

    route_ports = resolve_master_route_slice(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=origin_latlon,
        dest_latlon=dest_latlon,
    )

    route_path_latlon = build_route_arc_path(
        [
            RouteArcPort(
                name=str(route_port.name),
                latlon=(float(route_port.latlon[0]), float(route_port.latlon[1])),
            )
            for route_port in route_ports
        ],
        reference_path_builder=lambda start_port, end_port: build_leg_reference_path(
            origin_port_name=start_port.name,
            dest_port_name=end_port.name,
            origin_latlon=start_port.latlon,
            dest_latlon=end_port.latlon,
        ),
        clutter_points_latlon=_peer_port_latlons(),
        n_points_per_leg=max(int(n_points), 2),
    )
    return [[float(lon), float(lat)] for lat, lon in route_path_latlon]
