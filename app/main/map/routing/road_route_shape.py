from __future__ import annotations

import hashlib
import math
from typing import Sequence

from app.main.map.routing.geometry_utils import EPS, dedupe_latlon_path, densify_latlon_path, smooth_lonlat_path


def _project(lat: float, lon: float, ref_lat: float) -> tuple[float, float]:
    return lon * math.cos(math.radians(ref_lat)), lat


def _unproject(x: float, y: float, ref_lat: float) -> tuple[float, float]:
    cos_lat = max(abs(math.cos(math.radians(ref_lat))), 0.01)
    return y, x / cos_lat


def _path_deviation(path_lonlat: Sequence[Sequence[float]]) -> float:
    if len(path_lonlat) < 3:
        return 0.0

    start_lon, start_lat = float(path_lonlat[0][0]), float(path_lonlat[0][1])
    end_lon, end_lat = float(path_lonlat[-1][0]), float(path_lonlat[-1][1])
    ref_lat = (start_lat + end_lat) / 2.0
    x0, y0 = _project(start_lat, start_lon, ref_lat)
    x1, y1 = _project(end_lat, end_lon, ref_lat)

    dx = x1 - x0
    dy = y1 - y0
    seg_len = math.hypot(dx, dy)
    if seg_len <= EPS:
        return 0.0

    deviation = 0.0
    for lon, lat in path_lonlat[1:-1]:
        px, py = _project(float(lat), float(lon), ref_lat)
        distance = abs((dy * px) - (dx * py) + (x1 * y0) - (y1 * x0)) / seg_len
        deviation = max(deviation, distance)
    return deviation


def _stable_direction(origin: tuple[float, float], destiny: tuple[float, float]) -> int:
    digest = hashlib.sha1(
        f"{origin[0]:.6f},{origin[1]:.6f}|{destiny[0]:.6f},{destiny[1]:.6f}".encode("ascii")
    ).digest()
    return -1 if digest[0] % 2 else 1


def _shape_control_points(origin: tuple[float, float], destiny: tuple[float, float]) -> list[tuple[float, float]]:
    start_lat, start_lon = origin
    end_lat, end_lon = destiny
    ref_lat = (start_lat + end_lat) / 2.0

    x0, y0 = _project(start_lat, start_lon, ref_lat)
    x1, y1 = _project(end_lat, end_lon, ref_lat)
    dx = x1 - x0
    dy = y1 - y0
    seg_len = math.hypot(dx, dy)
    if seg_len <= EPS:
        return [origin, destiny]

    sign = _stable_direction(origin, destiny)
    perp_x = (-dy / seg_len) * sign
    perp_y = (dx / seg_len) * sign

    amplitude = max(0.015, min(seg_len * 0.12, 1.10))
    fractions = (0.18, 0.36, 0.62, 0.83)
    offsets = (0.18, 0.62, -0.42, -0.14)

    controls: list[tuple[float, float]] = [origin]
    for fraction, offset in zip(fractions, offsets, strict=True):
        base_x = x0 + (dx * fraction)
        base_y = y0 + (dy * fraction)
        lat, lon = _unproject(base_x + (perp_x * amplitude * offset), base_y + (perp_y * amplitude * offset), ref_lat)
        controls.append((lat, lon))
    controls.append(destiny)
    return controls


def build_shaped_road_path(
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    *,
    preferred_path: Sequence[Sequence[float]] | None = None,
    n_points: int = 48,
    smooth_window: int = 5,
) -> list[list[float]]:
    if preferred_path and len(preferred_path) >= 3 and _path_deviation(preferred_path) > 0.01:
        return [[float(point[0]), float(point[1])] for point in preferred_path]

    control_points = dedupe_latlon_path(_shape_control_points(origin_latlon, dest_latlon))
    dense = densify_latlon_path(control_points, n_points=max(int(n_points), 16))
    return smooth_lonlat_path(dense, smooth_window=smooth_window)
