from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import (
    latlon_delta_km,
    offset_latlon_km,
    segment_perpendicular_unit,
)
from app.main.map.routing.marine_leg_interpolation import interpolate_leg_intermediate_points
from app.main.map.routing.marine_point_correction import correct_point_to_water
from app.main.map.routing.water_validation import build_leg_reference_path

COASTAL_TOLERANCE_KM = 2.5
COASTAL_STEP_KM = 0.1
COASTAL_MAX_SEARCH_KM = 20.0


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
    base_points = interpolate_leg_intermediate_points(
        leg_start_latlon,
        leg_end_latlon,
        n_points=n_points,
    )
    if not base_points:
        return []

    reference_path = build_leg_reference_path(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=leg_start_latlon,
        dest_latlon=leg_end_latlon,
    )
    corrected_points = [
        correct_point_to_water(
            point_latlon=point_latlon,
            leg_start_latlon=leg_start_latlon,
            leg_end_latlon=leg_end_latlon,
            reference_path=reference_path,
            tolerance_km=COASTAL_TOLERANCE_KM,
            step_km=COASTAL_STEP_KM,
            max_search_km=COASTAL_MAX_SEARCH_KM,
        )
        for point_latlon in base_points
    ]

    unit_east, unit_north = segment_perpendicular_unit(leg_start_latlon, leg_end_latlon)
    lateral_offsets_km = [
        _signed_lateral_offset_km(
            base_point,
            corrected_point,
            unit_east=unit_east,
            unit_north=unit_north,
        )
        for base_point, corrected_point in zip(base_points, corrected_points)
    ]

    smoothed_offsets_km = _smooth_lateral_offsets(
        lateral_offsets_km,
        smooth_window=smooth_window,
        style=style,
        curvature=curvature,
    )
    smoothed_points = [
        offset_latlon_km(
            base_point[0],
            base_point[1],
            east_km=(unit_east * offset_km),
            north_km=(unit_north * offset_km),
        )
        for base_point, offset_km in zip(base_points, smoothed_offsets_km)
    ]

    return [
        correct_point_to_water(
            point_latlon=point_latlon,
            leg_start_latlon=leg_start_latlon,
            leg_end_latlon=leg_end_latlon,
            reference_path=reference_path,
            tolerance_km=COASTAL_TOLERANCE_KM,
            step_km=COASTAL_STEP_KM,
            max_search_km=COASTAL_MAX_SEARCH_KM,
        )
        for point_latlon in smoothed_points
    ]


def _signed_lateral_offset_km(
    base_point: tuple[float, float],
    corrected_point: tuple[float, float],
    *,
    unit_east: float,
    unit_north: float,
) -> float:
    east_km, north_km = latlon_delta_km(base_point, corrected_point)
    return (east_km * unit_east) + (north_km * unit_north)


def _smooth_lateral_offsets(
    offsets_km: Sequence[float],
    *,
    smooth_window: int,
    style: str,
    curvature: float,
) -> list[float]:
    if len(offsets_km) < 3:
        return [float(offset_km) for offset_km in offsets_km]

    window = max(int(smooth_window), 3)
    if window % 2 == 0:
        window += 1

    if str(style) == "Arc (pretty)":
        window = min(window + 4, max(len(offsets_km) | 1, window))

    blend = min(max(0.35 + (float(curvature) * 0.9), 0.35), 0.8)
    smoothed = [float(offset_km) for offset_km in offsets_km]

    passes = 2 if len(offsets_km) >= 5 else 1
    if str(style) == "Arc (pretty)":
        passes += 1

    for _ in range(passes):
        averaged = _moving_average(smoothed, window)
        smoothed = [
            ((1.0 - blend) * original) + (blend * average)
            for original, average in zip(smoothed, averaged)
        ]

    return smoothed


def _moving_average(values: Sequence[float], window: int) -> list[float]:
    if len(values) < 3:
        return [float(value) for value in values]

    half = window // 2
    averaged: list[float] = []
    for idx in range(len(values)):
        start = max(0, idx - half)
        end = min(len(values), idx + half + 1)
        segment = values[start:end]
        averaged.append(sum(segment) / len(segment))
    return averaged
