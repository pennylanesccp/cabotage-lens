from __future__ import annotations

"""
Manual-tuning overrides for static chained maritime route arcs.

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


# A resolved override remembers whether the current route is traversing the
# stored key in the same order or in reverse order. When a route uses the
# reverse traversal, the manual `side` is inverted automatically so the same
# physical arc geometry is reused in both directions.
@dataclass(frozen=True)
class ResolvedLegArcOverride:
    override: LegArcOverride
    stored_key: tuple[str, str]
    requested_key: tuple[str, str]
    reverse_traversal: bool


# Manual overrides for problematic maritime legs.
# Important:
# - Keys identify the physical leg, not the travel direction.
# - Keep only one entry per port pair; reverse trips reuse the same override.
# - Keys must use the normalized port identifiers returned by `normalize_port_identifier`.
# - `side` is interpreted relative to the tuple order you write here, then
#   flipped automatically when the route traverses the same leg in reverse.
#
# Copy-ready template with all adjacent master-route leg possibilities.
# Paste the entries you want into LEG_ARC_OVERRIDES and then:
# - keep `central_angle_deg` at 60.0 or change it per leg
# - optionally add `"side": "left"` or `"side": "right"`
MASTER_ROUTE_LEG_OVERRIDE_TEMPLATE: dict[tuple[str, str], dict[str, object]] = {
    ("porto-do-rio-grande", "porto-de-imbituba"): {"central_angle_deg": 60.0},
    ("porto-de-imbituba", "porto-de-itajai"): {"central_angle_deg": 60.0},
    ("porto-de-itajai", "porto-de-navegantes"): {"central_angle_deg": 60.0},
    ("porto-de-navegantes", "porto-de-sao-francisco-do-sul"): {"central_angle_deg": 60.0},
    ("porto-de-sao-francisco-do-sul", "porto-de-itapoa"): {"central_angle_deg": 60.0},
    ("porto-de-itapoa", "porto-de-paranagua"): {"central_angle_deg": 60.0},
    ("porto-de-paranagua", "porto-de-santos"): {"central_angle_deg": 60.0},
    ("porto-de-santos", "porto-de-sao-sebastiao"): {"central_angle_deg": 60.0},
    ("porto-de-sao-sebastiao", "porto-de-angra-dos-reis"): {"central_angle_deg": 60.0},
    ("porto-de-angra-dos-reis", "porto-de-itaguai"): {"central_angle_deg": 60.0},
    ("porto-de-itaguai", "porto-do-rio-de-janeiro"): {"central_angle_deg": 30.0},
    ("porto-do-rio-de-janeiro", "porto-de-vitoria"): {"central_angle_deg": 30.0},
    ("porto-de-vitoria", "porto-de-salvador"): {"central_angle_deg": 60.0},
    ("porto-de-salvador", "porto-de-aratu"): {"central_angle_deg": 60.0},
    ("porto-de-aratu", "porto-de-maceio"): {"central_angle_deg": 60.0},
    ("porto-de-maceio", "porto-de-suape"): {"central_angle_deg": 60.0},
    ("porto-de-suape", "porto-do-recife"): {"central_angle_deg": 60.0},
    ("porto-do-recife", "porto-de-cabedelo"): {"central_angle_deg": 60.0},
    ("porto-de-cabedelo", "porto-de-natal"): {"central_angle_deg": 60.0},
    ("porto-de-natal", "porto-de-fortaleza"): {"central_angle_deg": 60.0},
    ("porto-de-fortaleza", "porto-do-pecem"): {"central_angle_deg": 60.0},
    ("porto-do-pecem", "porto-do-itaqui"): {"central_angle_deg": 60.0},
    ("porto-do-itaqui", "porto-de-belem"): {"central_angle_deg": 60.0},
    ("porto-de-belem", "porto-de-vila-do-conde"): {"central_angle_deg": 60.0},
    ("porto-de-vila-do-conde", "porto-de-santana"): {"central_angle_deg": 60.0},
    ("porto-de-santana", "porto-de-santarem"): {"central_angle_deg": 60.0},
    ("porto-de-santarem", "porto-de-manaus"): {"central_angle_deg": 60.0},
}
# Backward-compatible alias for older references to the former template name.
MASTER_ROUTE_DIRECTIONAL_LEG_OVERRIDE_TEMPLATE = MASTER_ROUTE_LEG_OVERRIDE_TEMPLATE

LEG_ARC_OVERRIDES: dict[tuple[str, str], dict[str, object]] = {
    # Example:
    # This single entry is reused for both Santos -> Sao Sebastiao and
    # Sao Sebastiao -> Santos. The side is interpreted relative to the tuple
    # order written here, then flipped automatically for reverse traversal.
    ("porto-de-itaguai", "porto-do-rio-de-janeiro"): {
        "central_angle_deg": 30.0,
        "side": "right",
    },
    ("porto-do-rio-de-janeiro", "porto-de-vitoria"): {
        "central_angle_deg": 30.0,
        "side": "right",
    },
}


def normalize_port_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def normalize_directional_leg_key(start_port: Any, end_port: Any) -> tuple[str, str]:
    return normalize_port_identifier(start_port), normalize_port_identifier(end_port)


def normalize_leg_key(start_port: Any, end_port: Any) -> tuple[str, str]:
    start_key, end_key = normalize_directional_leg_key(start_port, end_port)
    return (start_key, end_key) if start_key <= end_key else (end_key, start_key)


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


def flip_arc_side(side: str | None) -> str | None:
    normalized = normalize_arc_side(side)
    if normalized is None:
        return None
    return "left" if normalized == "right" else "right"


def resolve_leg_arc_override(start_port: Any, end_port: Any) -> ResolvedLegArcOverride | None:
    requested_key = normalize_directional_leg_key(start_port, end_port)
    physical_key = normalize_leg_key(start_port, end_port)
    matches: list[ResolvedLegArcOverride] = []

    for raw_key, raw_override in LEG_ARC_OVERRIDES.items():
        if not isinstance(raw_key, tuple) or len(raw_key) != 2:
            raise ValueError(f"LEG_ARC_OVERRIDES keys must be 2-tuples, got {raw_key!r}")
        stored_key = normalize_directional_leg_key(raw_key[0], raw_key[1])
        if normalize_leg_key(stored_key[0], stored_key[1]) != physical_key:
            continue
        override = parse_leg_arc_override(raw_override)
        if override is None:
            continue
        matches.append(
            ResolvedLegArcOverride(
                override=override,
                stored_key=stored_key,
                requested_key=requested_key,
                reverse_traversal=(requested_key != stored_key),
            )
        )

    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(
            "LEG_ARC_OVERRIDES contains duplicate entries for the same physical leg "
            f"{physical_key!r}; keep only one direction because arcs are static."
        )
    return matches[0]


def get_leg_arc_override(start_port: Any, end_port: Any) -> LegArcOverride | None:
    resolved = resolve_leg_arc_override(start_port, end_port)
    return None if resolved is None else resolved.override
