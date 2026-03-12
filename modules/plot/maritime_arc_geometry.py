from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

EARTH_RADIUS_KM = 6371.0088
CENTRAL_ANGLE_DEGREES = 60.0
CENTRAL_ANGLE_RADIANS = math.radians(CENTRAL_ANGLE_DEGREES)
EPS = 1e-9
DEFAULT_ARC_POINTS = 100
MIN_SIDE_DISTANCE_KM = 1.0


@dataclass(frozen=True)
class MetricProjection:
    anchor_lat_deg: float
    anchor_lon_deg: float
    anchor_lat_rad: float
    anchor_lon_rad: float
    sin_anchor_lat: float
    cos_anchor_lat: float

    @classmethod
    def from_endpoints(
        cls,
        port_a_latlon: tuple[float, float],
        port_b_latlon: tuple[float, float],
    ) -> "MetricProjection":
        anchor_lat, anchor_lon = _geographic_midpoint(port_a_latlon, port_b_latlon)
        anchor_lat_rad = math.radians(anchor_lat)
        anchor_lon_rad = math.radians(anchor_lon)
        return cls(
            anchor_lat_deg=anchor_lat,
            anchor_lon_deg=anchor_lon,
            anchor_lat_rad=anchor_lat_rad,
            anchor_lon_rad=anchor_lon_rad,
            sin_anchor_lat=math.sin(anchor_lat_rad),
            cos_anchor_lat=max(math.cos(anchor_lat_rad), EPS),
        )

    def project(self, latlon: tuple[float, float]) -> tuple[float, float]:
        lat_rad = math.radians(float(latlon[0]))
        lon_rad = math.radians(float(latlon[1]))
        delta_lon = _normalize_longitude_radians(lon_rad - self.anchor_lon_rad)

        cos_c = (
            (self.sin_anchor_lat * math.sin(lat_rad))
            + (self.cos_anchor_lat * math.cos(lat_rad) * math.cos(delta_lon))
        )
        c = math.acos(_clamp(cos_c, -1.0, 1.0))
        if c <= EPS:
            return 0.0, 0.0

        sin_c = math.sin(c)
        k = 1.0 if abs(sin_c) <= EPS else c / sin_c
        x = EARTH_RADIUS_KM * k * math.cos(lat_rad) * math.sin(delta_lon)
        y = EARTH_RADIUS_KM * k * (
            (self.cos_anchor_lat * math.sin(lat_rad))
            - (self.sin_anchor_lat * math.cos(lat_rad) * math.cos(delta_lon))
        )
        return x, y

    def unproject(self, point_xy: tuple[float, float]) -> tuple[float, float]:
        x_km = float(point_xy[0])
        y_km = float(point_xy[1])
        rho = math.hypot(x_km, y_km)
        if rho <= EPS:
            return self.anchor_lat_deg, self.anchor_lon_deg

        c = rho / EARTH_RADIUS_KM
        sin_c = math.sin(c)
        cos_c = math.cos(c)

        lat_rad = math.asin(
            (cos_c * self.sin_anchor_lat) + ((y_km * sin_c * self.cos_anchor_lat) / rho)
        )
        lon_rad = self.anchor_lon_rad + math.atan2(
            x_km * sin_c,
            (rho * self.cos_anchor_lat * cos_c) - (y_km * self.sin_anchor_lat * sin_c),
        )
        return math.degrees(lat_rad), _normalize_longitude_degrees(math.degrees(lon_rad))


@dataclass(frozen=True)
class CandidateArcCenters:
    projection: MetricProjection
    port_a_xy: tuple[float, float]
    port_b_xy: tuple[float, float]
    radius_km: float
    height_km: float
    center_a_xy: tuple[float, float]
    center_b_xy: tuple[float, float]

    @property
    def center_a_latlon(self) -> tuple[float, float]:
        return self.projection.unproject(self.center_a_xy)

    @property
    def center_b_latlon(self) -> tuple[float, float]:
        return self.projection.unproject(self.center_b_xy)


@dataclass(frozen=True)
class CircularArcGeometry:
    port_a_latlon: tuple[float, float]
    port_b_latlon: tuple[float, float]
    center_latlon: tuple[float, float]
    radius_km: float
    central_angle_radians: float
    midpoint_latlon: tuple[float, float]
    arc_points_latlon: tuple[tuple[float, float], ...]
    reference_side_distance_km: float


