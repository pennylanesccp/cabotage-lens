from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any, Iterable, Sequence

from modules.infra.log_manager import get_logger

from app.heatmap.config import (
    HEATMAP_BRAZIL_BOUNDARY_PATH,
    HEATMAP_COLOR_MID,
    HEATMAP_COLOR_NEGATIVE,
    HEATMAP_COLOR_POSITIVE,
    HEATMAP_SURFACE_ALPHA,
    HEATMAP_SURFACE_CELL_SIZE_DEGREES,
    HEATMAP_SURFACE_COLOR_QUANTILE,
    HEATMAP_SURFACE_ELEVATION_BOOST,
    HEATMAP_SURFACE_ELEVATION_FLOOR_RATIO,
    HEATMAP_SURFACE_ELEVATION_GAMMA,
    HEATMAP_SURFACE_ELEVATION_QUANTILE,
    HEATMAP_SURFACE_INTERPOLATION_RADIUS_FACTOR,
    HEATMAP_SURFACE_INTERPOLATION_RADIUS_MAX_KM,
    HEATMAP_SURFACE_INTERPOLATION_RADIUS_MIN_KM,
    HEATMAP_SURFACE_INTERPOLATION_RADIUS_QUANTILE,
    HEATMAP_SURFACE_MAX_ELEVATION_M,
)
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapSurface, HeatmapSurfaceCell

_EARTH_RADIUS_KM = 6_371.0
_GEOMETRY_EPSILON = 1e-9
_TRIANGLE_EDGE_TOLERANCE = 1e-7
_Sample = tuple[str, str, float, float, float, float]
_GeometrySample = tuple[str, str, float, float]
_Coordinate = tuple[float, float]
_HullPolygon = tuple[_Coordinate, ...]
_Cell = tuple[_HullPolygon, float, float]
_PreparedTriangle = tuple[int, int, int, float, float, float, float, float]

_log = get_logger(__name__)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def _interpolate_channel(start: Iterable[int], end: Iterable[int], ratio: float) -> tuple[int, int, int]:
    weight = _clamp(ratio, 0.0, 1.0)
    start_values = list(start)
    end_values = list(end)
    return tuple(int(round(s + ((e - s) * weight))) for s, e in zip(start_values, end_values))  # type: ignore[return-value]


def _color_for_value(value: float, negative_scale: float, positive_scale: float) -> tuple[int, int, int, int]:
    numeric_value = float(value)
    if numeric_value == 0.0:
        rgb = tuple(HEATMAP_COLOR_MID)
    elif numeric_value > 0.0:
        if positive_scale <= 0.0:
            rgb = tuple(HEATMAP_COLOR_MID)
        else:
            rgb = _interpolate_channel(HEATMAP_COLOR_MID, HEATMAP_COLOR_POSITIVE, numeric_value / float(positive_scale))
    else:
        if negative_scale <= 0.0:
            rgb = tuple(HEATMAP_COLOR_MID)
        else:
            rgb = _interpolate_channel(HEATMAP_COLOR_MID, HEATMAP_COLOR_NEGATIVE, abs(numeric_value) / float(negative_scale))
    return (*rgb, HEATMAP_SURFACE_ALPHA)


