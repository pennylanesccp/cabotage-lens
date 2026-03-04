# modules/plot/sea_lane_brazil.py
# -*- coding: utf-8 -*-

"""Brazil coastal-lane sea-path helper for map visualization only."""

from __future__ import annotations

import math
from bisect import bisect_right
from typing import Iterable

_EPS = 1e-12

# Ordered south->north coastal lane, then Amazon estuary -> Manaus waterway points.
# Coordinates are stored as (lat, lon) and intentionally kept offshore/channel-side.
BRAZIL_COASTAL_SEA_WAYPOINTS: tuple[tuple[float, float], ...] = (
    (-32.90, -50.20),  # RS offshore
    (-29.60, -48.60),  # SC offshore
    (-26.20, -47.80),  # PR offshore
    (-24.20, -46.05),  # Santos offshore
    (-22.70, -43.05),  # RJ offshore
    (-20.00, -39.45),  # ES offshore
    (-16.10, -38.20),  # BA offshore
    (-12.90, -37.05),  # Salvador offshore
    (-9.25, -34.70),   # Recife/Suape offshore
    (-7.10, -34.55),   # RN offshore
    (-3.85, -38.25),   # Fortaleza offshore
    (-2.45, -44.20),   # Sao Luis offshore
    (-0.80, -47.85),   # Belem offshore
    (-0.30, -49.20),   # Amazon mouth
    (-1.45, -51.90),   # Macapa channel
    (-2.05, -54.70),   # Santarem channel
    (-2.75, -57.50),   # Obidos channel
    (-3.15, -59.35),   # Itacoatiara channel
    (-3.15, -60.02),   # Manaus waterway
)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2.0) ** 2) + math.cos(p1) * math.cos(p2) * (math.sin(dl / 2.0) ** 2)
    return 2.0 * r_km * math.asin(min(1.0, math.sqrt(max(a, 0.0))))


def _nearest_index(target: tuple[float, float], points: list[tuple[float, float]]) -> int:
    t_lat, t_lon = target
    best_idx = 0
    best_dist = float('inf')
    for idx, (lat, lon) in enumerate(points):
        d = _haversine_km(t_lat, t_lon, lat, lon)
        if d < best_dist:
            best_dist = d
            best_idx = idx
    return best_idx


def _path_length_km(path_latlon: Iterable[tuple[float, float]]) -> float:
    pts = list(path_latlon)
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for idx in range(1, len(pts)):
        a_lat, a_lon = pts[idx - 1]
        b_lat, b_lon = pts[idx]
        total += _haversine_km(a_lat, a_lon, b_lat, b_lon)
    return total


def _densify_path(path_latlon: list[tuple[float, float]], n_points: int) -> list[list[float]]:
    if len(path_latlon) < 2:
        return [[float(path_latlon[0][1]), float(path_latlon[0][0])]] if path_latlon else []

    target_n = max(int(n_points), 2)

    cumulative = [0.0]
    for idx in range(1, len(path_latlon)):
        a_lat, a_lon = path_latlon[idx - 1]
        b_lat, b_lon = path_latlon[idx]
        cumulative.append(cumulative[-1] + _haversine_km(a_lat, a_lon, b_lat, b_lon))

    total = cumulative[-1]
    if total <= _EPS:
        a_lat, a_lon = path_latlon[0]
        b_lat, b_lon = path_latlon[-1]
        return [
            [a_lon + (b_lon - a_lon) * (i / (target_n - 1)), a_lat + (b_lat - a_lat) * (i / (target_n - 1))]
            for i in range(target_n)
        ]

    out: list[list[float]] = []
    for i in range(target_n):
        d = total * (i / (target_n - 1))
        seg = max(1, bisect_right(cumulative, d))
        if seg >= len(cumulative):
            seg = len(cumulative) - 1

        d0 = cumulative[seg - 1]
        d1 = cumulative[seg]
        lat0, lon0 = path_latlon[seg - 1]
        lat1, lon1 = path_latlon[seg]

        frac = 0.0 if abs(d1 - d0) <= _EPS else (d - d0) / (d1 - d0)
        lat = lat0 + ((lat1 - lat0) * frac)
        lon = lon0 + ((lon1 - lon0) * frac)
        out.append([lon, lat])

    return out


def _smooth_lonlat_path(path_lonlat: list[list[float]], smooth_window: int) -> list[list[float]]:
    if len(path_lonlat) < 3:
        return [p[:] for p in path_lonlat]

    window = max(int(smooth_window), 1)
    if window % 2 == 0:
        window += 1
    half = window // 2

    out: list[list[float]] = []
    for idx in range(len(path_lonlat)):
        start = max(0, idx - half)
        end = min(len(path_lonlat) - 1, idx + half)
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


def _apply_offshore_offset(waypoints: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Apply a small eastward offshore offset to east-coast points only."""
    out: list[tuple[float, float]] = []
    for idx, (lat, lon) in enumerate(waypoints):
        if idx <= 12 and (-35.0 <= lat <= -0.5):
            out.append((lat, lon + 0.25))
        else:
            out.append((lat, lon))
    return out


def build_sea_lane_path(
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
    waypoints: Iterable[tuple[float, float]] = BRAZIL_COASTAL_SEA_WAYPOINTS,
    n_points: int = 200,
    smooth_window: int = 7,
) -> list[list[float]]:
    """Build a coastal lane path between origin and destination as [lon, lat] points."""
    lane = list(waypoints)
    if not lane:
        o_lat, o_lon = origin_latlon
        d_lat, d_lon = dest_latlon
        return _densify_path([(o_lat, o_lon), (d_lat, d_lon)], n_points=n_points)

    lane = _apply_offshore_offset(lane)

    o_idx = _nearest_index(origin_latlon, lane)
    d_idx = _nearest_index(dest_latlon, lane)

    lo = min(o_idx, d_idx)
    hi = max(o_idx, d_idx)
    base_segment = lane[lo : hi + 1]

    if o_idx <= d_idx:
        forward_lane = base_segment
        backward_lane = list(reversed(base_segment))
    else:
        forward_lane = list(reversed(base_segment))
        backward_lane = base_segment

    o_lat, o_lon = origin_latlon
    d_lat, d_lon = dest_latlon

    path_forward: list[tuple[float, float]] = [(o_lat, o_lon)] + forward_lane + [(d_lat, d_lon)]
    path_backward: list[tuple[float, float]] = [(o_lat, o_lon)] + backward_lane + [(d_lat, d_lon)]

    selected_lane = forward_lane
    if _path_length_km(path_backward) < _path_length_km(path_forward):
        selected_lane = backward_lane

    path_latlon: list[tuple[float, float]] = [(o_lat, o_lon)] + selected_lane + [(d_lat, d_lon)]

    deduped: list[tuple[float, float]] = []
    for lat, lon in path_latlon:
        if deduped and abs(deduped[-1][0] - lat) <= _EPS and abs(deduped[-1][1] - lon) <= _EPS:
            continue
        deduped.append((lat, lon))

    dense = _densify_path(deduped, n_points=n_points)
    return _smooth_lonlat_path(dense, smooth_window=smooth_window)
