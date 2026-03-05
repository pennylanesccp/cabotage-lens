from __future__ import annotations

from typing import Any, Mapping

from app.main.utils.formatters import safe_float


def multimodal_total_distance(results: Mapping[str, Any]) -> float:
    mm = results.get("multimodal", {})
    return (
        safe_float(mm.get("first_mile", {}).get("distance_km"))
        + safe_float(mm.get("sea", {}).get("distance_km"))
        + safe_float(mm.get("last_mile", {}).get("distance_km"))
    )


def best_option(results: Mapping[str, Any]) -> str:
    road_cost = safe_float(results.get("road_only", {}).get("cost"))
    mm_cost = safe_float(results.get("multimodal", {}).get("total_cost"))
    return "Multimodal" if mm_cost < road_cost else "Road"
