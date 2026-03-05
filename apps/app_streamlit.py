#!/usr/bin/env python3
# apps/app_streamlit.py
# -*- coding: utf-8 -*-

"""Streamlit UI for road vs multimodal comparison."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sys
import tempfile
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

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




def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_place_label(label: Any) -> str:
    text = str(label or "").strip()
    if not text:
        return ""

    text = re.sub(r"\s*,\s*(?:brazil|brasil)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*,\s*,+", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,")


def _fmt_distance_km(value: Any) -> str:
    return f"{_safe_float(value):,.1f} km"


def _fmt_currency_brl(value: Any) -> str:
    return f"R$ {_safe_float(value):,.2f}"


def _fmt_emissions_kg(value: Any) -> str:
    return f"{_safe_float(value):,.1f} kg CO2e"


def _path_midpoint(path_lonlat: List[List[float]]) -> List[float]:
    if not path_lonlat:
        return [0.0, 0.0]
    return path_lonlat[len(path_lonlat) // 2]


def _route_metric_label(name: str, distance_km: Any, cost_brl: Any, co2e_kg: Any) -> str:
    return (
        f"{name}: {_fmt_distance_km(distance_km)} | "
        f"{_fmt_currency_brl(cost_brl)} | {_fmt_emissions_kg(co2e_kg)}"
    )


def _maritime_component_breakdown(results: Dict[str, Any]) -> Dict[str, float]:
    sea = results.get("multimodal", {}).get("sea", {})
    inputs = results.get("inputs", {})

    bunker_price = _safe_float(inputs.get("bunker_price"))
    marine_ef = _safe_float(inputs.get("marine_ef_kg_per_kg"))

    sailing_fuel_kg = _safe_float(sea.get("fuel_kg_sailing"))
    hoteling_fuel_kg = _safe_float(sea.get("hoteling_fuel_kg"))

    sailing_cost_brl = (sailing_fuel_kg / 1000.0) * bunker_price
    sailing_co2e_kg = sailing_fuel_kg * marine_ef

    hoteling_cost_brl = (hoteling_fuel_kg / 1000.0) * bunker_price
    hoteling_co2e_kg = hoteling_fuel_kg * marine_ef

    port_ops_cost_brl = _safe_float(sea.get("port_ops_cost"))
    port_ops_co2e_kg = _safe_float(sea.get("port_ops_co2e"))

    return {
        "sailing_cost_brl": sailing_cost_brl,
        "sailing_co2e_kg": sailing_co2e_kg,
        "hoteling_cost_brl": hoteling_cost_brl,
        "hoteling_co2e_kg": hoteling_co2e_kg,
        "port_ops_cost_brl": port_ops_cost_brl,
        "port_ops_co2e_kg": port_ops_co2e_kg,
    }


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


def _extract_leg_path(leg: Dict[str, Any], origin: Tuple[float, float], destiny: Tuple[float, float]) -> List[List[float]]:
    if not isinstance(leg, dict):
        return _to_lonlat([origin, destiny])

    candidates = [
        leg.get("geometry"),
        leg.get("path"),
        leg.get("polyline"),
        leg.get("coords"),
        leg.get("coordinates"),
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


def _build_map_deck(geo: Dict[str, Any], results: Dict[str, Any] | None = None) -> pdk.Deck:
    results = results or {}

    origin = _safe_latlon(geo["origin"])
    destiny = _safe_latlon(geo["destiny"])

    po = geo["port_origin"]
    pd = geo["port_destiny"]
    po_coords = _safe_latlon(po["gate"]) if po.get("gate") else _safe_latlon(po)
    pd_coords = _safe_latlon(pd["gate"]) if pd.get("gate") else _safe_latlon(pd)

    road = results.get("road_only", {})
    mm = results.get("multimodal", {})
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})

    maritime = _maritime_component_breakdown(results)

    origin_name = clean_place_label(geo.get("origin", {}).get("label")) or clean_place_label(st.session_state.origin)
    destiny_name = clean_place_label(geo.get("destiny", {}).get("label")) or clean_place_label(st.session_state.destiny)
    port_origin_name = clean_place_label(po.get("name"))
    port_destiny_name = clean_place_label(pd.get("name"))

    direct_path = _extract_leg_path(geo.get("road_direct", {}), origin, destiny)
    first_path = _extract_leg_path(geo.get("first_mile", {}), origin, po_coords)
    last_path = _extract_leg_path(geo.get("last_mile", {}), pd_coords, destiny)

    sea_path_style = str(st.session_state.map_sea_path_style)
    if sea_path_style == "Coastal lane (default)":
        sea_path = build_sea_lane_path(
            origin_latlon=po_coords,
            dest_latlon=pd_coords,
            waypoints=BRAZIL_COASTAL_SEA_WAYPOINTS,
            n_points=int(st.session_state.map_sea_n_points),
            smooth_window=int(st.session_state.map_sea_smooth_window),
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

    route_rows: list[dict[str, Any]] = []

    if st.session_state.map_show_direct:
        route_rows.append(
            {
                "route_name": "Road",
                "path": direct_path,
                "color": [220, 72, 62, 215],
                "width": 5,
                "tooltip": _route_metric_label(
                    "Road",
                    road.get("distance_km"),
                    road.get("cost"),
                    road.get("co2e"),
                ),
            }
        )

    if st.session_state.map_show_first_last and origin != po_coords:
        route_rows.append(
            {
                "route_name": "Road (pre-carriage)",
                "path": first_path,
                "color": [155, 89, 182, 220],
                "width": 5,
                "tooltip": _route_metric_label(
                    "Road (pre-carriage)",
                    first.get("distance_km"),
                    first.get("cost"),
                    first.get("co2e"),
                ),
            }
        )

    if st.session_state.map_show_sea:
        route_rows.append(
            {
                "route_name": f"Sea (cabotage): {port_origin_name} -> {port_destiny_name}",
                "path": sea_path,
                "color": [41, 128, 185, 230],
                "width": 6,
                "tooltip": _route_metric_label(
                    f"Sea (cabotage): {port_origin_name} -> {port_destiny_name}",
                    sea.get("distance_km"),
                    maritime.get("sailing_cost_brl"),
                    maritime.get("sailing_co2e_kg"),
                ),
            }
        )

    if st.session_state.map_show_first_last and pd_coords != destiny:
        route_rows.append(
            {
                "route_name": "Road (on-carriage)",
                "path": last_path,
                "color": [155, 89, 182, 220],
                "width": 5,
                "tooltip": _route_metric_label(
                    "Road (on-carriage)",
                    last.get("distance_km"),
                    last.get("cost"),
                    last.get("co2e"),
                ),
            }
        )

    for row in route_rows:
        row["label_position"] = _path_midpoint(row.get("path") or [])
        row["label"] = row["tooltip"]
        row["hitbox_color"] = [255, 255, 255, 4]
        row["hitbox_width"] = 18

    zoom = float(st.session_state.map_zoom)
    radius_base = max(1200.0, 9000.0 - (zoom * 550.0))

    layers: list[pdk.Layer] = []
    if route_rows:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=route_rows,
                get_path="path",
                get_color="hitbox_color",
                get_width="hitbox_width",
                width_min_pixels=12,
                pickable=True,
            )
        )
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=route_rows,
                get_path="path",
                get_color="color",
                get_width="width",
                width_min_pixels=3,
                pickable=True,
            )
        )

    if st.session_state.map_show_labels and route_rows:
        layers.append(
            pdk.Layer(
                "TextLayer",
                data=route_rows,
                get_position="label_position",
                get_text="label",
                get_size=11,
                get_color=[245, 247, 250, 250],
                get_text_anchor="middle",
                get_alignment_baseline="center",
                pickable=False,
            )
        )

    points = [
        {
            "kind": "Origin",
            "label": origin_name,
            "position": [origin[1], origin[0]],
            "lat": origin[0],
            "lon": origin[1],
            "color": [192, 57, 43, 245],
            "radius": radius_base,
            "tooltip": f"Origin: {origin_name}",
        },
        {
            "kind": "Destination",
            "label": destiny_name,
            "position": [destiny[1], destiny[0]],
            "lat": destiny[0],
            "lon": destiny[1],
            "color": [192, 57, 43, 245],
            "radius": radius_base,
            "tooltip": f"Destination: {destiny_name}",
        },
    ]

    if st.session_state.map_show_ports:
        port_ops_cost_each = _safe_float(maritime.get("port_ops_cost_brl")) / 2.0
        port_ops_co2_each = _safe_float(maritime.get("port_ops_co2e_kg")) / 2.0
        hoteling_cost_each = _safe_float(maritime.get("hoteling_cost_brl")) / 2.0
        hoteling_co2_each = _safe_float(maritime.get("hoteling_co2e_kg")) / 2.0

        points.extend(
            [
                {
                    "kind": "Port",
                    "label": port_origin_name,
                    "position": [po_coords[1], po_coords[0]],
                    "lat": po_coords[0],
                    "lon": po_coords[1],
                    "color": [39, 174, 96, 245],
                    "radius": radius_base * 1.1,
                    "tooltip": (
                        f"Origin port: {port_origin_name}\n"
                        f"Port ops: {_fmt_currency_brl(port_ops_cost_each)} | {_fmt_emissions_kg(port_ops_co2_each)}\n"
                        f"Hoteling: {_fmt_currency_brl(hoteling_cost_each)} | {_fmt_emissions_kg(hoteling_co2_each)}\n"
                        f"Port total: {_fmt_currency_brl(port_ops_cost_each + hoteling_cost_each)} | "
                        f"{_fmt_emissions_kg(port_ops_co2_each + hoteling_co2_each)}"
                    ),
                },
                {
                    "kind": "Port",
                    "label": port_destiny_name,
                    "position": [pd_coords[1], pd_coords[0]],
                    "lat": pd_coords[0],
                    "lon": pd_coords[1],
                    "color": [39, 174, 96, 245],
                    "radius": radius_base * 1.1,
                    "tooltip": (
                        f"Destination port: {port_destiny_name}\n"
                        f"Port ops: {_fmt_currency_brl(port_ops_cost_each)} | {_fmt_emissions_kg(port_ops_co2_each)}\n"
                        f"Hoteling: {_fmt_currency_brl(hoteling_cost_each)} | {_fmt_emissions_kg(hoteling_co2_each)}\n"
                        f"Port total: {_fmt_currency_brl(port_ops_cost_each + hoteling_cost_each)} | "
                        f"{_fmt_emissions_kg(port_ops_co2_each + hoteling_co2_each)}"
                    ),
                },
            ]
        )

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=points,
            get_position="position",
            get_color=[255, 255, 255, 4],
            get_radius="radius",
            radius_min_pixels=16,
            radius_max_pixels=30,
            pickable=True,
        )
    )

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=points,
            get_position="position",
            get_color="color",
            get_radius="radius",
            radius_min_pixels=5,
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
                get_color=[248, 250, 252, 245],
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
        tooltip={"text": "{tooltip}"},
    )


def _overlay_cards_html(results: Dict[str, Any] | None) -> str:
    if not results:
        return (
            "<div class='map-overlay-cards'>"
            "<article class='overlay-card overlay-note'>"
            "<h4>Run analysis</h4>"
            "<p>Map overlays appear here with route totals.</p>"
            "</article>"
            "</div>"
        )

    road = results.get("road_only", {})
    mm = results.get("multimodal", {})
    comp = results.get("comparison", {})

    road_cost = _safe_float(road.get("cost"))
    mm_cost = _safe_float(mm.get("total_cost"))
    road_co2e = _safe_float(road.get("co2e"))
    mm_co2e = _safe_float(mm.get("total_co2e"))

    best_option = "Multimodal" if mm_cost < road_cost else "Road"
    delta_cost = _safe_float(comp.get("delta_cost"))
    delta_co2e = _safe_float(comp.get("delta_co2e"))

    return f"""
