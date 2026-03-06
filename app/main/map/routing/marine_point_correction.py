from __future__ import annotations

import math
from typing import Sequence

from app.main.map.routing.geometry_utils import EPS, offset_latlon_km
from app.main.map.routing.water_validation import distance_to_water_km, is_water_point
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)


def correct_leg_intermediate_points(
    intermediate_points: Sequence[tuple[float, float]],
    *,
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float = 8.0,
    step_km: float = 1.0,
    max_search_km: float = 20.0,
) -> list[tuple[float, float]]:
    corrected: list[tuple[float, float]] = []
    for point_latlon in intermediate_points:
        corrected.append(
            correct_point_to_water(
                point_latlon=point_latlon,
                leg_start_latlon=leg_start_latlon,
                leg_end_latlon=leg_end_latlon,
                reference_path=reference_path,
                tolerance_km=tolerance_km,
                step_km=step_km,
                max_search_km=max_search_km,
            )
        )
    return corrected


def correct_path_to_water(
    path_latlon: Sequence[tuple[float, float]],
    *,
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float = 8.0,
    step_km: float = 1.0,
    max_search_km: float = 20.0,
) -> list[tuple[float, float]]:
    path = list(path_latlon)
    if len(path) < 3:
        return path

    return [
        path[0],
        *correct_leg_intermediate_points(
            path[1:-1],
            leg_start_latlon=path[0],
            leg_end_latlon=path[-1],
            reference_path=reference_path,
            tolerance_km=tolerance_km,
            step_km=step_km,
            max_search_km=max_search_km,
        ),
        path[-1],
    ]


def correct_point_to_water(
    *,
    point_latlon: tuple[float, float],
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float,
    step_km: float,
    max_search_km: float,
) -> tuple[float, float]:
    if is_water_point(point_latlon, reference_path, tolerance_km=tolerance_km):
        return point_latlon

    unit_east, unit_north = _segment_perpendicular_unit(leg_start_latlon, leg_end_latlon)
    best_candidate = point_latlon
    best_distance = distance_to_water_km(point_latlon, reference_path)
    max_steps = max(int(round(float(max_search_km) / max(float(step_km), EPS))), 1)

    for step_idx in range(1, max_steps + 1):
        offset_km = step_idx * float(step_km)
        candidates = (
            offset_latlon_km(
                point_latlon[0],
                point_latlon[1],
                east_km=(unit_east * offset_km),
                north_km=(unit_north * offset_km),
            ),
            offset_latlon_km(
                point_latlon[0],
                point_latlon[1],
                east_km=(-unit_east * offset_km),
                north_km=(-unit_north * offset_km),
            ),
        )

        valid_candidates: list[tuple[float, tuple[float, float]]] = []
        for candidate in candidates:
            water_distance = distance_to_water_km(candidate, reference_path)
            if water_distance < best_distance:
                best_distance = water_distance
                best_candidate = candidate
            if water_distance <= tolerance_km:
                valid_candidates.append((water_distance, candidate))

        if valid_candidates:
            valid_candidates.sort(key=lambda item: (item[0], -item[1][1], -item[1][0]))
            return valid_candidates[0][1]

    _log.debug(
        "No water correction found within %.1f km for point (%.6f, %.6f); keeping closest fallback.",
        max_search_km,
        point_latlon[0],
        point_latlon[1],
    )
    return best_candidate


def _segment_perpendicular_unit(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
) -> tuple[float, float]:
    mean_lat = math.radians((start_latlon[0] + end_latlon[0]) / 2.0)
    cos_lat = max(abs(math.cos(mean_lat)), 0.01)

    dx = (end_latlon[1] - start_latlon[1]) * 111.320 * cos_lat
    dy = (end_latlon[0] - start_latlon[0]) * 110.574
    length = math.hypot(dx, dy)
    if length <= EPS:
        return 1.0, 0.0

    unit_east = -dy / length
    unit_north = dx / length
    return unit_east, unit_north
