# modules/cabotage/sea_matrix.py
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Sea distance matrix with optional directional efficiency metadata.

The matrix keeps deterministic port-to-port sea distances in km, with a
coastline-adjusted haversine fallback when a pair is missing. When the enriched
`data/sea_matrix.json` is present, the same loader also exposes route-specific
fuel-per-transport-work stats under `voyage_fuel_g_per_tnm_directional`.
"""

import json
import heapq
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from modules.infra.data_assets import resolve_data_asset_path
from modules.infra.log_manager import get_logger

__all__ = ["SeaMatrix"]

_log = get_logger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km using a spherical approximation."""
    radius_km = 6371.0088
    a1 = math.radians(float(lat1))
    b1 = math.radians(float(lon1))
    a2 = math.radians(float(lat2))
    b2 = math.radians(float(lon2))
    delta_lat = a2 - a1
    delta_lon = b2 - b1
    s = (
        (math.sin(delta_lat / 2.0) ** 2)
        + (math.cos(a1) * math.cos(a2) * (math.sin(delta_lon / 2.0) ** 2))
    )
    c = 2.0 * math.atan2(math.sqrt(s), math.sqrt(1.0 - s))
    return float(radius_km * c)


def _norm(label: str) -> str:
    return " ".join(str(label or "").casefold().split())


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0.0 else None


def _clean_directional_payload(payload: Any) -> Dict[str, Dict[str, Dict[str, Any]]]:
    cleaned: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not isinstance(payload, dict):
        return cleaned

    for origin, destinations in payload.items():
        if not isinstance(destinations, dict):
            continue
        origin_label = str(origin)
        cleaned_destinations: Dict[str, Dict[str, Any]] = {}
        for destiny, stats in destinations.items():
            if not isinstance(stats, dict):
                continue
            cleaned_destinations[str(destiny)] = dict(stats)
        if cleaned_destinations:
            cleaned[origin_label] = cleaned_destinations
    return cleaned


