from __future__ import annotations

import math
from bisect import bisect_right
from typing import Iterable, Sequence

EPS = 1e-12


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
