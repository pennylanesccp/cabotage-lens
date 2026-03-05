#!/usr/bin/env python3
# apps/app_streamlit.py
# -*- coding: utf-8 -*-

"""Streamlit UI for road vs multimodal comparison."""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import pydeck as pdk
import streamlit as st

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.10
    import tomli as tomllib  # type: ignore[import-not-found]

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]
else:
    ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.core.env_loader import load_repo_env

load_repo_env(ROOT / ".env")

from modules.fuel.truck_specs import list_truck_keys
from modules.infra.database_manager import DEFAULT_DB_PATH, db_session, list_place_names
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal import build_path_geometry, evaluate_path
from modules.multimodal.container_efficiency import (
    CONTAINER_VESSEL_CLASSES,
    DEFAULT_VESSEL_CLASS,
)
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios
from modules.plot.sea_lane_brazil import BRAZIL_COASTAL_SEA_WAYPOINTS, build_sea_lane_path
from modules.plot.sea_path_pretty import build_pretty_sea_path

st.set_page_config(page_title="EcoFreight Streamlit", page_icon=":earth_americas:", layout="wide")


def _secret_or_env(key: str, default: Any = None) -> Any:
    value = st.secrets.get(key, os.getenv(key))
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
    return value


def _bool_from_any(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _validated_log_level(value: Any, default: str = "INFO") -> str:
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    candidate = str(value or default).strip().upper()
    return candidate if candidate in allowed else default


def _resolve_runtime_db_path(configured_path: Any = None) -> Path:
    configured = configured_path if configured_path is not None else _secret_or_env("CARBON_DB_PATH", str(DEFAULT_DB_PATH))
    candidate = Path(str(configured)).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate

    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        with candidate.open("a", encoding="utf-8"):
            pass
        return candidate.resolve()
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "carbon-footprint" / "carbon_footprint.sqlite"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback.resolve()


def _bootstrap_runtime_env() -> None:
    for key in ("ORS_API_KEY", "CARBON_LOG_LEVEL"):
        value = _secret_or_env(key)
        if value is not None:
            normalized = str(value).strip()
            if normalized:
                os.environ[key] = normalized

MAP_STYLES: dict[str, str] = {
    "Voyager": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    "Positron": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Dark Matter": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
}

DEFAULTS: Dict[str, Any] = {
    "origin": "Pelotas, RS",
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
    "map_show_legend": True,
    "map_sea_path_style": "Coastal lane (default)",
    "map_direct_road_style": "Arc (default)",
    "map_sea_n_points": 200,
    "map_sea_curvature": 0.25,
    "map_sea_smooth_window": 7,
    "map_pitch": 30,
    "map_bearing": 5,
    "map_zoom": 4.8,
    "map_center_lat": None,
    "map_center_lon": None,
    "log_level": "INFO",
    "write_log_file": False,
    "db_path_str": str(DEFAULT_DB_PATH),
    "log_last_n": 300,
    "log_filter": "",
}

_log = get_logger("streamlit_app")


class StreamlitLogHandler(logging.Handler):
    """Push log lines into Streamlit session state."""

    def __init__(self, key: str = "ui_logs", max_lines: int = 1000) -> None:
        super().__init__()
        self.key = key
        self.max_lines = max_lines

    def emit(self, record: logging.LogRecord) -> None:
        try:
            logs = st.session_state.setdefault(self.key, [])
            logs.append(self.format(record))
            if len(logs) > self.max_lines:
                del logs[:-self.max_lines]
        except Exception:
            pass


def _project_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return "dev"
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return str(payload.get("project", {}).get("version") or "dev")
    except Exception:
        return "dev"



def _route_endpoint_options(db_path_str: str, current_values: list[str]) -> list[str]:
    options: set[str] = set()

    for value in current_values:
        value_clean = str(value).strip()
        if value_clean:
            options.add(value_clean)

    try:
        with db_session(Path(db_path_str)) as conn:
            for value in list_place_names(conn):
                value_clean = str(value).strip()
                if value_clean:
                    options.add(value_clean)
    except Exception as exc:
        _log.debug("Could not load route endpoint options from %s: %s", db_path_str, exc)

    return sorted(options, key=str.casefold)


def _init_state() -> None:
    _bootstrap_runtime_env()

    runtime_defaults: Dict[str, Any] = dict(DEFAULTS)
    runtime_defaults["db_path_str"] = str(_resolve_runtime_db_path())
    runtime_defaults["log_level"] = _validated_log_level(
        _secret_or_env("CARBON_LOG_LEVEL", DEFAULTS["log_level"]),
        default=str(DEFAULTS["log_level"]),
    )
    runtime_defaults["write_log_file"] = _bool_from_any(
        _secret_or_env("CARBON_WRITE_LOG_FILE", DEFAULTS["write_log_file"]),
        default=bool(DEFAULTS["write_log_file"]),
    )

    for k, v in runtime_defaults.items():
        st.session_state.setdefault(k, v)

    st.session_state.setdefault("ui_logs", [])
    st.session_state.setdefault("last_geo", None)
    st.session_state.setdefault("last_results", None)
    st.session_state.setdefault("scenario_json_blob", "")


def _attach_streamlit_logging(level: str, write_to_file: bool) -> None:
    safe_level = _validated_log_level(level, default=str(DEFAULTS["log_level"]))
    try:
        init_logging(level=safe_level, write_to_file=write_to_file, force_clean=True)
    except Exception as exc:
        init_logging(level=safe_level, write_to_file=False, force_clean=True)
        st.session_state.write_log_file = False
        _log.warning("File logging disabled due to runtime filesystem limits: %s", exc)

    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, StreamlitLogHandler):
            root.removeHandler(handler)

    ui_handler = StreamlitLogHandler()
    ui_handler.setLevel(logging.DEBUG)
    ui_handler.setFormatter(
        logging.Formatter(
            fmt="[{asctime}][{levelname}][{name}] {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )
    )
    root.addHandler(ui_handler)


def _safe_latlon(point: Dict[str, Any]) -> Tuple[float, float]:
    return float(point["lat"]), float(point["lon"])


def _to_lonlat(path_latlon: List[Tuple[float, float]]) -> List[List[float]]:
    return [[float(lon), float(lat)] for lat, lon in path_latlon]


def _path_endpoint_error(path_lonlat: List[List[float]], origin: Tuple[float, float], destiny: Tuple[float, float]) -> float:
    if not path_lonlat:
        return float("inf")

    o_lon, o_lat = path_lonlat[0]
    d_lon, d_lat = path_lonlat[-1]
    return (
        abs(o_lat - origin[0])
        + abs(o_lon - origin[1])
        + abs(d_lat - destiny[0])
        + abs(d_lon - destiny[1])
    )


def _extract_direct_road_path(geo: Dict[str, Any], origin: Tuple[float, float], destiny: Tuple[float, float]) -> List[List[float]]:
    road_leg = geo.get("road_direct", {})
    if not isinstance(road_leg, dict):
        return _to_lonlat([origin, destiny])

    candidates = [
        road_leg.get("geometry"),
        road_leg.get("path"),
        road_leg.get("polyline"),
        road_leg.get("coords"),
        road_leg.get("coordinates"),
    ]

    for raw in candidates:
        if not isinstance(raw, list) or len(raw) < 2:
            continue

        first = raw[0]
        if isinstance(first, dict) and "lat" in first and "lon" in first:
            try:
                return [[float(p["lon"]), float(p["lat"])] for p in raw]
            except (TypeError, ValueError, KeyError):
                continue

        if isinstance(first, (list, tuple)) and len(first) >= 2:
            try:
                as_lonlat = [[float(p[0]), float(p[1])] for p in raw]
                as_latlon = [[float(p[1]), float(p[0])] for p in raw]
            except (TypeError, ValueError):
                continue

            score_lonlat = _path_endpoint_error(as_lonlat, origin, destiny)
            score_latlon = _path_endpoint_error(as_latlon, origin, destiny)
            return as_lonlat if score_lonlat <= score_latlon else as_latlon

    return _to_lonlat([origin, destiny])


def _zoom_from_span(lat_span: float, lon_span: float) -> float:
    span = max(lat_span, lon_span)
    if span < 0.05:
        return 11.5
    if span < 0.2:
        return 10.0
    if span < 0.8:
        return 8.5
    if span < 2.0:
        return 7.2
    if span < 5.0:
        return 6.0
    if span < 10.0:
        return 5.2
    if span < 20.0:
        return 4.5
    return 3.8


def _map_points(geo: Dict[str, Any]) -> list[Tuple[float, float]]:
    origin = _safe_latlon(geo["origin"])
    destiny = _safe_latlon(geo["destiny"])

    po = geo["port_origin"]
    pd = geo["port_destiny"]
    po_coords = _safe_latlon(po["gate"]) if po.get("gate") else _safe_latlon(po)
    pd_coords = _safe_latlon(pd["gate"]) if pd.get("gate") else _safe_latlon(pd)

    return [origin, destiny, po_coords, pd_coords]


def _fit_view(points: list[Tuple[float, float]]) -> tuple[float, float, float]:
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    center_lat = (lat_min + lat_max) / 2.0
    center_lon = (lon_min + lon_max) / 2.0
    zoom = _zoom_from_span(lat_max - lat_min, lon_max - lon_min)
    return center_lat, center_lon, zoom


def _build_map_deck(geo: Dict[str, Any]) -> pdk.Deck:
    origin = _safe_latlon(geo["origin"])
    destiny = _safe_latlon(geo["destiny"])

    po = geo["port_origin"]
    pd = geo["port_destiny"]
    po_coords = _safe_latlon(po["gate"]) if po.get("gate") else _safe_latlon(po)
    pd_coords = _safe_latlon(pd["gate"]) if pd.get("gate") else _safe_latlon(pd)

    zoom = float(st.session_state.map_zoom)
    radius_base = max(1200.0, 9000.0 - (zoom * 550.0))

    layers: list[pdk.Layer] = []

    if st.session_state.map_show_first_last:
        road_legs: list[dict[str, Any]] = []
        if origin != po_coords:
            road_legs.append(
                {
                    "name": "First mile",
                    "path": _to_lonlat([origin, po_coords]),
                    "color": [155, 89, 182, 220],
                    "width": 5,
                }
            )
        if pd_coords != destiny:
            road_legs.append(
                {
                    "name": "Last mile",
                    "path": _to_lonlat([pd_coords, destiny]),
                    "color": [155, 89, 182, 220],
                    "width": 5,
                }
            )
        if road_legs:
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=road_legs,
                    get_path="path",
                    get_color="color",
                    get_width="width",
                    width_min_pixels=2,
                    pickable=True,
                )
            )

    sea_path_style = str(st.session_state.map_sea_path_style)
    direct_road_style = str(st.session_state.map_direct_road_style)

    if st.session_state.map_show_sea:
        if sea_path_style == "Coastal lane (default)":
            sea_path = build_sea_lane_path(
                origin_latlon=po_coords,
                dest_latlon=pd_coords,
                waypoints=BRAZIL_COASTAL_SEA_WAYPOINTS,
                n_points=int(st.session_state.map_sea_n_points),
                smooth_window=int(st.session_state.map_sea_smooth_window),
            )
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=[
                        {
                            "name": "Sea leg (coastal lane)",
                            "path": sea_path,
                            "color": [33, 113, 181, 255],
                            "width": 6,
                        }
                    ],
                    get_path="path",
                    get_color="color",
                    get_width="width",
                    width_min_pixels=3,
                    pickable=True,
                )
            )
        else:
            sea_path = build_pretty_sea_path(
                origin_lat=po_coords[0],
                origin_lon=po_coords[1],
                dest_lat=pd_coords[0],
                dest_lon=pd_coords[1],
                n_points=int(st.session_state.map_sea_n_points),
                curvature=float(st.session_state.map_sea_curvature),
                smooth_window=int(st.session_state.map_sea_smooth_window),
            )
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=[
                        {
                            "name": "Sea leg (arc pretty)",
                            "path": sea_path,
                            "color": [52, 152, 219, 235],
                            "width": 4,
                        }
                    ],
                    get_path="path",
                    get_color="color",
                    get_width="width",
                    width_min_pixels=2,
                    pickable=True,
                )
            )

    if st.session_state.map_show_direct:
        if direct_road_style == "Arc (default)":
            layers.append(
                pdk.Layer(
                    "ArcLayer",
                    data=[
                        {
                            "name": "Direct road",
                            "source_position": [origin[1], origin[0]],
                            "target_position": [destiny[1], destiny[0]],
                            "source_color": [231, 76, 60, 180],
                            "target_color": [192, 57, 43, 190],
                            "width": 2,
                        }
                    ],
                    get_source_position="source_position",
                    get_target_position="target_position",
                    get_source_color="source_color",
                    get_target_color="target_color",
                    get_width="width",
                    great_circle=True,
                    pickable=True,
                )
            )
        else:
            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=[
                        {
                            "name": "Direct road",
                            "path": _extract_direct_road_path(geo, origin=origin, destiny=destiny),
                            "color": [231, 76, 60, 180],
                            "width": 2,
                        }
                    ],
                    get_path="path",
                    get_color="color",
                    get_width="width",
                    width_min_pixels=1,
                    pickable=True,
                )
            )

    points = [
        {
            "kind": "Origin",
            "label": geo["origin"]["label"],
            "lat": origin[0],
            "lon": origin[1],
            "position": [origin[1], origin[0]],
            "color": [192, 57, 43, 245],
            "radius": radius_base,
        },
        {
            "kind": "Destiny",
            "label": geo["destiny"]["label"],
            "lat": destiny[0],
            "lon": destiny[1],
            "position": [destiny[1], destiny[0]],
            "color": [192, 57, 43, 245],
            "radius": radius_base,
        },
    ]

    if st.session_state.map_show_ports:
        points.extend(
            [
                {
                    "kind": "Port",
                    "label": po["name"],
                    "lat": po_coords[0],
                    "lon": po_coords[1],
                    "position": [po_coords[1], po_coords[0]],
                    "color": [39, 174, 96, 245],
                    "radius": radius_base * 1.1,
                },
                {
                    "kind": "Port",
                    "label": pd["name"],
                    "lat": pd_coords[0],
                    "lon": pd_coords[1],
                    "position": [pd_coords[1], pd_coords[0]],
                    "color": [39, 174, 96, 245],
                    "radius": radius_base * 1.1,
                },
            ]
        )

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=points,
            get_position="position",
            get_color="color",
            get_radius="radius",
            radius_min_pixels=4,
            radius_max_pixels=18,
            pickable=True,
        )
    )

    if st.session_state.map_show_labels:
        layers.append(
            pdk.Layer(
                "TextLayer",
                data=points,
                get_position="position",
                get_text="kind",
                get_size=13,
                get_color=[248, 250, 252, 240],
                get_text_anchor="middle",
                get_alignment_baseline="bottom",
                pickable=False,
            )
        )

    return pdk.Deck(
        map_style=MAP_STYLES[st.session_state.map_style],
        initial_view_state=pdk.ViewState(
            latitude=float(st.session_state.map_center_lat),
            longitude=float(st.session_state.map_center_lon),
            zoom=float(st.session_state.map_zoom),
            pitch=float(st.session_state.map_pitch),
            bearing=float(st.session_state.map_bearing),
        ),
        layers=layers,
        tooltip={"text": "{kind}\n{label}\nlat: {lat}\nlon: {lon}"},
    )


