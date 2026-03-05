# modules/multimodal/container_efficiency.py
# -*- coding: utf-8 -*-

"""
Container vessel-class fuel intensity loader.

Runtime logic must read preprocessed class distributions from:
    data/processed/cabotage_data/container_ship_efficiency_classes.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

CONTAINER_VESSEL_CLASSES: tuple[str, ...] = (
    "container_small",
    "container_feeder",
    "container_large",
)
DEFAULT_VESSEL_CLASS = "container_feeder"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTAINER_EFFICIENCY_PATH = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "container_ship_efficiency_classes.json"


@dataclass(frozen=True)
class VesselClassEfficiency:
    requested_class: str
    vessel_class: str
    fuel_per_nm: float
    fuel_g_per_tnm: float | None
    size_proxy_t_median: float | None
    teu_capacity: float | None
    lightship_t: float | None
    sample_size: int
    source_path: Path


@lru_cache(maxsize=4)
def _load_payload_cached(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"Container efficiency artifact not found: {path}. "
            "Run 'python calcs/mrv_container_efficiency.py' first."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"Invalid container efficiency payload: {path}")
    return payload


def _resolve_payload(efficiency_json_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    path = Path(efficiency_json_path or DEFAULT_CONTAINER_EFFICIENCY_PATH).resolve()
    payload = _load_payload_cached(str(path))
    return path, payload


def _metric_median(entry: Any, metric_key: str) -> float | None:
    if not isinstance(entry, dict):
        return None
    stats = entry.get(metric_key)
    if not isinstance(stats, dict):
        return None
    value = stats.get("median")
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    return val


def _class_median(entry: Any) -> float | None:
    val = _metric_median(entry, "fuel_per_nm")
    if val is None or val <= 0:
        return None
    return val


def list_vessel_classes(efficiency_json_path: Path | None = None) -> tuple[str, ...]:
    """Return available vessel classes, preferring canonical order."""
    try:
        _, payload = _resolve_payload(efficiency_json_path)
    except Exception:
        return CONTAINER_VESSEL_CLASSES

    out: list[str] = [name for name in CONTAINER_VESSEL_CLASSES if name in payload]
    for name in payload.keys():
        if isinstance(name, str) and name not in out:
            out.append(name)
    return tuple(out) if out else CONTAINER_VESSEL_CLASSES


def resolve_vessel_class_efficiency(
    vessel_class: str = DEFAULT_VESSEL_CLASS,
    *,
    efficiency_json_path: Path | None = None,
) -> VesselClassEfficiency:
    """
    Resolve selected vessel class and its median fuel_per_nm (kg / n mile).

    Selection order:
    1) requested class
    2) default class (container_feeder)
    3) first class with valid median in payload
    """
    source_path, payload = _resolve_payload(efficiency_json_path)

    requested = str(vessel_class or "").strip().lower() or DEFAULT_VESSEL_CLASS
    candidates: list[str] = [requested]
    if DEFAULT_VESSEL_CLASS not in candidates:
        candidates.append(DEFAULT_VESSEL_CLASS)

    for key in payload.keys():
        if isinstance(key, str) and key not in candidates:
            candidates.append(key)

    for class_name in candidates:
        entry = payload.get(class_name)
        median = _class_median(entry)
        if median is None:
            continue

        sample_size = 0
        fuel_g_per_tnm: float | None = None
        size_proxy_t_median: float | None = None
        teu_capacity: float | None = None
        lightship_t: float | None = None
        if isinstance(entry, dict):
            try:
                sample_size = int(entry.get("sample_size") or 0)
            except (TypeError, ValueError):
                sample_size = 0
            f_twork = _metric_median(entry, "fuel_g_per_tnm")
            if isinstance(f_twork, (int, float)) and f_twork > 0:
                fuel_g_per_tnm = float(f_twork)
            size_proxy = _metric_median(entry, "size_proxy_t")
            if isinstance(size_proxy, (int, float)) and size_proxy > 0:
                size_proxy_t_median = float(size_proxy)
            try:
                cap = float(entry.get("teu_capacity"))
                if cap > 0:
                    teu_capacity = cap
            except (TypeError, ValueError):
                teu_capacity = None
            try:
                light = float(entry.get("lightship_t"))
                if light > 0:
                    lightship_t = light
            except (TypeError, ValueError):
                lightship_t = None

        if class_name != requested:
            _log.warning(
                "Vessel class '%s' unavailable or invalid in %s. Falling back to '%s'.",
                requested,
                source_path,
                class_name,
            )

        return VesselClassEfficiency(
            requested_class=requested,
            vessel_class=class_name,
            fuel_per_nm=median,
            fuel_g_per_tnm=fuel_g_per_tnm,
            size_proxy_t_median=size_proxy_t_median,
            teu_capacity=teu_capacity,
            lightship_t=lightship_t,
            sample_size=sample_size,
            source_path=source_path,
        )

    raise ValueError(
        "No vessel class in container efficiency payload has a valid positive fuel_per_nm median: "
        f"{source_path}"
    )