def _robust_abs_scale(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 1.0
    ordered = sorted(abs(float(value)) for value in values)
    if not ordered:
        return 1.0
    index = min(max(int(round((len(ordered) - 1) * quantile)), 0), len(ordered) - 1)
    candidate = ordered[index]
    return candidate if candidate > 0.0 else 1.0


def _robust_side_scale(values: Sequence[float], quantile: float, *, positive: bool) -> float:
    filtered = [abs(float(value)) for value in values if (float(value) > 0.0 if positive else float(value) < 0.0)]
    if not filtered:
        return 0.0
    ordered = sorted(filtered)
    index = min(max(int(round((len(ordered) - 1) * quantile)), 0), len(ordered) - 1)
    candidate = ordered[index]
    return candidate if candidate > 0.0 else 0.0


def _quantile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = min(max(int(round((len(ordered) - 1) * quantile)), 0), len(ordered) - 1)
    return float(ordered[index])


def _metric_percentage(point: HeatmapPoint, metric: str) -> float:
    raw_value = point.cost_savings_pct if metric == "cost" else point.emissions_savings_pct
    if raw_value is not None:
        return float(raw_value)

    baseline = point.road_cost_r if metric == "cost" else point.road_emissions_kg
    absolute = point.cost_delta_r if metric == "cost" else point.emissions_delta_kg
    if not baseline:
        return 0.0
    return (float(absolute) / float(baseline)) * 100.0


def _metric_absolute(point: HeatmapPoint, metric: str) -> float:
    return float(point.cost_delta_r if metric == "cost" else point.emissions_delta_kg)


def _align_quantitative_sign(percentage_value: float, quantitative_value: float) -> float:
    value = float(quantitative_value)
    if value == 0.0:
        return 0.0
    direction = float(percentage_value)
    if direction == 0.0:
        return value
    return math.copysign(abs(value), direction)


def _dataset_signature(dataset: HeatmapDataset, metric: str) -> tuple[_Sample, ...]:
    return tuple(
        sorted(
            (
                (
                    point.destiny_name,
                    str(point.destiny_uf or "").strip(),
                    round(float(point.destiny_lat), 4),
                    round(float(point.destiny_lon), 4),
                    round(_metric_percentage(point, metric), 4),
                    round(_metric_absolute(point, metric), 4),
                )
                for point in dataset.points
            ),
            key=lambda item: (item[0], item[1], item[2], item[3]),
        )
    )


@lru_cache(maxsize=1)
def load_brazil_boundary_geojson() -> dict[str, Any]:
    with HEATMAP_BRAZIL_BOUNDARY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _extract_rings(geometry: dict[str, Any]) -> list[tuple[tuple[float, float], ...]]:
    geometry_type = str(geometry.get("type") or "").strip()
    coordinates = geometry.get("coordinates") or []
    rings: list[tuple[tuple[float, float], ...]] = []

    if geometry_type == "Polygon":
        if coordinates:
            rings.append(tuple((float(lon), float(lat)) for lon, lat in coordinates[0]))
        return rings

    if geometry_type == "MultiPolygon":
        for polygon in coordinates:
            if polygon:
                rings.append(tuple((float(lon), float(lat)) for lon, lat in polygon[0]))
        return rings

    return rings


def _point_on_segment(lon: float, lat: float, start: _Coordinate, end: _Coordinate) -> bool:
    start_lon, start_lat = start
    end_lon, end_lat = end
    cross = ((lon - start_lon) * (end_lat - start_lat)) - ((lat - start_lat) * (end_lon - start_lon))
    if abs(cross) > _GEOMETRY_EPSILON:
        return False
    return (
        min(start_lon, end_lon) - _GEOMETRY_EPSILON <= lon <= max(start_lon, end_lon) + _GEOMETRY_EPSILON
        and min(start_lat, end_lat) - _GEOMETRY_EPSILON <= lat <= max(start_lat, end_lat) + _GEOMETRY_EPSILON
    )


def _point_in_ring(lon: float, lat: float, ring: Sequence[_Coordinate]) -> bool:
    inside = False
    if len(ring) < 3:
        return False

    prev_lon, prev_lat = ring[-1]
    for curr_lon, curr_lat in ring:
        if _point_on_segment(lon, lat, (prev_lon, prev_lat), (curr_lon, curr_lat)):
            return True
        intersects = ((curr_lat > lat) != (prev_lat > lat)) and (
            lon < ((prev_lon - curr_lon) * (lat - curr_lat) / ((prev_lat - curr_lat) or 1e-12)) + curr_lon
        )
        if intersects:
            inside = not inside
        prev_lon, prev_lat = curr_lon, curr_lat
    return inside


def _coordinate_cross(origin: _Coordinate, a: _Coordinate, b: _Coordinate) -> float:
    return ((a[0] - origin[0]) * (b[1] - origin[1])) - ((a[1] - origin[1]) * (b[0] - origin[0]))


def _convex_hull(points: Sequence[_Coordinate]) -> _HullPolygon:
    unique_points = sorted({(float(lon), float(lat)) for lon, lat in points})
    if len(unique_points) <= 1:
        return tuple(unique_points)

    lower: list[_Coordinate] = []
    for point in unique_points:
        while len(lower) >= 2 and _coordinate_cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)

    upper: list[_Coordinate] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and _coordinate_cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)

    return tuple(lower[:-1] + upper[:-1])