def _scenario_payload() -> Dict[str, Any]:
    cargo_teu_value = float(st.session_state.cargo_teu_input)
    t_per_teu_default = max(float(st.session_state.t_per_teu_default), 0.1)
    allocation_mode = str(st.session_state.allocation_mode).strip().lower()
    allocation_load_factor = min(max(float(st.session_state.allocation_load_factor), 0.01), 1.0)
    return {
        "origin": st.session_state.origin.strip(),
        "destiny": st.session_state.destiny.strip(),
        "cargo_t": float(st.session_state.cargo_t),
        "cargo_teu": None if cargo_teu_value <= 0.0 else cargo_teu_value,
        "t_per_teu_default": t_per_teu_default,
        "allocation_mode": None if allocation_mode == "auto" else allocation_mode,
        "allocation_load_factor": allocation_load_factor,
        "truck_key": str(st.session_state.truck_key),
        "ors_profile": str(st.session_state.profile),
        "overwrite_road": bool(st.session_state.overwrite_road),
        "vessel_class": str(st.session_state.vessel_class),
        "include_hoteling": bool(st.session_state.include_hoteling),
        "hoteling_hours_per_call": float(st.session_state.hoteling_hours_per_call),
        "port_calls": int(st.session_state.port_calls),
        "include_port_ops": bool(st.session_state.include_port_ops),
        "full_call_mode": bool(st.session_state.full_call_mode),
        "port_moves_per_call": (
            None
            if float(st.session_state.port_moves_per_call_input) <= 0.0
            else float(st.session_state.port_moves_per_call_input)
        ),
        "port_ops_scenario": str(st.session_state.port_ops_scenario),
    }


