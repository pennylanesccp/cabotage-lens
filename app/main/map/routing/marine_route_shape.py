from __future__ import annotations

from app.main.map.routing.marine_route_builder import build_marine_route_polyline


def build_marine_route_path(
    *,
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    n_points: int = 100,
    smooth_window: int = 7,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
    debug_leg_key: tuple[str, str] | None = None,
) -> list[list[float]]:
    return build_marine_route_polyline(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=origin_latlon,
        dest_latlon=dest_latlon,
        n_points=n_points,
        smooth_window=smooth_window,
        style=style,
        curvature=curvature,
        debug_leg_key=debug_leg_key,
    )
