from __future__ import annotations

import re
from typing import Any, List


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_place_label(label: Any) -> str:
    text = str(label or "").strip()
    if not text:
        return ""

    text = re.sub(r"\s*,\s*(?:brazil|brasil)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*,+", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,")


def fmt_distance_km(value: Any) -> str:
    return f"{safe_float(value):,.1f} km"


def fmt_currency_brl(value: Any) -> str:
    return f"R$ {safe_float(value):,.2f}"


def fmt_emissions_kg(value: Any) -> str:
    return f"{safe_float(value):,.1f} kg CO2e"


def path_midpoint(path_lonlat: List[List[float]]) -> List[float]:
    if not path_lonlat:
        return [0.0, 0.0]
    return path_lonlat[len(path_lonlat) // 2]


def route_metric_label(name: str, distance_km: Any, cost_brl: Any, co2e_kg: Any) -> str:
    return (
        f"{name}: {fmt_distance_km(distance_km)} | "
        f"{fmt_currency_brl(cost_brl)} | {fmt_emissions_kg(co2e_kg)}"
    )

