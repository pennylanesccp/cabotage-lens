#!/usr/bin/env python3
# apps/app_streamlit.py
# -*- coding: utf-8 -*-

"""
Streamlit UI for road vs multimodal comparison.

Run with:
    streamlit run apps/app_streamlit.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pydeck as pdk
import streamlit as st

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]
else:
    ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.core.env_loader import load_repo_env

load_repo_env(ROOT / ".env")

from modules.fuel.truck_specs import list_truck_keys
from modules.infra.database_manager import DEFAULT_DB_PATH
from modules.infra.log_manager import get_logger, init_logging
from modules.multimodal import build_path_geometry, evaluate_path
from modules.multimodal.container_efficiency import (
    CONTAINER_VESSEL_CLASSES,
    DEFAULT_VESSEL_CLASS,
)
from modules.plot.cabotage_plot_helper import get_visual_sea_path

st.set_page_config(page_title="EcoFreight Streamlit", page_icon="🌍", layout="wide")

MAP_STYLES: dict[str, str] = {
    "Voyager": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
    "Positron": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Dark Matter": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
}

_log = get_logger("streamlit_app")


class StreamlitLogHandler(logging.Handler):
    """Push log lines into Streamlit session state."""

    def __init__(self, key: str = "ui_logs", max_lines: int = 800) -> None:
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
            # Keep logging non-blocking for app flow.
            pass


def _attach_streamlit_logging(level: str, write_to_file: bool) -> None:
    init_logging(level=level, write_to_file=write_to_file, force_clean=True)

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


def _zoom_from_span(lat_span: float, lon_span: float) -> float:
    span = max(lat_span, lon_span)
    if span < 0.05:
        return 12.0
    if span < 0.2:
        return 10.5
    if span < 0.8:
        return 9.0
    if span < 2.0:
        return 7.5
    if span < 5.0:
        return 6.2
    if span < 10.0:
        return 5.4
    if span < 20.0:
        return 4.7
    return 3.8


def _build_map_deck(geo: Dict[str, Any], map_style: str) -> pdk.Deck:
    origin = _safe_latlon(geo["origin"])
    destiny = _safe_latlon(geo["destiny"])

    po = geo["port_origin"]
    pd = geo["port_destiny"]
    po_coords = _safe_latlon(po["gate"]) if po.get("gate") else _safe_latlon(po)
    pd_coords = _safe_latlon(pd["gate"]) if pd.get("gate") else _safe_latlon(pd)

    try:
        sea_path = get_visual_sea_path(po_coords, pd_coords)
    except Exception as e:
        _log.error("Failed to render curved sea path: %s", e)
        sea_path = [po_coords, pd_coords]

    path_rows: List[Dict[str, Any]] = []
    if origin != po_coords:
        path_rows.append(
            {
                "name": "First mile",
                "path": _to_lonlat([origin, po_coords]),
                "color": [160, 32, 240, 210],
                "width": 6,
            }
        )

    if len(sea_path) > 1:
        path_rows.append(
            {
                "name": "Sea leg",
                "path": _to_lonlat(sea_path),
                "color": [30, 136, 229, 220],
                "width": 5,
            }
        )

    if pd_coords != destiny:
        path_rows.append(
            {
                "name": "Last mile",
                "path": _to_lonlat([pd_coords, destiny]),
                "color": [160, 32, 240, 210],
                "width": 6,
            }
        )

    path_rows.append(
        {
            "name": "Direct road",
            "path": _to_lonlat([origin, destiny]),
            "color": [229, 57, 53, 220],
            "width": 3,
        }
    )

    points = [
        {
            "label": geo["origin"]["label"],
            "kind": "Origin",
            "position": [origin[1], origin[0]],
            "color": [229, 57, 53, 245],
            "radius": 22000,
        },
        {
            "label": geo["destiny"]["label"],
            "kind": "Destiny",
            "position": [destiny[1], destiny[0]],
            "color": [229, 57, 53, 245],
            "radius": 22000,
        },
        {
            "label": f"Port: {po['name']}",
            "kind": "Port",
            "position": [po_coords[1], po_coords[0]],
            "color": [30, 136, 229, 245],
            "radius": 26000,
        },
        {
            "label": f"Port: {pd['name']}",
            "kind": "Port",
            "position": [pd_coords[1], pd_coords[0]],
            "color": [30, 136, 229, 245],
            "radius": 26000,
        },
    ]

    all_coords = [origin, destiny] + sea_path
    lats = [c[0] for c in all_coords]
    lons = [c[1] for c in all_coords]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2
    zoom = _zoom_from_span(lat_max - lat_min, lon_max - lon_min)

    deck = pdk.Deck(
        map_style=MAP_STYLES[map_style],
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=38,
            bearing=7,
        ),
        layers=[
            pdk.Layer(
                "PathLayer",
                data=path_rows,
                get_path="path",
                get_color="color",
                get_width="width",
                width_min_pixels=2,
                pickable=True,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=points,
                get_position="position",
                get_color="color",
                get_radius="radius",
                radius_min_pixels=4,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=points,
                get_position="position",
                get_text="kind",
                get_size=14,
                get_color=[245, 245, 245, 255],
                get_angle=0,
                get_text_anchor="middle",
                get_alignment_baseline="bottom",
                pickable=False,
            ),
        ],
        tooltip={"text": "{kind}\n{label}"},
    )
    return deck


def _render_results(results: Dict[str, Any]) -> None:
    road = results["road_only"]
    mm = results["multimodal"]
    sea = mm.get("sea", {})
    comp = results["comparison"]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Road cost", f"R$ {road['cost']:,.2f}")
        st.metric("Road CO2e", f"{road['co2e']:,.1f} kg")
    with col_b:
        st.metric("Multimodal cost", f"R$ {mm['total_cost']:,.2f}")
        st.metric("Multimodal CO2e", f"{mm['total_co2e']:,.1f} kg")
    with col_c:
        st.metric("Delta cost", f"R$ {comp['delta_cost']:,.2f}")
        st.metric("Savings", f"{comp['savings_pct']:,.1f}%")

    status = "BETTER" if float(comp["savings_pct"]) > 0 else "WORSE"
    st.markdown(f"**Decision:** `{status}` compared to road-only")

    sea_inputs = results.get("inputs", {})
    vessel_class = sea_inputs.get("vessel_class")
    sea_fuel_nm = sea_inputs.get("sea_fuel_per_nm_kg")
    sample_size = sea_inputs.get("vessel_sample_size")
    if vessel_class and sea_fuel_nm:
        st.caption(
            f"Sea vessel class: {vessel_class} | MRV median fuel intensity: "
            f"{float(sea_fuel_nm):.2f} kg/nm | sample: {int(sample_size or 0)}"
        )

    st.caption(
        "Sea fuel breakdown: "
        f"sailing={float(sea.get('fuel_kg_sailing') or 0.0):,.1f} kg, "
        f"hoteling={float(sea.get('hoteling_fuel_kg') or 0.0):,.1f} kg, "
        f"total={float(sea.get('fuel_kg') or 0.0):,.1f} kg"
    )


def _run_analysis(
    origin: str,
    destiny: str,
    cargo_t: float,
    truck_key: str,
    profile: str,
    overwrite_road: bool,
    db_path: Path,
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None, str | None]:
    _log.info("Routing: %s -> %s (%.3ft)", origin, destiny, cargo_t)

    geo = build_path_geometry(
        origin,
        destiny,
        ors_profile=profile,
        overwrite_road=overwrite_road,
        db_path=db_path,
    )
    if not geo or geo.get("status") != "ok":
        _log.error("Failed to build route geometry.")
        return None, None, "Failed to build route geometry. Check inputs and API key."

    _log.info("Calculating costs and emissions...")
    results = evaluate_path(
        geo,
        cargo_t=cargo_t,
        truck_key=truck_key,
        vessel_class=vessel_class,
        include_hoteling=include_hoteling,
        hoteling_hours_per_call=hoteling_hours_per_call,
        port_calls=port_calls,
    )
    if not results:
        _log.error("Failed to evaluate route.")
        return (
            geo,
            None,
            "Failed to evaluate route. Ensure processed MRV artifacts exist in data/processed.",
        )

    _log.info("Analysis finished.")
    return geo, results, None


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: radial-gradient(1200px 500px at 10% -5%, #1e3a8a33, transparent 50%),
                            radial-gradient(1200px 500px at 100% 0%, #0f766e22, transparent 40%);
            }
            .main .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }
            .hero {
                border: 1px solid rgba(148, 163, 184, 0.25);
                border-radius: 14px;
                padding: 1rem 1.2rem;
                background: linear-gradient(135deg, rgba(17,24,39,.65), rgba(3,7,18,.85));
                margin-bottom: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.session_state.setdefault("ui_logs", [])
    st.session_state.setdefault("last_geo", None)
    st.session_state.setdefault("last_results", None)

    _inject_styles()

    st.markdown(
        """
        <div class='hero'>
            <h2 style='margin:0;'>EcoFreight Streamlit</h2>
            <p style='margin:.35rem 0 0 0;'>Road vs cabotage comparison with live logs and interactive corridor map.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    class_options = list(CONTAINER_VESSEL_CLASSES)
    default_class_idx = class_options.index(DEFAULT_VESSEL_CLASS) if DEFAULT_VESSEL_CLASS in class_options else 0

    with st.sidebar:
        st.subheader("Shipment")
        origin = st.text_input("Origin", value="Pelotas, RS")
        destiny = st.text_input("Destiny", value="Manaus, AM")
        cargo_t = st.number_input("Cargo (t)", min_value=0.1, value=30.0, step=0.5)

        with st.expander("Advanced", expanded=False):
            vessel_class = st.selectbox("Vessel class", options=class_options, index=default_class_idx)
            include_hoteling = st.checkbox("Include hoteling", value=True)
            hoteling_hours_per_call = st.number_input(
                "Hoteling hours per port call",
                min_value=0.0,
                value=14.0,
                step=1.0,
            )
            port_calls = int(
                st.number_input(
                    "Port calls per voyage",
                    min_value=0,
                    value=2,
                    step=1,
                )
            )
            hoteling_hours_total = hoteling_hours_per_call * float(port_calls) if include_hoteling else 0.0
            st.caption(f"Derived hoteling hours total: {hoteling_hours_total:.1f} h")

            truck_key = st.selectbox("Truck", options=sorted(list_truck_keys()), index=0)
            profile = st.selectbox("ORS profile", options=["driving-hgv", "driving-car"], index=0)
            overwrite_road = st.checkbox("Overwrite road cache", value=False)
            db_path_str = st.text_input("DB path", value=str(DEFAULT_DB_PATH))
            map_style = st.selectbox("Map style", options=list(MAP_STYLES.keys()), index=0)
            log_level = st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], index=0)
            write_log_file = st.checkbox("Write log file", value=True)

        col_run, col_clear = st.columns(2)
        run_clicked = col_run.button("Run analysis", type="primary", use_container_width=True)
        clear_logs_clicked = col_clear.button("Clear logs", use_container_width=True)

    _attach_streamlit_logging(level=log_level, write_to_file=write_log_file)

    if clear_logs_clicked:
        st.session_state["ui_logs"] = []

    if run_clicked:
        st.session_state["ui_logs"] = []
        with st.spinner("Running route analysis..."):
            geo, results, err = _run_analysis(
                origin=origin.strip(),
                destiny=destiny.strip(),
                cargo_t=float(cargo_t),
                truck_key=truck_key,
                profile=profile,
                overwrite_road=overwrite_road,
                db_path=Path(db_path_str),
                vessel_class=vessel_class,
                include_hoteling=include_hoteling,
                hoteling_hours_per_call=float(hoteling_hours_per_call),
                port_calls=int(port_calls),
            )
        if err:
            st.error(err)
            st.session_state["last_geo"] = geo
            st.session_state["last_results"] = results
        else:
            st.success("Analysis completed.")
            st.session_state["last_geo"] = geo
            st.session_state["last_results"] = results

    geo = st.session_state.get("last_geo")
    results = st.session_state.get("last_results")

    tab_map, tab_results, tab_logs, tab_json = st.tabs(["Map", "Results", "Logs", "Raw JSON"])

    with tab_map:
        if geo:
            deck = _build_map_deck(geo, map_style=map_style)
            st.pydeck_chart(deck, use_container_width=True)
        else:
            st.info("Run an analysis to render the map.")

    with tab_results:
        if results:
            _render_results(results)
        else:
            st.info("No results yet.")

    with tab_logs:
        log_text = "\n".join(st.session_state.get("ui_logs", []))
        st.text_area("Pipeline logs", value=log_text, height=360)

    with tab_json:
        if results:
            st.json(results)
        else:
            st.info("No JSON payload yet.")


if __name__ == "__main__":
    main()
