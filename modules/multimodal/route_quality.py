"""Route-quality warnings for cabotage interpretation."""

from __future__ import annotations

import unicodedata
from typing import Any, Mapping

from modules.multimodal.distance_provenance import is_maritime_fallback_source

# Warning heuristic only. This is not a validation rule, model formula, or route
# optimization constraint.
MIN_MEANINGFUL_SEA_LEG_KM = 50.0


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


def _normalized_text(value: Any) -> str:
    text = _clean_text(value) or ""
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_accents.casefold().split())


def _port_name(port: Any) -> str | None:
    if not isinstance(port, Mapping):
        return None
    return _clean_text(port.get("name") or port.get("label") or port.get("code"))


def _warning(code: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "warning",
        "title": "Cabotage route warning",
        "message": message,
    }


def build_route_quality_warnings(geometry: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return non-blocking warnings for cabotage route interpretation."""
    warnings: list[dict[str, str]] = []

    origin_port_name = _port_name(geometry.get("port_origin"))
    destination_port_name = _port_name(geometry.get("port_destiny"))
    same_port = bool(
        origin_port_name
        and destination_port_name
        and _normalized_text(origin_port_name) == _normalized_text(destination_port_name)
    )
    if same_port:
        warnings.append(
            _warning(
                "same_port",
                (
                    "The selected origin and destination ports are the same, so this result should not be "
                    "interpreted as a meaningful cabotage alternative."
                ),
            )
        )

    sea_leg = geometry.get("sea_leg") if isinstance(geometry.get("sea_leg"), Mapping) else {}
    sea_distance_km = _float_or_none(sea_leg.get("distance_km"))
    if sea_distance_km is None:
        warnings.append(
            _warning(
                "missing_maritime_distance",
                (
                    "The maritime leg distance is missing, so this result should be reviewed before it is used "
                    "for cabotage interpretation."
                ),
            )
        )
    elif sea_distance_km <= 0.0:
        warnings.append(
            _warning(
                "zero_maritime_distance",
                (
                    "The maritime leg distance is zero, so this result should not be interpreted as a meaningful "
                    "cabotage alternative."
                ),
            )
        )
    elif sea_distance_km < MIN_MEANINGFUL_SEA_LEG_KM:
        warnings.append(
            _warning(
                "small_maritime_distance",
                (
                    "The maritime leg distance is very short for a cabotage corridor; treat this result as a "
                    "screening estimate."
                ),
            )
        )

    provenance = sea_leg.get("distance_provenance") if isinstance(sea_leg, Mapping) else None
    source_type = provenance.get("source_type") if isinstance(provenance, Mapping) else None
    if is_maritime_fallback_source(sea_leg.get("source"), source_type=source_type):
        warnings.append(
            _warning(
                "fallback_maritime_distance",
                "The maritime distance was estimated using fallback logic; treat this result as a screening estimate.",
            )
        )

    road_distance_km = _float_or_none((geometry.get("road_direct") or {}).get("distance_km"))
    first_mile_km = _float_or_none((geometry.get("first_mile") or {}).get("distance_km")) or 0.0
    last_mile_km = _float_or_none((geometry.get("last_mile") or {}).get("distance_km")) or 0.0
    access_distance_km = first_mile_km + last_mile_km
    if (
        road_distance_km is not None
        and road_distance_km > 0.0
        and sea_distance_km is not None
        and 0.0 <= sea_distance_km < MIN_MEANINGFUL_SEA_LEG_KM
        and access_distance_km >= road_distance_km
    ):
        warnings.append(
            _warning(
                "access_dominates_local_cabotage",
                (
                    "The cabotage option's road access distance is greater than or equal to the direct road "
                    "distance while the maritime leg is local-scale; treat the comparison as a route-selection "
                    "warning rather than a modal conclusion."
                ),
            )
        )

    return warnings
