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
import math
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

    def directional_fuel_g_per_tnm(self, a_label: str, b_label: str) -> Optional[float]:
        stats = self.directional_stats(a_label, b_label)
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
