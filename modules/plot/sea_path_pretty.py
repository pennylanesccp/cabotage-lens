# modules/plot/sea_path_pretty.py
# -*- coding: utf-8 -*-

"""Pretty sea-path geometry helper for map visualization only."""

from __future__ import annotations

import math

_EPS = 1e-12


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _to_xyz(lat_deg: float, lon_deg: float) -> tuple[float, float, float]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    cos_lat = math.cos(lat)
    return (
        cos_lat * math.cos(lon),
        cos_lat * math.sin(lon),
        math.sin(lat),
    )


def _to_latlon(x: float, y: float, z: float) -> tuple[float, float]:
    hyp = math.hypot(x, y)
    lat = math.degrees(math.atan2(z, hyp))
    lon = math.degrees(math.atan2(y, x))
    return lat, lon


def _slerp_lonlat(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    n_points: int,
) -> list[list[float]]:
    v0 = _to_xyz(origin_lat, origin_lon)
    v1 = _to_xyz(dest_lat, dest_lon)

    dot = _clamp((v0[0] * v1[0]) + (v0[1] * v1[1]) + (v0[2] * v1[2]), -1.0, 1.0)
    omega = math.acos(dot)
    sin_omega = math.sin(omega)

    points: list[list[float]] = []

    for idx in range(n_points):
        t = idx / (n_points - 1)

        if abs(sin_omega) <= _EPS:
            x = ((1.0 - t) * v0[0]) + (t * v1[0])
            y = ((1.0 - t) * v0[1]) + (t * v1[1])
            z = ((1.0 - t) * v0[2]) + (t * v1[2])
            norm = math.sqrt((x * x) + (y * y) + (z * z))
            if norm > _EPS:
                x /= norm
                y /= norm
                z /= norm
        else:
            w0 = math.sin((1.0 - t) * omega) / sin_omega
            w1 = math.sin(t * omega) / sin_omega
            x = (w0 * v0[0]) + (w1 * v1[0])
            y = (w0 * v0[1]) + (w1 * v1[1])
            z = (w0 * v0[2]) + (w1 * v1[2])

        lat, lon = _to_latlon(x, y, z)
        points.append([lon, lat])

    return points


def _apply_lateral_bulge(path_lonlat: list[list[float]], curvature: float) -> list[list[float]]:
    if len(path_lonlat) < 3 or curvature <= 0.0:
        return [p[:] for p in path_lonlat]

    start_lon, start_lat = path_lonlat[0]
    end_lon, end_lat = path_lonlat[-1]
    mean_lat_rad = math.radians((start_lat + end_lat) / 2.0)
    cos_lat = max(abs(math.cos(mean_lat_rad)), 0.01)

    x0 = start_lon * cos_lat
    y0 = start_lat
    x1 = end_lon * cos_lat
    y1 = end_lat

    dx = x1 - x0
    dy = y1 - y0
    seg_len = math.hypot(dx, dy)
    if seg_len <= _EPS:
        return [p[:] for p in path_lonlat]

    perp_x = -dy / seg_len
    perp_y = dx / seg_len

    out: list[list[float]] = []
    n_last = len(path_lonlat) - 1

    for idx, (lon, lat) in enumerate(path_lonlat):
        if idx == 0 or idx == n_last:
            out.append([lon, lat])
            continue

        t = idx / n_last
        bulge = math.sin(math.pi * t) * curvature * seg_len

        x = (lon * cos_lat) + (perp_x * bulge)
        y = lat + (perp_y * bulge)

        out_lon = x / cos_lat
        out_lat = _clamp(y, -89.9, 89.9)
        out.append([out_lon, out_lat])

    return out


def _smooth_path(path_lonlat: list[list[float]], smooth_window: int) -> list[list[float]]:
    n_points = len(path_lonlat)
    if n_points < 3:
        return [p[:] for p in path_lonlat]

    window = max(int(smooth_window), 1)
    if window % 2 == 0:
        window += 1

    half = window // 2
    out: list[list[float]] = []

    for idx in range(n_points):
        start = max(0, idx - half)
        end = min(n_points - 1, idx + half)
        count = (end - start) + 1

        lon_sum = 0.0
        lat_sum = 0.0
        for pos in range(start, end + 1):
            lon_sum += path_lonlat[pos][0]
            lat_sum += path_lonlat[pos][1]

        out.append([lon_sum / count, lat_sum / count])

    out[0] = path_lonlat[0][:]
    out[-1] = path_lonlat[-1][:]
    return out


def build_pretty_sea_path(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    n_points: int = 200,
    curvature: float = 0.25,
    smooth_window: int = 7,
) -> list[list[float]]:
    """Build a visually smoother sea corridor polyline for pydeck PathLayer.

    Output is a list of `[lon, lat]` points and is intended for map rendering only.
    """
    n = max(int(n_points), 2)
    curve = _clamp(float(curvature), 0.0, 0.5)

    path = _slerp_lonlat(
        origin_lat=float(origin_lat),
        origin_lon=float(origin_lon),
        dest_lat=float(dest_lat),
        dest_lon=float(dest_lon),
        n_points=n,
    )
    path = _apply_lateral_bulge(path, curvature=curve)
    path = _smooth_path(path, smooth_window=int(smooth_window))
    return path
