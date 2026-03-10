# modules/multimodal/scenario_keys.py
# -*- coding: utf-8 -*-

"""
Helpers for building stable bulk-evaluation scenario keys.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.addressing.text import ascii_place_text

_PLACE_INPUT_KEYS = ("input_origin", "input_destiny")


def normalize_bulk_place_input(value: Any) -> str:
    """Normalize user-facing place inputs to the canonical ASCII form used in persisted scenario keys."""
    return ascii_place_text(value)


def canonicalize_bulk_scenario_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of the payload with place inputs normalized for stable hashing."""
    canonical = dict(payload)
    for key in _PLACE_INPUT_KEYS:
        if key in canonical:
            canonical[key] = normalize_bulk_place_input(canonical.get(key))
    return canonical


def build_bulk_scenario_key(payload: Mapping[str, Any]) -> str:
    """Build a deterministic scenario key for bulk results."""
    canonical = canonicalize_bulk_scenario_payload(payload)
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