<div class='map-overlay-cards'>
  <article class='overlay-card'>
    <h4>Road</h4>
    <p>{_fmt_distance_km(road.get('distance_km'))}</p>
    <p>{_fmt_currency_brl(road_cost)}</p>
    <p>{_fmt_emissions_kg(road_co2e)}</p>
  </article>
  <article class='overlay-card'>
    <h4>Multimodal (Road + Cabotage)</h4>
    <p>{_fmt_distance_km(_safe_float(mm.get('first_mile', {}).get('distance_km')) + _safe_float(mm.get('sea', {}).get('distance_km')) + _safe_float(mm.get('last_mile', {}).get('distance_km')))}</p>
    <p>{_fmt_currency_brl(mm_cost)}</p>
    <p>{_fmt_emissions_kg(mm_co2e)}</p>
  </article>
  <article class='overlay-card overlay-highlight'>
    <h4>Best option: {escape(best_option)}</h4>
    <p>Delta cost: {_fmt_currency_brl(delta_cost)}</p>
    <p>Delta emissions: {_fmt_emissions_kg(delta_co2e)}</p>
  </article>
</div>
"""


def _render_map_with_overlay(geo: Dict[str, Any], results: Dict[str, Any] | None) -> None:
    map_height = 560
    deck = _build_map_deck(geo, results=results)

    deck_html = deck.to_html(
        as_string=True,
        notebook_display=False,
        iframe_width="100%",
        iframe_height=map_height,
    )

    overlay_html = _overlay_cards_html(results)
    overlay_css = """
