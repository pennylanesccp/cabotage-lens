from __future__ import annotations

from html import escape
from typing import Any, Iterable

import streamlit as st

from app.main.cards import render_route_quality_warnings, render_summary_cards
from app.main.run_feedback import (
    inject_run_feedback_css,
    make_progress_callback,
    render_live_run_logs,
    status_card,
)
from modules.multimodal.container_efficiency import (
    DEFAULT_VESSEL_CLASS,
    list_vessel_classes,
)
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios

from app.main.details import render_details
from app.main.map import fit_view, map_points, render_map, render_map_placeholder
from app.main.sidebar import render_sidebar
from app.main.styles import inject_css
from app.main.utils.antaq import run_antaq_refresh_for_app
from app.main.utils.constants import PAGE_TITLE
from app.main.utils.formatters import clean_place_label, safe_float
from app.main.utils.pipeline import build_scenario_payload, run_analysis
from app.main.utils.state import attach_streamlit_logging, init_state


def _render_header(payload: dict[str, Any]) -> None:
    origin_label = clean_place_label(payload.get("origin"))
    destiny_label = clean_place_label(payload.get("destiny"))

    st.markdown(
        f"""
        <section class='page-header'>
            <h1>{escape(PAGE_TITLE)}</h1>
            <p>{escape(origin_label)} -> {escape(destiny_label)} | {safe_float(payload.get('cargo_t')):,.1f} t cargo compared across road and cabotage.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _normalize_choice(session_key: str, valid_options: Iterable[str], default_value: str) -> None:
    options = list(valid_options)
    if not options:
        st.session_state[session_key] = default_value
        return

    if st.session_state.get(session_key) not in options:
        st.session_state[session_key] = default_value if default_value in options else options[0]


def render_page() -> None:
    init_state()
    inject_css()
    inject_run_feedback_css()

    class_options = list(list_vessel_classes())
    _normalize_choice("vessel_class", class_options, DEFAULT_VESSEL_CLASS)

    _normalize_choice("allocation_mode", ["auto", "teu_share", "dwt_share"], "auto")
    try:
        st.session_state.allocation_load_factor = min(max(float(st.session_state.allocation_load_factor), 0.01), 1.0)
    except (TypeError, ValueError):
        st.session_state.allocation_load_factor = 0.8

    port_ops_scenarios = list(list_port_ops_scenarios())
    _normalize_choice("port_ops_scenario", port_ops_scenarios, DEFAULT_PORT_OPS_SCENARIO)

    attach_streamlit_logging(
        level=str(st.session_state.log_level),
        archive_to_storage=bool(st.session_state.archive_logs),
    )

    run_clicked = render_sidebar(class_options=class_options, port_ops_scenarios=port_ops_scenarios)

    payload = build_scenario_payload(st.session_state)
    _render_header(payload)

    if run_clicked:
        st.session_state.ui_logs = []
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        cooldown_box = st.empty()
        log_box = st.empty()
        geo = None
        results = None
        err = None
        run_failed = False
        resolved_db_target = str(st.session_state.db_target_str)
        progress_callback = make_progress_callback(
            progress_bar,
            status_box,
            cooldown_box,
            log_box,
            default_working_message="Running router analysis...",
            log_title="Live router log",
        )
        status_box.markdown(status_card("Starting router analysis...", tone="info"), unsafe_allow_html=True)
        render_live_run_logs(log_box, title="Live router log")

        refresh_requested = bool(st.session_state.get("refresh_antaq_before_run", False))
        try:
            if refresh_requested:
                run_antaq_refresh_for_app(progress_callback=progress_callback)
            geo, results, err, resolved_db_target = run_analysis(
                payload=payload,
                progress_callback=progress_callback,
            )
        except Exception as exc:
            progress_bar.empty()
            cooldown_box.empty()
            render_live_run_logs(log_box, title="Live router log")
            status_box.markdown(status_card("Router analysis failed.", tone="error"), unsafe_allow_html=True)
            st.error(f"Router analysis failed: {exc}")
            run_failed = True

        if resolved_db_target != str(st.session_state.db_target_str):
            st.session_state.db_target_str = resolved_db_target

        if run_failed:
            pass
        elif err:
            progress_bar.empty()
            cooldown_box.empty()
            render_live_run_logs(log_box, title="Live router log")
            status_box.markdown(status_card("Router analysis failed.", tone="error"), unsafe_allow_html=True)
            st.error(err)
            st.session_state.last_geo = geo
            st.session_state.last_results = results
        else:
            progress_bar.progress(1.0)
            cooldown_box.empty()
            log_box.empty()
            status_box.markdown(
                status_card("Router analysis completed.", tone="success"),
                unsafe_allow_html=True,
            )
            st.session_state.last_geo = geo
            st.session_state.last_results = results
            if geo:
                c_lat, c_lon, zoom = fit_view(map_points(geo))
                st.session_state.map_center_lat = c_lat
                st.session_state.map_center_lon = c_lon
                st.session_state.map_zoom = zoom

    geo = st.session_state.last_geo
    results = st.session_state.last_results

    render_summary_cards(results)
    render_route_quality_warnings(results)

    if geo:
        if st.session_state.map_center_lat is None or st.session_state.map_center_lon is None:
            c_lat, c_lon, zoom = fit_view(map_points(geo))
            st.session_state.map_center_lat = c_lat
            st.session_state.map_center_lon = c_lon
            st.session_state.map_zoom = zoom

        render_map(geo, results=results, state=st.session_state)
    else:
        render_map_placeholder()

    render_details(payload=payload, geo=geo, results=results)


def main() -> None:
    render_page()


if __name__ == "__main__":
    render_page()
