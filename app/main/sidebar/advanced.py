from __future__ import annotations

from typing import Iterable

import streamlit as st

from modules.fuel.truck_specs import list_truck_keys


def render_advanced(class_options: Iterable[str], port_ops_scenarios: Iterable[str]) -> None:
    st.markdown("##### Routing")
    st.selectbox("ORS profile", options=["driving-hgv", "driving-car"], key="profile")
    st.checkbox("Overwrite road cache", key="overwrite_road")

    st.markdown("##### Road")
    st.selectbox("Truck", options=sorted(list_truck_keys()), key="truck_key")

    st.markdown("##### Maritime")
    st.selectbox("Vessel class", options=list(class_options), key="vessel_class")
    st.selectbox("Allocation mode", options=["auto", "teu_share", "dwt_share"], key="allocation_mode")
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
    st.selectbox("Port ops scenario", options=list(port_ops_scenarios), key="port_ops_scenario")

    st.markdown("##### Map")
    st.selectbox("Map style", options=["Voyager", "Positron", "Dark Matter"], key="map_style")
    st.checkbox("Show first/last mile", key="map_show_first_last")
    st.checkbox("Show sea leg", key="map_show_sea")
    st.checkbox("Show direct road", key="map_show_direct")
    st.checkbox("Show ports", key="map_show_ports")
    st.checkbox("Show labels", key="map_show_labels")
    st.caption("Sea leg visualization uses one 60-degree circular arc for each consecutive port-to-port leg.")
    st.slider("Sea arc points per leg", min_value=60, max_value=400, step=10, key="map_sea_n_points", disabled=not bool(st.session_state.map_show_sea))
    st.slider("Pitch", min_value=0, max_value=60, key="map_pitch")
    st.slider("Bearing", min_value=-180, max_value=180, key="map_bearing")

    st.markdown("##### App")
    st.text_input(
        "Database target",
        key="db_path_str",
        help="Shows the active Supabase Postgres target configured through Streamlit secrets.",
        disabled=True,
    )
    st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], key="log_level")
    st.checkbox("Write log file", key="write_log_file")
    st.slider("Debug log lines", min_value=50, max_value=1000, step=50, key="log_last_n")
