from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from modules.infra.log_manager import get_logger

from app.heatmap.config import (
    HEATMAP_DEFAULT_METRIC,
    HEATMAP_DESTINATION_LABEL,
    HEATMAP_PAGE_TITLE,
)
from app.heatmap.map import render_heatmap_map, render_legend
from app.heatmap.service import (
    HeatmapConfigurationError,
    HeatmapDataError,
    get_latest_run_info,
    list_cargo_options,
    rerun_heatmap,
    load_latest_dataset,
)
from app.main.sidebar.filters import (
    LOCATION_RESOLUTION_POLL_SECONDS,
    apply_resolved_location_values,
    ensure_location_state,
    handle_location_change,
    location_error_message,
    location_is_loading,
    route_endpoint_options,
    sync_location_resolution,
)
from app.heatmap.types import HeatmapDataset, HeatmapScenario
from app.main.styles import inject_css
from app.main.utils.formatters import clean_place_label
from app.main.utils.state import attach_streamlit_logging, init_state

_log = get_logger(__name__)
_HEATMAP_ORIGIN_FIELD = "heatmap_origin"



def _init_page_state() -> None:
    st.session_state.setdefault(_HEATMAP_ORIGIN_FIELD, "")
    st.session_state.setdefault("heatmap_cargo", 30.0)
    st.session_state.setdefault("heatmap_metric", HEATMAP_DEFAULT_METRIC)
    st.session_state.setdefault("heatmap_dataset", None)



def _format_timestamp(value: Any) -> str:
    if value is None:
        return "Unknown"
    text = str(value).replace("T", " ").strip()
    if "+" in text:
        text = text.split("+", 1)[0].strip()
    return text or "Unknown"



