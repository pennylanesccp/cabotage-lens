from __future__ import annotations

"""
Chained maritime arc geometry helpers.

The rendered sea path remains one circular arc per consecutive port-to-port leg.
Per-leg overrides only tune central angle and side selection for problematic
legs; they do not collapse or replace the underlying port sequence.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from modules.infra.log_manager import get_logger
from modules.plot.maritime_arc_overrides import (
    DEFAULT_LEG_CENTRAL_ANGLE_DEG,
    flip_arc_side,
    normalize_arc_side,
    normalize_directional_leg_key,
    normalize_leg_key,
    normalize_port_identifier,
    resolve_leg_arc_override,
)

_log = get_logger(__name__)

EARTH_RADIUS_KM = 6371.0088
DEFAULT_CENTRAL_ANGLE_DEGREES = float(DEFAULT_LEG_CENTRAL_ANGLE_DEG)
CENTRAL_ANGLE_DEGREES = DEFAULT_CENTRAL_ANGLE_DEGREES
CENTRAL_ANGLE_RADIANS = math.radians(DEFAULT_CENTRAL_ANGLE_DEGREES)
EPS = 1e-9
DEFAULT_ARC_POINTS = 100
MIN_SIDE_DISTANCE_KM = 1.0
AUTO_SIDE_BIAS_THRESHOLD_KM = 25.0
DEFAULT_AUTO_ARC_SIDE = "right"
BRAZIL_INLAND_CENTROID_LATLON = (-14.2350, -51.9253)
BRAZIL_ARC_BIAS_LAT_RANGE = (-35.0, 6.0)
BRAZIL_ARC_BIAS_LON_RANGE = (-60.0, -30.0)


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
    central_angle_degrees: float
    central_angle_radians: float
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
    port_a_key: str
    port_b_key: str
    port_a_latlon: tuple[float, float]
    port_b_latlon: tuple[float, float]
    center_latlon: tuple[float, float]
    radius_km: float
    central_angle_degrees: float
    central_angle_radians: float
    midpoint_latlon: tuple[float, float]
    arc_points_latlon: tuple[tuple[float, float], ...]
    reference_side_distance_km: float
    side: str | None
    side_source: str
    angle_source: str


@dataclass(frozen=True)
class RouteArcPort:
    name: str
    latlon: tuple[float, float]
    key: str | None = None


@dataclass(frozen=True)
class LegArcConfig:
    leg_key: tuple[str, str]
    central_angle_deg: float
    side_override: str | None
    configured_side_override: str | None
    override_key: tuple[str, str] | None
    override_reverse_traversal: bool
    angle_source: str


@dataclass(frozen=True)
class LegArcCandidateDebug:
    center_latlon: tuple[float, float]
    center_side: str
    arc_side: str
    default_side_penalty: int
    midpoint_latlon: tuple[float, float]
    side_match_penalty: int
    midpoint_context_distance_km: float
    mean_context_distance_km: float
    nearest_clutter_distance_km: float


@dataclass(frozen=True)
class LegArcDebugPayload:
    leg_key: tuple[str, str]
    port_a_name: str
    port_b_name: str
    port_a_latlon: tuple[float, float]
    port_b_latlon: tuple[float, float]
    central_angle_deg: float
    angle_source: str
    side_override: str | None
    configured_side_override: str | None
    override_key: tuple[str, str] | None
    override_reverse_traversal: bool
    side_source: str
    chosen_arc_side: str | None
    chosen_center_side: str | None
    candidate_centers_latlon: tuple[tuple[float, float], tuple[float, float]]
    chosen_center_latlon: tuple[float, float]
    route_context_latlon: tuple[tuple[float, float], ...]
    reference_path_latlon: tuple[tuple[float, float], ...]
    candidates: tuple[LegArcCandidateDebug, ...]


@dataclass(frozen=True)
class _ArcCandidateScore:
    center_xy: tuple[float, float]
    center_latlon: tuple[float, float]
    arc_points_xy: tuple[tuple[float, float], ...]
    midpoint_xy: tuple[float, float]
    midpoint_latlon: tuple[float, float]
    center_side: str
    arc_side: str
    default_side_penalty: int
    side_match_penalty: int
    midpoint_context_distance_km: float
    mean_context_distance_km: float
    nearest_clutter_distance_km: float
    inland_centroid_distance_km: float


LegReferencePathBuilder = Callable[[RouteArcPort, RouteArcPort], Sequence[tuple[float, float]]]


def compute_candidate_arc_centers(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    *,
    central_angle_deg: float = DEFAULT_CENTRAL_ANGLE_DEGREES,
) -> CandidateArcCenters:
    normalized_angle_deg = _normalize_central_angle_deg(central_angle_deg)
    central_angle_radians = math.radians(normalized_angle_deg)
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
            central_angle_degrees=normalized_angle_deg,
            central_angle_radians=central_angle_radians,
            center_a_xy=port_a_xy,
            center_b_xy=port_b_xy,
        )

    midpoint_xy = (
        (port_a_xy[0] + port_b_xy[0]) / 2.0,
        (port_a_xy[1] + port_b_xy[1]) / 2.0,
    )
    half_chord_km = chord_length_km / 2.0
    sin_half = math.sin(central_angle_radians / 2.0)
    if abs(sin_half) <= EPS:
        raise ValueError(f"Invalid central_angle_deg={central_angle_deg!r}")
    radius_km = half_chord_km / sin_half
    height_km = math.sqrt(max((radius_km * radius_km) - (half_chord_km * half_chord_km), 0.0))
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
        central_angle_degrees=normalized_angle_deg,
        central_angle_radians=central_angle_radians,
        center_a_xy=(midpoint_xy[0] + offset_xy[0], midpoint_xy[1] + offset_xy[1]),
        center_b_xy=(midpoint_xy[0] - offset_xy[0], midpoint_xy[1] - offset_xy[1]),
    )


def get_leg_arc_config(
    port_a: RouteArcPort | tuple[float, float],
    port_b: RouteArcPort | tuple[float, float],
) -> LegArcConfig:
    port_a_obj = _coerce_route_arc_port(port_a)
    port_b_obj = _coerce_route_arc_port(port_b)
    leg_key = (_route_arc_port_key(port_a_obj), _route_arc_port_key(port_b_obj))
    resolved_override = resolve_leg_arc_override(leg_key[0], leg_key[1])
    override = None if resolved_override is None else resolved_override.override
    configured_side_override = None if override is None else override.side
    applied_side_override = configured_side_override
    if (
        configured_side_override is not None
        and resolved_override is not None
        and resolved_override.reverse_traversal
    ):
        applied_side_override = flip_arc_side(configured_side_override)
    return LegArcConfig(
        leg_key=leg_key,
        central_angle_deg=(
            DEFAULT_CENTRAL_ANGLE_DEGREES
            if override is None or override.central_angle_deg is None
            else _normalize_central_angle_deg(override.central_angle_deg)
        ),
        side_override=applied_side_override,
        configured_side_override=configured_side_override,
        override_key=(None if resolved_override is None else resolved_override.stored_key),
        override_reverse_traversal=(
            False if resolved_override is None else resolved_override.reverse_traversal
        ),
        angle_source=("default" if override is None or override.central_angle_deg is None else "override"),
    )


def choose_maritime_side_center(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    *,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
    central_angle_deg: float = DEFAULT_CENTRAL_ANGLE_DEGREES,
    side_override: str | None = None,
) -> tuple[float, float]:
    geometry, _ = _resolve_leg_arc_geometry(
        port_a=RouteArcPort(name="Port A", latlon=port_a_latlon),
        port_b=RouteArcPort(name="Port B", latlon=port_b_latlon),
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
        clutter_points_latlon=clutter_points_latlon,
        n_points=n_points,
        config=LegArcConfig(
            leg_key=normalize_directional_leg_key("Port A", "Port B"),
            central_angle_deg=central_angle_deg,
            side_override=normalize_arc_side(side_override),
            configured_side_override=normalize_arc_side(side_override),
            override_key=None,
            override_reverse_traversal=False,
            angle_source="manual" if central_angle_deg != DEFAULT_CENTRAL_ANGLE_DEGREES else "default",
        ),
    )
    return geometry.center_latlon


def choose_arc_center_automatically(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    *,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
    central_angle_deg: float = DEFAULT_CENTRAL_ANGLE_DEGREES,
) -> tuple[float, float]:
    construction = compute_candidate_arc_centers(
        port_a_latlon,
        port_b_latlon,
        central_angle_deg=central_angle_deg,
    )
    if construction.radius_km <= EPS:
        return construction.center_a_latlon

    context_latlon = _prepare_route_context_path(
        port_a_latlon=port_a_latlon,
        port_b_latlon=port_b_latlon,
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
    )
    context_xy = tuple(construction.projection.project(point) for point in context_latlon)
    clutter_xy = tuple(
        construction.projection.project((float(point[0]), float(point[1])))
        for point in _dedupe_latlon(clutter_points_latlon)
    )
    scores = (
        _score_candidate_center(
            construction=construction,
            center_xy=construction.center_a_xy,
            route_context_xy=context_xy,
            clutter_points_xy=clutter_xy,
            n_points=n_points,
        ),
        _score_candidate_center(
            construction=construction,
            center_xy=construction.center_b_xy,
            route_context_xy=context_xy,
            clutter_points_xy=clutter_xy,
            n_points=n_points,
        ),
    )
    chosen = min(scores, key=_candidate_sort_key)
    return chosen.center_latlon


def apply_side_override_if_present(
    candidates: Sequence[_ArcCandidateScore],
    side_override: str | None,
) -> _ArcCandidateScore | None:
    side = normalize_arc_side(side_override)
    if side is None:
        return None
    for candidate in candidates:
        if candidate.arc_side == side:
            return candidate
    return None


def choose_arc_center_for_leg(
    port_a: RouteArcPort | tuple[float, float],
    port_b: RouteArcPort | tuple[float, float],
    *,
    previous_port: RouteArcPort | tuple[float, float] | None = None,
    next_port: RouteArcPort | tuple[float, float] | None = None,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
) -> tuple[float, float]:
    geometry = build_arc_for_leg(
        port_a,
        port_b,
        previous_port=previous_port,
        next_port=next_port,
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
        clutter_points_latlon=clutter_points_latlon,
        n_points=n_points,
    )
    return geometry.center_latlon


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


def sample_leg_arc(
    port_a: RouteArcPort | tuple[float, float],
    port_b: RouteArcPort | tuple[float, float],
    center_latlon: tuple[float, float],
    *,
    n_points: int = DEFAULT_ARC_POINTS,
) -> tuple[tuple[float, float], ...]:
    port_a_latlon = _coerce_route_arc_port(port_a).latlon
    port_b_latlon = _coerce_route_arc_port(port_b).latlon
    return sample_circular_arc(
        port_a_latlon,
        port_b_latlon,
        center_latlon,
        n_points=n_points,
    )


def build_port_to_port_arc(
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    *,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
    central_angle_deg: float = DEFAULT_CENTRAL_ANGLE_DEGREES,
    side_override: str | None = None,
    leg_key: tuple[str, str] | None = None,
) -> CircularArcGeometry:
    geometry, _ = _resolve_leg_arc_geometry(
        port_a=RouteArcPort(name="Port A", latlon=port_a_latlon, key=(None if leg_key is None else leg_key[0])),
        port_b=RouteArcPort(name="Port B", latlon=port_b_latlon, key=(None if leg_key is None else leg_key[1])),
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
        clutter_points_latlon=clutter_points_latlon,
        n_points=n_points,
        config=LegArcConfig(
            leg_key=(
                normalize_port_identifier("Port A" if leg_key is None else leg_key[0]),
                normalize_port_identifier("Port B" if leg_key is None else leg_key[1]),
            ),
            central_angle_deg=central_angle_deg,
            side_override=normalize_arc_side(side_override),
            configured_side_override=normalize_arc_side(side_override),
            override_key=None,
            override_reverse_traversal=False,
            angle_source="manual" if central_angle_deg != DEFAULT_CENTRAL_ANGLE_DEGREES else "default",
        ),
    )
    return geometry


def build_leg_arc(
    port_a: RouteArcPort | tuple[float, float],
    port_b: RouteArcPort | tuple[float, float],
    *,
    previous_port: RouteArcPort | tuple[float, float] | None = None,
    next_port: RouteArcPort | tuple[float, float] | None = None,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
) -> CircularArcGeometry:
    port_a_obj = _coerce_route_arc_port(port_a)
    port_b_obj = _coerce_route_arc_port(port_b)
    geometry, _ = _resolve_leg_arc_geometry(
        port_a=port_a_obj,
        port_b=port_b_obj,
        previous_port=None if previous_port is None else _coerce_route_arc_port(previous_port),
        next_port=None if next_port is None else _coerce_route_arc_port(next_port),
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
        clutter_points_latlon=clutter_points_latlon,
        n_points=n_points,
        config=get_leg_arc_config(port_a_obj, port_b_obj),
    )
    return geometry


def build_arc_for_leg(
    port_a: RouteArcPort | tuple[float, float],
    port_b: RouteArcPort | tuple[float, float],
    *,
    previous_port: RouteArcPort | tuple[float, float] | None = None,
    next_port: RouteArcPort | tuple[float, float] | None = None,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
) -> CircularArcGeometry:
    return build_leg_arc(
        port_a,
        port_b,
        previous_port=previous_port,
        next_port=next_port,
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
        clutter_points_latlon=clutter_points_latlon,
        n_points=n_points,
    )


def build_leg_arc_debug_payload(
    port_a: RouteArcPort | tuple[float, float],
    port_b: RouteArcPort | tuple[float, float],
    *,
    previous_port: RouteArcPort | tuple[float, float] | None = None,
    next_port: RouteArcPort | tuple[float, float] | None = None,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int = DEFAULT_ARC_POINTS,
) -> LegArcDebugPayload:
    port_a_obj = _coerce_route_arc_port(port_a)
    port_b_obj = _coerce_route_arc_port(port_b)
    _, payload = _resolve_leg_arc_geometry(
        port_a=port_a_obj,
        port_b=port_b_obj,
        previous_port=None if previous_port is None else _coerce_route_arc_port(previous_port),
        next_port=None if next_port is None else _coerce_route_arc_port(next_port),
        reference_path_latlon=reference_path_latlon,
        route_context_latlon=route_context_latlon,
        clutter_points_latlon=clutter_points_latlon,
        n_points=n_points,
        config=get_leg_arc_config(port_a_obj, port_b_obj),
    )
    return payload


def build_route_arcs_from_port_sequence(
    port_sequence: Sequence[RouteArcPort | tuple[float, float]],
    *,
    reference_path_builder: LegReferencePathBuilder | None = None,
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points_per_leg: int = DEFAULT_ARC_POINTS,
    debug_leg_key: tuple[str, str] | None = None,
) -> tuple[CircularArcGeometry, ...]:
    ports = [_coerce_route_arc_port(port, default_name=f"Port {index}") for index, port in enumerate(port_sequence)]
    if len(ports) < 2:
        return ()

    debug_key = None if debug_leg_key is None else normalize_leg_key(debug_leg_key[0], debug_leg_key[1])
    arcs: list[CircularArcGeometry] = []
    for index in range(1, len(ports)):
        port_a = ports[index - 1]
        port_b = ports[index]
        previous_port = None if index < 2 else ports[index - 2]
        next_port = None if index + 1 >= len(ports) else ports[index + 1]
        reference_path = (
            tuple(reference_path_builder(port_a, port_b))
            if reference_path_builder is not None
            else ()
        )
        geometry, payload = _resolve_leg_arc_geometry(
            port_a=port_a,
            port_b=port_b,
            previous_port=previous_port,
            next_port=next_port,
            reference_path_latlon=reference_path,
            clutter_points_latlon=clutter_points_latlon,
            n_points=n_points_per_leg,
            config=get_leg_arc_config(port_a, port_b),
        )
        if (
            debug_key is not None
            and normalize_leg_key(payload.leg_key[0], payload.leg_key[1]) == debug_key
        ):
            _log_leg_arc_debug_payload(payload)
        arcs.append(geometry)
    return tuple(arcs)


def build_route_arc_path(
    port_sequence: Sequence[RouteArcPort | tuple[float, float]],
    *,
    reference_path_builder: LegReferencePathBuilder | None = None,
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points_per_leg: int = DEFAULT_ARC_POINTS,
    debug_leg_key: tuple[str, str] | None = None,
) -> tuple[tuple[float, float], ...]:
    ports = [_coerce_route_arc_port(port, default_name=f"Port {index}") for index, port in enumerate(port_sequence)]
    if not ports:
        return ()
    if len(ports) == 1:
        return (ports[0].latlon,)

    route_path_latlon: list[tuple[float, float]] = []
    route_arcs = build_route_arcs_from_port_sequence(
        ports,
        reference_path_builder=reference_path_builder,
        clutter_points_latlon=clutter_points_latlon,
        n_points_per_leg=n_points_per_leg,
        debug_leg_key=debug_leg_key,
    )
    for index, leg_arc in enumerate(route_arcs):
        leg_points = list(leg_arc.arc_points_latlon)
        if index > 0:
            leg_points = leg_points[1:]
        route_path_latlon.extend(leg_points)
    return tuple(route_path_latlon)


def build_route_from_port_sequence(
    port_sequence: Sequence[RouteArcPort | tuple[float, float]],
    *,
    reference_path_builder: LegReferencePathBuilder | None = None,
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points_per_leg: int = DEFAULT_ARC_POINTS,
    debug_leg_key: tuple[str, str] | None = None,
) -> tuple[tuple[float, float], ...]:
    return build_route_arc_path(
        port_sequence,
        reference_path_builder=reference_path_builder,
        clutter_points_latlon=clutter_points_latlon,
        n_points_per_leg=n_points_per_leg,
        debug_leg_key=debug_leg_key,
    )


def build_route_arc_debug_payloads(
    port_sequence: Sequence[RouteArcPort | tuple[float, float]],
    *,
    reference_path_builder: LegReferencePathBuilder | None = None,
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points_per_leg: int = DEFAULT_ARC_POINTS,
    debug_leg_key: tuple[str, str] | None = None,
) -> tuple[LegArcDebugPayload, ...]:
    """Return debug payloads for all route legs, or one physical leg if filtered."""
    ports = [_coerce_route_arc_port(port, default_name=f"Port {index}") for index, port in enumerate(port_sequence)]
    if len(ports) < 2:
        return ()

    debug_key = None if debug_leg_key is None else normalize_leg_key(debug_leg_key[0], debug_leg_key[1])
    payloads: list[LegArcDebugPayload] = []
    for index in range(1, len(ports)):
        port_a = ports[index - 1]
        port_b = ports[index]
        previous_port = None if index < 2 else ports[index - 2]
        next_port = None if index + 1 >= len(ports) else ports[index + 1]
        reference_path = (
            tuple(reference_path_builder(port_a, port_b))
            if reference_path_builder is not None
            else ()
        )
        _, payload = _resolve_leg_arc_geometry(
            port_a=port_a,
            port_b=port_b,
            previous_port=previous_port,
            next_port=next_port,
            reference_path_latlon=reference_path,
            clutter_points_latlon=clutter_points_latlon,
            n_points=n_points_per_leg,
            config=get_leg_arc_config(port_a, port_b),
        )
        if (
            debug_key is None
            or normalize_leg_key(payload.leg_key[0], payload.leg_key[1]) == debug_key
        ):
            payloads.append(payload)
    return tuple(payloads)


def _resolve_leg_arc_geometry(
    *,
    port_a: RouteArcPort,
    port_b: RouteArcPort,
    previous_port: RouteArcPort | None = None,
    next_port: RouteArcPort | None = None,
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    clutter_points_latlon: Sequence[tuple[float, float]] = (),
    n_points: int,
    config: LegArcConfig,
) -> tuple[CircularArcGeometry, LegArcDebugPayload]:
    construction = compute_candidate_arc_centers(
        port_a.latlon,
        port_b.latlon,
        central_angle_deg=config.central_angle_deg,
    )
    if construction.radius_km <= EPS:
        point = (float(port_a.latlon[0]), float(port_a.latlon[1]))
        geometry = CircularArcGeometry(
            port_a_key=config.leg_key[0],
            port_b_key=config.leg_key[1],
            port_a_latlon=point,
            port_b_latlon=point,
            center_latlon=point,
            radius_km=0.0,
            central_angle_degrees=config.central_angle_deg,
            central_angle_radians=0.0,
            midpoint_latlon=point,
            arc_points_latlon=(point,),
            reference_side_distance_km=0.0,
            side=None,
            side_source=("manual" if config.side_override is not None else "auto"),
            angle_source=config.angle_source,
        )
        payload = LegArcDebugPayload(
            leg_key=config.leg_key,
            port_a_name=port_a.name,
            port_b_name=port_b.name,
            port_a_latlon=point,
            port_b_latlon=point,
            central_angle_deg=config.central_angle_deg,
            angle_source=config.angle_source,
            side_override=config.side_override,
            configured_side_override=config.configured_side_override,
            override_key=config.override_key,
            override_reverse_traversal=config.override_reverse_traversal,
            side_source=("manual" if config.side_override is not None else "auto"),
            chosen_arc_side=None,
            chosen_center_side=None,
            candidate_centers_latlon=(point, point),
            chosen_center_latlon=point,
            route_context_latlon=(point,),
            reference_path_latlon=(point,),
            candidates=(),
        )
        return geometry, payload

    prepared_reference_path = tuple(_dedupe_latlon(reference_path_latlon))
    prepared_route_context = tuple(
        _prepare_route_context_path(
            port_a_latlon=port_a.latlon,
            port_b_latlon=port_b.latlon,
            reference_path_latlon=prepared_reference_path,
            route_context_latlon=route_context_latlon,
            previous_port=previous_port,
            next_port=next_port,
        )
    )
    route_context_xy = tuple(construction.projection.project(point) for point in prepared_route_context)
    clutter_points_xy = tuple(
        construction.projection.project((float(point[0]), float(point[1])))
        for point in _dedupe_latlon(clutter_points_latlon)
    )
    candidates = (
        _score_candidate_center(
            construction=construction,
            center_xy=construction.center_a_xy,
            route_context_xy=route_context_xy,
            clutter_points_xy=clutter_points_xy,
            n_points=n_points,
        ),
        _score_candidate_center(
            construction=construction,
            center_xy=construction.center_b_xy,
            route_context_xy=route_context_xy,
            clutter_points_xy=clutter_points_xy,
            n_points=n_points,
        ),
    )
    chosen = apply_side_override_if_present(candidates, config.side_override)
    side_source = "manual" if chosen is not None and config.side_override is not None else "auto"
    if chosen is None:
        chosen = min(candidates, key=_candidate_sort_key)

    arc_points_latlon = [construction.projection.unproject(point_xy) for point_xy in chosen.arc_points_xy]
    arc_points_latlon[0] = (float(port_a.latlon[0]), float(port_a.latlon[1]))
    arc_points_latlon[-1] = (float(port_b.latlon[0]), float(port_b.latlon[1]))
    geometry = CircularArcGeometry(
        port_a_key=config.leg_key[0],
        port_b_key=config.leg_key[1],
        port_a_latlon=(float(port_a.latlon[0]), float(port_a.latlon[1])),
        port_b_latlon=(float(port_b.latlon[0]), float(port_b.latlon[1])),
        center_latlon=chosen.center_latlon,
        radius_km=construction.radius_km,
        central_angle_degrees=construction.central_angle_degrees,
        central_angle_radians=construction.central_angle_radians,
        midpoint_latlon=chosen.midpoint_latlon,
        arc_points_latlon=tuple(arc_points_latlon),
        reference_side_distance_km=_context_side_bias(
            construction.port_a_xy,
            construction.port_b_xy,
            route_context_xy,
        ),
        side=chosen.arc_side,
        side_source=side_source,
        angle_source=config.angle_source,
    )
    payload = LegArcDebugPayload(
        leg_key=config.leg_key,
        port_a_name=port_a.name,
        port_b_name=port_b.name,
        port_a_latlon=geometry.port_a_latlon,
        port_b_latlon=geometry.port_b_latlon,
        central_angle_deg=construction.central_angle_degrees,
        angle_source=config.angle_source,
        side_override=config.side_override,
        configured_side_override=config.configured_side_override,
        override_key=config.override_key,
        override_reverse_traversal=config.override_reverse_traversal,
        side_source=side_source,
        chosen_arc_side=chosen.arc_side,
        chosen_center_side=chosen.center_side,
        candidate_centers_latlon=(construction.center_a_latlon, construction.center_b_latlon),
        chosen_center_latlon=chosen.center_latlon,
        route_context_latlon=prepared_route_context,
        reference_path_latlon=prepared_reference_path,
        candidates=tuple(
            LegArcCandidateDebug(
                center_latlon=candidate.center_latlon,
                center_side=candidate.center_side,
                arc_side=candidate.arc_side,
                default_side_penalty=candidate.default_side_penalty,
                midpoint_latlon=candidate.midpoint_latlon,
                side_match_penalty=candidate.side_match_penalty,
                midpoint_context_distance_km=candidate.midpoint_context_distance_km,
                mean_context_distance_km=candidate.mean_context_distance_km,
                nearest_clutter_distance_km=candidate.nearest_clutter_distance_km,
            )
            for candidate in candidates
        ),
    )
    return geometry, payload


def _score_candidate_center(
    *,
    construction: CandidateArcCenters,
    center_xy: tuple[float, float],
    route_context_xy: Sequence[tuple[float, float]],
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
    midpoint_context_distance_km = _distance_point_to_polyline(midpoint_xy, route_context_xy)
    mean_context_distance_km = _mean_distance_to_polyline(arc_points_xy[1:-1], route_context_xy)
    nearest_clutter_distance_km = _nearest_point_distance(midpoint_xy, clutter_points_xy)
    inland_centroid_distance_km = 0.0
    if _use_brazil_inland_centroid_bias(construction):
        inland_centroid_xy = construction.projection.project(BRAZIL_INLAND_CENTROID_LATLON)
        inland_centroid_distance_km = _vector_length(_subtract(midpoint_xy, inland_centroid_xy))
    context_side_bias_km = _context_side_bias(
        construction.port_a_xy,
        construction.port_b_xy,
        route_context_xy,
    )
    midpoint_side_distance_km = _signed_line_distance(
        construction.port_a_xy,
        construction.port_b_xy,
        midpoint_xy,
    )
    side_match_penalty = 0
    if abs(context_side_bias_km) >= AUTO_SIDE_BIAS_THRESHOLD_KM:
        if context_side_bias_km * midpoint_side_distance_km < 0.0:
            side_match_penalty = 1
    default_side_penalty = 0 if _side_name(midpoint_side_distance_km) == DEFAULT_AUTO_ARC_SIDE else 1

    return _ArcCandidateScore(
        center_xy=center_xy,
        center_latlon=construction.projection.unproject(center_xy),
        arc_points_xy=arc_points_xy,
        midpoint_xy=midpoint_xy,
        midpoint_latlon=construction.projection.unproject(midpoint_xy),
        center_side=_side_name(
            _signed_line_distance(construction.port_a_xy, construction.port_b_xy, center_xy),
        ),
        arc_side=_side_name(midpoint_side_distance_km),
        default_side_penalty=default_side_penalty,
        side_match_penalty=side_match_penalty,
        midpoint_context_distance_km=midpoint_context_distance_km,
        mean_context_distance_km=mean_context_distance_km,
        nearest_clutter_distance_km=nearest_clutter_distance_km,
        inland_centroid_distance_km=inland_centroid_distance_km,
    )


def _candidate_sort_key(score: _ArcCandidateScore) -> tuple[float, float, float, float, float, float]:
    return (
        -float(score.inland_centroid_distance_km),
        float(score.side_match_penalty),
        float(score.default_side_penalty),
        float(score.midpoint_context_distance_km),
        float(score.mean_context_distance_km),
        -float(score.nearest_clutter_distance_km),
    )


def _use_brazil_inland_centroid_bias(construction: CandidateArcCenters) -> bool:
    endpoints = (
        construction.projection.unproject(construction.port_a_xy),
        construction.projection.unproject(construction.port_b_xy),
    )
    for lat, lon in endpoints:
        if not (
            BRAZIL_ARC_BIAS_LAT_RANGE[0] <= float(lat) <= BRAZIL_ARC_BIAS_LAT_RANGE[1]
            and BRAZIL_ARC_BIAS_LON_RANGE[0] <= float(lon) <= BRAZIL_ARC_BIAS_LON_RANGE[1]
        ):
            return False
    return True


def _prepare_route_context_path(
    *,
    port_a_latlon: tuple[float, float],
    port_b_latlon: tuple[float, float],
    reference_path_latlon: Sequence[tuple[float, float]] = (),
    route_context_latlon: Sequence[tuple[float, float]] = (),
    previous_port: RouteArcPort | None = None,
    next_port: RouteArcPort | None = None,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if previous_port is not None:
        points.append((float(previous_port.latlon[0]), float(previous_port.latlon[1])))
    if route_context_latlon:
        points.extend(_dedupe_latlon(route_context_latlon))
    elif reference_path_latlon:
        points.extend(_dedupe_latlon(reference_path_latlon))
    else:
        points.extend(
            [
                (float(port_a_latlon[0]), float(port_a_latlon[1])),
                (float(port_b_latlon[0]), float(port_b_latlon[1])),
            ]
        )
    if next_port is not None:
        points.append((float(next_port.latlon[0]), float(next_port.latlon[1])))
    return _dedupe_latlon(points)


def _context_side_bias(
    port_a_xy: tuple[float, float],
    port_b_xy: tuple[float, float],
    route_context_xy: Sequence[tuple[float, float]],
) -> float:
    signed_distances = [
        _signed_line_distance(port_a_xy, port_b_xy, point_xy)
        for point_xy in route_context_xy
    ]
    weighted = [distance for distance in signed_distances if abs(distance) >= MIN_SIDE_DISTANCE_KM]
    if not weighted:
        return 0.0
    return sum(weighted) / len(weighted)


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


def _side_name(side_distance_km: float) -> str:
    if side_distance_km > EPS:
        return "left"
    if side_distance_km < -EPS:
        return "right"
    return "center"


def _normalize_central_angle_deg(value: float) -> float:
    angle = float(value)
    if angle <= 0.0 or angle >= 180.0:
        raise ValueError(f"central_angle_deg must be between 0 and 180, got {value!r}")
    return angle


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


def _coerce_route_arc_port(
    port: RouteArcPort | tuple[float, float],
    *,
    default_name: str = "Port",
) -> RouteArcPort:
    if isinstance(port, RouteArcPort):
        return RouteArcPort(
            name=str(port.name),
            latlon=(float(port.latlon[0]), float(port.latlon[1])),
            key=(None if port.key is None else normalize_port_identifier(port.key)),
        )
    return RouteArcPort(
        name=default_name,
        latlon=(float(port[0]), float(port[1])),
        key=normalize_port_identifier(default_name),
    )


def _route_arc_port_key(port: RouteArcPort) -> str:
    return normalize_port_identifier(port.key or port.name)


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


def _log_leg_arc_debug_payload(payload: LegArcDebugPayload) -> None:
    _log.info(
        (
            "Maritime arc debug leg=%s->%s angle_deg=%.2f angle_source=%s side_override=%s "
            "configured_side_override=%s override_key=%s override_reverse_traversal=%s side_source=%s "
            "chosen_arc_side=%s chosen_center_side=%s chosen_center=%s candidates=%s"
        ),
        payload.leg_key[0],
        payload.leg_key[1],
        payload.central_angle_deg,
        payload.angle_source,
        payload.side_override,
        payload.configured_side_override,
        payload.override_key,
        payload.override_reverse_traversal,
        payload.side_source,
        payload.chosen_arc_side,
        payload.chosen_center_side,
        payload.chosen_center_latlon,
        [
            {
                "center_side": candidate.center_side,
                "arc_side": candidate.arc_side,
                "default_side_penalty": candidate.default_side_penalty,
                "center": candidate.center_latlon,
                "midpoint": candidate.midpoint_latlon,
                "side_penalty": candidate.side_match_penalty,
                "mid_context_km": round(candidate.midpoint_context_distance_km, 3),
                "mean_context_km": round(candidate.mean_context_distance_km, 3),
                "nearest_clutter_km": round(candidate.nearest_clutter_distance_km, 3),
            }
            for candidate in payload.candidates
        ],
    )
