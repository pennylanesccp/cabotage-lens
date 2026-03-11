from __future__ import annotations

"""
Coastal maritime leg builder.

The active geometry is corridor-based and delegates the adaptive port-arc math to
modules.plot.port_arc_geometry. It does not use a fixed-radius chord arc anymore.
"""

from app.main.map.routing.marine_corridor_leg import build_corridor_leg_points
from app.main.map.routing.water_validation import build_leg_reference_path


def build_coastal_leg_points(
    *,
    origin_port_name: str,
    dest_port_name: str,
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    n_points: int = 100,
    smooth_window: int = 7,
    style: str = "Coastal lane (default)",
    curvature: float = 0.25,
) -> list[tuple[float, float]]:
    anchor_path = build_leg_reference_path(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=leg_start_latlon,
        dest_latlon=leg_end_latlon,
    )
    return build_corridor_leg_points(
        start_name=origin_port_name,
        end_name=dest_port_name,
        anchor_path_latlon=anchor_path,
        n_points=n_points,
        smooth_window=smooth_window,
        style=style,
        curvature=curvature,
    )