<style>
body {
  margin: 0;
  overflow: hidden;
  position: relative;
  font-family: "Segoe UI", sans-serif;
}
#overlay-root {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 1000;
  pointer-events: none;
}
.map-overlay-cards {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  align-items: flex-start;
}
.overlay-card {
  pointer-events: auto;
  min-width: 210px;
  max-width: 320px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  background: rgba(12, 18, 31, 0.9);
  color: #e2e8f0;
  padding: 0.55rem 0.7rem;
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.42);
}
.overlay-card h4 {
  margin: 0 0 0.2rem 0;
  font-size: 0.84rem;
  color: #cbd5e1;
}
.overlay-card p {
  margin: 0.05rem 0;
  font-size: 0.79rem;
}
.overlay-highlight {
  border-color: rgba(251, 191, 36, 0.55);
}
.overlay-note {
  max-width: 280px;
}
@media (max-width: 840px) {
  #overlay-root {
    left: 8px;
    right: 8px;
    top: 8px;
  }
  .map-overlay-cards {
    flex-direction: column;
  }
  .overlay-card {
    min-width: 0;
    width: 100%;
    max-width: 100%;
  }
}
</style>
"""

    if "</head>" in deck_html:
        deck_html = deck_html.replace("</head>", overlay_css + "</head>", 1)
    else:
        deck_html = overlay_css + deck_html

    if "<body>" in deck_html:
        deck_html = deck_html.replace("<body>", f"<body><div id='overlay-root'>{overlay_html}</div>", 1)
    else:
        deck_html = f"<div id='overlay-root'>{overlay_html}</div>" + deck_html

    components.html(deck_html, height=map_height, scrolling=False)


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


def _render_header(payload: Dict[str, Any]) -> None:
    origin_label = clean_place_label(payload.get("origin"))
    destiny_label = clean_place_label(payload.get("destiny"))

    st.markdown(
        f"""
        <section class='page-header'>
            <h1>EcoFreight Brazil</h1>
            <p>{escape(origin_label)} -> {escape(destiny_label)} | {_safe_float(payload.get('cargo_t')):,.1f} t cargo compared across road and cabotage.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _summary_table(results: Dict[str, Any]) -> pd.DataFrame:
    road = results.get("road_only", {})
    mm = results.get("multimodal", {})

    mm_distance = (
        _safe_float(mm.get("first_mile", {}).get("distance_km"))
        + _safe_float(mm.get("sea", {}).get("distance_km"))
        + _safe_float(mm.get("last_mile", {}).get("distance_km"))
    )

    rows = [
        {
            "Route": "Road",
            "Distance": _fmt_distance_km(road.get("distance_km")),
            "Cost": _fmt_currency_brl(road.get("cost")),
            "Emissions": _fmt_emissions_kg(road.get("co2e")),
        },
        {
            "Route": "Multimodal (Road + Cabotage)",
            "Distance": _fmt_distance_km(mm_distance),
            "Cost": _fmt_currency_brl(mm.get("total_cost")),
            "Emissions": _fmt_emissions_kg(mm.get("total_co2e")),
        },
    ]
    return pd.DataFrame(rows)


