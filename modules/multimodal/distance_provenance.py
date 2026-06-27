"""Structured maritime-distance provenance helpers."""

from __future__ import annotations

from typing import Any

NM_TO_KM = 1.852

_SOURCE_TYPE_ALIASES = {
    "sea_matrix": "seamatrix",
    "seamatrix": "seamatrix",
    "matrix": "seamatrix",
    "directional_direct": "seamatrix",
    "directional_corridor": "seamatrix",
    "haversine": "haversine_fallback",
    "haversine_fallback": "haversine_fallback",
    "fallback": "haversine_fallback",
    "manual": "manual_override",
    "manual_override": "manual_override",
    "override": "manual_override",
    "validation_override": "manual_override",
    "external": "external_reference",
    "external_reference": "external_reference",
    "reference": "external_reference",
}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def maritime_distance_source_type(
    source: Any,
    *,
    source_type: Any = None,
    is_override: bool = False,
) -> str:
    """Normalize maritime distance source labels to thesis-facing categories."""
    configured = _clean_text(source_type)
    if configured:
        key = configured.casefold().replace("-", "_").replace(" ", "_")
        return _SOURCE_TYPE_ALIASES.get(key, key)

    text = (_clean_text(source) or "").casefold()
    if "haversine" in text or "fallback" in text:
        return "haversine_fallback"
    if is_override:
        if any(token in text for token in ("antaq", "costa", "reference", "external")):
            return "external_reference"
        return "manual_override"
    if any(token in text for token in ("directional", "sea_matrix", "seamatrix", "matrix")):
        return "seamatrix"
    if any(token in text for token in ("antaq", "costa", "reference", "external")):
        return "external_reference"
    return "unknown"


def is_maritime_fallback_source(source: Any, *, source_type: Any = None) -> bool:
    return maritime_distance_source_type(source, source_type=source_type) == "haversine_fallback"


def build_maritime_distance_provenance(
    *,
    distance_km: Any,
    source: Any,
    unit: Any = "km",
    distance_value: Any = None,
    distance_nm: Any = None,
    source_type: Any = None,
    notes: Any = None,
    lower_bound_km: Any = None,
    upper_bound_km: Any = None,
    is_override: bool = False,
) -> dict[str, Any]:
    """Return a compact provenance object for a maritime distance value."""
    km = _float_or_none(distance_km)
    nm = _float_or_none(distance_nm)
    if nm is None and km is not None:
        nm = km / NM_TO_KM

    unit_text = (_clean_text(unit) or "km").casefold()
    if unit_text in {"nmi", "nautical_mile", "nautical_miles", "nautical mile", "nautical miles"}:
        unit_text = "nm"
    elif unit_text not in {"km", "nm"}:
        unit_text = "km"

    value = _float_or_none(distance_value)
    if value is None:
        value = nm if unit_text == "nm" else km

    return {
        "distance_value": value,
        "unit": unit_text,
        "distance_km": km,
        "distance_nm": nm,
        "source": _clean_text(source),
        "source_type": maritime_distance_source_type(
            source,
            source_type=source_type,
            is_override=is_override,
        ),
        "notes": _clean_text(notes),
        "lower_bound_km": _float_or_none(lower_bound_km),
        "upper_bound_km": _float_or_none(upper_bound_km),
    }
