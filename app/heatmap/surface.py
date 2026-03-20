from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any, Iterable, Sequence, Tuple

from app.heatmap.config import (
    HEATMAP_BRAZIL_BOUNDARY_PATH,
    HEATMAP_COLOR_MID,
    HEATMAP_COLOR_NEGATIVE,
    HEATMAP_COLOR_POSITIVE,
    HEATMAP_SURFACE_ALPHA,
    HEATMAP_SURFACE_CELL_SIZE_DEGREES,
    HEATMAP_SURFACE_COLOR_QUANTILE,
    HEATMAP_SURFACE_ELEVATION_QUANTILE,
    HEATMAP_SURFACE_IDW_NEIGHBORS,
    HEATMAP_SURFACE_IDW_POWER,
    HEATMAP_SURFACE_MAX_ELEVATION_M,
)
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapSurface, HeatmapSurfaceCell

_EARTH_RADIUS_KM = 6_371.0
_EPSILON_DISTANCE_KM = 0.001
_QuantileScale = tuple[float, ...]
_Sample = tuple[str, str, float, float, float, float]
_Cell = tuple[tuple[tuple[float, float], ...], float, float]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def _interpolate_channel(start: Iterable[int], end: Iterable[int], ratio: float) -> tuple[int, int, int]:
    weight = _clamp(ratio, 0.0, 1.0)
    start_values = list(start)
    end_values = list(end)
    return tuple(int(round(s + ((e - s) * weight))) for s, e in zip(start_values, end_values))  # type: ignore[return-value]


def _color_for_value(value: float, scale: float) -> tuple[int, int, int, int]:
    if scale <= 0.0:
        rgb = tuple(HEATMAP_COLOR_MID)
    else:
        normalized = _clamp(float(value) / float(scale), -1.0, 1.0)
        if normalized >= 0.0:
            rgb = _interpolate_channel(HEATMAP_COLOR_MID, HEATMAP_COLOR_POSITIVE, normalized)
        else:
            rgb = _interpolate_channel(HEATMAP_COLOR_MID, HEATMAP_COLOR_NEGATIVE, abs(normalized))
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