@lru_cache(maxsize=24)
def _hull_cells(hull_polygon: _HullPolygon) -> tuple[_Cell, ...]:
    if len(hull_polygon) < 3:
        return tuple()

    all_lons = [coord[0] for coord in hull_polygon]
    all_lats = [coord[1] for coord in hull_polygon]
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)
    step = float(HEATMAP_SURFACE_CELL_SIZE_DEGREES)

    cells: list[_Cell] = []
    lon = min_lon
    while lon < max_lon:
        lat = min_lat
        while lat < max_lat:
            center_lon = lon + (step / 2.0)
            center_lat = lat + (step / 2.0)
            if _point_in_ring(center_lon, center_lat, hull_polygon):
                polygon = (
                    (lon, lat),
                    (lon + step, lat),
                    (lon + step, lat + step),
                    (lon, lat + step),
                )
                cells.append((polygon, center_lat, center_lon))
            lat += step
        lon += step
    return tuple(cells)


def _distance_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    x = math.radians(lon_b - lon_a) * math.cos(math.radians((lat_a + lat_b) / 2.0))
    y = math.radians(lat_b - lat_a)
    return math.hypot(x, y) * _EARTH_RADIUS_KM


def _interpolation_radius_km(samples: Sequence[_Sample]) -> float:
    if len(samples) <= 1:
        return float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_MAX_KM)

    nearest_neighbor_distances: list[float] = []
    for index, sample in enumerate(samples):
        nearest_distance = float("inf")
        for other_index, other in enumerate(samples):
            if index == other_index:
                continue
            distance = _distance_km(float(sample[2]), float(sample[3]), float(other[2]), float(other[3]))
            if distance < nearest_distance:
                nearest_distance = distance
        if math.isfinite(nearest_distance):
            nearest_neighbor_distances.append(float(nearest_distance))

    if not nearest_neighbor_distances:
        return float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_MAX_KM)

    baseline = _quantile(nearest_neighbor_distances, float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_QUANTILE))
    radius = baseline * float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_FACTOR)
    return _clamp(
        radius,
        float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_MIN_KM),
        float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_MAX_KM),
    )


def _geometry_signature(points_signature: tuple[_Sample, ...]) -> tuple[_GeometrySample, ...]:
    return tuple((sample[0], sample[1], sample[2], sample[3]) for sample in points_signature)


def _unique_geometry_samples(geometry_signature: tuple[_GeometrySample, ...]) -> tuple[_GeometrySample, ...]:
    seen: set[tuple[float, float]] = set()
    unique_samples: list[_GeometrySample] = []
    for sample in geometry_signature:
        key = (sample[2], sample[3])
        if key in seen:
            continue
        seen.add(key)
        unique_samples.append(sample)
    return tuple(unique_samples)


def _value_samples(
    points_signature: tuple[_Sample, ...],
    geometry_samples: Sequence[_GeometrySample],
) -> tuple[_Sample, ...]:
    aggregated: dict[tuple[float, float], tuple[float, float, int]] = {}
    for sample in points_signature:
        key = (sample[2], sample[3])
        pct_sum, abs_sum, count = aggregated.get(key, (0.0, 0.0, 0))
        aggregated[key] = (
            pct_sum + float(sample[4]),
            abs_sum + float(sample[5]),
            count + 1,
        )

    value_samples: list[_Sample] = []
    for name, uf, lat, lon in geometry_samples:
        pct_sum, abs_sum, count = aggregated[(lat, lon)]
        divisor = max(count, 1)
        value_samples.append((name, uf, lat, lon, pct_sum / divisor, abs_sum / divisor))
    return tuple(value_samples)


def _super_triangle(points: Sequence[_Coordinate]) -> tuple[_Coordinate, _Coordinate, _Coordinate]:
    min_lon = min(point[0] for point in points)
    max_lon = max(point[0] for point in points)
    min_lat = min(point[1] for point in points)
    max_lat = max(point[1] for point in points)
    span = max(max_lon - min_lon, max_lat - min_lat, 1.0)
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0
    return (
        (center_lon - (20.0 * span), center_lat - span),
        (center_lon, center_lat + (20.0 * span)),
        (center_lon + (20.0 * span), center_lat - span),
    )


def _circumcircle_contains(a: _Coordinate, b: _Coordinate, c: _Coordinate, point: _Coordinate) -> bool:
    ax = a[0] - point[0]
    ay = a[1] - point[1]
    bx = b[0] - point[0]
    by = b[1] - point[1]
    cx = c[0] - point[0]
    cy = c[1] - point[1]

    determinant = (
        ((ax * ax) + (ay * ay)) * ((bx * cy) - (cx * by))
        - ((bx * bx) + (by * by)) * ((ax * cy) - (cx * ay))
        + ((cx * cx) + (cy * cy)) * ((ax * by) - (bx * ay))
    )
    orientation = _coordinate_cross(a, b, c)
    if orientation > 0.0:
        return determinant > _GEOMETRY_EPSILON
    if orientation < 0.0:
        return determinant < -_GEOMETRY_EPSILON
    return False


