from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.main.map.routing.geometry_utils import EPS, offset_latlon_km, segment_perpendicular_unit
from app.main.map.routing.water_validation import distance_to_water_km, is_water_point
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class DirectionalWaterSearchResult:
    side: str
    corrected_point_latlon: tuple[float, float]
    reached_water: bool
    iterations: int
    correction_distance_km: float
    best_distance_to_water_km: float


@dataclass(frozen=True)
class PointCorrectionResult:
    original_point_latlon: tuple[float, float]
    corrected_point_latlon: tuple[float, float]
    was_on_water: bool
    reached_water: bool
    selected_side: str | None
    iterations: int
    correction_distance_km: float
    best_distance_to_water_km: float


def correct_leg_intermediate_points(
    intermediate_points: Sequence[tuple[float, float]],
    *,
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float = 8.0,
    step_km: float = 1.0,
    max_search_km: float = 20.0,
    max_iterations: int | None = None,
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
                max_iterations=max_iterations,
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
    max_iterations: int | None = None,
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
            max_iterations=max_iterations,
        ),
        path[-1],
    ]


def correct_point_to_water_result(
    *,
    point_latlon: tuple[float, float],
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float,
    step_km: float,
    max_search_km: float,
    max_iterations: int | None = None,
) -> PointCorrectionResult:
    initial_distance_to_water_km = distance_to_water_km(point_latlon, reference_path)
    if is_water_point(point_latlon, reference_path, tolerance_km=tolerance_km):
        return PointCorrectionResult(
            original_point_latlon=point_latlon,
            corrected_point_latlon=point_latlon,
            was_on_water=True,
            reached_water=True,
            selected_side=None,
            iterations=0,
            correction_distance_km=0.0,
            best_distance_to_water_km=initial_distance_to_water_km,
        )

    left_unit_east, left_unit_north = segment_perpendicular_unit(leg_start_latlon, leg_end_latlon)
    left_result = _march_to_water(
        point_latlon=point_latlon,
        reference_path=reference_path,
        tolerance_km=tolerance_km,
        step_km=step_km,
        max_search_km=max_search_km,
        max_iterations=max_iterations,
        unit_east=left_unit_east,
        unit_north=left_unit_north,
        side="left",
        initial_distance_to_water_km=initial_distance_to_water_km,
    )
    right_result = _march_to_water(
        point_latlon=point_latlon,
        reference_path=reference_path,
        tolerance_km=tolerance_km,
        step_km=step_km,
        max_search_km=max_search_km,
        max_iterations=max_iterations,
        unit_east=-left_unit_east,
        unit_north=-left_unit_north,
        side="right",
        initial_distance_to_water_km=initial_distance_to_water_km,
    )

    successful_results = [result for result in (left_result, right_result) if result.reached_water]
    if successful_results:
        chosen = min(
            successful_results,
            key=lambda result: (
                result.correction_distance_km,
                result.best_distance_to_water_km,
                0 if result.side == "left" else 1,
            ),
        )
        _log.debug(
            (
                "Corrected maritime point (%.6f, %.6f) side=%s iterations=%d "
                "distance_km=%.3f residual_to_water_km=%.3f"
            ),
            point_latlon[0],
            point_latlon[1],
            chosen.side,
            chosen.iterations,
            chosen.correction_distance_km,
            chosen.best_distance_to_water_km,
        )
        return PointCorrectionResult(
            original_point_latlon=point_latlon,
            corrected_point_latlon=chosen.corrected_point_latlon,
            was_on_water=False,
            reached_water=True,
            selected_side=chosen.side,
            iterations=chosen.iterations,
            correction_distance_km=chosen.correction_distance_km,
            best_distance_to_water_km=chosen.best_distance_to_water_km,
        )

    fallback = min(
        (left_result, right_result),
        key=lambda result: (
            result.best_distance_to_water_km,
            result.correction_distance_km,
            0 if result.side == "left" else 1,
        ),
    )
    _log.warning(
        (
            "No water correction found within %.1f km for maritime point (%.6f, %.6f); "
            "keeping %s fallback with residual_to_water_km=%.3f."
        ),
        max_search_km,
        point_latlon[0],
        point_latlon[1],
        fallback.side,
        fallback.best_distance_to_water_km,
    )
    return PointCorrectionResult(
        original_point_latlon=point_latlon,
        corrected_point_latlon=fallback.corrected_point_latlon,
        was_on_water=False,
        reached_water=False,
        selected_side=fallback.side,
        iterations=fallback.iterations,
        correction_distance_km=fallback.correction_distance_km,
        best_distance_to_water_km=fallback.best_distance_to_water_km,
    )


def correct_point_to_water(
    *,
    point_latlon: tuple[float, float],
    leg_start_latlon: tuple[float, float],
    leg_end_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float,
    step_km: float,
    max_search_km: float,
    max_iterations: int | None = None,
) -> tuple[float, float]:
    return correct_point_to_water_result(
        point_latlon=point_latlon,
        leg_start_latlon=leg_start_latlon,
        leg_end_latlon=leg_end_latlon,
        reference_path=reference_path,
        tolerance_km=tolerance_km,
        step_km=step_km,
        max_search_km=max_search_km,
        max_iterations=max_iterations,
    ).corrected_point_latlon


def _march_to_water(
    *,
    point_latlon: tuple[float, float],
    reference_path: Sequence[tuple[float, float]],
    tolerance_km: float,
    step_km: float,
    max_search_km: float,
    max_iterations: int | None,
    unit_east: float,
    unit_north: float,
    side: str,
    initial_distance_to_water_km: float,
) -> DirectionalWaterSearchResult:
    best_candidate = point_latlon
    best_distance_to_water_km = initial_distance_to_water_km
    best_iteration = 0
    safe_step_km = max(float(step_km), EPS)
    max_distance_steps = max(int(round(float(max_search_km) / safe_step_km)), 1)
    if max_iterations is None:
        max_steps = max_distance_steps
    else:
        max_steps = max(1, min(int(max_iterations), max_distance_steps))

    for iteration in range(1, max_steps + 1):
        correction_distance_km = iteration * safe_step_km
        candidate = offset_latlon_km(
            point_latlon[0],
            point_latlon[1],
            east_km=(unit_east * correction_distance_km),
            north_km=(unit_north * correction_distance_km),
        )
        candidate_distance_to_water_km = distance_to_water_km(candidate, reference_path)
        if candidate_distance_to_water_km < best_distance_to_water_km:
            best_candidate = candidate
            best_distance_to_water_km = candidate_distance_to_water_km
            best_iteration = iteration

        if is_water_point(candidate, reference_path, tolerance_km=tolerance_km):
            return DirectionalWaterSearchResult(
                side=side,
                corrected_point_latlon=candidate,
                reached_water=True,
                iterations=iteration,
                correction_distance_km=correction_distance_km,
                best_distance_to_water_km=candidate_distance_to_water_km,
            )

    return DirectionalWaterSearchResult(
        side=side,
        corrected_point_latlon=best_candidate,
        reached_water=False,
        iterations=best_iteration,
        correction_distance_km=(best_iteration * safe_step_km),
        best_distance_to_water_km=best_distance_to_water_km,
    )
