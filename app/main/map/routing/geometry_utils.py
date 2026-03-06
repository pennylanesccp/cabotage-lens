from __future__ import annotations

import math
from bisect import bisect_right
from typing import Iterable, Sequence

EPS = 1e-12
KM_PER_DEG_LAT = 110.574


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2.0) ** 2) + math.cos(p1) * math.cos(p2) * (math.sin(dl / 2.0) ** 2)
    return 2.0 * radius_km * math.asin(min(1.0, math.sqrt(max(a, 0.0))))


def path_length_km(path_latlon: Iterable[tuple[float, float]]) -> float:
    points = list(path_latlon)
    if len(points) < 2:
        return 0.0

    total = 0.0
    for idx in range(1, len(points)):
        a_lat, a_lon = points[idx - 1]
        b_lat, b_lon = points[idx]
        total += haversine_km(a_lat, a_lon, b_lat, b_lon)
    return total


def dedupe_latlon_path(path_latlon: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for lat, lon in path_latlon:
        lat_f = float(lat)
        lon_f = float(lon)
        if deduped and abs(deduped[-1][0] - lat_f) <= EPS and abs(deduped[-1][1] - lon_f) <= EPS:
            continue
        deduped.append((lat_f, lon_f))
    return deduped


def densify_latlon_path(path_latlon: Sequence[tuple[float, float]], n_points: int) -> list[list[float]]:
    if not path_latlon:
        return []
    if len(path_latlon) == 1:
        lat, lon = path_latlon[0]
        return [[float(lon), float(lat)]]

    target_n = max(int(n_points), 2)
    cumulative = [0.0]

    for idx in range(1, len(path_latlon)):
        a_lat, a_lon = path_latlon[idx - 1]
        b_lat, b_lon = path_latlon[idx]
        cumulative.append(cumulative[-1] + haversine_km(a_lat, a_lon, b_lat, b_lon))

    total = cumulative[-1]
    if total <= EPS:
        a_lat, a_lon = path_latlon[0]
        b_lat, b_lon = path_latlon[-1]
        return [
            [a_lon + ((b_lon - a_lon) * (idx / (target_n - 1))), a_lat + ((b_lat - a_lat) * (idx / (target_n - 1)))]
            for idx in range(target_n)
        ]

    dense: list[list[float]] = []
    for idx in range(target_n):
        distance = total * (idx / (target_n - 1))
        seg = max(1, bisect_right(cumulative, distance))
        if seg >= len(cumulative):
            seg = len(cumulative) - 1

        d0 = cumulative[seg - 1]
        d1 = cumulative[seg]
        lat0, lon0 = path_latlon[seg - 1]
        lat1, lon1 = path_latlon[seg]

        fraction = 0.0 if abs(d1 - d0) <= EPS else (distance - d0) / (d1 - d0)
        lat = lat0 + ((lat1 - lat0) * fraction)
        lon = lon0 + ((lon1 - lon0) * fraction)
        dense.append([lon, lat])

    return dense


def smooth_lonlat_path(path_lonlat: Sequence[Sequence[float]], smooth_window: int) -> list[list[float]]:
    if len(path_lonlat) < 3:
        return [[float(point[0]), float(point[1])] for point in path_lonlat]

    window = max(int(smooth_window), 1)
    if window % 2 == 0:
        window += 1
    half = window // 2

    smoothed: list[list[float]] = []
    for idx in range(len(path_lonlat)):
        start = max(0, idx - half)
        end = min(len(path_lonlat) - 1, idx + half)
        count = (end - start) + 1

        lon_sum = 0.0
        lat_sum = 0.0
        for pos in range(start, end + 1):
            lon_sum += float(path_lonlat[pos][0])
            lat_sum += float(path_lonlat[pos][1])
        smoothed.append([lon_sum / count, lat_sum / count])

    smoothed[0] = [float(path_lonlat[0][0]), float(path_lonlat[0][1])]
    smoothed[-1] = [float(path_lonlat[-1][0]), float(path_lonlat[-1][1])]
    return smoothed


def offset_latlon_km(lat: float, lon: float, *, east_km: float = 0.0, north_km: float = 0.0) -> tuple[float, float]:
    cos_lat = max(abs(math.cos(math.radians(lat))), 0.01)
    lat_out = float(lat) + (float(north_km) / KM_PER_DEG_LAT)
    lon_out = float(lon) + (float(east_km) / (111.320 * cos_lat))
    return lat_out, lon_out


def latlon_delta_km(
    origin_latlon: tuple[float, float],
    target_latlon: tuple[float, float],
) -> tuple[float, float]:
    mean_lat = math.radians((origin_latlon[0] + target_latlon[0]) / 2.0)
    cos_lat = max(abs(math.cos(mean_lat)), 0.01)

    east_km = (float(target_latlon[1]) - float(origin_latlon[1])) * 111.320 * cos_lat
    north_km = (float(target_latlon[0]) - float(origin_latlon[0])) * KM_PER_DEG_LAT
    return east_km, north_km


def segment_perpendicular_unit(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
) -> tuple[float, float]:
    mean_lat = math.radians((start_latlon[0] + end_latlon[0]) / 2.0)
    cos_lat = max(abs(math.cos(mean_lat)), 0.01)

    dx = (end_latlon[1] - start_latlon[1]) * 111.320 * cos_lat
    dy = (end_latlon[0] - start_latlon[0]) * KM_PER_DEG_LAT
    length = math.hypot(dx, dy)
    if length <= EPS:
        return 1.0, 0.0

    unit_east = -dy / length
    unit_north = dx / length
    return unit_east, unit_north


def point_to_segment_distance_km(
    point_latlon: tuple[float, float],
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
) -> float:
    point_lat, point_lon = point_latlon
    start_lat, start_lon = start_latlon
    end_lat, end_lon = end_latlon

    mean_lat = (point_lat + start_lat + end_lat) / 3.0
    cos_lat = max(abs(math.cos(math.radians(mean_lat))), 0.01)

    px = point_lon * cos_lat * 111.320
    py = point_lat * KM_PER_DEG_LAT
    ax = start_lon * cos_lat * 111.320
    ay = start_lat * KM_PER_DEG_LAT
    bx = end_lon * cos_lat * 111.320
    by = end_lat * KM_PER_DEG_LAT

    dx = bx - ax
    dy = by - ay
    seg_len_sq = (dx * dx) + (dy * dy)
    if seg_len_sq <= EPS:
        return math.hypot(px - ax, py - ay)

    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    proj_x = ax + (t * dx)
    proj_y = ay + (t * dy)
    return math.hypot(px - proj_x, py - proj_y)
