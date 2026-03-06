from __future__ import annotations

import math
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


def fmt_currency_brl_rounded(value: Any) -> str:
    return f"R$ {safe_float(value):,.0f}"


def fmt_emissions_kg(value: Any) -> str:
    return f"{safe_float(value):,.1f} kg CO2e"


def fmt_distance_km_rounded(value: Any) -> str:
    return f"{safe_float(value):,.0f} km"


def _sig_fig_decimals(value: float, sig_figs: int = 3) -> int:
    if value == 0.0:
        return 0
    magnitude = math.floor(math.log10(abs(value)))
    return max(0, sig_figs - magnitude - 1)


def format_significant(value: Any, sig_figs: int = 3) -> str:
    number = safe_float(value)
    if number == 0.0:
        return "0"

    decimals = _sig_fig_decimals(number, sig_figs=sig_figs)
    return f"{number:,.{decimals}f}"


def fmt_currency_brl_compact(value: Any) -> str:
    number = safe_float(value)
    scale = abs(number)

    if scale >= 1_000_000_000:
        scaled, suffix = number / 1_000_000_000, "B"
    elif scale >= 1_000_000:
        scaled, suffix = number / 1_000_000, "M"
    elif scale >= 1_000:
        scaled, suffix = number / 1_000, "k"
    else:
        scaled, suffix = number, ""

    return f"R$ {format_significant(scaled)}{suffix}"


def fmt_distance_km_compact(value: Any) -> str:
    number = safe_float(value)
    scale = abs(number)

    if scale >= 1_000_000:
        scaled, unit = number / 1_000_000, "M km"
    elif scale >= 1_000:
        scaled, unit = number / 1_000, "k km"
    else:
        scaled, unit = number, "km"

    return f"{format_significant(scaled)} {unit}"


def fmt_emissions_compact(value: Any) -> str:
    number = safe_float(value)
    scale = abs(number)

    if scale >= 1_000_000_000:
        scaled, unit = number / 1_000_000_000, "Mt CO2e"
    elif scale >= 1_000_000:
        scaled, unit = number / 1_000_000, "kt CO2e"
    elif scale >= 1_000:
        scaled, unit = number / 1_000, "ton CO2e"
    else:
        scaled, unit = number, "kg CO2e"

    return f"{format_significant(scaled)} {unit}"


def path_midpoint(path_lonlat: List[List[float]]) -> List[float]:
    if not path_lonlat:
        return [0.0, 0.0]
    return path_lonlat[len(path_lonlat) // 2]


def route_metric_label(name: str, distance_km: Any, cost_brl: Any, co2e_kg: Any) -> str:
    return (
        f"{name}: {fmt_distance_km(distance_km)} | "
        f"{fmt_currency_brl(cost_brl)} | {fmt_emissions_kg(co2e_kg)}"
    )