def _triangle_denominator(a: _Coordinate, b: _Coordinate, c: _Coordinate) -> float:
    return ((b[1] - c[1]) * (a[0] - c[0])) + ((c[0] - b[0]) * (a[1] - c[1]))


def _build_delaunay_triangulation(geometry_samples: Sequence[_GeometrySample]) -> tuple[tuple[int, int, int], ...]:
    vertices = [(float(sample[3]), float(sample[2])) for sample in geometry_samples]
    if len(vertices) < 3 or len(_convex_hull(vertices)) < 3:
        return tuple()

    super_triangle = _super_triangle(vertices)
    working_vertices = vertices + list(super_triangle)
    point_count = len(vertices)

    triangles: list[tuple[int, int, int]] = [(point_count, point_count + 1, point_count + 2)]
    for point_index in range(point_count):
        bad_triangles: list[tuple[int, int, int]] = []
        for triangle in triangles:
            a, b, c = (working_vertices[triangle[0]], working_vertices[triangle[1]], working_vertices[triangle[2]])
            if _circumcircle_contains(a, b, c, working_vertices[point_index]):
                bad_triangles.append(triangle)

        edge_counts: dict[tuple[int, int], int] = {}
        for triangle in bad_triangles:
            for edge in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
                edge_key = tuple(sorted(edge))
                edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1

        bad_set = set(bad_triangles)
        triangles = [triangle for triangle in triangles if triangle not in bad_set]
        for edge, count in edge_counts.items():
            if count == 1:
                triangles.append((edge[0], edge[1], point_index))

    unique_triangles: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for triangle in triangles:
        if any(index >= point_count for index in triangle):
            continue
        a, b, c = (working_vertices[triangle[0]], working_vertices[triangle[1]], working_vertices[triangle[2]])
        if abs(_coordinate_cross(a, b, c)) <= _GEOMETRY_EPSILON:
            continue
        triangle_key = tuple(sorted(triangle))
        if triangle_key in seen:
            continue
        seen.add(triangle_key)
        unique_triangles.append(triangle)
    return tuple(unique_triangles)


def _prepare_triangles(geometry_samples: Sequence[_GeometrySample]) -> tuple[_PreparedTriangle, ...]:
    prepared: list[_PreparedTriangle] = []
    for triangle in _build_delaunay_triangulation(geometry_samples):
        i, j, k = triangle
        a = (float(geometry_samples[i][3]), float(geometry_samples[i][2]))
        b = (float(geometry_samples[j][3]), float(geometry_samples[j][2]))
        c = (float(geometry_samples[k][3]), float(geometry_samples[k][2]))
        denominator = _triangle_denominator(a, b, c)
        if abs(denominator) <= _GEOMETRY_EPSILON:
            continue
        prepared.append(
            (
                i,
                j,
                k,
                min(a[0], b[0], c[0]),
                max(a[0], b[0], c[0]),
                min(a[1], b[1], c[1]),
                max(a[1], b[1], c[1]),
                denominator,
            )
        )
    return tuple(prepared)


def _triangle_weights(
    lon: float,
    lat: float,
    triangle: _PreparedTriangle,
    samples: Sequence[_Sample],
) -> tuple[float, float, float] | None:
    i, j, k, min_lon, max_lon, min_lat, max_lat, denominator = triangle
    if (
        lon < (min_lon - _TRIANGLE_EDGE_TOLERANCE)
        or lon > (max_lon + _TRIANGLE_EDGE_TOLERANCE)
        or lat < (min_lat - _TRIANGLE_EDGE_TOLERANCE)
        or lat > (max_lat + _TRIANGLE_EDGE_TOLERANCE)
    ):
        return None

    ax, ay = float(samples[i][3]), float(samples[i][2])
    bx, by = float(samples[j][3]), float(samples[j][2])
    cx, cy = float(samples[k][3]), float(samples[k][2])
    weight_a = (((by - cy) * (lon - cx)) + ((cx - bx) * (lat - cy))) / denominator
    weight_b = (((cy - ay) * (lon - cx)) + ((ax - cx) * (lat - cy))) / denominator
    weight_c = 1.0 - weight_a - weight_b
    return (weight_a, weight_b, weight_c)


