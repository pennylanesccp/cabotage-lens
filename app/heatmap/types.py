from __future__ import annotations

from dataclasses import dataclass, field
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
class HeatmapFailureRecord:
    destination: str
    failed_leg: Optional[str]
    failed_step: Optional[str]
    failure_reason: Optional[str]
    failure_detail: Optional[str]
    port_origin: Optional[str]
    port_destiny: Optional[str]
    retryable: bool = False
    provider: Optional[str] = None
    provider_operation: Optional[str] = None


@dataclass(frozen=True)
class HeatmapDatasetDiagnostics:
    successful_rows: int
    plottable_points: int
    skipped_missing_coordinates: int
    skipped_missing_costs: int
    skipped_missing_emissions: int
    loaded_bulk_rows: int = 0
    loaded_single_compare_rows: int = 0
    failed_destinations: List[HeatmapFailureRecord] = field(default_factory=list)

    @property
    def skipped_total(self) -> int:
        return (
            int(self.skipped_missing_coordinates)
            + int(self.skipped_missing_costs)
            + int(self.skipped_missing_emissions)
        )


@dataclass(frozen=True)
class HeatmapDataset:
    scenario: HeatmapScenario
    run: HeatmapRunInfo
    points: List[HeatmapPoint]
    max_abs_cost_delta: float
    max_abs_emissions_delta: float
    diagnostics: HeatmapDatasetDiagnostics


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
    negative_color_scale: float
    positive_color_scale: float
    elevation_scale: float
    source_point_count: int
    unique_source_coordinate_count: int
    hull_vertex_count: int
    interpolation_radius_km: float
    skipped_far_cells: int = 0
