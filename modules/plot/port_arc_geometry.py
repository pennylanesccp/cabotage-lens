from __future__ import annotations

"""
Corridor-based maritime port-arc geometry for map visualization.

This module does not validate land/water orientation against a real Brazil
shoreline polygon because that dataset is not present in this repository.
Instead, it infers the water-facing side from the nearest available maritime
corridor geometry (reference waypoints / route corridors already curated in the
repo). The API is intentionally structured so a future polygon backend can be
plugged in without changing the app layer.
"""

import math
from dataclasses import dataclass
from typing import Sequence

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

EARTH_RADIUS_KM = 6371.0088
KM_PER_DEG_LAT = 110.574
EPS = 1e-12
ARC_VISIBLE_FRACTION = 0.10
ARC_VISIBLE_ANGLE_RAD = 2.0 * math.pi * ARC_VISIBLE_FRACTION
MIN_TARGET_ARC_LENGTH_KM = 8.0
MAX_TARGET_ARC_LENGTH_KM = 35.0
NEAREST_PORT_DISTANCE_SCALE = 0.30
CORRIDOR_SPACING_SCALE = 0.80
DEFAULT_ARC_SAMPLE_COUNT = 15
MIN_CORRIDOR_DISTANCE_FOR_VECTOR_KM = 0.05


@dataclass(frozen=True)
class LocalProjection:
    anchor_lat: float
    anchor_lon: float
    cos_lat: float

    @classmethod
    def from_anchor(cls, anchor_latlon: tuple[float, float]) -> "LocalProjection":
        anchor_lat = float(anchor_latlon[0])
        anchor_lon = float(anchor_latlon[1])
        cos_lat = max(abs(math.cos(math.radians(anchor_lat))), 0.01)
        return cls(anchor_lat=anchor_lat, anchor_lon=anchor_lon, cos_lat=cos_lat)

    def project(self, latlon: tuple[float, float]) -> tuple[float, float]:
        lat = float(latlon[0])
        lon = float(latlon[1])
        east_km = (lon - self.anchor_lon) * 111.320 * self.cos_lat
        north_km = (lat - self.anchor_lat) * KM_PER_DEG_LAT
        return east_km, north_km

    def unproject(self, point_xy: tuple[float, float]) -> tuple[float, float]:
        east_km = float(point_xy[0])
        north_km = float(point_xy[1])
        lat = self.anchor_lat + (north_km / KM_PER_DEG_LAT)
        lon = self.anchor_lon + (east_km / (111.320 * self.cos_lat))
        return lat, lon


@dataclass(frozen=True)
class CorridorContext:
    projection: LocalProjection
    corridor_latlon: tuple[tuple[float, float], ...]
    corridor_xy: tuple[tuple[float, float], ...]
    nearest_segment_index: int
    nearest_point_xy: tuple[float, float]
    nearest_point_latlon: tuple[float, float]
    nearest_distance_km: float
    tangent_unit: tuple[float, float]
    forward_probe_unit: tuple[float, float]
    local_spacing_km: float
    port_distance_to_corridor_km: float


@dataclass(frozen=True)
class PortArcGeometry:
    port_latlon: tuple[float, float]
    corridor_anchor_latlon: tuple[float, float]
    center_latlon: tuple[float, float]
    radius_km: float
    center_offset_km: float
    visible_angle_rad: float
    target_arc_length_km: float
    nearest_port_distance_km: float
    local_corridor_spacing_km: float
    water_direction_unit: tuple[float, float]
    midpoint_latlon: tuple[float, float]
    port_distance_to_corridor_km: float
    midpoint_distance_to_corridor_km: float
    arc_points_latlon: tuple[tuple[float, float], ...]
    route_ordered_arc_points_latlon: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class PortArcDebugPayload:
    name: str
    port_latlon: tuple[float, float]
    corridor_path_latlon: tuple[tuple[float, float], ...]
    nearest_segment_latlon: tuple[tuple[float, float], ...]
    corridor_anchor_latlon: tuple[float, float]
    center_latlon: tuple[float, float]
    water_vector_latlon: tuple[tuple[float, float], tuple[float, float]]
    arc_points_latlon: tuple[tuple[float, float], ...]
    midpoint_latlon: tuple[float, float]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2.0) ** 2) + math.cos(p1) * math.cos(p2) * (math.sin(dl / 2.0) ** 2)
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(max(a, 0.0))))