def _dataset_signature(dataset: HeatmapDataset, metric: str) -> tuple[_Sample, ...]:
    return tuple(
        sorted(
            (
                point.destiny_name,
                str(point.destiny_uf or "").strip(),
                round(float(point.destiny_lat), 4),
                round(float(point.destiny_lon), 4),
                round(_metric_percentage(point, metric), 4),
                round(_metric_absolute(point, metric), 4),
            )
            for point in dataset.points
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


@lru_cache(maxsize=1)
def _boundary_rings() -> tuple[tuple[tuple[float, float], ...], ...]:
    geojson = load_brazil_boundary_geojson()
    features = geojson.get("features") or []
    rings: list[tuple[tuple[float, float], ...]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry") or {}
        rings.extend(_extract_rings(geometry))
    return tuple(rings)


def _point_in_ring(lon: float, lat: float, ring: Sequence[tuple[float, float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False

    prev_lon, prev_lat = ring[-1]
    for curr_lon, curr_lat in ring:
        intersects = ((curr_lat > lat) != (prev_lat > lat)) and (
            lon < ((prev_lon - curr_lon) * (lat - curr_lat) / ((prev_lat - curr_lat) or 1e-12)) + curr_lon
        )
        if intersects:
            inside = not inside
        prev_lon, prev_lat = curr_lon, curr_lat
    return inside


def _point_in_boundary(lon: float, lat: float) -> bool:
    return any(_point_in_ring(lon, lat, ring) for ring in _boundary_rings())


@lru_cache(maxsize=1)
def _boundary_cells() -> tuple[_Cell, ...]:
    rings = _boundary_rings()
    if not rings:
        return tuple()

    all_lons = [coord[0] for ring in rings for coord in ring]
    all_lats = [coord[1] for ring in rings for coord in ring]
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
            if _point_in_boundary(center_lon, center_lat):
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


def _idw_interpolate(lat: float, lon: float, samples: Sequence[_Sample]) -> tuple[float, float, str, str | None, float]:
    distances: list[tuple[float, _Sample]] = []
    nearest_distance = float("inf")
    nearest_sample: _Sample | None = None

    for sample in samples:
        sample_lat = float(sample[2])
        sample_lon = float(sample[3])
        distance = _distance_km(lat, lon, sample_lat, sample_lon)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_sample = sample
        if distance <= _EPSILON_DISTANCE_KM:
            return float(sample[4]), float(sample[5]), sample[0], sample[1] or None, 0.0
        distances.append((distance, sample))

    selected = sorted(distances, key=lambda item: item[0])[: max(int(HEATMAP_SURFACE_IDW_NEIGHBORS), 1)]
    pct_weighted = 0.0
    abs_weighted = 0.0
    weight_total = 0.0
    for distance, sample in selected:
        weight = 1.0 / max(distance, _EPSILON_DISTANCE_KM) ** float(HEATMAP_SURFACE_IDW_POWER)
        weight_total += weight
        pct_weighted += weight * float(sample[4])
        abs_weighted += weight * float(sample[5])

    if weight_total <= 0.0:
        if nearest_sample is None:
            return 0.0, 0.0, "", None, 0.0
        return (
            float(nearest_sample[4]),
            float(nearest_sample[5]),
            nearest_sample[0],
            nearest_sample[1] or None,
            float(nearest_distance if math.isfinite(nearest_distance) else 0.0),
        )

    reference_name = "" if nearest_sample is None else nearest_sample[0]
    reference_uf = None if nearest_sample is None else (nearest_sample[1] or None)
    reference_distance = 0.0 if not math.isfinite(nearest_distance) else float(nearest_distance)
    return (
        pct_weighted / weight_total,
        abs_weighted / weight_total,
        reference_name,
        reference_uf,
        reference_distance,
    )


def _elevation_for_value(value: float, scale: float, mode: str) -> float:
    if mode != "3d" or scale <= 0.0:
        return 0.0
    normalized = _clamp(abs(float(value)) / float(scale), 0.0, 1.0)
    emphasized = math.pow(normalized, 0.85)
    return round(math.copysign(emphasized * float(HEATMAP_SURFACE_MAX_ELEVATION_M), float(value)), 2)


@lru_cache(maxsize=24)
def _build_surface_cached(points_signature: tuple[_Sample, ...], metric: str, mode: str) -> HeatmapSurface:
    if not points_signature:
        return HeatmapSurface(metric=metric, mode=mode, cells=[], color_scale=1.0, elevation_scale=1.0)

    color_scale = _robust_abs_scale([float(sample[4]) for sample in points_signature], HEATMAP_SURFACE_COLOR_QUANTILE)
    elevation_scale = _robust_abs_scale(
        [float(sample[5]) for sample in points_signature],
        HEATMAP_SURFACE_ELEVATION_QUANTILE,
    )

    cells: list[HeatmapSurfaceCell] = []
    for polygon, center_lat, center_lon in _boundary_cells():
        percentage_value, absolute_value, nearest_name, nearest_uf, nearest_distance = _idw_interpolate(
            center_lat,
            center_lon,
            points_signature,
        )
        cells.append(
            HeatmapSurfaceCell(
                polygon=polygon,
                center_lat=center_lat,
                center_lon=center_lon,
                percentage_value=percentage_value,
                absolute_value=absolute_value,
                fill_color=_color_for_value(percentage_value, color_scale),
                elevation_m=_elevation_for_value(absolute_value, elevation_scale, mode),
                nearest_destiny_name=nearest_name,
                nearest_destiny_uf=nearest_uf,
                nearest_distance_km=nearest_distance,
            )
        )

    return HeatmapSurface(
        metric=metric,
        mode=mode,
        cells=cells,
        color_scale=color_scale,
        elevation_scale=elevation_scale,
    )


def build_surface(dataset: HeatmapDataset, metric: str, mode: str) -> HeatmapSurface:
    normalized_metric = "emissions" if str(metric).strip().lower() == "emissions" else "cost"
    normalized_mode = "3d" if str(mode).strip().lower() == "3d" else "2d"
    return _build_surface_cached(_dataset_signature(dataset, normalized_metric), normalized_metric, normalized_mode)
