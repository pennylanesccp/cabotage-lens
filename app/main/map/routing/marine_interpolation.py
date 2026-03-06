from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import dedupe_latlon_path


def interpolate_segment_latlon(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
    *,
    n_points: int = 100,
) -> list[tuple[float, float]]:
    count = max(int(n_points), 2)
    start_lat, start_lon = start_latlon
    end_lat, end_lon = end_latlon

    points: list[tuple[float, float]] = []
    for idx in range(count):
        fraction = idx / (count - 1)
        lat = start_lat + ((end_lat - start_lat) * fraction)
        lon = start_lon + ((end_lon - start_lon) * fraction)
        points.append((float(lat), float(lon)))
    return points


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