@dataclass
class SeaMatrix:
    """
    Sea distance matrix plus optional route-level directional efficiency stats.
    """

    matrix: Dict[str, Dict[str, float]]
    coastline_factor: float = 1.0
    directional_efficiency: Dict[str, Dict[str, Dict[str, Any]]] | None = None

    _canon: Dict[str, str] = None  # type: ignore[assignment]
    _directional_graph: Dict[str, tuple[tuple[str, Dict[str, Any]], ...]] = None  # type: ignore[assignment]
    _corridor_cache: Dict[tuple[str, str], Dict[str, Any] | None] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        cleaned_matrix: Dict[str, Dict[str, float]] = {}
        for origin, destinations in (self.matrix or {}).items():
            origin_label = str(origin)
            cleaned_matrix[origin_label] = {}
            for destiny, distance_km in (destinations or {}).items():
                cleaned_matrix[origin_label][str(destiny)] = float(distance_km)

        self.matrix = cleaned_matrix
        self.coastline_factor = float(self.coastline_factor)
        self.directional_efficiency = _clean_directional_payload(self.directional_efficiency)

        self._canon = {}
        for origin, destinations in self.matrix.items():
            self._canon.setdefault(_norm(origin), origin)
            for destiny in destinations.keys():
                self._canon.setdefault(_norm(destiny), destiny)
        for origin, destinations in self.directional_efficiency.items():
            self._canon.setdefault(_norm(origin), origin)
            for destiny in destinations.keys():
                self._canon.setdefault(_norm(destiny), destiny)

        for origin, destinations in list(self.matrix.items()):
            for destiny, distance_km in list(destinations.items()):
                self.matrix.setdefault(destiny, {})
                if origin not in self.matrix[destiny]:
                    self.matrix[destiny][origin] = float(distance_km)

        self._directional_graph = {}
        self._corridor_cache = {}
        for origin, destinations in self.directional_efficiency.items():
            edges: list[tuple[str, Dict[str, Any]]] = []
            for destiny, stats in destinations.items():
                if (
                    _positive_float(stats.get("distance_km")) is None
                    or _positive_float(stats.get("fuel_g_per_tnm_weighted_mean")) is None
                ):
                    continue
                edges.append((destiny, dict(stats)))
            if edges:
                self._directional_graph[origin] = tuple(edges)

        _log.debug(
            (
                "SeaMatrix initialized labels=%d directed_edges=%d coastline_factor=%.3f "
                "directional_pairs=%d"
            ),
            len(self._canon),
            sum(len(destinations) for destinations in self.matrix.values()),
            self.coastline_factor,
            sum(len(destinations) for destinations in self.directional_efficiency.values()),
        )

    @classmethod
    def from_json_dict(cls, payload: Dict[str, Any]) -> "SeaMatrix":
        if not isinstance(payload, dict):
            raise TypeError("SeaMatrix.from_json_dict: payload must be a dict.")

        matrix = payload.get("matrix") or {}
        coastline_factor = float(payload.get("coastline_factor", 1.0))
        directional = payload.get("voyage_fuel_g_per_tnm_directional") or {}

        cleaned_matrix: Dict[str, Dict[str, float]] = {
            str(origin): {str(destiny): float(value) for destiny, value in (destinations or {}).items()}
            for origin, destinations in (matrix or {}).items()
        }
        return cls(
            matrix=cleaned_matrix,
            coastline_factor=coastline_factor,
            directional_efficiency=_clean_directional_payload(directional),
        )

    @classmethod
    def from_json_path(cls, path: Path | str) -> "SeaMatrix":
        resolved = resolve_data_asset_path(path)
        with resolved.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        _log.debug("SeaMatrix loaded from %s", resolved)
        return cls.from_json_dict(payload)

    def size(self) -> int:
        return len(self._canon)

    def labels(self) -> Tuple[str, ...]:
        return tuple(sorted(self._canon.values()))

    def _resolve_label(self, label: Optional[str]) -> Optional[str]:
        if label is None:
            return None
        return self._canon.get(_norm(label))

    def get(self, a_label: str, b_label: str) -> Optional[float]:
        a = self._resolve_label(a_label)
        b = self._resolve_label(b_label)
        if not a or not b:
            return None
        if a == b:
            return 0.0
        value = self.matrix.get(a, {}).get(b)
        return None if value is None else float(value)

    def directional_stats(self, a_label: str, b_label: str) -> Optional[Dict[str, Any]]:
        a = self._resolve_label(a_label)
        b = self._resolve_label(b_label)
        if not a or not b or a == b:
            return None
        stats = self.directional_efficiency.get(a, {}).get(b)
        if not isinstance(stats, dict):
            return None
        return dict(stats)

    def best_directional_stats(self, a_label: str, b_label: str) -> Optional[Dict[str, Any]]:
        direct_stats = self.directional_stats(a_label, b_label)
        if direct_stats:
            weighted_mean = _positive_float(direct_stats.get("fuel_g_per_tnm_weighted_mean"))
            distance_km = _positive_float(direct_stats.get("distance_km"))
            if weighted_mean is not None and distance_km is not None:
                direct_stats["distance_source"] = "directional_direct"
                direct_stats["corridor_leg_count"] = 1
                direct_stats["corridor_port_path"] = [self._resolve_label(a_label), self._resolve_label(b_label)]
                return direct_stats
        return self.corridor_stats(a_label, b_label)

    def corridor_stats(self, a_label: str, b_label: str) -> Optional[Dict[str, Any]]:
        a = self._resolve_label(a_label)
        b = self._resolve_label(b_label)
        if not a or not b or a == b:
            return None

        cache_key = (a, b)
        if cache_key in self._corridor_cache:
            cached = self._corridor_cache[cache_key]
            return None if cached is None else dict(cached)

        path = self._shortest_directional_path(a, b)
        if not path or len(path) < 3:
            self._corridor_cache[cache_key] = None
            return None

        edge_stats: list[Dict[str, Any]] = []
        for origin, destiny in zip(path[:-1], path[1:]):
            stats = self.directional_efficiency.get(origin, {}).get(destiny)
            if not isinstance(stats, dict):
                self._corridor_cache[cache_key] = None
                return None
            if (
                _positive_float(stats.get("distance_km")) is None
                or _positive_float(stats.get("fuel_g_per_tnm_weighted_mean")) is None
            ):
                self._corridor_cache[cache_key] = None
                return None
            edge_stats.append(dict(stats))

        aggregated = self._aggregate_corridor_stats(path, edge_stats)
        self._corridor_cache[cache_key] = dict(aggregated)
        return dict(aggregated)

    def directional_fuel_g_per_tnm(self, a_label: str, b_label: str) -> Optional[float]:
        stats = self.best_directional_stats(a_label, b_label)
        if not stats:
            return None
        value = stats.get("fuel_g_per_tnm_weighted_mean")
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0.0 else None

    def km_with_source(self, p_from: Dict[str, Any], p_to: Dict[str, Any]) -> Tuple[float, str]:
        a_label = str(p_from["name"])
        b_label = str(p_to["name"])

        matrix_distance = self.get(a_label, b_label)
        if matrix_distance is not None:
            return float(matrix_distance), "matrix"

        haversine_km = _haversine_km(
            float(p_from["lat"]),
            float(p_from["lon"]),
            float(p_to["lat"]),
            float(p_to["lon"]),
        )
        adjusted_km = haversine_km * float(self.coastline_factor)
        _log.info(
            (
                "SeaMatrix haversine fallback origin=%s destiny=%s haversine_km=%.3f "
                "coastline_factor=%.3f adjusted_km=%.3f"
            ),
            a_label,
            b_label,
            haversine_km,
            self.coastline_factor,
            adjusted_km,
        )
        return float(adjusted_km), "haversine"

    def km(self, p_from: Dict[str, Any], p_to: Dict[str, Any]) -> float:
        distance_km, _ = self.km_with_source(p_from, p_to)
        return float(distance_km)

    def _shortest_directional_path(self, origin: str, destiny: str) -> tuple[str, ...] | None:
        if origin not in self._directional_graph:
            return None

        frontier: list[tuple[float, str, tuple[str, ...]]] = [(0.0, origin, (origin,))]
        best_distance: Dict[str, float] = {}

        while frontier:
            total_distance_km, current, path = heapq.heappop(frontier)
            previous_best = best_distance.get(current)
            if previous_best is not None and total_distance_km >= previous_best:
                continue
            best_distance[current] = total_distance_km
            if current == destiny:
                return path

            for next_port, stats in self._directional_graph.get(current, ()):
                edge_distance_km = _positive_float(stats.get("distance_km"))
                if edge_distance_km is None:
                    continue
                heapq.heappush(
                    frontier,
                    (total_distance_km + edge_distance_km, next_port, (*path, next_port)),
                )

        return None

    def _aggregate_corridor_stats(
        self,
        path: tuple[str, ...],
        edge_stats: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        distance_km_total = 0.0
        distance_nm_total = 0.0
        weighted_fuel_distance_total = 0.0
        fuel_values: list[float] = []

        segment_count = 0
        matched_segment_count = 0
        voyage_count = 0
        matched_voyage_count = 0
        unique_imo_count = 0
        matched_imo_count = 0
        cargo_weight_t_total = 0.0
        cargo_weight_t_matched_total = 0.0
        tonne_nm_total = 0.0
        tonne_nm_matched_total = 0.0

        for stats in edge_stats:
            edge_distance_km = float(stats.get("distance_km") or 0.0)
            edge_distance_nm = float(stats.get("distance_nm") or 0.0)
            if edge_distance_nm <= 0.0 and edge_distance_km > 0.0:
                edge_distance_nm = edge_distance_km / 1.852
            edge_fuel_g_per_tnm = float(stats.get("fuel_g_per_tnm_weighted_mean") or 0.0)

            distance_km_total += edge_distance_km
            distance_nm_total += edge_distance_nm
            weighted_fuel_distance_total += edge_fuel_g_per_tnm * edge_distance_nm
            fuel_values.append(edge_fuel_g_per_tnm)

            segment_count += int(stats.get("segment_count") or 0)
            matched_segment_count += int(stats.get("matched_segment_count") or 0)
            voyage_count += int(stats.get("voyage_count") or 0)
            matched_voyage_count += int(stats.get("matched_voyage_count") or 0)
            unique_imo_count += int(stats.get("unique_imo_count") or 0)
            matched_imo_count += int(stats.get("matched_imo_count") or 0)
            cargo_weight_t_total += float(stats.get("cargo_weight_t_total") or 0.0)
            cargo_weight_t_matched_total += float(stats.get("cargo_weight_t_matched_total") or 0.0)
            tonne_nm_total += float(stats.get("tonne_nm_total") or 0.0)
            tonne_nm_matched_total += float(stats.get("tonne_nm_matched_total") or 0.0)

        weighted_mean = None
        if distance_nm_total > 0.0:
            weighted_mean = weighted_fuel_distance_total / distance_nm_total

        return {
            "distance_km": round(distance_km_total, 3),
            "distance_nm": round(distance_nm_total, 3),
            "fuel_g_per_tnm_weighted_mean": (round(weighted_mean, 6) if weighted_mean is not None else None),
            "fuel_g_per_tnm_mean": (round(sum(fuel_values) / len(fuel_values), 6) if fuel_values else None),
            "fuel_g_per_tnm_median": (round(statistics.median(fuel_values), 6) if fuel_values else None),
            "segment_count": int(segment_count),
            "matched_segment_count": int(matched_segment_count),
            "voyage_count": int(voyage_count),
            "matched_voyage_count": int(matched_voyage_count),
            "unique_imo_count": int(unique_imo_count),
            "matched_imo_count": int(matched_imo_count),
            "cargo_weight_t_total": round(cargo_weight_t_total, 3),
            "cargo_weight_t_matched_total": round(cargo_weight_t_matched_total, 3),
            "tonne_nm_total": round(tonne_nm_total, 3),
            "tonne_nm_matched_total": round(tonne_nm_matched_total, 3),
            "match_rate_segments": (
                round(matched_segment_count / segment_count, 6) if segment_count > 0 else None
            ),
            "match_rate_tonne_nm": (
                round(tonne_nm_matched_total / tonne_nm_total, 6) if tonne_nm_total > 0.0 else None
            ),
            "distance_source": "directional_corridor",
            "corridor_leg_count": len(edge_stats),
            "corridor_port_path": list(path),
        }


if __name__ == "__main__":
    from modules.infra.log_manager import init_logging

    init_logging(level="INFO", force_clean=True, archive_to_storage=False)

    sample_payload = {
        "matrix": {
            "Santos (SP)": {
                "Rio de Janeiro (RJ)": 430.0,
            }
        },
        "coastline_factor": 1.15,
        "voyage_fuel_g_per_tnm_directional": {
            "Santos (SP)": {
                "Rio de Janeiro (RJ)": {
                    "fuel_g_per_tnm_weighted_mean": 5.4321,
                    "matched_segment_count": 12,
                }
            }
        },
    }

    sea_matrix = SeaMatrix.from_json_dict(sample_payload)
    print("size=", sea_matrix.size())
    print("labels=", sea_matrix.labels())
    print("matrix_km=", sea_matrix.get("Santos (SP)", "Rio de Janeiro (RJ)"))
    print(
        "directional_fuel_g_per_tnm=",
        sea_matrix.directional_fuel_g_per_tnm("Santos (SP)", "Rio de Janeiro (RJ)"),
    )