@dataclass(frozen=True)
class _ArcCandidateScore:
    center_xy: tuple[float, float]
    center_latlon: tuple[float, float]
    arc_points_xy: tuple[tuple[float, float], ...]
    midpoint_xy: tuple[float, float]
    reference_side_match_penalty: int
    midpoint_reference_distance_km: float
    mean_reference_distance_km: float
    nearest_clutter_distance_km: float


def compute_candidate_arc_centers(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
) -> CandidateArcCenters:
    projection = MetricProjection.from_endpoints(port_a_latlon, port_b_latlon)
    port_a_xy = projection.project(port_a_latlon)
    port_b_xy = projection.project(port_b_latlon)
    chord_vector = _subtract(port_b_xy, port_a_xy)
    chord_length_km = _vector_length(chord_vector)
    if chord_length_km <= EPS:
        return CandidateArcCenters(
            projection=projection,
            port_a_xy=port_a_xy,
            port_b_xy=port_b_xy,
            radius_km=0.0,
            height_km=0.0,
            center_a_xy=port_a_xy,
            center_b_xy=port_b_xy,
        )

    midpoint_xy = (
        (port_a_xy[0] + port_b_xy[0]) / 2.0,
        (port_a_xy[1] + port_b_xy[1]) / 2.0,
    )
    radius_km = chord_length_km
    height_km = chord_length_km * math.sqrt(3.0) / 2.0
    perpendicular_unit = _normalize_vector((-chord_vector[1], chord_vector[0]))
    if perpendicular_unit is None:
        perpendicular_unit = (0.0, 1.0)

    offset_xy = (
        perpendicular_unit[0] * height_km,
        perpendicular_unit[1] * height_km,
    )
    return CandidateArcCenters(
        projection=projection,
        port_a_xy=port_a_xy,
        port_b_xy=port_b_xy,
        radius_km=radius_km,
        height_km=height_km,
        center_a_xy=(midpoint_xy[0] + offset_xy[0], midpoint_xy[1] + offset_xy[1]),
        center_b_xy=(midpoint_xy[0] - offset_xy[0], midpoint_xy[1] - offset_xy[1]),
    )


def choose_maritime_side_center(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    *,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
) -> tuple[float, float]:
    construction = compute_candidate_arc_centers(port_a_latlon, port_b_latlon)
    if construction.radius_km <= EPS:
        return construction.center_a_latlon

    reference_path_xy = tuple(
        construction.projection.project((float(point[0]), float(point[1])))
        for point in _dedupe_latlon(reference_path_latlon)
    )
    clutter_points_xy = tuple(
        construction.projection.project((float(point[0]), float(point[1])))
        for point in _dedupe_latlon(clutter_points_latlon)
    )
    scores = (
        _score_candidate_center(
            construction=construction,
            center_xy=construction.center_a_xy,
            reference_path_xy=reference_path_xy,
            clutter_points_xy=clutter_points_xy,
            n_points=n_points,
        ),
        _score_candidate_center(
            construction=construction,
            center_xy=construction.center_b_xy,
            reference_path_xy=reference_path_xy,
            clutter_points_xy=clutter_points_xy,
            n_points=n_points,
        ),
    )
    chosen = min(
        scores,
        key=lambda score: (
            score.reference_side_match_penalty,
            score.midpoint_reference_distance_km,
            score.mean_reference_distance_km,
            -score.nearest_clutter_distance_km,
        ),
    )
    rejected = scores[0] if scores[1] is chosen else scores[1]
    _log.debug(
        (
            "Selected maritime arc center radius_km=%.3f midpoint_ref_km=%.3f mean_ref_km=%.3f "
            "rejected_midpoint_ref_km=%.3f rejected_mean_ref_km=%.3f"
        ),
        construction.radius_km,
        chosen.midpoint_reference_distance_km,
        chosen.mean_reference_distance_km,
        rejected.midpoint_reference_distance_km,
        rejected.mean_reference_distance_km,
    )
    return chosen.center_latlon


