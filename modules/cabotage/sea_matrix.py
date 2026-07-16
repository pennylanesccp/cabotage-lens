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

__all__ = ["OBSERVED_VOYAGE_CORRIDORS_MODE", "SeaMatrix"]

_log = get_logger(__name__)
OBSERVED_VOYAGE_CORRIDORS_MODE = "observed_voyage_corridors"


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


def _clean_route_observation_mode(value: Any) -> str:
    return str(value or "").strip().casefold()


def _first_value(payload: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _canonical_corridor_subleg(payload: Dict[str, Any]) -> Dict[str, Any]:
    subleg = dict(payload)
    subleg["origin_port"] = _first_value(
        payload,
        "origin_port",
        "from_port_name",
        "from_port",
        "origin",
    )
    subleg["destination_port"] = _first_value(
        payload,
        "destination_port",
        "to_port_name",
        "to_port",
        "destination",
    )

    aliases = {
        "distance_km": ("distance_km",),
        "distance_nm": ("distance_nm",),
        "observed_cargo_t": (
            "observed_cargo_t",
            "average_cargo_onboard_t",
            "cargo_onboard_t",
            "cargo_weight_t",
        ),
        "transport_work_tnm": (
            "transport_work_tnm",
            "observed_transport_work_tnm",
            "tonne_nm",
        ),
        "resolved_transport_work_tnm": (
            "resolved_transport_work_tnm",
            "transport_work_resolved_tnm",
        ),
        "fuel_g_per_tnm": (
            "fuel_g_per_tnm",
            "intensity_g_per_tnm",
            "weighted_fuel_intensity_g_per_tnm",
            "fuel_g_per_tnm_weighted_mean",
        ),
        "intensity_source": ("intensity_source", "fuel_g_per_tnm_source"),
        "intensity_source_level": ("intensity_source_level", "source_level"),
    }
    for canonical, candidates in aliases.items():
        value = _first_value(payload, *candidates)
        if value is not None:
            subleg[canonical] = value

    observed_fuel_kg = _first_value(
        payload,
        "observed_fuel_kg",
        "fuel_consumption_kg",
        "fuel_kg",
    )
    if observed_fuel_kg is None:
        observed_fuel_g = _positive_float(payload.get("fuel_consumption_g"))
        if observed_fuel_g is not None:
            observed_fuel_kg = observed_fuel_g / 1000.0
    if observed_fuel_kg is not None:
        subleg["observed_fuel_kg"] = observed_fuel_kg

    if subleg.get("fuel_g_per_tnm") is None:
        resolved_transport_work_tnm = _positive_float(
            subleg.get("resolved_transport_work_tnm")
        )
        if resolved_transport_work_tnm is None:
            observed_count = _positive_float(payload.get("observed_segment_count"))
            resolved_count = _positive_float(payload.get("resolved_segment_count"))
            if (
                observed_count is not None
                and resolved_count is not None
                and observed_count == resolved_count
            ):
                resolved_transport_work_tnm = _positive_float(
                    subleg.get("transport_work_tnm")
                )
        observed_fuel = _positive_float(subleg.get("observed_fuel_kg"))
        if observed_fuel is not None and resolved_transport_work_tnm is not None:
            subleg["fuel_g_per_tnm"] = (
                observed_fuel * 1000.0 / resolved_transport_work_tnm
            )

    source_counts = payload.get("intensity_source_counts")
    if isinstance(source_counts, dict) and source_counts:
        positive_sources = [
            str(key)
            for key, value in source_counts.items()
            if _positive_float(value) is not None and str(key) != "unavailable"
        ]
        if subleg.get("intensity_source") is None:
            if not positive_sources:
                subleg["intensity_source"] = "unavailable"
            else:
                subleg["intensity_source"] = (
                    positive_sources[0] if len(positive_sources) == 1 else "mixed"
                )
        if subleg.get("intensity_source_level") is None:
            levels = {
                "eu_mrv_imo_latest": "imo",
                "eu_mrv_vessel_class_mean": "vessel_class",
                "eu_mrv_vessel_class_trimmed_mean_1pct": "vessel_class",
                "eu_mrv_vessel_class_median": "vessel_class",
                "eu_mrv_ship_type_mean": "ship_type",
                "eu_mrv_ship_type_trimmed_mean_1pct": "ship_type",
                "eu_mrv_ship_type_median": "ship_type",
                "eu_mrv_ship_type_mean_default_container_ship": "ship_type",
            }
            resolved_levels = {
                levels[source] for source in positive_sources if source in levels
            }
            if not positive_sources:
                subleg["intensity_source_level"] = "unresolved"
            else:
                subleg["intensity_source_level"] = (
                    next(iter(resolved_levels))
                    if len(resolved_levels) == 1
                    else "mixed"
                )
    return subleg


@dataclass
class SeaMatrix:
    """
    Sea distance matrix plus optional route-level directional efficiency stats.
    """

    matrix: Dict[str, Dict[str, float]]
    coastline_factor: float = 1.0
    directional_efficiency: Dict[str, Dict[str, Dict[str, Any]]] | None = None
    route_observation_mode: str = ""

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
        self.route_observation_mode = _clean_route_observation_mode(self.route_observation_mode)

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
        if self.route_observation_mode != OBSERVED_VOYAGE_CORRIDORS_MODE:
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
        directional_meta = payload.get("voyage_fuel_g_per_tnm_directional_meta") or {}
        route_observation_mode = _clean_route_observation_mode(
            payload.get("route_observation_mode")
            or (
                directional_meta.get("route_observation_mode")
                if isinstance(directional_meta, dict)
                else None
            )
        )
        directional = payload.get("voyage_fuel_g_per_tnm_directional") or {}
        if not route_observation_mode and isinstance(directional, dict):
            for destinations in directional.values():
                if not isinstance(destinations, dict):
                    continue
                for stats in destinations.values():
                    if not isinstance(stats, dict):
                        continue
                    route_observation_mode = _clean_route_observation_mode(
                        stats.get("route_observation_mode")
                    )
                    if route_observation_mode:
                        break
                if route_observation_mode:
                    break
        if route_observation_mode == OBSERVED_VOYAGE_CORRIDORS_MODE:
            observed_corridors = (
                payload.get("observed_voyage_corridors_directional")
                or payload.get("voyage_corridors_directional")
            )
            if isinstance(observed_corridors, dict):
                directional = observed_corridors

        cleaned_matrix: Dict[str, Dict[str, float]] = {
            str(origin): {str(destiny): float(value) for destiny, value in (destinations or {}).items()}
            for origin, destinations in (matrix or {}).items()
        }
        return cls(
            matrix=cleaned_matrix,
            coastline_factor=coastline_factor,
            directional_efficiency=_clean_directional_payload(directional),
            route_observation_mode=route_observation_mode,
        )

    @classmethod
    def from_json_path(cls, path: Path | str) -> "SeaMatrix":
        resolved = resolve_data_asset_path(path)
        local_path = Path(path).resolve()
        try:
            sea_matrix = cls._from_resolved_json_path(resolved)
        except ValueError:
            if resolved.resolve() == local_path or not local_path.is_file():
                raise

            _log.warning(
                "Rejected invalid resolved sea matrix asset=%s; falling back to local asset=%s",
                resolved,
                local_path,
            )
            return cls._from_resolved_json_path(local_path)

        if (
            resolved.resolve() != local_path
            and local_path.is_file()
            and sea_matrix.route_observation_mode
            != OBSERVED_VOYAGE_CORRIDORS_MODE
        ):
            local_matrix = cls._from_resolved_json_path(local_path)
            if (
                local_matrix.route_observation_mode
                == OBSERVED_VOYAGE_CORRIDORS_MODE
            ):
                _log.warning(
                    (
                        "Resolved sea matrix asset=%s uses a legacy route schema; "
                        "using tracked observed-voyage corridor asset=%s"
                    ),
                    resolved,
                    local_path,
                )
                return local_matrix
        return sea_matrix

    @classmethod
    def _from_resolved_json_path(cls, resolved: Path) -> "SeaMatrix":
        with resolved.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        _log.debug("SeaMatrix loaded from %s", resolved)
        sea_matrix = cls.from_json_dict(payload)
        has_usable_distance = any(
            _norm(origin) != _norm(destiny) and _positive_float(distance_km) is not None
            for origin, destinations in sea_matrix.matrix.items()
            for destiny, distance_km in destinations.items()
        )
        if not has_usable_distance:
            raise ValueError(
                f"Sea matrix asset contains no usable positive port-pair distances: {resolved}"
            )
        return sea_matrix

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

    @staticmethod
    def _selected_observed_corridor_stats(stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize the corridor selected offline without selecting or stitching at runtime."""
        merged = dict(stats)
        selected = None
        for key in ("selected_corridor", "selected_voyage_corridor", "selected_route"):
            candidate = stats.get(key)
            if isinstance(candidate, dict):
                selected = dict(candidate)
                break

        selected_corridor_id = _first_value(
            stats,
            "selected_corridor_id",
            "selected_route_id",
        )
        if selected is None and selected_corridor_id is not None:
            candidates = _first_value(stats, "corridors", "candidate_corridors", "routes")
            if isinstance(candidates, list):
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_id = _first_value(candidate, "corridor_id", "route_id", "voyage_id")
                    if str(candidate_id or "") == str(selected_corridor_id):
                        selected = dict(candidate)
                        break

        if selected is not None:
            merged.update(selected)
        selected_corridor_id = _first_value(
            merged,
            "selected_corridor_id",
            "corridor_id",
            "selected_route_id",
            "route_id",
            "voyage_id",
        )
        if selected_corridor_id is not None:
            merged["selected_corridor_id"] = str(selected_corridor_id)

        aliases: dict[str, tuple[str, ...]] = {
            "corridor_count": ("corridor_count", "observed_corridor_count"),
            "candidate_voyage_count": ("candidate_voyage_count", "candidate_count", "voyage_count"),
            "candidate_voyage_observation_count": (
                "candidate_voyage_observation_count",
                "candidate_voyage_count",
            ),
            "direct_voyage_count": ("direct_voyage_count", "direct_count"),
            "multistop_voyage_count": (
                "multistop_voyage_count",
                "multi_stop_voyage_count",
                "indirect_voyage_count",
            ),
            "resolved_voyage_count": ("resolved_voyage_count", "complete_calculation_count"),
            "imo_intensity_voyage_count": (
                "imo_intensity_voyage_count",
                "imo_resolved_voyage_count",
                "mrv_imo_voyage_count",
            ),
            "class_fallback_voyage_count": (
                "class_fallback_voyage_count",
                "vessel_class_fallback_voyage_count",
            ),
            "type_fallback_voyage_count": (
                "type_fallback_voyage_count",
                "ship_type_fallback_voyage_count",
            ),
            "fallback_voyage_count": ("fallback_voyage_count",),
            "unresolved_intensity_voyage_count": (
                "unresolved_intensity_voyage_count",
                "unresolved_voyage_count",
            ),
            "haversine_fallback_segment_count": (
                "haversine_fallback_segment_count",
            ),
            "observed_transport_work_tnm": (
                "observed_transport_work_tnm",
                "transport_work_tnm_total",
                "tonne_nm_total",
            ),
            "observed_fuel_kg": (
                "observed_fuel_kg",
                "fuel_consumption_kg_total",
                "fuel_kg_total",
            ),
        }
        for canonical, candidates in aliases.items():
            value = _first_value(merged, *candidates)
            if value is not None:
                merged[canonical] = value

        if merged.get("observed_fuel_kg") is None:
            observed_fuel_g = _positive_float(merged.get("fuel_consumption_g_total"))
            if observed_fuel_g is not None:
                merged["observed_fuel_kg"] = observed_fuel_g / 1000.0

        raw_sublegs = _first_value(
            merged,
            "selected_corridor_sublegs",
            "subleg_details",
            "sublegs",
            "legs",
        )
        sublegs = [
            _canonical_corridor_subleg(dict(item))
            for item in (raw_sublegs or [])
            if isinstance(item, dict)
        ] if isinstance(raw_sublegs, list) else []
        if sublegs:
            merged["selected_corridor_sublegs"] = sublegs
            merged["corridor_leg_count"] = int(
                _first_value(merged, "corridor_leg_count", "subleg_count", "leg_count")
                or len(sublegs)
            )

        port_path = _first_value(merged, "corridor_port_path", "port_path")
        if isinstance(port_path, list) and port_path:
            merged["corridor_port_path"] = [str(item) for item in port_path]
        elif sublegs:
            derived_path = [str(sublegs[0].get("origin_port") or "")]
            derived_path.extend(str(item.get("destination_port") or "") for item in sublegs)
            if all(derived_path):
                merged["corridor_port_path"] = derived_path

        distance_km = _positive_float(
            _first_value(merged, "distance_km", "distance_km_total")
        )
        distance_nm = _positive_float(
            _first_value(merged, "distance_nm", "distance_nm_total")
        )
        if distance_km is None and sublegs:
            values = [_positive_float(item.get("distance_km")) for item in sublegs]
            if all(value is not None for value in values):
                distance_km = sum(float(value) for value in values if value is not None)
        if distance_nm is None and sublegs:
            values = [_positive_float(item.get("distance_nm")) for item in sublegs]
            if all(value is not None for value in values):
                distance_nm = sum(float(value) for value in values if value is not None)
        if distance_km is None and distance_nm is not None:
            distance_km = distance_nm * 1.852
        if distance_nm is None and distance_km is not None:
            distance_nm = distance_km / 1.852
        if distance_km is not None:
            merged["distance_km"] = float(distance_km)
        if distance_nm is not None:
            merged["distance_nm"] = float(distance_nm)

        if merged.get("fuel_g_per_tnm_weighted_mean") is None and sublegs:
            weighted_total = 0.0
            distance_total = 0.0
            for subleg in sublegs:
                intensity = _positive_float(subleg.get("fuel_g_per_tnm"))
                leg_distance_nm = _positive_float(subleg.get("distance_nm"))
                if intensity is None or leg_distance_nm is None:
                    weighted_total = 0.0
                    distance_total = 0.0
                    break
                weighted_total += intensity * leg_distance_nm
                distance_total += leg_distance_nm
            if distance_total > 0.0:
                merged["fuel_g_per_tnm_weighted_mean"] = weighted_total / distance_total

        if _positive_float(merged.get("distance_km")) is None and not sublegs:
            return None
        merged["distance_source"] = "observed_voyage_corridor"
        merged["route_observation_mode"] = OBSERVED_VOYAGE_CORRIDORS_MODE
        return merged

    def best_directional_stats(self, a_label: str, b_label: str) -> Optional[Dict[str, Any]]:
        direct_stats = self.directional_stats(a_label, b_label)
        if self.route_observation_mode == OBSERVED_VOYAGE_CORRIDORS_MODE:
            if not direct_stats:
                return None
            return self._selected_observed_corridor_stats(direct_stats)
        if direct_stats:
            weighted_mean = _positive_float(direct_stats.get("fuel_g_per_tnm_weighted_mean"))
            distance_km = _positive_float(direct_stats.get("distance_km"))
            if weighted_mean is not None and distance_km is not None:
                origin = self._resolve_label(a_label)
                destination = self._resolve_label(b_label)
                direct_stats["distance_source"] = "directional_direct"
                direct_stats["corridor_leg_count"] = 1
                direct_stats["corridor_port_path"] = [origin, destination]
                direct_stats["observed_port_pair_legs"] = [
                    self._observed_port_pair_leg(origin, destination, direct_stats)
                ]
                return direct_stats
        return self.corridor_stats(a_label, b_label)

    def corridor_stats(self, a_label: str, b_label: str) -> Optional[Dict[str, Any]]:
        if self.route_observation_mode == OBSERVED_VOYAGE_CORRIDORS_MODE:
            return None
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

        observed_port_pair_legs = [
            self._observed_port_pair_leg(origin, destination, stats)
            for origin, destination, stats in zip(path[:-1], path[1:], edge_stats)
        ]

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
            "observed_port_pair_legs": observed_port_pair_legs,
        }

    @staticmethod
    def _observed_port_pair_leg(
        origin: str | None,
        destination: str | None,
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        segment_count = int(stats.get("segment_count") or 0)
        cargo_total_t = float(stats.get("cargo_weight_t_total") or 0.0)
        average_cargo_t = cargo_total_t / segment_count if segment_count > 0 else None
        distance_km = _positive_float(stats.get("distance_km"))
        distance_nm = _positive_float(stats.get("distance_nm"))
        if distance_nm is None and distance_km is not None:
            distance_nm = distance_km / 1.852

        return {
            "origin_port": origin,
            "destination_port": destination,
            "observed_segment_count": segment_count,
            "matched_segment_count": int(stats.get("matched_segment_count") or 0),
            "distinct_voyage_count": int(stats.get("voyage_count") or 0),
            "matched_voyage_count": int(stats.get("matched_voyage_count") or 0),
            "distinct_imo_count": int(stats.get("unique_imo_count") or 0),
            "matched_imo_count": int(stats.get("matched_imo_count") or 0),
            "average_cargo_t": (
                None if average_cargo_t is None else round(average_cargo_t, 6)
            ),
            "distance_km": distance_km,
            "distance_nm": distance_nm,
            "weighted_fuel_intensity_g_per_tnm": _positive_float(
                stats.get("fuel_g_per_tnm_weighted_mean")
            ),
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
