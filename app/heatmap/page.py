from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

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
    list_origin_options,
    rerun_heatmap,
    load_latest_dataset,
)
from app.heatmap.types import HeatmapDataset, HeatmapScenario
from app.main.styles import inject_css
from app.main.utils.state import attach_streamlit_logging, init_state



def _init_page_state() -> None:
    st.session_state.setdefault("heatmap_origin", "")
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
        origin_name=str(st.session_state.get("heatmap_origin", "")).strip(),
        cargo_t=float(st.session_state.get("heatmap_cargo", 30.0)),
    )



def _clear_loaded_dataset_if_stale(scenario: HeatmapScenario) -> None:
    dataset = st.session_state.get("heatmap_dataset")
    if not isinstance(dataset, HeatmapDataset):
        return
    if dataset.run.origin_name != scenario.origin_name or float(dataset.run.cargo_t) != float(scenario.cargo_t):
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

    try:
        origins = list_origin_options()
    except HeatmapConfigurationError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Failed to load heatmap origins from Supabase: {exc}")
        return

    options = [""] + origins
    st.selectbox(
        "Origin",
        options=options,
        key="heatmap_origin",
        accept_new_options=True,
        format_func=lambda value: "Select an origin" if not value else value,
    )

    scenario = _current_scenario()
    _clear_loaded_dataset_if_stale(scenario)

    try:
        cargo_options = list_cargo_options(scenario.origin_name)
    except Exception as exc:
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
        st.error(str(exc))
        return
    except Exception as exc:
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
        try:
            dataset = load_latest_dataset(scenario)
        except HeatmapDataError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Failed to load the latest heatmap rows: {exc}")
        else:
            st.session_state.heatmap_dataset = dataset

    if rerun_clicked:
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        status_box.markdown("Starting rerun...")
        try:
            dataset = rerun_heatmap(
                scenario,
                progress_callback=_progress_callback(progress_bar, status_box),
            )
        except Exception as exc:
            progress_bar.empty()
            status_box.empty()
            st.error(f"Heatmap rerun failed: {exc}")
        else:
            progress_bar.progress(1.0)
            status_box.markdown("Rerun completed. Loading the latest Supabase results.")
            st.session_state.heatmap_dataset = dataset

    dataset = st.session_state.get("heatmap_dataset")
    if isinstance(dataset, HeatmapDataset):
        _render_dataset(dataset)
        return

    if latest_run is not None:
        st.info("A completed batch is available. Load the latest results or run the batch again.")