def project_geometry(
    anchor_latlon: tuple[float, float],
    points_latlon: Sequence[tuple[float, float]],
) -> tuple[LocalProjection, list[tuple[float, float]]]:
    projection = LocalProjection.from_anchor(anchor_latlon)
    return projection, [projection.project(point) for point in points_latlon]


def infer_water_direction_from_polygon(*args, **kwargs) -> tuple[float, float]:
    raise NotImplementedError(
        "Polygon-backed land/water validation is not available in this repository. "
        "Use infer_water_direction_from_corridor() until a shoreline dataset is added."
    )


def get_local_corridor_context(
    port_latlon: tuple[float, float],
    corridor_latlon: Sequence[tuple[float, float]],
) -> CorridorContext:
    corridor_points = _prepare_corridor_points(port_latlon, corridor_latlon)
    projection, corridor_xy = project_geometry(port_latlon, corridor_points)

    if not corridor_xy:
        return CorridorContext(
            projection=projection,
            corridor_latlon=(),
            corridor_xy=(),
            nearest_segment_index=0,
            nearest_point_xy=(1.0, 0.0),
            nearest_point_latlon=projection.unproject((1.0, 0.0)),
            nearest_distance_km=1.0,
            tangent_unit=(1.0, 0.0),
            forward_probe_unit=(1.0, 0.0),
            local_spacing_km=MIN_TARGET_ARC_LENGTH_KM,
            port_distance_to_corridor_km=1.0,
        )

    if len(corridor_xy) == 1:
        nearest_xy = corridor_xy[0]
        tangent_unit = _normalize_vector(nearest_xy) or (1.0, 0.0)
        local_spacing = max(_vector_length(nearest_xy), MIN_TARGET_ARC_LENGTH_KM)
        return CorridorContext(
            projection=projection,
            corridor_latlon=tuple(corridor_points),
            corridor_xy=tuple(corridor_xy),
            nearest_segment_index=0,
            nearest_point_xy=nearest_xy,
            nearest_point_latlon=projection.unproject(nearest_xy),
            nearest_distance_km=_vector_length(nearest_xy),
            tangent_unit=tangent_unit,
            forward_probe_unit=tangent_unit,
            local_spacing_km=local_spacing,
            port_distance_to_corridor_km=_vector_length(nearest_xy),
        )

    best_distance = float("inf")
    best_segment_index = 0
    best_point_xy = corridor_xy[0]

    for index in range(1, len(corridor_xy)):
        point_xy = _closest_point_on_segment((0.0, 0.0), corridor_xy[index - 1], corridor_xy[index])
        distance = _vector_length(point_xy)
        if distance < best_distance:
            best_distance = distance
            best_segment_index = index - 1
            best_point_xy = point_xy

    tangent_unit = _segment_tangent(corridor_xy, best_segment_index)
    forward_probe_unit = _forward_probe_direction(corridor_xy, best_segment_index, best_point_xy) or tangent_unit
    local_spacing = _local_corridor_spacing(corridor_xy, best_segment_index)
    return CorridorContext(
        projection=projection,
        corridor_latlon=tuple(corridor_points),
        corridor_xy=tuple(corridor_xy),
        nearest_segment_index=best_segment_index,
        nearest_point_xy=best_point_xy,
        nearest_point_latlon=projection.unproject(best_point_xy),
        nearest_distance_km=best_distance,
        tangent_unit=tangent_unit,
        forward_probe_unit=forward_probe_unit,
        local_spacing_km=max(local_spacing, MIN_TARGET_ARC_LENGTH_KM),
        port_distance_to_corridor_km=best_distance,
    )


def infer_water_direction_from_corridor(
    port_latlon: tuple[float, float],
    corridor_latlon: Sequence[tuple[float, float]],
) -> tuple[tuple[float, float], CorridorContext]:
    context = get_local_corridor_context(port_latlon, corridor_latlon)
    direct_vector = _normalize_vector(context.nearest_point_xy)
    if direct_vector is not None and context.nearest_distance_km >= MIN_CORRIDOR_DISTANCE_FOR_VECTOR_KM:
        return direct_vector, context

    trend_vector = _forward_trend_vector(context)
    if trend_vector is not None and _vector_length(trend_vector) > EPS:
        left_normal = (-context.tangent_unit[1], context.tangent_unit[0])
        right_normal = (context.tangent_unit[1], -context.tangent_unit[0])
        if _dot(left_normal, trend_vector) >= _dot(right_normal, trend_vector):
            return left_normal, context
        return right_normal, context

    fallback = _normalize_vector(context.nearest_point_xy) or context.forward_probe_unit or context.tangent_unit
    return fallback, context