def _render_header() -> None:
    st.markdown(
        f"""
        <section style='padding: 1.4rem 1.5rem; border-radius: 24px; background: linear-gradient(135deg, rgba(233, 247, 235, 0.98), rgba(255, 244, 224, 0.96)); border: 1px solid rgba(22, 101, 52, 0.12); margin-bottom: 1rem;'>
            <p style='margin: 0 0 0.35rem 0; text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.78rem; color: #3b5d2a;'>Supabase-backed heatmap</p>
            <h1 style='margin: 0; font-size: 2rem; color: #142312;'>{escape(HEATMAP_PAGE_TITLE)}</h1>
            <p style='margin: 0.65rem 0 0 0; max-width: 52rem; color: #334155;'>
                Compare where multimodal freight wins or loses across Brazil using the latest completed batch stored in Supabase. Green always means multimodal advantage, red means road advantage.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )



def _current_scenario() -> HeatmapScenario:
    return HeatmapScenario(
        origin_name=str(st.session_state.get(_HEATMAP_ORIGIN_FIELD, "")).strip(),
        cargo_t=float(st.session_state.get("heatmap_cargo", 30.0)),
    )


def _render_origin_field() -> None:
    ensure_location_state(_HEATMAP_ORIGIN_FIELD)
    sync_location_resolution(_HEATMAP_ORIGIN_FIELD)
    apply_resolved_location_values([_HEATMAP_ORIGIN_FIELD])

    options = route_endpoint_options(current_values=[str(st.session_state.get(_HEATMAP_ORIGIN_FIELD, ""))])
    _log.debug("Prepared heatmap origin options count=%d", len(options))

    st.selectbox(
        "Origin",
        options=[""] + options,
        key=_HEATMAP_ORIGIN_FIELD,
        accept_new_options=True,
        format_func=lambda value: "Select an origin" if not value else clean_place_label(value),
        on_change=handle_location_change,
        args=(_HEATMAP_ORIGIN_FIELD, options),
    )

    error_message = location_error_message(_HEATMAP_ORIGIN_FIELD)
    if error_message:
        st.caption(error_message)

    @st.fragment(run_every=LOCATION_RESOLUTION_POLL_SECONDS if location_is_loading(_HEATMAP_ORIGIN_FIELD) else None)
    def _poll_origin_resolution() -> None:
        if sync_location_resolution(_HEATMAP_ORIGIN_FIELD):
            st.rerun()

    _poll_origin_resolution()



def _clear_loaded_dataset_if_stale(scenario: HeatmapScenario) -> None:
    dataset = st.session_state.get("heatmap_dataset")
    if not isinstance(dataset, HeatmapDataset):
        return
    if dataset.run.origin_name != scenario.origin_name or float(dataset.run.cargo_t) != float(scenario.cargo_t):
        _log.debug(
            "Clearing stale heatmap dataset cached_run_id=%s cached_origin=%s cached_cargo_t=%.3f selected_origin=%s selected_cargo_t=%.3f",
            dataset.run.run_id,
            dataset.run.origin_name,
            float(dataset.run.cargo_t),
            scenario.origin_name,
            float(scenario.cargo_t),
        )
        st.session_state.heatmap_dataset = None



def _progress_callback(progress_bar: Any, status_box: Any):
    def _callback(payload: dict[str, Any]) -> None:
        total = max(int(payload.get("total") or 0), 1)
        current = min(max(int(payload.get("current") or 0), 0), total)
        progress_bar.progress(current / total)
        message = str(payload.get("message") or "Working...")
        success_count = payload.get("success_count")
        fail_count = payload.get("fail_count")
        destination = str(payload.get("destination") or "").strip()
        parts = [message]
        if destination:
            parts.append(destination)
        if success_count is not None or fail_count is not None:
            parts.append(f"ok={int(success_count or 0)} fail={int(fail_count or 0)}")
        status_box.markdown("  ".join(parts))

    return _callback



def _render_dataset(dataset: HeatmapDataset) -> None:
    metric = st.radio(
        "View",
        options=["cost", "emissions"],
        format_func=lambda value: "Cost" if value == "cost" else "Emissions",
        horizontal=True,
        key="heatmap_metric",
    )

    better_cost = sum(1 for point in dataset.points if point.cost_delta_r > 0)
    better_emissions = sum(1 for point in dataset.points if point.emissions_delta_kg > 0)
    cols = st.columns(3)
    cols[0].metric("Destinations loaded", f"{len(dataset.points)}")
    cols[1].metric("Multimodal better on cost", f"{better_cost}")
    cols[2].metric("Multimodal better on emissions", f"{better_emissions}")

    render_legend(metric)
    render_heatmap_map(dataset, metric)



def render_page() -> None:
    init_state()
    _init_page_state()
    inject_css()
    attach_streamlit_logging(
        level=str(st.session_state.log_level),
        write_to_file=bool(st.session_state.write_log_file),
    )

    _render_header()
    _render_origin_field()

    scenario = _current_scenario()
    _clear_loaded_dataset_if_stale(scenario)

    if location_is_loading(_HEATMAP_ORIGIN_FIELD):
        st.info("Resolving origin...")
        return

    try:
        cargo_options = list_cargo_options(scenario.origin_name)
    except Exception as exc:
        _log.exception("Failed to load heatmap cargo options origin=%s", scenario.origin_name)
        st.error(f"Failed to load available cargo values: {exc}")
        return

    if float(st.session_state.heatmap_cargo) not in cargo_options:
        cargo_options = sorted(set(cargo_options + [float(st.session_state.heatmap_cargo)]))

    st.selectbox(
        "Cargo (t)",
        options=cargo_options,
        key="heatmap_cargo",
        format_func=lambda value: f"{float(value):,.1f} t",
    )

    scenario = _current_scenario()
    _clear_loaded_dataset_if_stale(scenario)

    st.caption(
        f"Hidden defaults match the main comparison flow. The heatmap rerun uses the stored destination universe: {HEATMAP_DESTINATION_LABEL}."
    )

    if not scenario.origin_name:
        st.info("Select an origin to inspect the latest stored heatmap or trigger a rerun.")
        return

    latest_run = None
    try:
        latest_run = get_latest_run_info(scenario)
    except HeatmapConfigurationError as exc:
        _log.error(
            "Heatmap latest-run lookup unavailable due to configuration origin=%s cargo_t=%.3f error=%s",
            scenario.origin_name,
            scenario.cargo_t,
            exc,
        )
        st.error(str(exc))
        return
    except Exception as exc:
        _log.exception(
            "Failed to query latest heatmap batch origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        st.error(f"Failed to query the latest heatmap batch: {exc}")
        return

    load_clicked = False
    rerun_clicked = False

    if latest_run is None:
        st.warning("No completed heatmap batch was found for this origin and cargo in Supabase.")
        rerun_clicked = st.button("Generate results", type="primary")
    else:
        st.success(
            f"Values last updated on {_format_timestamp(latest_run.completed_timestamp or latest_run.updated_timestamp)}."
        )
        st.caption(
            f"Completed batch: {latest_run.success_count}/{latest_run.destination_count} destinations succeeded. Run again if you want to refresh the Supabase results."
        )
        button_cols = st.columns(2)
        load_clicked = button_cols[0].button("Load latest", type="primary")
        rerun_clicked = button_cols[1].button("Run again")

    if load_clicked:
        _log.info(
            "Heatmap UI requested latest dataset origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        try:
            dataset = load_latest_dataset(scenario)
        except HeatmapDataError as exc:
            _log.warning(
                "Heatmap dataset is not plottable origin=%s cargo_t=%.3f error=%s",
                scenario.origin_name,
                scenario.cargo_t,
                exc,
            )
            st.error(str(exc))
        except Exception as exc:
            _log.exception(
                "Failed to load latest heatmap rows origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            st.error(f"Failed to load the latest heatmap rows: {exc}")
        else:
            if dataset is None:
                _log.warning(
                    "Heatmap dataset load returned no completed batch origin=%s cargo_t=%.3f",
                    scenario.origin_name,
                    scenario.cargo_t,
                )
                st.warning("No completed heatmap batch is currently available for this selection.")
            else:
                _log.info(
                    "Heatmap dataset loaded into session run_id=%s points=%d",
                    dataset.run.run_id,
                    len(dataset.points),
                )
                st.session_state.heatmap_dataset = dataset

    if rerun_clicked:
        _log.info(
            "Heatmap UI requested rerun origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        status_box.markdown("Starting rerun...")
        try:
            dataset = rerun_heatmap(
                scenario,
                progress_callback=_progress_callback(progress_bar, status_box),
            )
        except Exception as exc:
            _log.exception(
                "Heatmap rerun failed origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            progress_bar.empty()
            status_box.empty()
            st.error(f"Heatmap rerun failed: {exc}")
        else:
            progress_bar.progress(1.0)
            status_box.markdown("Rerun completed. Loading the latest Supabase results.")
            _log.info(
                "Heatmap rerun completed run_id=%s points=%d",
                dataset.run.run_id,
                len(dataset.points),
            )
            st.session_state.heatmap_dataset = dataset

    dataset = st.session_state.get("heatmap_dataset")
    if isinstance(dataset, HeatmapDataset):
        _render_dataset(dataset)
        return

    if latest_run is not None:
        st.info("A completed batch is available. Load the latest results or run the batch again.")

