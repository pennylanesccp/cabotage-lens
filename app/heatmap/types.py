from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class HeatmapScenario:
    origin_name: str
    cargo_t: float


@dataclass(frozen=True)
class HeatmapRunInfo:
    run_id: str
    origin_name: str
    cargo_t: float
    destination_count: int
    success_count: int
    fail_count: int
    duration_s: Optional[float]
    completed_timestamp: Any
    updated_timestamp: Any
    destination_set_id: str


@dataclass(frozen=True)
class HeatmapPoint:
    destiny_name: str
    destiny_lat: float
    destiny_lon: float
    destiny_uf: Optional[str]
    port_destiny_name: Optional[str]
    road_cost_r: float
    multimodal_cost_r: float
    cost_delta_r: float
    cost_savings_pct: Optional[float]
    road_emissions_kg: float
    multimodal_emissions_kg: float
    emissions_delta_kg: float
    emissions_savings_pct: Optional[float]
    road_distance_km: Optional[float]
    sea_km: Optional[float]
    updated_timestamp: Any


@dataclass(frozen=True)
class HeatmapDataset:
    run: HeatmapRunInfo
    points: List[HeatmapPoint]
    max_abs_cost_delta: float
    max_abs_emissions_delta: float
