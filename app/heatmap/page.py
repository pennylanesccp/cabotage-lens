from __future__ import annotations

from html import escape
from typing import Any, Iterable

import streamlit as st

from modules.infra.log_manager import get_logger
from modules.multimodal.container_efficiency import DEFAULT_VESSEL_CLASS, list_vessel_classes
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios

from app.heatmap.config import (
    HEATMAP_DEFAULT_METRIC,
    HEATMAP_DESTINATION_LABEL,
    HEATMAP_METRICS,
    HEATMAP_PAGE_TITLE,
    HEATMAP_SURFACE_MODE_DEFAULT,
    HEATMAP_SURFACE_MODES,
)
from app.heatmap.map import render_heatmap_map, render_legend
from app.heatmap.surface import build_surface
from app.heatmap.service import (
    HeatmapConfigurationError,
    HeatmapDataError,
    get_heatmap_status,
    list_cargo_options,
    load_current_dataset,
    rerun_heatmap,
    run_heatmap,
)
from app.heatmap.sidebar import render_run_actions, render_sidebar
from app.heatmap.types import HeatmapDataset, HeatmapScenario
from app.main.sidebar.filters import location_is_loading
from app.main.styles import inject_css
from app.main.utils.constants import DEFAULT_ORIGIN
from app.main.utils.state import attach_streamlit_logging, init_state

_log = get_logger(__name__)
_HEATMAP_ORIGIN_FIELD = "heatmap_origin"


def _init_page_state() -> None:
    st.session_state.setdefault(_HEATMAP_ORIGIN_FIELD, str(DEFAULT_ORIGIN))
    st.session_state.setdefault("heatmap_cargo", 30.0)
    st.session_state.setdefault("heatmap_metric", HEATMAP_DEFAULT_METRIC)
    st.session_state.setdefault("heatmap_surface_mode", HEATMAP_SURFACE_MODE_DEFAULT)
    st.session_state.setdefault("heatmap_show_points", False)
    st.session_state.setdefault("heatmap_dataset", None)


def _normalize_choice(session_key: str, valid_options: Iterable[str], default_value: str) -> None:
    options = list(valid_options)
    if not options:
        st.session_state[session_key] = default_value
        return
    if st.session_state.get(session_key) not in options:
        st.session_state[session_key] = default_value if default_value in options else options[0]


def _optional_positive_float(value: Any) -> float | None:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    return None if candidate <= 0.0 else candidate


