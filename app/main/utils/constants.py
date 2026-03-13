from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from modules.fuel.truck_specs import list_truck_keys
from modules.multimodal.container_efficiency import DEFAULT_VESSEL_CLASS
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO

ROOT = Path(__file__).resolve().parents[3]

PAGE_TITLE = "EcoFreight Brazil"
PAGE_ICON = ":earth_americas:"
PAGE_LAYOUT = "wide"
DEFAULT_ORIGIN = "Avenida Professor Luciano Gualberto, Sao Paulo"

MAP_STYLES: dict[str, str] = {
    "Voyager": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    "Positron": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Dark Matter": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
}

DEFAULTS: Dict[str, Any] = {
    "origin": DEFAULT_ORIGIN,
    "destiny": "Manaus, AM",
    "cargo_t": 30.0,
    "cargo_teu_input": 0.0,
    "profile": "driving-hgv",
    "overwrite_road": False,
    "truck_key": sorted(list_truck_keys())[0] if list_truck_keys() else "semi_27t",
    "vessel_class": DEFAULT_VESSEL_CLASS,
    "include_hoteling": True,
    "hoteling_hours_per_call": 14.0,
    "port_calls": 2,
    "include_port_ops": True,
    "port_moves_per_call_input": 0.0,
    "port_ops_scenario": DEFAULT_PORT_OPS_SCENARIO,
    "t_per_teu_default": 14.0,
    "allocation_mode": "auto",
    "allocation_load_factor": 0.8,
    "full_call_mode": False,
    "map_style": "Voyager",
    "map_show_first_last": True,
    "map_show_sea": True,
    "map_show_direct": True,
    "map_show_ports": True,
    "map_show_labels": True,
    "map_sea_path_style": "Coastal lane (default)",
    "map_sea_n_points": 100,
    "map_sea_curvature": 0.25,
    "map_sea_smooth_window": 7,
    "map_pitch": 30,
    "map_bearing": 5,
    "map_zoom": 4.8,
    "map_center_lat": None,
    "map_center_lon": None,
    "log_level": "INFO",
    "archive_logs": False,
    "db_target_str": "postgresql://***",
    "log_last_n": 300,
}