def compute_adaptive_arc_radius(
    port_latlon: tuple[float, float],
    peer_port_latlons: Sequence[tuple[float, float]],
    corridor_context: CorridorContext,
) -> tuple[float, float, float, float]:
    nearest_port_distance_km = _nearest_other_port_distance_km(port_latlon, peer_port_latlons)
    local_corridor_spacing_km = max(
        corridor_context.local_spacing_km,
        corridor_context.port_distance_to_corridor_km * 2.0,
        MIN_TARGET_ARC_LENGTH_KM,
    )

    candidates = [local_corridor_spacing_km * CORRIDOR_SPACING_SCALE]
    if math.isfinite(nearest_port_distance_km):
        candidates.append(nearest_port_distance_km * NEAREST_PORT_DISTANCE_SCALE)

    target_arc_length_km = min(candidates) if candidates else MIN_TARGET_ARC_LENGTH_KM
    target_arc_length_km = max(MIN_TARGET_ARC_LENGTH_KM, min(MAX_TARGET_ARC_LENGTH_KM, target_arc_length_km))
    radius_km = target_arc_length_km / ARC_VISIBLE_ANGLE_RAD
    return radius_km, target_arc_length_km, nearest_port_distance_km, local_corridor_spacing_km


def build_arc_from_center(
    *,
    port_latlon: tuple[float, float],
    water_direction_unit: tuple[float, float],
    corridor_context: CorridorContext,
    radius_km: float,
    target_arc_length_km: float,
    nearest_port_distance_km: float,
    local_corridor_spacing_km: float,
    sample_count: int = DEFAULT_ARC_SAMPLE_COUNT,
) -> PortArcGeometry:
    projection = corridor_context.projection
    theta = ARC_VISIBLE_ANGLE_RAD
    center_offset_km = radius_km * math.cos(theta / 2.0)
    center_xy = (
        -float(water_direction_unit[0]) * center_offset_km,
        -float(water_direction_unit[1]) * center_offset_km,
    )
    mid_angle = math.atan2(float(water_direction_unit[1]), float(water_direction_unit[0]))
    start_angle = mid_angle - (theta / 2.0)
    end_angle = mid_angle + (theta / 2.0)

    raw_points_xy: list[tuple[float, float]] = []
    point_count = max(int(sample_count), 5)
    for idx in range(point_count):
        fraction = idx / (point_count - 1)
        angle = start_angle + ((end_angle - start_angle) * fraction)
        raw_points_xy.append(
            (
                center_xy[0] + (radius_km * math.cos(angle)),
                center_xy[1] + (radius_km * math.sin(angle)),
            )
        )

    midpoint_xy = (
        center_xy[0] + (radius_km * math.cos(mid_angle)),
        center_xy[1] + (radius_km * math.sin(mid_angle)),
    )
    midpoint_distance = _distance_point_to_polyline(midpoint_xy, corridor_context.corridor_xy)
    ordered_points_xy = _order_arc_points_for_corridor_flow(raw_points_xy, corridor_context)
    arc_points_latlon = tuple(projection.unproject(point_xy) for point_xy in raw_points_xy)
    ordered_arc_points_latlon = tuple(projection.unproject(point_xy) for point_xy in ordered_points_xy)

    return PortArcGeometry(
        port_latlon=(float(port_latlon[0]), float(port_latlon[1])),
        corridor_anchor_latlon=corridor_context.nearest_point_latlon,
        center_latlon=projection.unproject(center_xy),
        radius_km=float(radius_km),
        center_offset_km=float(center_offset_km),
        visible_angle_rad=theta,
        target_arc_length_km=float(target_arc_length_km),
        nearest_port_distance_km=float(nearest_port_distance_km),
        local_corridor_spacing_km=float(local_corridor_spacing_km),
        water_direction_unit=(float(water_direction_unit[0]), float(water_direction_unit[1])),
        midpoint_latlon=projection.unproject(midpoint_xy),
        port_distance_to_corridor_km=float(corridor_context.port_distance_to_corridor_km),
        midpoint_distance_to_corridor_km=float(midpoint_distance),
        arc_points_latlon=arc_points_latlon,
        route_ordered_arc_points_latlon=ordered_arc_points_latlon,
    )