def sample_circular_arc(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    center_latlon: tuple[float, float],
    *,
    n_points: int = DEFAULT_ARC_POINTS,
) -> tuple[tuple[float, float], ...]:
    projection = MetricProjection.from_endpoints(port_a_latlon, port_b_latlon)
    port_a_xy = projection.project(port_a_latlon)
    port_b_xy = projection.project(port_b_latlon)
    center_xy = projection.project(center_latlon)
    arc_points_xy = _sample_circular_arc_xy(
        port_a_xy=port_a_xy,
        port_b_xy=port_b_xy,
        center_xy=center_xy,
        n_points=n_points,
    )
    points = [projection.unproject(point_xy) for point_xy in arc_points_xy]
    if points:
        points[0] = (float(port_a_latlon[0]), float(port_a_latlon[1]))
        points[-1] = (float(port_b_latlon[0]), float(port_b_latlon[1]))
    return tuple(points)


def build_port_to_port_arc(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    *,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
) -> CircularArcGeometry:
    construction = compute_candidate_arc_centers(port_a_latlon, port_b_latlon)
    if construction.radius_km <= EPS:
        point = (float(port_a_latlon[0]), float(port_a_latlon[1]))
        return CircularArcGeometry(
            port_a_latlon=point,
            port_b_latlon=point,
            center_latlon=point,
            radius_km=0.0,
            central_angle_radians=0.0,
            midpoint_latlon=point,
            arc_points_latlon=(point,),
            reference_side_distance_km=0.0,
        )

    reference_path_xy = tuple(
        construction.projection.project((float(point[0]), float(point[1])))
        for point in _dedupe_latlon(reference_path_latlon)
    )
    clutter_points_xy = tuple(
        construction.projection.project((float(point[0]), float(point[1])))
        for point in _dedupe_latlon(clutter_points_latlon)
    )
    chosen = min(
        (
            _score_candidate_center(
                construction=construction,
                center_xy=construction.center_a_xy,
                reference_path_xy=reference_path_xy,
                clutter_points_xy=clutter_points_xy,
                n_points=n_points,
            ),
            _score_candidate_center(
                construction=construction,
                center_xy=construction.center_b_xy,
                reference_path_xy=reference_path_xy,
                clutter_points_xy=clutter_points_xy,
                n_points=n_points,
            ),
        ),
        key=lambda score: (
            score.reference_side_match_penalty,
            score.midpoint_reference_distance_km,
            score.mean_reference_distance_km,
            -score.nearest_clutter_distance_km,
        ),
    )
    arc_points_latlon = [construction.projection.unproject(point_xy) for point_xy in chosen.arc_points_xy]
    arc_points_latlon[0] = (float(port_a_latlon[0]), float(port_a_latlon[1]))
    arc_points_latlon[-1] = (float(port_b_latlon[0]), float(port_b_latlon[1]))
    return CircularArcGeometry(
        port_a_latlon=(float(port_a_latlon[0]), float(port_a_latlon[1])),
        port_b_latlon=(float(port_b_latlon[0]), float(port_b_latlon[1])),
        center_latlon=chosen.center_latlon,
        radius_km=construction.radius_km,
        central_angle_radians=CENTRAL_ANGLE_RADIANS,
        midpoint_latlon=construction.projection.unproject(chosen.midpoint_xy),
        arc_points_latlon=tuple(arc_points_latlon),
        reference_side_distance_km=_reference_side_distance(
            construction.port_a_xy,
            construction.port_b_xy,
            reference_path_xy,
        ),
    )


