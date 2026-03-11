from __future__ import annotations

from typing import Sequence

from app.main.map.routing.geometry_utils import (
    EPS,
    latlon_delta_km,
    offset_latlon_km,
    segment_perpendicular_unit,
)
from app.main.map.routing.marine_leg_interpolation import interpolate_leg_intermediate_points
from app.main.map.routing.marine_point_correction import PointCorrectionResult, correct_point_to_water_result
from app.main.map.routing.water_validation import build_leg_reference_path, is_water_point
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

# Keep this strict: the water validator uses a reference maritime corridor, so
# a broad tolerance lets inland points slip through as "water" without any fix.
COASTAL_WATER_HIT_TOLERANCE_KM = 0.15
COASTAL_STEP_KM = 0.1
COASTAL_MAX_SEARCH_KM = 20.0
COASTAL_MAX_ITERATIONS = 200
COASTAL_EXTRA_OFFSHORE_MARGIN_KM = 0.15
COASTAL_SHOULDER_BORROW_KM = 0.4


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
    unit_east, unit_north = segment_perpendicular_unit(leg_start_latlon, leg_end_latlon)
    correction_results = [
        correct_point_to_water_result(
            point_latlon=point_latlon,
            leg_start_latlon=leg_start_latlon,
            leg_end_latlon=leg_end_latlon,
            reference_path=reference_path,
            tolerance_km=COASTAL_WATER_HIT_TOLERANCE_KM,
            step_km=COASTAL_STEP_KM,
            max_search_km=COASTAL_MAX_SEARCH_KM,
            max_iterations=COASTAL_MAX_ITERATIONS,
        )
        for point_latlon in base_points
    ]
    raw_corrected_points = [result.corrected_point_latlon for result in correction_results]
    raw_offsets_km = [
        _signed_lateral_offset_km(
            base_point,
            corrected_point,
            unit_east=unit_east,
            unit_north=unit_north,
        )
        for base_point, corrected_point in zip(base_points, raw_corrected_points)
    ]

    smoothed_offsets_km = _smooth_lateral_offsets(
        raw_offsets_km,
        smooth_window=smooth_window,
        style=style,
        curvature=curvature,
    )
    final_offsets_km = _resolve_nearshore_offsets(
        base_points=base_points,
        raw_offsets_km=raw_offsets_km,
        smoothed_offsets_km=smoothed_offsets_km,
        unit_east=unit_east,
        unit_north=unit_north,
        reference_path=reference_path,
    )
    final_points = [
        _point_at_offset(
            base_point,
            offset_km=offset_km,
            unit_east=unit_east,
            unit_north=unit_north,
        )
        for base_point, offset_km in zip(base_points, final_offsets_km)
    ]
    _log_coastal_leg_summary(
        origin_port_name=origin_port_name,
        dest_port_name=dest_port_name,
        correction_results=correction_results,
        final_offsets_km=final_offsets_km,
    )
    return final_points


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

    window = max(int(smooth_window), 5)
    if window % 2 == 0:
        window += 1

    window += 2
    if str(style) == "Arc (pretty)":
        window += 2

    max_window = len(offsets_km) if len(offsets_km) % 2 == 1 else max(len(offsets_km) - 1, 1)
    window = max(3, min(window, max_window))

    blend = min(max(0.55 + (float(curvature) * 0.35), 0.55), 0.82)
    smoothed = [float(offset_km) for offset_km in offsets_km]

    passes = 3 if len(offsets_km) >= 5 else 1
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