def choose_best_arc_orientation(
    *,
    port_latlon: tuple[float, float],
    corridor_context: CorridorContext,
    preferred_water_direction_unit: tuple[float, float],
    radius_km: float,
    target_arc_length_km: float,
    nearest_port_distance_km: float,
    local_corridor_spacing_km: float,
    sample_count: int = DEFAULT_ARC_SAMPLE_COUNT,
) -> PortArcGeometry:
    candidate_a = build_arc_from_center(
        port_latlon=port_latlon,
        water_direction_unit=preferred_water_direction_unit,
        corridor_context=corridor_context,
        radius_km=radius_km,
        target_arc_length_km=target_arc_length_km,
        nearest_port_distance_km=nearest_port_distance_km,
        local_corridor_spacing_km=local_corridor_spacing_km,
        sample_count=sample_count,
    )
    candidate_b = build_arc_from_center(
        port_latlon=port_latlon,
        water_direction_unit=(-preferred_water_direction_unit[0], -preferred_water_direction_unit[1]),
        corridor_context=corridor_context,
        radius_km=radius_km,
        target_arc_length_km=target_arc_length_km,
        nearest_port_distance_km=nearest_port_distance_km,
        local_corridor_spacing_km=local_corridor_spacing_km,
        sample_count=sample_count,
    )

    ranked = sorted(
        (candidate_a, candidate_b),
        key=lambda candidate: (
            0 if candidate.midpoint_distance_to_corridor_km < candidate.port_distance_to_corridor_km else 1,
            candidate.midpoint_distance_to_corridor_km,
        ),
    )
    chosen = ranked[0]
    flipped = ranked[0].water_direction_unit != candidate_a.water_direction_unit
    if flipped:
        _log.debug(
            "Flipped corridor arc orientation port=(%.6f, %.6f) port_distance_km=%.3f kept_midpoint_km=%.3f rejected_midpoint_km=%.3f",
            float(port_latlon[0]),
            float(port_latlon[1]),
            chosen.port_distance_to_corridor_km,
            chosen.midpoint_distance_to_corridor_km,
            ranked[1].midpoint_distance_to_corridor_km,
        )
    return chosen


def generate_port_arc_geometry(
    *,
    port_name: str,
    port_latlon: tuple[float, float],
    corridor_latlon: Sequence[tuple[float, float]],
    peer_port_latlons: Sequence[tuple[float, float]],
    sample_count: int = DEFAULT_ARC_SAMPLE_COUNT,
) -> PortArcGeometry:
    inferred_water_direction, corridor_context = infer_water_direction_from_corridor(port_latlon, corridor_latlon)
    radius_km, target_arc_length_km, nearest_port_distance_km, local_corridor_spacing_km = compute_adaptive_arc_radius(
        port_latlon,
        peer_port_latlons,
        corridor_context,
    )
    geometry = choose_best_arc_orientation(
        port_latlon=port_latlon,
        corridor_context=corridor_context,
        preferred_water_direction_unit=inferred_water_direction,
        radius_km=radius_km,
        target_arc_length_km=target_arc_length_km,
        nearest_port_distance_km=nearest_port_distance_km,
        local_corridor_spacing_km=local_corridor_spacing_km,
        sample_count=sample_count,
    )
    _log.debug(
        (
            "Generated corridor-based port arc port=%s radius_km=%.3f target_arc_km=%.3f visible_deg=%.2f "
            "nearest_port_km=%.3f corridor_spacing_km=%.3f port_to_corridor_km=%.3f midpoint_to_corridor_km=%.3f"
        ),
        port_name,
        geometry.radius_km,
        geometry.target_arc_length_km,
        math.degrees(geometry.visible_angle_rad),
        geometry.nearest_port_distance_km,
        geometry.local_corridor_spacing_km,
        geometry.port_distance_to_corridor_km,
        geometry.midpoint_distance_to_corridor_km,
    )
    return geometry


