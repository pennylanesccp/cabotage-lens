from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import dedupe_latlon_path
from app.main.map.routing.marine_leg_interpolation import interpolate_leg_intermediate_points


def interpolate_segment_latlon(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
    *,
    n_points: int = 100,
) -> list[tuple[float, float]]:
    count = max(int(n_points), 2)
    if count == 2:
        return [(float(start_latlon[0]), float(start_latlon[1])), (float(end_latlon[0]), float(end_latlon[1]))]

    return [
        (float(start_latlon[0]), float(start_latlon[1])),
        *interpolate_leg_intermediate_points(start_latlon, end_latlon, n_points=count - 2),
        (float(end_latlon[0]), float(end_latlon[1])),
    ]


def interpolate_path_latlon(
    path_latlon: Sequence[tuple[float, float]],
    *,
    n_points_per_segment: int = 100,
) -> list[tuple[float, float]]:
    path = dedupe_latlon_path(path_latlon)
    if len(path) < 2:
        return path

    dense: list[tuple[float, float]] = []
    for idx in range(1, len(path)):
        segment = interpolate_segment_latlon(
            path[idx - 1],
            path[idx],
            n_points=n_points_per_segment,
        )
        if dense:
            segment = segment[1:]
        dense.extend(segment)
    return dense