def _triangle_gap(weights: tuple[float, float, float]) -> float:
    return max(-min(weights), max(weights) - 1.0, 0.0)


def _interpolate_triangle_values(
    triangle: _PreparedTriangle,
    weights: tuple[float, float, float],
    samples: Sequence[_Sample],
) -> tuple[float, float]:
    i, j, k = triangle[:3]
    percentage_value = (
        (weights[0] * float(samples[i][4]))
        + (weights[1] * float(samples[j][4]))
        + (weights[2] * float(samples[k][4]))
    )
    absolute_value = (
        (weights[0] * float(samples[i][5]))
        + (weights[1] * float(samples[j][5]))
        + (weights[2] * float(samples[k][5]))
    )
    return percentage_value, absolute_value


def _nearest_sample_reference(lat: float, lon: float, samples: Sequence[_Sample]) -> tuple[str, str | None, float]:
    nearest_sample: _Sample | None = None
    nearest_distance = float("inf")
    for sample in samples:
        distance = _distance_km(lat, lon, float(sample[2]), float(sample[3]))
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_sample = sample

    if nearest_sample is None:
        return "", None, 0.0
    return nearest_sample[0], nearest_sample[1] or None, float(nearest_distance)


def _triangulated_interpolate(
    lat: float,
    lon: float,
    samples: Sequence[_Sample],
    triangles: Sequence[_PreparedTriangle],
) -> tuple[float, float, str, str | None, float] | None:
    best_match: tuple[_PreparedTriangle, tuple[float, float, float]] | None = None
    best_gap = float("inf")

    for triangle in triangles:
        weights = _triangle_weights(lon, lat, triangle, samples)
        if weights is None:
            continue
        gap = _triangle_gap(weights)
        if gap <= _TRIANGLE_EDGE_TOLERANCE:
            percentage_value, absolute_value = _interpolate_triangle_values(triangle, weights, samples)
            nearest_name, nearest_uf, nearest_distance = _nearest_sample_reference(lat, lon, samples)
            return percentage_value, absolute_value, nearest_name, nearest_uf, nearest_distance
        if gap < best_gap:
            best_gap = gap
            best_match = (triangle, weights)

    if best_match is None or best_gap > (_TRIANGLE_EDGE_TOLERANCE * 8.0):
        return None

    percentage_value, absolute_value = _interpolate_triangle_values(best_match[0], best_match[1], samples)
    nearest_name, nearest_uf, nearest_distance = _nearest_sample_reference(lat, lon, samples)
    return percentage_value, absolute_value, nearest_name, nearest_uf, nearest_distance


@lru_cache(maxsize=24)
def _surface_geometry_cached(
    geometry_signature: tuple[_GeometrySample, ...],
) -> tuple[tuple[_GeometrySample, ...], _HullPolygon, tuple[_PreparedTriangle, ...], tuple[_Cell, ...]]:
    geometry_samples = _unique_geometry_samples(geometry_signature)
    hull_polygon = _convex_hull([(float(sample[3]), float(sample[2])) for sample in geometry_samples])
    prepared_triangles = _prepare_triangles(geometry_samples)
    return geometry_samples, hull_polygon, prepared_triangles, _hull_cells(hull_polygon)


def _elevation_for_value(value: float, scale: float) -> float:
    floor_height = float(HEATMAP_SURFACE_MAX_ELEVATION_M) * float(HEATMAP_SURFACE_ELEVATION_FLOOR_RATIO)
    if scale <= 0.0:
        return 0.0
    magnitude = abs(float(value))
    if magnitude <= 0.0:
        return 0.0
    usable_height = max(float(HEATMAP_SURFACE_MAX_ELEVATION_M) - floor_height, 0.0)
    normalized = _clamp(float(value) / float(scale), -1.0, 1.0)
    curved = math.copysign(abs(normalized) ** float(HEATMAP_SURFACE_ELEVATION_GAMMA), normalized)
    curved = math.copysign(min(abs(curved) * float(HEATMAP_SURFACE_ELEVATION_BOOST), 1.0), curved)
    visible_height = floor_height + (min(abs(curved), 1.0) * usable_height)
    return round(math.copysign(visible_height, float(value)), 2)