def _resolve_cargo_teu(payload: Dict[str, Any]) -> int:
    cargo_teu = payload.get("cargo_teu")
    if isinstance(cargo_teu, (int, float)) and float(cargo_teu) > 0:
        return max(int(math.ceil(float(cargo_teu))), 1)
    cargo_t = max(float(payload.get("cargo_t") or 0.0), 0.0)
    t_per_teu_default = max(float(payload.get("t_per_teu_default") or 14.0), 0.1)
    return max(int(math.ceil(cargo_t / t_per_teu_default)), 1) if cargo_t > 0 else 0


def _render_header(version: str, payload: Dict[str, Any]) -> None:
    route_label = f"{payload['origin']} -> {payload['destiny']}"
    cargo_teu_resolved = _resolve_cargo_teu(payload)
    st.markdown(
        f"""
        <div class='hero'>
            <div class='hero-top'>
                <div>
                    <h2>EcoFreight Streamlit</h2>
                    <p>Road vs cabotage comparison with improved route map and leg-level breakdown.</p>
                </div>
                <div class='version-pill'>v{version}</div>
            </div>
            <div class='scenario-row'>
                <span class='scenario-chip'><b>Route:</b> {route_label}</span>
                <span class='scenario-chip'><b>Cargo:</b> {payload['cargo_t']:.1f} t</span>
                <span class='scenario-chip'><b>Cargo:</b> {cargo_teu_resolved} TEU</span>
                <span class='scenario-chip'><b>Vessel:</b> {payload['vessel_class']}</span>
                <span class='scenario-chip'><b>Allocation:</b> {payload['allocation_mode'] or 'auto(container->teu_share)'}</span>
                <span class='scenario-chip'><b>Hoteling:</b> {'ON' if payload['include_hoteling'] else 'OFF'}</span>
                <span class='scenario-chip'><b>Port ops:</b> {'ON' if payload['include_port_ops'] else 'OFF'}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns([1, 1, 1])
    with cols[0]:
        if st.button("Copy scenario JSON", width='stretch'):
            st.session_state.scenario_json_blob = json.dumps(payload, ensure_ascii=False, indent=2)
    with cols[1]:
        if st.session_state.scenario_json_blob:
            st.download_button(
                "Download scenario",
                data=st.session_state.scenario_json_blob,
                file_name="scenario.json",
                mime="application/json",
                width='stretch',
            )
    with cols[2]:
        if st.session_state.scenario_json_blob:
            st.caption("Scenario JSON is available in the Raw JSON tab.")


def _render_map_legend() -> None:
    if not st.session_state.map_show_legend:
        return

    st.markdown(
        """
        <div class='map-legend'>
            <div class='legend-title'>Legend</div>
            <div class='legend-item'><span class='swatch purple'></span>First/Last mile</div>
            <div class='legend-item'><span class='swatch blue'></span>Sea leg</div>
            <div class='legend-item'><span class='swatch red'></span>Direct road</div>
            <div class='legend-item'><span class='swatch green'></span>Ports</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _breakdown_frames(results: Dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    road = results.get("road_only", {})
    mm = results.get("multimodal", {})
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})
    inputs = results.get("inputs", {})

    bunker_price = float(inputs.get("bunker_price") or 0.0)
    marine_ef = float(inputs.get("marine_ef_kg_per_kg") or 0.0)

    sailing_fuel = float(sea.get("fuel_kg_sailing") or 0.0)
    hoteling_fuel = float(sea.get("hoteling_fuel_kg") or 0.0)

    sailing_cost = (sailing_fuel / 1000.0) * bunker_price
    hoteling_cost = (hoteling_fuel / 1000.0) * bunker_price
    port_ops_cost = float(sea.get("port_ops_cost") or 0.0)

    sailing_co2 = sailing_fuel * marine_ef
    hoteling_co2 = hoteling_fuel * marine_ef
    port_ops_co2 = float(sea.get("port_ops_co2e") or 0.0)

    mm_road_cost = float(first.get("cost") or 0.0) + float(last.get("cost") or 0.0)
    mm_road_co2 = float(first.get("co2e") or 0.0) + float(last.get("co2e") or 0.0)

    cost_df = pd.DataFrame(
        {
            "Road legs": [float(road.get("cost") or 0.0), mm_road_cost],
            "Sea sailing": [0.0, sailing_cost],
            "Sea hoteling": [0.0, hoteling_cost],
            "Port ops": [0.0, port_ops_cost],
        },
        index=["Road-only", "Multimodal"],
    )

    co2_df = pd.DataFrame(
        {
            "Road legs": [float(road.get("co2e") or 0.0), mm_road_co2],
            "Sea sailing": [0.0, sailing_co2],
            "Sea hoteling": [0.0, hoteling_co2],
            "Port ops": [0.0, port_ops_co2],
        },
        index=["Road-only", "Multimodal"],
    )

    return cost_df, co2_df


