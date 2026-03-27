# modules/multimodal/hoteling.py
# -*- coding: utf-8 -*-

"""
Container vessel-class hoteling (at-berth) fuel-rate loader.

Runtime logic must read preprocessed class distributions from:
    data/processed/cabotage_data/container_ship_hoteling_rate_by_class.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from modules.infra.data_assets import resolve_data_asset_path
from modules.infra.log_manager import get_logger
from modules.multimodal.container_efficiency import DEFAULT_VESSEL_CLASS

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOTELING_RATE_PATH = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "container_ship_hoteling_rate_by_class.json"


@dataclass(frozen=True)
class HotelingRateSelection:
    requested_class: str
    vessel_class: str
    fuel_rate_hoteling_t_per_h: float
    sample_size: int
    ratio_used: float
    aux_main_ratio: float
    source_path: Path


@lru_cache(maxsize=4)
def _load_payload_cached(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"Hoteling-rate artifact not found: {path}. "
            "Run 'python calcs/mrv_container_efficiency.py' first."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"Invalid hoteling-rate payload: {path}")
    return payload


def _resolve_payload(hoteling_rate_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = resolve_data_asset_path(hoteling_rate_path or DEFAULT_HOTELING_RATE_PATH)
    payload = _load_payload_cached(str(path))
    return path, payload


def _rate_median(entry: Any) -> float | None:
    if not isinstance(entry, dict):
        return None
    stats = entry.get("fuel_rate_hoteling_t_per_h")
    if not isinstance(stats, dict):
        return None
    value = stats.get("median")
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if val <= 0:
        return None
    return val


def resolve_hoteling_rate(
    vessel_class: str = DEFAULT_VESSEL_CLASS,
    *,
    hoteling_rate_path: Path | None = None,
) -> HotelingRateSelection:
    """
    Resolve selected vessel class and its median hoteling rate (t fuel / h).

    Selection order:
    1) requested class
    2) default class (container_feeder)
    3) first class with valid median in payload
    """
    source_path, payload = _resolve_payload(hoteling_rate_path)

    requested = str(vessel_class or "").strip().lower() or DEFAULT_VESSEL_CLASS
    candidates: list[str] = [requested]
    if DEFAULT_VESSEL_CLASS not in candidates:
        candidates.append(DEFAULT_VESSEL_CLASS)

    for key in payload.keys():
        if isinstance(key, str) and key not in candidates:
            candidates.append(key)

    for class_name in candidates:
        entry = payload.get(class_name)
        median = _rate_median(entry)
        if median is None:
            continue

        sample_size = 0
        ratio_used = 0.0
        aux_main_ratio = 0.0
        if isinstance(entry, dict):
            try:
                sample_size = int(entry.get("sample_size") or 0)
            except (TypeError, ValueError):
                sample_size = 0
            try:
                ratio_used = float(entry.get("ratio_used") or 0.0)
            except (TypeError, ValueError):
                ratio_used = 0.0
            try:
                aux_main_ratio = float(entry.get("aux_main_ratio") or 0.0)
            except (TypeError, ValueError):
                aux_main_ratio = 0.0

        if class_name != requested:
            _log.warning(
                "Hoteling rate for vessel class '%s' unavailable in %s. Falling back to '%s'.",
                requested,
                source_path,
                class_name,
            )

        return HotelingRateSelection(
            requested_class=requested,
            vessel_class=class_name,
            fuel_rate_hoteling_t_per_h=median,
            sample_size=sample_size,
            ratio_used=ratio_used,
            aux_main_ratio=aux_main_ratio,
            source_path=source_path,
        )

    raise ValueError(
        "No vessel class in hoteling-rate payload has a valid positive median: "
        f"{source_path}"
    )