@lru_cache(maxsize=24)
def _build_surface_cached(points_signature: tuple[_Sample, ...], metric: str) -> HeatmapSurface:
    if not points_signature:
        return HeatmapSurface(
            metric=metric,
            mode="3d",
            cells=[],
            color_scale=1.0,
            negative_color_scale=0.0,
            positive_color_scale=0.0,
            elevation_scale=1.0,
            source_point_count=0,
            unique_source_coordinate_count=0,
            hull_vertex_count=0,
            interpolation_radius_km=float(HEATMAP_SURFACE_INTERPOLATION_RADIUS_MAX_KM),
            skipped_far_cells=0,
        )

    geometry_samples, hull_polygon, prepared_triangles, hull_cells = _surface_geometry_cached(
        _geometry_signature(points_signature)
    )
    value_samples = _value_samples(points_signature, geometry_samples)
    signed_values = [float(sample[5]) for sample in value_samples]
    negative_color_scale = _robust_side_scale(signed_values, HEATMAP_SURFACE_COLOR_QUANTILE, positive=False)
    positive_color_scale = _robust_side_scale(signed_values, HEATMAP_SURFACE_COLOR_QUANTILE, positive=True)
    color_scale = max(negative_color_scale, positive_color_scale, 1.0)
    elevation_scale = _robust_abs_scale([float(sample[5]) for sample in value_samples], HEATMAP_SURFACE_ELEVATION_QUANTILE)
    interpolation_radius_km = _interpolation_radius_km(value_samples)

    if len(value_samples) < 3 or len(hull_polygon) < 3 or not prepared_triangles or not hull_cells:
        return HeatmapSurface(
            metric=metric,
            mode="3d",
            cells=[],
            color_scale=color_scale,
            negative_color_scale=negative_color_scale,
            positive_color_scale=positive_color_scale,
            elevation_scale=elevation_scale,
            source_point_count=len(points_signature),
            unique_source_coordinate_count=len(value_samples),
            hull_vertex_count=len(hull_polygon),
            interpolation_radius_km=interpolation_radius_km,
            skipped_far_cells=0,
        )

    cells: list[HeatmapSurfaceCell] = []
    skipped_far_cells = 0
    for polygon, center_lat, center_lon in hull_cells:
        interpolated = _triangulated_interpolate(center_lat, center_lon, value_samples, prepared_triangles)
        if interpolated is None:
            continue
        percentage_value, absolute_value, nearest_name, nearest_uf, nearest_distance = interpolated
        if nearest_distance > interpolation_radius_km:
            skipped_far_cells += 1
            continue
        signed_quantitative_value = _align_quantitative_sign(percentage_value, absolute_value)
        cells.append(
            HeatmapSurfaceCell(
                polygon=polygon,
                center_lat=center_lat,
                center_lon=center_lon,
                percentage_value=percentage_value,
                absolute_value=signed_quantitative_value,
                fill_color=_color_for_value(
                    signed_quantitative_value,
                    negative_color_scale,
                    positive_color_scale,
                ),
                elevation_m=_elevation_for_value(signed_quantitative_value, elevation_scale),
                nearest_destiny_name=nearest_name,
                nearest_destiny_uf=nearest_uf,
                nearest_distance_km=nearest_distance,
            )
        )

    return HeatmapSurface(
        metric=metric,
        mode="3d",
        cells=cells,
        color_scale=color_scale,
        negative_color_scale=negative_color_scale,
        positive_color_scale=positive_color_scale,
        elevation_scale=elevation_scale,
        source_point_count=len(points_signature),
        unique_source_coordinate_count=len(value_samples),
        hull_vertex_count=len(hull_polygon),
        interpolation_radius_km=interpolation_radius_km,
        skipped_far_cells=skipped_far_cells,
    )


def build_surface(dataset: HeatmapDataset, metric: str) -> HeatmapSurface:
    normalized_metric = "emissions" if str(metric).strip().lower() == "emissions" else "cost"
    points_signature = _dataset_signature(dataset, normalized_metric)
    surface = _build_surface_cached(points_signature, normalized_metric)
    _log.info(
        (
            "Heatmap surface built origin=%s cargo_t=%.3f metric=%s mode=3d source_points=%d "
            "unique_coordinates=%d hull_vertices=%d cells=%d interpolation_radius_km=%.1f skipped_far_cells=%d"
        ),
        dataset.scenario.origin_name,
        dataset.scenario.cargo_t,
        normalized_metric,
        surface.source_point_count,
        surface.unique_source_coordinate_count,
        surface.hull_vertex_count,
        len(surface.cells),
        surface.interpolation_radius_km,
        surface.skipped_far_cells,
    )
    return surface