def _resolve_nearshore_offsets(
    *,
    base_points: Sequence[tuple[float, float]],
    raw_offsets_km: Sequence[float],
    smoothed_offsets_km: Sequence[float],
    unit_east: float,
    unit_north: float,
    reference_path: Sequence[tuple[float, float]],
) -> list[float]:
    final_offsets_km: list[float] = []
    for idx, base_point in enumerate(base_points):
        raw_offset = float(raw_offsets_km[idx])
        max_allowed_abs = _max_allowed_offset_abs(raw_offsets_km, idx)
        target_offset = _normalize_target_offset(
            smoothed_offset_km=smoothed_offsets_km[idx],
            raw_offsets_km=raw_offsets_km,
            idx=idx,
            max_allowed_abs=max_allowed_abs,
        )
        final_offsets_km.append(
            _resolve_valid_offset(
                base_point=base_point,
                target_offset_km=target_offset,
                raw_offset_km=raw_offset,
                max_allowed_abs=max_allowed_abs,
                unit_east=unit_east,
                unit_north=unit_north,
                reference_path=reference_path,
            )
        )
    return final_offsets_km


def _normalize_target_offset(
    *,
    smoothed_offset_km: float,
    raw_offsets_km: Sequence[float],
    idx: int,
    max_allowed_abs: float,
) -> float:
    local_sign = _offset_sign(_local_average(raw_offsets_km, idx, radius=2))
    raw_sign = _offset_sign(raw_offsets_km[idx])
    smooth_sign = _offset_sign(smoothed_offset_km)

    if local_sign != 0 and smooth_sign != 0 and local_sign != smooth_sign:
        sign = local_sign
    else:
        sign = smooth_sign or local_sign or raw_sign

    return float(sign) * min(abs(float(smoothed_offset_km)), max_allowed_abs)


def _resolve_valid_offset(
    *,
    base_point: tuple[float, float],
    target_offset_km: float,
    raw_offset_km: float,
    max_allowed_abs: float,
    unit_east: float,
    unit_north: float,
    reference_path: Sequence[tuple[float, float]],
) -> float:
    raw_sign = _offset_sign(raw_offset_km)
    raw_abs = abs(float(raw_offset_km))

    if _is_valid_offset(
        base_point,
        target_offset_km=target_offset_km,
        unit_east=unit_east,
        unit_north=unit_north,
        reference_path=reference_path,
    ):
        return target_offset_km

    if raw_abs > EPS and raw_sign == _offset_sign(target_offset_km) and abs(float(target_offset_km)) < raw_abs:
        return _binary_search_valid_offset(
            base_point=base_point,
            invalid_offset_km=target_offset_km,
            valid_offset_km=raw_offset_km,
            unit_east=unit_east,
            unit_north=unit_north,
            reference_path=reference_path,
        )

    if raw_abs > EPS:
        return raw_offset_km

    if _is_valid_offset(
        base_point,
        target_offset_km=0.0,
        unit_east=unit_east,
        unit_north=unit_north,
        reference_path=reference_path,
    ):
        return 0.0

    preferred_sign = _offset_sign(target_offset_km) or 1
    return _search_first_valid_offset(
        base_point=base_point,
        preferred_sign=preferred_sign,
        max_allowed_abs=max_allowed_abs,
        unit_east=unit_east,
        unit_north=unit_north,
        reference_path=reference_path,
    )


def _binary_search_valid_offset(
    *,
    base_point: tuple[float, float],
    invalid_offset_km: float,
    valid_offset_km: float,
    unit_east: float,
    unit_north: float,
    reference_path: Sequence[tuple[float, float]],
) -> float:
    sign = _offset_sign(valid_offset_km) or 1
    low = min(abs(float(invalid_offset_km)), abs(float(valid_offset_km)))
    high = max(abs(float(invalid_offset_km)), abs(float(valid_offset_km)))

    for _ in range(12):
        mid = (low + high) / 2.0
        candidate_offset = float(sign) * mid
        if _is_valid_offset(
            base_point,
            target_offset_km=candidate_offset,
            unit_east=unit_east,
            unit_north=unit_north,
            reference_path=reference_path,
        ):
            high = mid
        else:
            low = mid

    return float(sign) * high


