from __future__ import annotations

from typing import Iterable, Tuple

import streamlit as st

from app.access import render_logout_control
from modules.fuel.truck_specs import list_truck_keys

from app.main.sidebar.branding import render_sidebar_brand
from app.main.sidebar.filters import (
    LOCATION_RESOLUTION_POLL_SECONDS,
    apply_resolved_location_values,
    ensure_location_state,
    handle_location_change,
    location_error_message,
    location_is_loading,
    route_origin_options,
    sync_location_resolution,
)
from app.main.sidebar.styles import apply_sidebar_styles
from app.main.utils.formatters import clean_place_label


def render_sidebar(
    *,
    origin_field_key: str,
    cargo_options: list[float],
    class_options: Iterable[str],
    port_ops_scenarios: Iterable[str],
) -> None:
    with st.sidebar:
        render_sidebar_brand()
        st.subheader("Scenario")
        _render_origin_field(origin_field_key)
        st.number_input("Cargo (t)", min_value=0.0, step=0.5, format="%g", key="heatmap_cargo")
        unique_cargo_values = sorted({float(value) for value in cargo_options if float(value) > 0.0})
        if unique_cargo_values:
            st.caption(
                "Stored cargo values for this origin: "
                + ", ".join(f"{value:,.1f} t" for value in unique_cargo_values[:8])
            )
        with st.expander("Advanced", expanded=False):
            _render_advanced(class_options=class_options, port_ops_scenarios=port_ops_scenarios)


def render_run_actions(*, found_count: int, missing_count: int) -> Tuple[bool, bool]:
    run_missing_label = "Run batch" if found_count <= 0 else "Run missing"
    run_missing_disabled = found_count > 0 and missing_count <= 0

    with st.sidebar:
        st.markdown("##### Batch")
        run_missing_clicked = st.button(
            run_missing_label,
            type="primary",
            width="stretch",
            disabled=run_missing_disabled,
            key="heatmap_run_missing_button",
        )
        rerun_clicked = st.button(
            "Rerun all",
            width="stretch",
            key="heatmap_rerun_all_button",
        )
        render_logout_control()
    return run_missing_clicked, rerun_clicked


def _render_origin_field(field_name: str) -> None:
    ensure_location_state(field_name)
    sync_location_resolution(field_name)
    apply_resolved_location_values([field_name])

    options = route_origin_options(current_values=[str(st.session_state.get(field_name, ""))])
    apply_sidebar_styles(field_loading={field_name: location_is_loading(field_name)})

    st.selectbox(
        "Origin",
        options=[""] + options,
        key=field_name,
        accept_new_options=True,
        format_func=lambda value: "Select an origin" if not value else clean_place_label(value),
        on_change=handle_location_change,
        args=(field_name, options),
    )

    error_message = location_error_message(field_name)
    if error_message:
        st.caption(error_message)

    @st.fragment(run_every=LOCATION_RESOLUTION_POLL_SECONDS if location_is_loading(field_name) else None)
    def _poll_origin_resolution() -> None:
        if sync_location_resolution(field_name):
            st.rerun()

    _poll_origin_resolution()


def _render_advanced(*, class_options: Iterable[str], port_ops_scenarios: Iterable[str]) -> None:
    st.markdown("##### Routing")
    st.selectbox("ORS profile", options=["driving-hgv", "driving-car"], key="profile")
    st.caption("Routes cache is never overwritten from the heatmap page.")

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
    st.number_input(
        "Port moves per call override (0 uses defaults)",
        min_value=0.0,
        step=1.0,
        key="port_moves_per_call_input",
    )
    st.selectbox("Port ops scenario", options=list(port_ops_scenarios), key="port_ops_scenario")

    st.markdown("##### App")
    st.text_input(
        "Database target",
        key="db_target_str",
        help="Shows the active Supabase Postgres target configured through Streamlit secrets.",
        disabled=True,
    )
    st.selectbox("Log level", options=["INFO", "DEBUG", "WARNING", "ERROR"], key="log_level")
    st.checkbox("Archive logs to Storage", key="archive_logs")
    st.slider("Debug log lines", min_value=50, max_value=1000, step=50, key="log_last_n")