def _leg_breakdown_table(results: Dict[str, Any]) -> pd.DataFrame:
    mm = results.get("multimodal", {})
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})
    maritime = _maritime_component_breakdown(results)

    rows = [
        {
            "Leg": "Road to port (pre-carriage)",
            "Distance": _fmt_distance_km(first.get("distance_km")),
            "Cost": _fmt_currency_brl(first.get("cost")),
            "Emissions": _fmt_emissions_kg(first.get("co2e")),
        },
        {
            "Leg": "Sea leg (cabotage)",
            "Distance": _fmt_distance_km(sea.get("distance_km")),
            "Cost": _fmt_currency_brl(maritime.get("sailing_cost_brl")),
            "Emissions": _fmt_emissions_kg(maritime.get("sailing_co2e_kg")),
        },
        {
            "Leg": "Port ops",
            "Distance": "-",
            "Cost": _fmt_currency_brl(maritime.get("port_ops_cost_brl")),
            "Emissions": _fmt_emissions_kg(maritime.get("port_ops_co2e_kg")),
        },
        {
            "Leg": "Hoteling",
            "Distance": "-",
            "Cost": _fmt_currency_brl(maritime.get("hoteling_cost_brl")),
            "Emissions": _fmt_emissions_kg(maritime.get("hoteling_co2e_kg")),
        },
        {
            "Leg": "Road from port (on-carriage)",
            "Distance": _fmt_distance_km(last.get("distance_km")),
            "Cost": _fmt_currency_brl(last.get("cost")),
            "Emissions": _fmt_emissions_kg(last.get("co2e")),
        },
    ]
    return pd.DataFrame(rows)