def build_port_arc_debug_payload(
    *,
    name: str,
    port_latlon: tuple[float, float],
    corridor_latlon: Sequence[tuple[float, float]],
    peer_port_latlons: Sequence[tuple[float, float]],
    sample_count: int = DEFAULT_ARC_SAMPLE_COUNT,
) -> PortArcDebugPayload:
    water_direction, corridor_context = infer_water_direction_from_corridor(port_latlon, corridor_latlon)
    radius_km, target_arc_length_km, nearest_port_distance_km, local_corridor_spacing_km = compute_adaptive_arc_radius(
        port_latlon,
        peer_port_latlons,
        corridor_context,
    )
    geometry = choose_best_arc_orientation(
        port_latlon=port_latlon,
        corridor_context=corridor_context,
        preferred_water_direction_unit=water_direction,
        radius_km=radius_km,
        target_arc_length_km=target_arc_length_km,
        nearest_port_distance_km=nearest_port_distance_km,
        local_corridor_spacing_km=local_corridor_spacing_km,
        sample_count=sample_count,
    )
    nearest_segment = _nearest_segment_latlon(corridor_context)
    return PortArcDebugPayload(
        name=name,
        port_latlon=(float(port_latlon[0]), float(port_latlon[1])),
        corridor_path_latlon=tuple(corridor_context.corridor_latlon),
        nearest_segment_latlon=nearest_segment,
        corridor_anchor_latlon=geometry.corridor_anchor_latlon,
        center_latlon=geometry.center_latlon,
        water_vector_latlon=(
            (float(port_latlon[0]), float(port_latlon[1])),
            geometry.midpoint_latlon,
        ),
        arc_points_latlon=geometry.route_ordered_arc_points_latlon,
        midpoint_latlon=geometry.midpoint_latlon,
    )


def _prepare_corridor_points(
    port_latlon: tuple[float, float],
    corridor_latlon: Sequence[tuple[float, float]],
) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for point in corridor_latlon:
        latlon = (float(point[0]), float(point[1]))
        if deduped and _same_point(latlon, deduped[-1]):
            continue
        if haversine_km(port_latlon[0], port_latlon[1], latlon[0], latlon[1]) <= MIN_CORRIDOR_DISTANCE_FOR_VECTOR_KM:
            continue
        deduped.append(latlon)
    return deduped


def _nearest_other_port_distance_km(
    port_latlon: tuple[float, float],
    peer_port_latlons: Sequence[tuple[float, float]],
) -> float:
    best = float("inf")
    for peer in peer_port_latlons:
        lat = float(peer[0])
        lon = float(peer[1])
        distance = haversine_km(port_latlon[0], port_latlon[1], lat, lon)
        if distance <= MIN_CORRIDOR_DISTANCE_FOR_VECTOR_KM:
            continue
        if distance < best:
            best = distance
    return best


def _local_corridor_spacing(
    corridor_xy: Sequence[tuple[float, float]],
    segment_index: int,
) -> float:
    lengths: list[float] = []
    start = max(segment_index - 1, 0)
    end = min(segment_index + 1, len(corridor_xy) - 2)
    for index in range(start, end + 1):
        lengths.append(_vector_length(_subtract(corridor_xy[index + 1], corridor_xy[index])))
    if not lengths:
        return MIN_TARGET_ARC_LENGTH_KM
    return sum(lengths) / len(lengths)


def _segment_tangent(
    corridor_xy: Sequence[tuple[float, float]],
    segment_index: int,
) -> tuple[float, float]:
    if len(corridor_xy) < 2:
        return (1.0, 0.0)
    vector = _subtract(corridor_xy[min(segment_index + 1, len(corridor_xy) - 1)], corridor_xy[segment_index])
    tangent = _normalize_vector(vector)
    if tangent is not None:
        return tangent
    average = _smoothed_segment_direction(corridor_xy, segment_index)
    return average or (1.0, 0.0)


def _forward_probe_direction(
    corridor_xy: Sequence[tuple[float, float]],
    segment_index: int,
    nearest_point_xy: tuple[float, float],
) -> tuple[float, float] | None:
    lookahead_points: list[tuple[float, float]] = []
    for index in range(segment_index + 1, min(segment_index + 4, len(corridor_xy))):
        lookahead_points.append(corridor_xy[index])
    if not lookahead_points:
        return None
    avg_x = sum(point[0] for point in lookahead_points) / len(lookahead_points)
    avg_y = sum(point[1] for point in lookahead_points) / len(lookahead_points)
    return _normalize_vector((avg_x - nearest_point_xy[0], avg_y - nearest_point_xy[1]))


def _forward_trend_vector(context: CorridorContext) -> tuple[float, float] | None:
    if not context.corridor_xy:
        return None
    lookahead_points = list(context.corridor_xy[: min(len(context.corridor_xy), 4)])
    if not lookahead_points:
        return None
    avg_x = sum(point[0] for point in lookahead_points) / len(lookahead_points)
    avg_y = sum(point[1] for point in lookahead_points) / len(lookahead_points)
    return _normalize_vector((avg_x, avg_y))