def _score_candidate_center(
    *,
    construction: CandidateArcCenters,
    center_xy: tuple[float, float],
    reference_path_xy: Sequence[tuple[float, float]],
    clutter_points_xy: Sequence[tuple[float, float]],
    n_points: int,
) -> _ArcCandidateScore:
    arc_points_xy = _sample_circular_arc_xy(
        port_a_xy=construction.port_a_xy,
        port_b_xy=construction.port_b_xy,
        center_xy=center_xy,
        n_points=n_points,
    )
    midpoint_xy = arc_points_xy[len(arc_points_xy) // 2]
    midpoint_reference_distance_km = _distance_point_to_polyline(midpoint_xy, reference_path_xy)
    mean_reference_distance_km = _mean_distance_to_polyline(arc_points_xy[1:-1], reference_path_xy)
    nearest_clutter_distance_km = _nearest_point_distance(midpoint_xy, clutter_points_xy)
    reference_side_distance_km = _reference_side_distance(
        construction.port_a_xy,
        construction.port_b_xy,
        reference_path_xy,
    )
    candidate_side_distance_km = _signed_line_distance(
        construction.port_a_xy,
        construction.port_b_xy,
        midpoint_xy,
    )
    side_penalty = 0
    if abs(reference_side_distance_km) >= MIN_SIDE_DISTANCE_KM:
        if reference_side_distance_km * candidate_side_distance_km < 0.0:
            side_penalty = 1

    return _ArcCandidateScore(
        center_xy=center_xy,
        center_latlon=construction.projection.unproject(center_xy),
        arc_points_xy=arc_points_xy,
        midpoint_xy=midpoint_xy,
        reference_side_match_penalty=side_penalty,
        midpoint_reference_distance_km=midpoint_reference_distance_km,
        mean_reference_distance_km=mean_reference_distance_km,
        nearest_clutter_distance_km=nearest_clutter_distance_km,
    )


def _sample_circular_arc_xy(
    *,
    port_a_xy: tuple[float, float],
    port_b_xy: tuple[float, float],
    center_xy: tuple[float, float],
    n_points: int,
) -> tuple[tuple[float, float], ...]:
    sample_count = max(int(n_points), 2)
    radius_km = _vector_length(_subtract(port_a_xy, center_xy))
    if radius_km <= EPS:
        return (port_a_xy, port_b_xy)

    start_angle = math.atan2(port_a_xy[1] - center_xy[1], port_a_xy[0] - center_xy[0])
    end_angle = math.atan2(port_b_xy[1] - center_xy[1], port_b_xy[0] - center_xy[0])
    delta_angle = _normalize_sweep(end_angle - start_angle)

    points_xy: list[tuple[float, float]] = []
    for index in range(sample_count):
        fraction = index / (sample_count - 1)
        angle = start_angle + (delta_angle * fraction)
        points_xy.append(
            (
                center_xy[0] + (radius_km * math.cos(angle)),
                center_xy[1] + (radius_km * math.sin(angle)),
            )
        )

    points_xy[0] = port_a_xy
    points_xy[-1] = port_b_xy
    return tuple(points_xy)


def _reference_side_distance(
    port_a_xy: tuple[float, float],
    port_b_xy: tuple[float, float],
    reference_path_xy: Sequence[tuple[float, float]],
) -> float:
    if not reference_path_xy:
        return 0.0

    chord_midpoint_xy = (
        (port_a_xy[0] + port_b_xy[0]) / 2.0,
        (port_a_xy[1] + port_b_xy[1]) / 2.0,
    )
    nearest_reference_xy = _nearest_point_on_polyline(chord_midpoint_xy, reference_path_xy)
    return _signed_line_distance(port_a_xy, port_b_xy, nearest_reference_xy)


def _nearest_point_on_polyline(
    point_xy: tuple[float, float],
    polyline_xy: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    if not polyline_xy:
        return point_xy
    if len(polyline_xy) == 1:
        return polyline_xy[0]

    best_distance = float("inf")
    best_point = polyline_xy[0]
    for index in range(1, len(polyline_xy)):
        closest_point = _closest_point_on_segment(point_xy, polyline_xy[index - 1], polyline_xy[index])
        distance = _vector_length(_subtract(point_xy, closest_point))
        if distance < best_distance:
            best_distance = distance
            best_point = closest_point
    return best_point


def _distance_point_to_polyline(
    point_xy: tuple[float, float],
    polyline_xy: Sequence[tuple[float, float]],
) -> float:
    if not polyline_xy:
        return float("inf")
    if len(polyline_xy) == 1:
        return _vector_length(_subtract(point_xy, polyline_xy[0]))
    return _vector_length(_subtract(point_xy, _nearest_point_on_polyline(point_xy, polyline_xy)))


def _mean_distance_to_polyline(
    points_xy: Sequence[tuple[float, float]],
    polyline_xy: Sequence[tuple[float, float]],
) -> float:
    if not points_xy:
        return float("inf")
    distances = [_distance_point_to_polyline(point_xy, polyline_xy) for point_xy in points_xy]
    return sum(distances) / len(distances)


def _nearest_point_distance(
    point_xy: tuple[float, float],
    other_points_xy: Sequence[tuple[float, float]],
) -> float:
    if not other_points_xy:
        return 0.0
    return min(_vector_length(_subtract(point_xy, other_point_xy)) for other_point_xy in other_points_xy)


def _closest_point_on_segment(
    point_xy: tuple[float, float],
    segment_start_xy: tuple[float, float],
    segment_end_xy: tuple[float, float],
) -> tuple[float, float]:
    segment_vector = _subtract(segment_end_xy, segment_start_xy)
    segment_length_sq = (segment_vector[0] * segment_vector[0]) + (segment_vector[1] * segment_vector[1])
    if segment_length_sq <= EPS:
        return segment_start_xy

    point_vector = _subtract(point_xy, segment_start_xy)
    factor = _dot(point_vector, segment_vector) / segment_length_sq
    factor = _clamp(factor, 0.0, 1.0)
    return (
        segment_start_xy[0] + (segment_vector[0] * factor),
        segment_start_xy[1] + (segment_vector[1] * factor),
    )


def _signed_line_distance(
    line_start_xy: tuple[float, float],
    line_end_xy: tuple[float, float],
    point_xy: tuple[float, float],
) -> float:
    line_vector = _subtract(line_end_xy, line_start_xy)
    line_length = _vector_length(line_vector)
    if line_length <= EPS:
        return 0.0
    relative = _subtract(point_xy, line_start_xy)
    cross = (line_vector[0] * relative[1]) - (line_vector[1] * relative[0])
    return cross / line_length


def _geographic_midpoint(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
) -> tuple[float, float]:
    lat_a_rad = math.radians(float(port_a_latlon[0]))
    lon_a_rad = math.radians(float(port_a_latlon[1]))
    lat_b_rad = math.radians(float(port_b_latlon[0]))
    lon_b_rad = math.radians(float(port_b_latlon[1]))

    delta_lon = _normalize_longitude_radians(lon_b_rad - lon_a_rad)
    bx = math.cos(lat_b_rad) * math.cos(delta_lon)
    by = math.cos(lat_b_rad) * math.sin(delta_lon)
    lat_mid_rad = math.atan2(
        math.sin(lat_a_rad) + math.sin(lat_b_rad),
        math.sqrt((math.cos(lat_a_rad) + bx) ** 2 + (by * by)),
    )
    lon_mid_rad = lon_a_rad + math.atan2(by, math.cos(lat_a_rad) + bx)
    return math.degrees(lat_mid_rad), _normalize_longitude_degrees(math.degrees(lon_mid_rad))


def _dedupe_latlon(points_latlon: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for point in points_latlon:
        latlon = (float(point[0]), float(point[1]))
        if deduped and abs(deduped[-1][0] - latlon[0]) <= EPS and abs(deduped[-1][1] - latlon[1]) <= EPS:
            continue
        deduped.append(latlon)
    return deduped


def _normalize_sweep(angle_radians: float) -> float:
    normalized = math.atan2(math.sin(angle_radians), math.cos(angle_radians))
    if abs(normalized) <= math.pi:
        return normalized
    return normalized - (math.tau if normalized > 0.0 else -math.tau)


def _normalize_vector(vector_xy: tuple[float, float]) -> tuple[float, float] | None:
    length = _vector_length(vector_xy)
    if length <= EPS:
        return None
    return vector_xy[0] / length, vector_xy[1] / length


def _normalize_longitude_radians(angle_radians: float) -> float:
    return ((angle_radians + math.pi) % math.tau) - math.pi


def _normalize_longitude_degrees(angle_degrees: float) -> float:
    return ((angle_degrees + 180.0) % 360.0) - 180.0


def _subtract(a_xy: tuple[float, float], b_xy: tuple[float, float]) -> tuple[float, float]:
    return a_xy[0] - b_xy[0], a_xy[1] - b_xy[1]


def _dot(a_xy: tuple[float, float], b_xy: tuple[float, float]) -> float:
    return (a_xy[0] * b_xy[0]) + (a_xy[1] * b_xy[1])


def _vector_length(vector_xy: tuple[float, float]) -> float:
    return math.hypot(vector_xy[0], vector_xy[1])


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
