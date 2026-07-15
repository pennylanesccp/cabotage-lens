from __future__ import annotations

from typing import Tuple

import streamlit as st

from app.access import render_logout_control
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
) -> None:
    with st.sidebar:
        render_sidebar_brand()
        st.markdown("<p class='sidebar-section-label'>Heatmap scenario</p>", unsafe_allow_html=True)
        _render_origin_field(origin_field_key)
        st.number_input("Cargo (t)", min_value=0.0, step=0.5, format="%g", key="heatmap_cargo")
        st.caption(
            "Fixed methodology: driving-car routing, default truck and vessel assumptions, with hoteling and port "
            "operations included. Existing road-route cache entries are never overwritten."
        )


def render_run_actions(*, has_origin: bool, has_loaded_dataset: bool) -> Tuple[bool, bool, bool]:
    with st.sidebar:
        st.markdown("<p class='sidebar-section-label'>Actions</p>", unsafe_allow_html=True)
        load_clicked = st.button(
            "Load stored results",
            type="primary",
            width="stretch",
            disabled=(not has_origin),
            key="heatmap_load_surface_button",
            help=(
                "Load every successful comparison result stored in Supabase for this exact scenario, across tracked "
                "destination sets, without calling ORS or LocationIQ."
            ),
        )
        run_missing_clicked = st.button(
            "Run missing",
            width="stretch",
            disabled=(not has_origin),
            key="heatmap_run_missing_button",
            help="Compute destinations that are still missing or whose latest stored attempt failed for this scenario.",
        )
        rerun_clicked = st.button(
            "Rerun all",
            width="stretch",
            disabled=(not has_origin),
            key="heatmap_rerun_all_button",
            help="Recompute the full stored destination set for this scenario.",
        )
        if has_loaded_dataset:
            st.caption("The loaded surface stays in session until you change the scenario or refresh it.")
        render_logout_control()
    return load_clicked, run_missing_clicked, rerun_clicked


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
