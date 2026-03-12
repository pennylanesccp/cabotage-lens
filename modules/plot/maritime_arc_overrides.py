from __future__ import annotations

"""
Directional manual-tuning overrides for chained maritime route arcs.

This module is intentionally small and user-editable: tune only the legs that
still need help after the automatic side-selection logic runs.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_LEG_CENTRAL_ANGLE_DEG = 60.0
VALID_ARC_SIDES = frozenset({"left", "right"})


@dataclass(frozen=True)
class LegArcOverride:
    central_angle_deg: float | None = None
    side: str | None = None


# Directional manual overrides for problematic maritime legs.
# Important:
# - Keys are directional: (A, B) is different from (B, A).
# - Keys must use the normalized port identifiers returned by `normalize_port_identifier`.
# - `side` refers to the visible arc-bulge side relative to the directed leg A -> B.
#
# Example dictionary with the supported override shapes:
# EXAMPLE_LEG_ARC_OVERRIDES = {
#     ("porto-de-santos", "porto-de-sao-sebastiao"): {
#         "central_angle_deg": 48.0,
#         "side": "right",
#     },
#     ("porto-de-salvador", "porto-de-aratu"): {
#         "central_angle_deg": 55.0,
#     },
#     ("porto-de-vila-do-conde", "porto-de-santarem"): {
#         "side": "left",
#     },
#     ("porto-de-santarem", "porto-de-manaus"): {
#         "central_angle_deg": 42.0,
#         "side": "left",
#     },
# }
LEG_ARC_OVERRIDES: dict[tuple[str, str], dict[str, object]] = {
    # Example:
    # ("porto-de-santos", "porto-de-sao-sebastiao"): {
    #     "central_angle_deg": 48.0,
    #     "side": "right",
    # },
}


def normalize_port_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def normalize_leg_key(start_port: Any, end_port: Any) -> tuple[str, str]:
    return normalize_port_identifier(start_port), normalize_port_identifier(end_port)


def normalize_arc_side(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text not in VALID_ARC_SIDES:
        raise ValueError(f"Unsupported maritime arc side override: {value!r}")
    return text


def parse_leg_arc_override(raw: Mapping[str, Any] | None) -> LegArcOverride | None:
    if not raw:
        return None

    angle = raw.get("central_angle_deg")
    central_angle_deg = None if angle in (None, "") else float(angle)
    if central_angle_deg is not None and central_angle_deg <= 0.0:
        raise ValueError(f"central_angle_deg must be positive, got {central_angle_deg!r}")

    side = normalize_arc_side(raw.get("side"))
    if central_angle_deg is None and side is None:
        return None
    return LegArcOverride(
        central_angle_deg=central_angle_deg,
        side=side,
    )


def get_leg_arc_override(start_port: Any, end_port: Any) -> LegArcOverride | None:
    return parse_leg_arc_override(LEG_ARC_OVERRIDES.get(normalize_leg_key(start_port, end_port)))
