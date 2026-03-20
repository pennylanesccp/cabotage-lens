from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass(frozen=True)
class HeatmapScenario:
    origin_name: str
    cargo_t: float
    truck_key: str
    ors_profile: str
    vessel_class: str
    include_hoteling: bool
    hoteling_hours_per_call: float
    port_calls: int
    include_port_ops: bool
    port_moves_per_call: Optional[float]
    cargo_teu: Optional[float]
    t_per_teu_default: float
    allocation_mode: Optional[str]
    allocation_load_factor: float
    full_call_mode: bool
    port_ops_scenario: str


@dataclass(frozen=True)
class HeatmapRunInfo:
    run_id: Optional[str]
    origin_name: str
    cargo_t: float
    destination_count: int
    found_count: int
    success_count: int
    fail_count: int
    missing_count: int
    pending_count: int
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
    scenario: HeatmapScenario
    run: HeatmapRunInfo
    points: List[HeatmapPoint]
    max_abs_cost_delta: float
    max_abs_emissions_delta: float


HeatmapCoordinate = Tuple[float, float]
HeatmapPolygon = Tuple[HeatmapCoordinate, ...]


@dataclass(frozen=True)
class HeatmapSurfaceCell:
    polygon: HeatmapPolygon
    center_lat: float
    center_lon: float
    percentage_value: float
    absolute_value: float
    fill_color: Tuple[int, int, int, int]
    elevation_m: float
    nearest_destiny_name: str
    nearest_destiny_uf: Optional[str]
    nearest_distance_km: float


@dataclass(frozen=True)
class HeatmapSurface:
    metric: str
    mode: str
    cells: List[HeatmapSurfaceCell]
    color_scale: float
    elevation_scale: float