def _smoothed_segment_direction(
    corridor_xy: Sequence[tuple[float, float]],
    segment_index: int,
) -> tuple[float, float] | None:
    vectors: list[tuple[float, float]] = []
    start = max(segment_index - 1, 0)
    end = min(segment_index + 1, len(corridor_xy) - 2)
    for index in range(start, end + 1):
        vector = _normalize_vector(_subtract(corridor_xy[index + 1], corridor_xy[index]))
        if vector is not None:
            vectors.append(vector)
    if not vectors:
        return None
    avg_x = sum(vector[0] for vector in vectors) / len(vectors)
    avg_y = sum(vector[1] for vector in vectors) / len(vectors)
    return _normalize_vector((avg_x, avg_y))


def _order_arc_points_for_corridor_flow(
    raw_points_xy: Sequence[tuple[float, float]],
    corridor_context: CorridorContext,
) -> tuple[tuple[float, float], ...]:
    if len(raw_points_xy) < 2:
        return tuple(raw_points_xy)
    probe_distance_km = max(corridor_context.local_spacing_km * 0.5, 1.5)
    probe_xy = (
        corridor_context.nearest_point_xy[0] + (corridor_context.forward_probe_unit[0] * probe_distance_km),
        corridor_context.nearest_point_xy[1] + (corridor_context.forward_probe_unit[1] * probe_distance_km),
    )
    if _vector_length(_subtract(raw_points_xy[-1], probe_xy)) <= _vector_length(_subtract(raw_points_xy[0], probe_xy)):
        return tuple(raw_points_xy)
    return tuple(reversed(raw_points_xy))


def _nearest_segment_latlon(context: CorridorContext) -> tuple[tuple[float, float], ...]:
    if len(context.corridor_latlon) < 2:
        return tuple(context.corridor_latlon[:1])
    index = min(context.nearest_segment_index, len(context.corridor_latlon) - 2)
    return (
        context.corridor_latlon[index],
        context.corridor_latlon[index + 1],
    )


def _closest_point_on_segment(
    point_xy: tuple[float, float],
    seg_a_xy: tuple[float, float],
    seg_b_xy: tuple[float, float],
) -> tuple[float, float]:
    ab_xy = _subtract(seg_b_xy, seg_a_xy)
    ab_len_sq = (ab_xy[0] * ab_xy[0]) + (ab_xy[1] * ab_xy[1])
    if ab_len_sq <= EPS:
        return seg_a_xy
    ap_xy = _subtract(point_xy, seg_a_xy)
    t = _dot(ap_xy, ab_xy) / ab_len_sq
    t = max(0.0, min(1.0, t))
    return (
        seg_a_xy[0] + (ab_xy[0] * t),
        seg_a_xy[1] + (ab_xy[1] * t),
    )


def _distance_point_to_polyline(
    point_xy: tuple[float, float],
    polyline_xy: Sequence[tuple[float, float]],
) -> float:
    if not polyline_xy:
        return float("inf")
    if len(polyline_xy) == 1:
        return _vector_length(_subtract(point_xy, polyline_xy[0]))
    best = float("inf")
    for index in range(1, len(polyline_xy)):
        closest = _closest_point_on_segment(point_xy, polyline_xy[index - 1], polyline_xy[index])
        distance = _vector_length(_subtract(point_xy, closest))
        if distance < best:
            best = distance
    return best


def _normalize_vector(vector_xy: tuple[float, float]) -> tuple[float, float] | None:
    length = _vector_length(vector_xy)
    if length <= EPS:
        return None
    return vector_xy[0] / length, vector_xy[1] / length


def _subtract(a_xy: tuple[float, float], b_xy: tuple[float, float]) -> tuple[float, float]:
    return a_xy[0] - b_xy[0], a_xy[1] - b_xy[1]


def _dot(a_xy: tuple[float, float], b_xy: tuple[float, float]) -> float:
    return (a_xy[0] * b_xy[0]) + (a_xy[1] * b_xy[1])


def _vector_length(vector_xy: tuple[float, float]) -> float:
    return math.hypot(vector_xy[0], vector_xy[1])


def _same_point(a_latlon: tuple[float, float], b_latlon: tuple[float, float]) -> bool:
    return haversine_km(a_latlon[0], a_latlon[1], b_latlon[0], b_latlon[1]) <= MIN_CORRIDOR_DISTANCE_FOR_VECTOR_KM