def _search_first_valid_offset(
    *,
    base_point: tuple[float, float],
    preferred_sign: int,
    max_allowed_abs: float,
    unit_east: float,
    unit_north: float,
    reference_path: Sequence[tuple[float, float]],
) -> float:
    if max_allowed_abs <= EPS:
        return 0.0

    max_steps = max(int(round(max_allowed_abs / COASTAL_STEP_KM)), 1)
    for step_idx in range(1, max_steps + 1):
        offset_abs = step_idx * COASTAL_STEP_KM
        signed_offsets = (
            float(preferred_sign) * offset_abs,
            float(-preferred_sign) * offset_abs,
        )
        for candidate_offset in signed_offsets:
            if _is_valid_offset(
                base_point,
                target_offset_km=candidate_offset,
                unit_east=unit_east,
                unit_north=unit_north,
                reference_path=reference_path,
            ):
                return candidate_offset
    return 0.0


def _is_valid_offset(
    base_point: tuple[float, float],
    *,
    target_offset_km: float,
    unit_east: float,
    unit_north: float,
    reference_path: Sequence[tuple[float, float]],
) -> bool:
    candidate_point = _point_at_offset(
        base_point,
        offset_km=target_offset_km,
        unit_east=unit_east,
        unit_north=unit_north,
    )
    return is_water_point(candidate_point, reference_path, tolerance_km=COASTAL_WATER_HIT_TOLERANCE_KM)


def _point_at_offset(
    base_point: tuple[float, float],
    *,
    offset_km: float,
    unit_east: float,
    unit_north: float,
) -> tuple[float, float]:
    return offset_latlon_km(
        base_point[0],
        base_point[1],
        east_km=(unit_east * float(offset_km)),
        north_km=(unit_north * float(offset_km)),
    )


def _max_allowed_offset_abs(raw_offsets_km: Sequence[float], idx: int) -> float:
    raw_abs = abs(float(raw_offsets_km[idx]))
    neighbor_abs = max(
        abs(float(raw_offsets_km[pos]))
        for pos in range(max(0, idx - 2), min(len(raw_offsets_km), idx + 3))
    )
    if raw_abs <= 0.05:
        return min(neighbor_abs * 0.35, COASTAL_SHOULDER_BORROW_KM)
    return max(raw_abs, min(raw_abs + COASTAL_EXTRA_OFFSHORE_MARGIN_KM, neighbor_abs))


def _local_average(values: Sequence[float], idx: int, *, radius: int) -> float:
    start = max(0, idx - radius)
    end = min(len(values), idx + radius + 1)
    segment = values[start:end]
    if not segment:
        return 0.0
    return sum(float(value) for value in segment) / len(segment)


def _offset_sign(value: float) -> int:
    if value > EPS:
        return 1
    if value < -EPS:
        return -1
    return 0


def _log_coastal_leg_summary(
    *,
    origin_port_name: str,
    dest_port_name: str,
    correction_results: Sequence[PointCorrectionResult],
    final_offsets_km: Sequence[float],
) -> None:
    if not correction_results:
        return

    moved_points = 0
    unresolved_points = 0
    max_correction_distance_km = 0.0
    max_abs_final_offset_km = 0.0

    for result in correction_results:
        correction_distance_km = float(result.correction_distance_km or 0.0)
        if correction_distance_km > EPS:
            moved_points += 1
        if not result.reached_water:
            unresolved_points += 1
        max_correction_distance_km = max(max_correction_distance_km, correction_distance_km)

    if final_offsets_km:
        max_abs_final_offset_km = max(abs(float(offset_km)) for offset_km in final_offsets_km)

    _log.debug(
        (
            "Coastal maritime leg summary %s -> %s base_points=%d moved=%d unresolved=%d "
            "max_correction_km=%.3f max_final_offset_km=%.3f"
        ),
        origin_port_name,
        dest_port_name,
        len(correction_results),
        moved_points,
        unresolved_points,
        max_correction_distance_km,
        max_abs_final_offset_km,
    )
