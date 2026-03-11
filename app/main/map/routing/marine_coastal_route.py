from __future__ import annotations

import math
from dataclasses import dataclass

from app.main.map.routing.geometry_utils import EPS, latlon_delta_km, offset_latlon_km, segment_perpendicular_unit
from app.main.map.routing.water_validation import build_leg_reference_path, distance_to_water_km, is_water_point
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

MARITIME_ARC_SAGITTA_KM = 60.0
MARITIME_ARC_SIDE_TEST_KM = MARITIME_ARC_SAGITTA_KM
# Sea-side selection still relies on the repo's curated maritime reference path.
MARITIME_ARC_WATER_TOLERANCE_KM = 8.0
MIN_INTERMEDIATE_ARC_POINTS = 50
MAX_INTERMEDIATE_ARC_POINTS = 160


@dataclass(frozen=True)
class ArcSideChoice:
    side: str
    unit_east: float
    unit_north: float
    test_point_latlon: tuple[float, float]
    is_water: bool
    distance_to_water_km: float


@dataclass(frozen=True)
class CircularArcGeometry:
    intermediate_points: list[tuple[float, float]]
    radius_km: float
    chord_length_km: float
    arc_length_km: float
    center_latlon: tuple[float, float]
    center_offset_km: float
    sample_count: int


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
    _ = (smooth_window, style, curvature)

    midpoint_latlon = _midpoint_latlon(leg_start_latlon, leg_end_latlon)
    chord_length_km = _chord_length_km(leg_start_latlon, leg_end_latlon)
    if chord_length_km <= EPS:
        return []

    reference_path = build_leg_reference_path(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        origin_latlon=leg_start_latlon,
        dest_latlon=leg_end_latlon,
    )
    sample_count = _resolve_intermediate_point_count(chord_length_km=chord_length_km, requested_n_points=n_points)
    if sample_count <= 0:
        return []
    side_choice, alternate_choice = _choose_sea_facing_side(
        midpoint_latlon=midpoint_latlon,
        leg_start_latlon=leg_start_latlon,
        leg_end_latlon=leg_end_latlon,
        reference_path=reference_path,
    )
    arc_geometry = _build_circular_arc_geometry(
        leg_start_latlon=leg_start_latlon,
        leg_end_latlon=leg_end_latlon,
        midpoint_latlon=midpoint_latlon,
        side_choice=side_choice,
        sample_count=sample_count,
    )
    _log.debug(
        (
            "Coastal maritime arc %s -> %s side=%s chosen_water=%s chosen_distance_km=%.3f "
            "alternate_distance_km=%.3f chord_km=%.3f radius_km=%.3f arc_km=%.3f samples=%d"
        ),
        origin_port_name,
        dest_port_name,
        side_choice.side,
        side_choice.is_water,
        side_choice.distance_to_water_km,
        alternate_choice.distance_to_water_km,
        arc_geometry.chord_length_km,
        arc_geometry.radius_km,
        arc_geometry.arc_length_km,
        arc_geometry.sample_count,
    )
    return arc_geometry.intermediate_points


def _choose_sea_facing_side(
    *,
    midpoint_latlon: tuple[float, float],
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    reference_path: list[tuple[float, float]],
) -> tuple[ArcSideChoice, ArcSideChoice]:
    left_unit_east, left_unit_north = segment_perpendicular_unit(leg_start_latlon, leg_end_latlon)
    candidates = [
        _build_side_choice(
            side="left",
            midpoint_latlon=midpoint_latlon,
            unit_east=left_unit_east,
            unit_north=left_unit_north,
            reference_path=reference_path,
        ),
        _build_side_choice(
            side="right",
            midpoint_latlon=midpoint_latlon,
            unit_east=-left_unit_east,
            unit_north=-left_unit_north,
            reference_path=reference_path,
        ),
    ]
    ranked = sorted(
        candidates,
        key=lambda choice: (
            0 if choice.is_water else 1,
            choice.distance_to_water_km,
            0 if choice.side == "left" else 1,
        ),
    )
    return ranked[0], ranked[1]