def _render_results(results: Dict[str, Any]) -> None:
    road = results["road_only"]
    mm = results["multimodal"]
    comp = results["comparison"]

    cards = [
        ("Road", f"R$ {float(road['cost']):,.2f}", f"CO2e {float(road['co2e']):,.1f} kg"),
        (
            "Multimodal",
            f"R$ {float(mm['total_cost']):,.2f}",
            f"CO2e {float(mm['total_co2e']):,.1f} kg",
        ),
        ("Delta cost", f"R$ {float(comp['delta_cost']):,.2f}", "Multimodal - Road"),
        ("Savings", f"{float(comp['savings_pct']):,.1f}%", "Positive is better"),
    ]

    cols = st.columns(4)
    for col, (title, value, sub) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class='kpi-card'>
                    <div class='kpi-title'>{title}</div>
                    <div class='kpi-value'>{value}</div>
                    <div class='kpi-sub'>{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    sea = mm.get("sea", {})
    inputs = results.get("inputs", {})
    vessel_class = inputs.get("vessel_class")
    sea_fuel_nm = inputs.get("sea_fuel_per_nm_kg")
    sea_fuel_twork = inputs.get("sea_fuel_g_per_tnm")
    sample_size = int(inputs.get("vessel_sample_size") or 0)
    cargo_share = float(inputs.get("cargo_allocation_share") or 0.0)
    cargo_teu_resolved = int(inputs.get("cargo_teu_resolved") or 0)
    allocation_mode_used = str(inputs.get("allocation_mode_used") or "")
    share_old_dwt = inputs.get("share_old_dwt")
    share_new_teu = inputs.get("share_new_teu")
    ratio_new_vs_old = inputs.get("ratio_new_vs_old")

    if vessel_class and sea_fuel_nm:
        st.caption(
            f"Vessel class {vessel_class} | MRV median {float(sea_fuel_nm):.2f} kg/nm | sample {sample_size}"
        )
    st.caption(
        "Cargo allocation: "
        f"mode={allocation_mode_used or 'n/a'} | "
        f"share={cargo_share:.4f} | "
        f"old_dwt={(f'{float(share_old_dwt):.4f}' if isinstance(share_old_dwt, (int, float)) else 'n/a')} | "
        f"new_teu={(f'{float(share_new_teu):.4f}' if isinstance(share_new_teu, (int, float)) else 'n/a')} | "
        f"ratio={(f'{float(ratio_new_vs_old):.3f}' if isinstance(ratio_new_vs_old, (int, float)) else 'n/a')} | "
        f"fuel_g_per_tnm={(f'{float(sea_fuel_twork):.3f}' if isinstance(sea_fuel_twork, (int, float)) else 'n/a')} | "
        f"resolved cargo={cargo_teu_resolved} TEU"
    )

    st.caption(
        "Sea fuel components: "
        f"sailing={float(sea.get('fuel_kg_sailing') or 0.0):,.1f} kg, "
        f"hoteling={float(sea.get('hoteling_fuel_kg') or 0.0):,.1f} kg, "
        f"port_ops={float(sea.get('port_ops_fuel_kg') or 0.0):,.1f} kg"
    )

    cost_df, co2_df = _breakdown_frames(results)
    tabs = st.tabs(["Cost breakdown", "CO2 breakdown"])

    with tabs[0]:
        st.bar_chart(cost_df, height=240)
        st.dataframe(cost_df.style.format("{:,.2f}"), width='stretch')

    with tabs[1]:
        st.bar_chart(co2_df, height=240)
        st.dataframe(co2_df.style.format("{:,.2f}"), width='stretch')


def _run_analysis(payload: Dict[str, Any]) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None, str | None]:
    _log.info("Routing: %s -> %s (%.3ft)", payload["origin"], payload["destiny"], payload["cargo_t"])
    db_path = _resolve_runtime_db_path(st.session_state.db_path_str)
    if str(db_path) != str(st.session_state.db_path_str):
        _log.warning("DB path '%s' unavailable; using '%s'.", st.session_state.db_path_str, db_path)
        st.session_state.db_path_str = str(db_path)

    geo = build_path_geometry(
        payload["origin"],
        payload["destiny"],
        ors_profile=payload["ors_profile"],
        overwrite_road=payload["overwrite_road"],
        db_path=db_path,
    )
    if not geo or geo.get("status") != "ok":
        _log.error("Failed to build route geometry.")
        return None, None, "Failed to build route geometry. Check inputs and API key."

    _log.info("Calculating costs and emissions...")
    results = evaluate_path(
        geo,
        cargo_t=payload["cargo_t"],
        truck_key=payload["truck_key"],
        vessel_class=payload["vessel_class"],
        include_hoteling=payload["include_hoteling"],
        hoteling_hours_per_call=payload["hoteling_hours_per_call"],
        port_calls=payload["port_calls"],
        include_port_ops=payload["include_port_ops"],
        port_moves_per_call=payload["port_moves_per_call"],
        cargo_teu=payload["cargo_teu"],
        t_per_teu_default=payload["t_per_teu_default"],
        allocation_mode=payload["allocation_mode"],
        allocation_load_factor=payload["allocation_load_factor"],
        full_call_mode=payload["full_call_mode"],
        port_ops_scenario=payload["port_ops_scenario"],
    )
    if not results:
        _log.error("Failed to evaluate route.")
        return (
            geo,
            None,
            "Failed to evaluate route. Ensure processed artifacts exist in data/processed/cabotage_data.",
        )

    _log.info("Analysis finished.")
    return geo, results, None


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(900px 360px at 5% -10%, rgba(52, 152, 219, .22), transparent 55%),
                    radial-gradient(1000px 450px at 100% 0%, rgba(22, 160, 133, .18), transparent 45%),
                    #0b1220;
            }
            .main .block-container { padding-top: 1.2rem; padding-bottom: 1.8rem; }
            .hero {
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 14px;
                padding: 1rem 1.2rem;
                background: linear-gradient(120deg, rgba(15,23,42,.88), rgba(2,6,23,.92));
                margin-bottom: 1rem;
            }
            .hero-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
            .hero h2 { margin: 0; color: #e2e8f0; }
            .hero p { margin: .35rem 0 .5rem 0; color: #cbd5e1; }
            .version-pill {
                border: 1px solid rgba(148,163,184,.35); border-radius: 999px; padding: .15rem .65rem;
                color: #cbd5e1; font-size: .85rem; white-space: nowrap;
            }
            .scenario-row { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .35rem; }
            .scenario-chip {
                border: 1px solid rgba(148, 163, 184, .3); border-radius: 999px; padding: .2rem .6rem;
                color: #cbd5e1; font-size: .84rem; background: rgba(15, 23, 42, .5);
            }
            .kpi-card {
                border: 1px solid rgba(148,163,184,.26); border-radius: 12px;
                background: linear-gradient(160deg, rgba(15,23,42,.9), rgba(2,6,23,.9));
                padding: .75rem .8rem; min-height: 98px;
            }
            .kpi-title { font-size: .83rem; color: #94a3b8; margin-bottom: .15rem; }
            .kpi-value { font-size: 1.1rem; font-weight: 650; color: #e2e8f0; margin-bottom: .2rem; }
            .kpi-sub { font-size: .78rem; color: #cbd5e1; }
            .map-legend {
                border: 1px solid rgba(148,163,184,.32); border-radius: 10px; padding: .5rem .65rem;
                background: rgba(2, 6, 23, .82); color: #e2e8f0; margin-bottom: .5rem; width: fit-content;
            }
            .legend-title { font-size: .82rem; font-weight: 700; margin-bottom: .25rem; color: #cbd5e1; }
            .legend-item { display: flex; align-items: center; gap: .4rem; font-size: .8rem; margin: .1rem 0; }
            .swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
            .swatch.purple { background: rgb(155, 89, 182); }
            .swatch.blue { background: rgb(52, 152, 219); }
            .swatch.red { background: rgb(231, 76, 60); }
            .swatch.green { background: rgb(39, 174, 96); }
            .sticky-run {
                position: sticky; bottom: 0; background: rgba(2,6,23,.95);
                padding-top: .55rem; border-top: 1px solid rgba(148,163,184,.24); z-index: 20;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _init_state()
    _inject_styles()

    class_options = list(CONTAINER_VESSEL_CLASSES)
    if st.session_state.vessel_class not in class_options:
        st.session_state.vessel_class = DEFAULT_VESSEL_CLASS

    allocation_mode_options = ["auto", "teu_share", "dwt_share"]
    if st.session_state.allocation_mode not in allocation_mode_options:
        st.session_state.allocation_mode = "auto"
    try:
        st.session_state.allocation_load_factor = min(max(float(st.session_state.allocation_load_factor), 0.01), 1.0)
    except (TypeError, ValueError):
        st.session_state.allocation_load_factor = 0.8

    port_ops_scenarios = list_port_ops_scenarios()
    if st.session_state.port_ops_scenario not in port_ops_scenarios:
        st.session_state.port_ops_scenario = (
            DEFAULT_PORT_OPS_SCENARIO if DEFAULT_PORT_OPS_SCENARIO in port_ops_scenarios else port_ops_scenarios[0]
        )

    with st.sidebar:
        st.subheader("Inputs")
        route_name_options = _route_endpoint_options(
            db_path_str=str(st.session_state.db_path_str),
            current_values=[str(st.session_state.origin), str(st.session_state.destiny)],
        )
        st.selectbox(
            "Origin",
            options=route_name_options,
            key="origin",
            accept_new_options=True,
            help="Choose a cached endpoint or type a city, state, address, or coordinates.",
        )
        st.selectbox(
            "Destination",
            options=route_name_options,
            key="destiny",
            accept_new_options=True,
            help="Choose a cached endpoint or type a city, state, address, or coordinates.",
        )
        st.number_input("Cargo (t)", min_value=0.0, step=0.5, key="cargo_t")

        clear_logs_clicked = False
        with st.expander("Advanced", expanded=False):
            st.markdown("##### Routing")
            st.selectbox("ORS profile", options=["driving-hgv", "driving-car"], key="profile")
            st.checkbox("Overwrite road cache", key="overwrite_road")

            st.markdown("##### Road")
            st.selectbox("Truck", options=sorted(list_truck_keys()), key="truck_key")

            st.markdown("##### Maritime")
            st.selectbox(
                "Vessel class",
                options=class_options,
                key="vessel_class",
                help="MRV class median fuel intensity is used for sea sailing.",
            )
            st.selectbox(
                "Allocation mode",
                options=["auto", "teu_share", "dwt_share"],
                key="allocation_mode",
                help="auto defaults to teu_share for container classes and keeps dwt_share as fallback.",
            )
            st.number_input(
                "TEU load factor",
                min_value=0.01,
                max_value=1.0,
                step=0.05,
                key="allocation_load_factor",
                help="Default from Costa papers is 0.8 (80% of nominal TEU capacity).",
                disabled=(st.session_state.allocation_mode == "dwt_share"),
            )

            st.markdown("##### Port")
            st.number_input(
                "Cargo (TEU, optional)",
                min_value=0.0,
                step=1.0,
                key="cargo_teu_input",
                help="If zero, TEU is derived from cargo_t / tonnes-per-TEU default.",
            )
            derived_teu = _resolve_cargo_teu(_scenario_payload())
            st.caption(f"Derived cargo TEU: {derived_teu}")
            st.checkbox(
                "Include hoteling",
                key="include_hoteling",
                help="At-berth fuel is derived from class sea rate via EMEP/EEA ratio assumptions.",
            )
            st.number_input("Hoteling hours per call", min_value=0.0, step=1.0, key="hoteling_hours_per_call")
            st.number_input("Port calls per voyage", min_value=0, step=1, key="port_calls")
            st.checkbox("Include port ops", key="include_port_ops")
            st.checkbox(
                "Full-call mode (terminal-level)",
                key="full_call_mode",
                help="ON uses scenario default full terminal call moves. OFF scales by cargo TEU.",
            )
            st.number_input(
                "Tonnes per TEU default",
                min_value=0.1,
                step=0.5,
                key="t_per_teu_default",
                help="Used to derive cargo TEU when explicit cargo TEU is omitted.",
            )
            st.number_input(
                "Port moves per call override (0 uses defaults)",
                min_value=0.0,
                step=1.0,
                key="port_moves_per_call_input",
            )
            st.selectbox("Port ops scenario", options=port_ops_scenarios, key="port_ops_scenario")

            if st.session_state.include_hoteling:
                total_h = float(st.session_state.hoteling_hours_per_call) * float(st.session_state.port_calls)
                st.caption(f"Derived hoteling total: {total_h:.1f} h")
            if st.session_state.include_port_ops:
                if st.session_state.port_moves_per_call_input > 0:
                    total_moves = float(st.session_state.port_moves_per_call_input) * float(st.session_state.port_calls)
                    st.caption(f"Derived port moves total (override): {total_moves:.1f}")
                elif st.session_state.full_call_mode:
                    st.caption("Port moves source: scenario full-call median (terminal-level).")
                else:
                    derived_teu = _resolve_cargo_teu(_scenario_payload())
                    total_moves = float(derived_teu) * float(st.session_state.port_calls)
                    st.caption(f"Derived port moves total (cargo-based): {total_moves:.1f}")

            st.markdown("##### Map")
            st.selectbox("Map style", options=list(MAP_STYLES.keys()), key="map_style")
            st.checkbox("Show first/last mile", key="map_show_first_last")
            st.checkbox("Show sea leg", key="map_show_sea")
            st.checkbox("Show direct road", key="map_show_direct")
            st.checkbox("Show ports", key="map_show_ports")
            st.checkbox("Show labels", key="map_show_labels")
            st.checkbox("Show legend", key="map_show_legend")
            st.selectbox(
                "Sea path style",
                options=["Coastal lane (default)", "Arc (pretty)"],
                key="map_sea_path_style",
            )
            st.selectbox(
                "Direct road style",
                options=["Arc (default)", "Polyline"],
                key="map_direct_road_style",
            )
            st.slider(
                "Sea lane points",
                min_value=50,
                max_value=400,
                step=10,
                key="map_sea_n_points",
                disabled=not bool(st.session_state.map_show_sea),
            )
            st.slider(
                "Sea arc curvature",
                min_value=0.0,
                max_value=0.5,
                step=0.01,
                key="map_sea_curvature",
                disabled=(
                    not bool(st.session_state.map_show_sea)
                    or st.session_state.map_sea_path_style != "Arc (pretty)"
                ),
            )
            st.select_slider(
                "Sea lane smooth window",
                options=[3, 5, 7, 9, 11, 13, 15],
                key="map_sea_smooth_window",
                disabled=not bool(st.session_state.map_show_sea),
            )
            st.slider("Pitch", min_value=0, max_value=60, key="map_pitch")
            st.slider("Bearing", min_value=-180, max_value=180, key="map_bearing")

            st.markdown("##### Pricing")
            st.caption("Diesel and bunker prices are loaded automatically from processed datasets.")

            st.markdown("##### App")
            st.text_input("DB path", key="db_path_str")
            st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], key="log_level")
            st.checkbox("Write log file", key="write_log_file")
            clear_logs_clicked = st.button("Clear logs", width='stretch')

        route_ok = bool(st.session_state.origin.strip()) and bool(st.session_state.destiny.strip())
        cargo_ok = float(st.session_state.cargo_t) > 0.0
        run_disabled = not (route_ok and cargo_ok)

        if run_disabled:
            st.warning("Fill origin/destination and cargo > 0 to run analysis.")

        st.markdown("<div class='sticky-run'>", unsafe_allow_html=True)
        run_clicked = st.button("Run analysis", type="primary", width='stretch', disabled=run_disabled)
        st.markdown("</div>", unsafe_allow_html=True)

    _attach_streamlit_logging(level=st.session_state.log_level, write_to_file=bool(st.session_state.write_log_file))

    if clear_logs_clicked:
        st.session_state.ui_logs = []

    payload = _scenario_payload()
    _render_header(_project_version(), payload)

    if run_clicked:
        st.session_state.ui_logs = []
        with st.spinner("Running route analysis..."):
            geo, results, err = _run_analysis(payload)

        if err:
            st.error(err)
            st.session_state.last_geo = geo
            st.session_state.last_results = results
        else:
            st.success("Analysis completed.")
            st.session_state.last_geo = geo
            st.session_state.last_results = results
            if geo:
                c_lat, c_lon, zoom = _fit_view(_map_points(geo))
                st.session_state.map_center_lat = c_lat
                st.session_state.map_center_lon = c_lon
                st.session_state.map_zoom = zoom

    geo = st.session_state.last_geo
    results = st.session_state.last_results

    left, right = st.columns([1.8, 1.2], gap="large")

    with left:
        st.markdown("#### Map")
        fit_clicked = st.button("Fit to route", width='content', disabled=geo is None)

        if fit_clicked and geo:
            c_lat, c_lon, zoom = _fit_view(_map_points(geo))
            st.session_state.map_center_lat = c_lat
            st.session_state.map_center_lon = c_lon
            st.session_state.map_zoom = zoom

        if geo:
            if st.session_state.map_center_lat is None or st.session_state.map_center_lon is None:
                c_lat, c_lon, zoom = _fit_view(_map_points(geo))
                st.session_state.map_center_lat = c_lat
                st.session_state.map_center_lon = c_lon
                st.session_state.map_zoom = zoom

            _render_map_legend()
            st.pydeck_chart(_build_map_deck(geo), width='stretch')
        else:
            st.info("Run an analysis to render the map.")

    with right:
        st.markdown("#### Results")
        if results:
            _render_results(results)
        else:
            st.info("No results yet.")

    tabs = st.tabs(["Logs", "Raw JSON"])

    with tabs[0]:
        with st.expander("Pipeline logs", expanded=True):
            st.slider("Last N lines", min_value=50, max_value=1000, step=50, key="log_last_n")
            st.text_input("Filter", key="log_filter", placeholder="Type text to filter lines")

            logs = list(st.session_state.ui_logs)
            filt = st.session_state.log_filter.strip().lower()
            if filt:
                logs = [line for line in logs if filt in line.lower()]

            shown = logs[-int(st.session_state.log_last_n) :]
            st.text_area("Logs", value="\n".join(shown), height=280)
            st.download_button(
                "Download logs",
                data="\n".join(st.session_state.ui_logs),
                file_name="ecofreight_logs.txt",
                mime="text/plain",
            )

    with tabs[1]:
        if st.session_state.scenario_json_blob:
            st.markdown("**Scenario JSON**")
            st.code(st.session_state.scenario_json_blob, language="json")
        if results:
            st.markdown("**Results JSON**")
            st.json(results)
        else:
            st.info("No JSON payload yet.")


if __name__ == "__main__":
    main()