def _assumptions_table(results: Dict[str, Any], payload: Dict[str, Any]) -> pd.DataFrame:
    inputs = results.get("inputs", {})
    assumption_rows = [
        ("Truck preset", str(payload.get("truck_key") or "n/a")),
        ("Vessel class", str(inputs.get("vessel_class") or payload.get("vessel_class") or "n/a")),
        ("Diesel price source", str(inputs.get("diesel_price_source") or "n/a")),
        ("Marine fuel type", str(inputs.get("marine_fuel_type") or "n/a")),
        ("Marine EF", f"{_safe_float(inputs.get('marine_ef_kg_per_kg')):.4f} kg CO2e/kg"),
        ("Allocation mode", str(inputs.get("allocation_mode_used") or payload.get("allocation_mode") or "auto")),
        ("TEU load factor", f"{_safe_float(inputs.get('allocation_load_factor')):.2f}"),
        ("Port ops scenario", str(payload.get("port_ops_scenario") or "n/a")),
        ("Hoteling", "enabled" if payload.get("include_hoteling") else "disabled"),
    ]
    return pd.DataFrame(assumption_rows, columns=["Parameter", "Value"])


def _render_details_section(payload: Dict[str, Any], geo: Dict[str, Any] | None, results: Dict[str, Any] | None) -> None:
    st.markdown("### Details")

    if not results:
        st.info("Run an analysis to populate breakdown, assumptions, and debug details.")
        return

    summary_df = _summary_table(results)
    legs_df = _leg_breakdown_table(results)
    assumptions_df = _assumptions_table(results, payload)

    with st.expander("Breakdown", expanded=True):
        st.markdown("**Total summary**")
        st.dataframe(summary_df, hide_index=True, width='stretch')
        st.markdown("**Multimodal leg breakdown**")
        st.dataframe(legs_df, hide_index=True, width='stretch')

    with st.expander("Assumptions", expanded=False):
        st.dataframe(assumptions_df, hide_index=True, width='stretch')

    with st.expander("Debug", expanded=False):
        with st.expander("Raw logs", expanded=False):
            logs = list(st.session_state.ui_logs)
            shown = logs[-int(st.session_state.log_last_n):]
            st.text_area("Logs", value="\n".join(shown), height=220)

        with st.expander("Pipeline JSON", expanded=False):
            pipeline_blob = {
                "scenario": payload,
                "geo": geo,
                "results": results,
            }
            st.code(json.dumps(pipeline_blob, ensure_ascii=False, indent=2), language="json")


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
                    radial-gradient(900px 360px at 8% -12%, rgba(52, 152, 219, .16), transparent 55%),
                    radial-gradient(900px 420px at 100% 0%, rgba(22, 160, 133, .14), transparent 45%),
                    #0b1220;
            }
            .main .block-container {
                padding-top: 1rem;
                padding-bottom: 1.75rem;
            }
            section[data-testid="stSidebar"] .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
            }
            section[data-testid="stSidebar"] .stButton > button {
                margin-top: 0.65rem;
            }
            .page-header {
                margin-bottom: 0.7rem;
            }
            .page-header h1 {
                margin: 0;
                font-size: 1.7rem;
                color: #e2e8f0;
                line-height: 1.2;
            }
            .page-header p {
                margin: 0.22rem 0 0 0;
                color: #cbd5e1;
                font-size: 0.96rem;
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
        st.subheader("Scenario")
        route_name_options = _route_endpoint_options(
            db_path_str=str(st.session_state.db_path_str),
            current_values=[str(st.session_state.origin), str(st.session_state.destiny)],
        )

        st.selectbox(
            "Origin",
            options=route_name_options,
            key="origin",
            accept_new_options=True,
            format_func=clean_place_label,
        )
        st.selectbox(
            "Destination",
            options=route_name_options,
            key="destiny",
            accept_new_options=True,
            format_func=clean_place_label,
        )
        st.number_input("Cargo (t)", min_value=0.0, step=0.5, key="cargo_t")

        with st.expander("Advanced", expanded=False):
            st.markdown("##### Routing")
            st.selectbox("ORS profile", options=["driving-hgv", "driving-car"], key="profile")
            st.checkbox("Overwrite road cache", key="overwrite_road")

            st.markdown("##### Road")
            st.selectbox("Truck", options=sorted(list_truck_keys()), key="truck_key")

            st.markdown("##### Maritime")
            st.selectbox("Vessel class", options=class_options, key="vessel_class")
            st.selectbox("Allocation mode", options=allocation_mode_options, key="allocation_mode")
            st.number_input(
                "TEU load factor",
                min_value=0.01,
                max_value=1.0,
                step=0.05,
                key="allocation_load_factor",
                disabled=(st.session_state.allocation_mode == "dwt_share"),
            )

            st.markdown("##### Port")
            st.number_input("Cargo (TEU, optional)", min_value=0.0, step=1.0, key="cargo_teu_input")
            st.checkbox("Include hoteling", key="include_hoteling")
            st.number_input("Hoteling hours per call", min_value=0.0, step=1.0, key="hoteling_hours_per_call")
            st.number_input("Port calls per voyage", min_value=0, step=1, key="port_calls")
            st.checkbox("Include port ops", key="include_port_ops")
            st.checkbox("Full-call mode (terminal-level)", key="full_call_mode")
            st.number_input("Tonnes per TEU default", min_value=0.1, step=0.5, key="t_per_teu_default")
            st.number_input("Port moves per call override (0 uses defaults)", min_value=0.0, step=1.0, key="port_moves_per_call_input")
            st.selectbox("Port ops scenario", options=port_ops_scenarios, key="port_ops_scenario")

            st.markdown("##### Map")
            st.selectbox("Map style", options=list(MAP_STYLES.keys()), key="map_style")
            st.checkbox("Show first/last mile", key="map_show_first_last")
            st.checkbox("Show sea leg", key="map_show_sea")
            st.checkbox("Show direct road", key="map_show_direct")
            st.checkbox("Show ports", key="map_show_ports")
            st.checkbox("Show labels", key="map_show_labels")
            st.selectbox("Sea path style", options=["Coastal lane (default)", "Arc (pretty)"], key="map_sea_path_style")
            st.slider("Sea lane points", min_value=50, max_value=400, step=10, key="map_sea_n_points", disabled=not bool(st.session_state.map_show_sea))
            st.slider(
                "Sea arc curvature",
                min_value=0.0,
                max_value=0.5,
                step=0.01,
                key="map_sea_curvature",
                disabled=(not bool(st.session_state.map_show_sea) or st.session_state.map_sea_path_style != "Arc (pretty)"),
            )
            st.select_slider("Sea lane smooth window", options=[3, 5, 7, 9, 11, 13, 15], key="map_sea_smooth_window", disabled=not bool(st.session_state.map_show_sea))
            st.slider("Pitch", min_value=0, max_value=60, key="map_pitch")
            st.slider("Bearing", min_value=-180, max_value=180, key="map_bearing")

            st.markdown("##### App")
            st.text_input("DB path", key="db_path_str")
            st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], key="log_level")
            st.checkbox("Write log file", key="write_log_file")
            st.slider("Debug log lines", min_value=50, max_value=1000, step=50, key="log_last_n")

        route_ok = bool(st.session_state.origin.strip()) and bool(st.session_state.destiny.strip())
        cargo_ok = float(st.session_state.cargo_t) > 0.0
        run_disabled = not (route_ok and cargo_ok)

        if run_disabled:
            st.caption("Fill origin, destination, and cargo above zero.")

        run_clicked = st.button("Run analysis", type="primary", width='stretch', disabled=run_disabled)

    _attach_streamlit_logging(level=st.session_state.log_level, write_to_file=bool(st.session_state.write_log_file))

    payload = _scenario_payload()
    _render_header(payload)

    if run_clicked:
        st.session_state.ui_logs = []
        with st.spinner("Running route analysis..."):
            geo, results, err = _run_analysis(payload)

        if err:
            st.error(err)
            st.session_state.last_geo = geo
            st.session_state.last_results = results
        else:
            st.session_state.last_geo = geo
            st.session_state.last_results = results
            if geo:
                c_lat, c_lon, zoom = _fit_view(_map_points(geo))
                st.session_state.map_center_lat = c_lat
                st.session_state.map_center_lon = c_lon
                st.session_state.map_zoom = zoom

    geo = st.session_state.last_geo
    results = st.session_state.last_results

    if geo:
        if st.session_state.map_center_lat is None or st.session_state.map_center_lon is None:
            c_lat, c_lon, zoom = _fit_view(_map_points(geo))
            st.session_state.map_center_lat = c_lat
            st.session_state.map_center_lon = c_lon
            st.session_state.map_zoom = zoom

        _render_map_with_overlay(geo, results)
    else:
        st.info("Run an analysis to render the map.")

    _render_details_section(payload=payload, geo=geo, results=results)


if __name__ == "__main__":
    main()