def _build_side_choice(
    *,
    side: str,
    midpoint_latlon: tuple[float, float],
    unit_east: float,
    unit_north: float,
    reference_path: list[tuple[float, float]],
) -> ArcSideChoice:
    test_point_latlon = offset_latlon_km(
        midpoint_latlon[0],
        midpoint_latlon[1],
        east_km=(unit_east * MARITIME_ARC_SIDE_TEST_KM),
        north_km=(unit_north * MARITIME_ARC_SIDE_TEST_KM),
    )
    distance_km = distance_to_water_km(test_point_latlon, reference_path)
    return ArcSideChoice(
        side=side,
        unit_east=unit_east,
        unit_north=unit_north,
        test_point_latlon=test_point_latlon,
        is_water=is_water_point(
            test_point_latlon,
            reference_path,
            tolerance_km=MARITIME_ARC_WATER_TOLERANCE_KM,
        ),
        distance_to_water_km=distance_km,
    )


def _build_circular_arc_geometry(
    *,
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    midpoint_latlon: tuple[float, float],
    side_choice: ArcSideChoice,
    sample_count: int,
) -> CircularArcGeometry:
    start_x_km, start_y_km = latlon_delta_km(midpoint_latlon, leg_start_latlon)
    end_x_km, end_y_km = latlon_delta_km(midpoint_latlon, leg_end_latlon)
    chord_length_km = math.hypot(end_x_km - start_x_km, end_y_km - start_y_km)
    sagitta_km = MARITIME_ARC_SAGITTA_KM
    radius_km = ((chord_length_km * chord_length_km) / (8.0 * sagitta_km)) + (sagitta_km / 2.0)

    center_offset_km = sagitta_km - radius_km
    center_x_km = side_choice.unit_east * center_offset_km
    center_y_km = side_choice.unit_north * center_offset_km
    bulge_x_km = side_choice.unit_east * sagitta_km
    bulge_y_km = side_choice.unit_north * sagitta_km

    start_angle = math.atan2(start_y_km - center_y_km, start_x_km - center_x_km)
    end_angle = math.atan2(end_y_km - center_y_km, end_x_km - center_x_km)
    bulge_angle = math.atan2(bulge_y_km - center_y_km, bulge_x_km - center_x_km)

    ccw_sweep = _angle_delta_ccw(start_angle, end_angle)
    ccw_to_bulge = _angle_delta_ccw(start_angle, bulge_angle)
    if ccw_to_bulge <= ccw_sweep:
        sweep_angle = ccw_sweep
    else:
        sweep_angle = -_angle_delta_ccw(end_angle, start_angle)

    arc_length_km = abs(sweep_angle) * radius_km
    center_latlon = offset_latlon_km(
        midpoint_latlon[0],
        midpoint_latlon[1],
        east_km=center_x_km,
        north_km=center_y_km,
    )

    points: list[tuple[float, float]] = []
    total_points = sample_count + 2
    for idx in range(1, total_points - 1):
        fraction = idx / (total_points - 1)
        angle = start_angle + (sweep_angle * fraction)
        x_km = center_x_km + (radius_km * math.cos(angle))
        y_km = center_y_km + (radius_km * math.sin(angle))
        points.append(
            offset_latlon_km(
                midpoint_latlon[0],
                midpoint_latlon[1],
                east_km=x_km,
                north_km=y_km,
            )
        )

    return CircularArcGeometry(
        intermediate_points=points,
        radius_km=radius_km,
        chord_length_km=chord_length_km,
        arc_length_km=arc_length_km,
        center_latlon=center_latlon,
        center_offset_km=center_offset_km,
        sample_count=sample_count,
    )


def _resolve_intermediate_point_count(*, chord_length_km: float, requested_n_points: int) -> int:
    requested = int(requested_n_points)
    if requested <= 0:
        return 0
    adaptive = max(int(math.ceil(chord_length_km / 12.0)), MIN_INTERMEDIATE_ARC_POINTS)
    return min(max(requested, adaptive), MAX_INTERMEDIATE_ARC_POINTS)


def _midpoint_latlon(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
) -> tuple[float, float]:
    return (
        (float(start_latlon[0]) + float(end_latlon[0])) / 2.0,
        (float(start_latlon[1]) + float(end_latlon[1])) / 2.0,
    )


def _chord_length_km(
    start_latlon: tuple[float, float],
    end_latlon: tuple[float, float],
) -> float:
    east_km, north_km = latlon_delta_km(start_latlon, end_latlon)
    return math.hypot(east_km, north_km)


def _angle_delta_ccw(start_angle: float, end_angle: float) -> float:
    delta = math.fmod(end_angle - start_angle, 2.0 * math.pi)
    if delta < 0.0:
        delta += 2.0 * math.pi
    return delta