def _current_scenario() -> HeatmapScenario:
    allocation_mode = str(st.session_state.get("allocation_mode", "auto")).strip().lower()
    return HeatmapScenario(
        origin_name=str(st.session_state.get(_HEATMAP_ORIGIN_FIELD, "")).strip(),
        cargo_t=float(st.session_state.get("heatmap_cargo", 30.0)),
        truck_key=str(st.session_state.get("truck_key", "")),
        ors_profile=str(st.session_state.get("profile", "driving-hgv")),
        vessel_class=str(st.session_state.get("vessel_class", "")),
        include_hoteling=bool(st.session_state.get("include_hoteling", True)),
        hoteling_hours_per_call=float(st.session_state.get("hoteling_hours_per_call", 14.0)),
        port_calls=int(st.session_state.get("port_calls", 2)),
        include_port_ops=bool(st.session_state.get("include_port_ops", True)),
        port_moves_per_call=_optional_positive_float(st.session_state.get("port_moves_per_call_input", 0.0)),
        cargo_teu=_optional_positive_float(st.session_state.get("cargo_teu_input", 0.0)),
        t_per_teu_default=max(float(st.session_state.get("t_per_teu_default", 14.0)), 0.1),
        allocation_mode=(None if allocation_mode == "auto" else allocation_mode),
        allocation_load_factor=min(max(float(st.session_state.get("allocation_load_factor", 0.8)), 0.01), 1.0),
        full_call_mode=bool(st.session_state.get("full_call_mode", False)),
        port_ops_scenario=str(st.session_state.get("port_ops_scenario", "")),
    )


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
                CabotageLens interpolates the current Supabase comparison table into a continuous signed surface between the available destination cities. Color shows relative multimodal advantage, while the optional 3D mode raises the surface from a shared floor using absolute cost or emissions advantage.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _clear_loaded_dataset_if_stale(scenario: HeatmapScenario) -> None:
    dataset = st.session_state.get("heatmap_dataset")
    if not isinstance(dataset, HeatmapDataset):
        return
    if dataset.scenario != scenario:
        _log.debug(
            "Clearing stale heatmap dataset cached_origin=%s cached_cargo_t=%.3f selected_origin=%s selected_cargo_t=%.3f",
            dataset.scenario.origin_name,
            float(dataset.scenario.cargo_t),
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
    control_cols = st.columns([1.2, 1.0, 1.0])
    with control_cols[0]:
        metric = st.radio(
            "Color metric",
            options=list(HEATMAP_METRICS),
            format_func=lambda value: "Cost" if value == "cost" else "Emissions",
            horizontal=True,
            key="heatmap_metric",
        )
    with control_cols[1]:
        surface_mode = st.radio(
            "Surface",
            options=list(HEATMAP_SURFACE_MODES),
            format_func=lambda value: "2D" if value == "2d" else "3D",
            horizontal=True,
            key="heatmap_surface_mode",
        )
    with control_cols[2]:
        show_points = st.toggle(
            "Show destination points",
            key="heatmap_show_points",
            help="Overlay the source destination-city points for debugging and hover inspection.",
        )

    better_cost = sum(1 for point in dataset.points if point.cost_delta_r > 0)
    better_emissions = sum(1 for point in dataset.points if point.emissions_delta_kg > 0)
    cols = st.columns(4)
    cols[0].metric("Destinations loaded", f"{len(dataset.points)}")
    cols[1].metric("Stored rows", f"{dataset.run.found_count}/{dataset.run.destination_count}")
    cols[2].metric("Multimodal better on cost", f"{better_cost}")
    cols[3].metric("Multimodal better on emissions", f"{better_emissions}")
    st.caption(
        f"Surface interpolation is derived from the latest successful destination comparisons in {HEATMAP_DESTINATION_LABEL}."
    )

    surface = build_surface(dataset, metric, surface_mode)
    render_legend(metric, surface_mode, surface)
    render_heatmap_map(
        dataset,
        metric,
        surface_mode,
        show_points=bool(show_points),
        surface=surface,
    )


def _load_dataset_into_session(scenario: HeatmapScenario) -> None:
    dataset = load_current_dataset(scenario)
    if dataset is not None:
        st.session_state.heatmap_dataset = dataset


def render_page() -> None:
    init_state()
    _init_page_state()
    inject_css()

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

    cargo_options = [float(st.session_state.get("heatmap_cargo", 30.0))]
    try:
        cargo_options = list_cargo_options(str(st.session_state.get(_HEATMAP_ORIGIN_FIELD, "")).strip())
    except Exception as exc:
        _log.exception("Failed to load heatmap cargo options origin=%s", st.session_state.get(_HEATMAP_ORIGIN_FIELD, ""))
        st.error(f"Failed to load available cargo values: {exc}")
    finally:
        current_cargo = float(st.session_state.get("heatmap_cargo", 30.0))
        if current_cargo not in cargo_options:
            cargo_options = sorted(set(cargo_options + [current_cargo]))

    render_sidebar(
        origin_field_key=_HEATMAP_ORIGIN_FIELD,
        cargo_options=cargo_options,
        class_options=class_options,
        port_ops_scenarios=port_ops_scenarios,
    )

    _render_header()

    scenario = _current_scenario()
    _clear_loaded_dataset_if_stale(scenario)

    if location_is_loading(_HEATMAP_ORIGIN_FIELD):
        st.info("Resolving origin...")
        return

    if not scenario.origin_name:
        st.info("Select an origin in the sidebar to inspect current heatmap rows or launch a run.")
        return

    try:
        status = get_heatmap_status(scenario)
    except HeatmapConfigurationError as exc:
        _log.error(
            "Heatmap status lookup unavailable due to configuration origin=%s cargo_t=%.3f error=%s",
            scenario.origin_name,
            scenario.cargo_t,
            exc,
        )
        st.error(str(exc))
        return
    except Exception as exc:
        _log.exception(
            "Failed to query heatmap comparison status origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        st.error(f"Failed to query the current heatmap status: {exc}")
        return

    if st.session_state.get("heatmap_dataset") is None and status.found_count > 0:
        try:
            _load_dataset_into_session(scenario)
        except HeatmapDataError as exc:
            _log.warning(
                "Heatmap comparison rows are not plottable origin=%s cargo_t=%.3f error=%s",
                scenario.origin_name,
                scenario.cargo_t,
                exc,
            )
            st.error(str(exc))
        except Exception as exc:
            _log.exception(
                "Failed to load current heatmap rows origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            st.error(f"Failed to load the current heatmap rows: {exc}")

    if status.updated_timestamp is None:
        st.warning("No comparison rows are stored yet for this scenario in Supabase.")
    else:
        st.success(f"Latest comparison update: {_format_timestamp(status.updated_timestamp)}.")
        st.caption(
            (
                f"Stored rows: {status.found_count}/{status.destination_count}. "
                f"ok={status.success_count} fail={status.fail_count} missing={status.missing_count} pending={status.pending_count}. "
                "Run missing retries failed destinies and fills any absent ones; rerun overwrites the comparison rows for this scenario."
            )
        )

    st.caption(
        "This page never overwrites the canonical routes cache. It only writes to the normalized bulk run tables used by the heatmap."
    )

    run_missing_clicked, rerun_clicked = render_run_actions(
        found_count=status.found_count,
        pending_count=status.pending_count,
    )

    if run_missing_clicked:
        _log.info(
            "Heatmap UI requested pending run origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        status_box.markdown("Starting pending run...")
        try:
            dataset = run_heatmap(
                scenario,
                rerun=False,
                progress_callback=_progress_callback(progress_bar, status_box),
            )
        except Exception as exc:
            _log.exception(
                "Heatmap pending run failed origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            progress_bar.empty()
            status_box.empty()
            st.error(f"Heatmap run failed: {exc}")
        else:
            progress_bar.progress(1.0)
            status_box.markdown("Pending run completed. Comparison table refreshed.")
            st.session_state.heatmap_dataset = dataset

    if rerun_clicked:
        _log.info(
            "Heatmap UI requested rerun-all origin=%s cargo_t=%.3f",
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
                "Heatmap rerun-all failed origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            progress_bar.empty()
            status_box.empty()
            st.error(f"Heatmap rerun failed: {exc}")
        else:
            progress_bar.progress(1.0)
            status_box.markdown("Rerun completed. Comparison table overwritten for this scenario.")
            st.session_state.heatmap_dataset = dataset

    dataset = st.session_state.get("heatmap_dataset")
    if isinstance(dataset, HeatmapDataset):
        _render_dataset(dataset)
        return

    if status.found_count > 0:
        st.info("Stored comparison rows were found. Use the sidebar to run missing, rerun all, or adjust the scenario.")
