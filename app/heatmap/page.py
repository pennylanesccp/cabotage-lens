from __future__ import annotations

from html import escape
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from modules.infra.log_manager import get_logger
from modules.multimodal.container_efficiency import DEFAULT_VESSEL_CLASS, list_vessel_classes
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO, list_port_ops_scenarios

from app.heatmap.config import (
    HEATMAP_DEFAULT_METRIC,
    HEATMAP_DESTINATION_SET_ID,
    heatmap_destination_label,
    list_heatmap_destination_sets,
    HEATMAP_METRICS,
    HEATMAP_PAGE_TITLE,
)
from app.heatmap.map import render_heatmap_map
from app.heatmap.surface import build_surface
from app.heatmap.service import (
    HeatmapConfigurationError,
    HeatmapDataError,
    load_cached_surface_dataset,
    rerun_heatmap,
    run_heatmap,
)
from app.heatmap.sidebar import render_run_actions, render_sidebar
from app.heatmap.types import HeatmapDataset, HeatmapScenario, HeatmapSurface
from app.main.sidebar.filters import location_is_loading
from app.main.run_feedback import (
    format_countdown as _shared_format_countdown,
    inject_run_feedback_css as _shared_inject_run_feedback_css,
    make_progress_callback as _shared_make_progress_callback,
    render_live_run_logs as _shared_render_live_run_logs,
    status_card as _shared_status_card,
)
from app.main.styles import inject_css
from app.main.utils.antaq import run_antaq_refresh_for_app
from app.main.utils.constants import DEFAULT_ORIGIN, DEFAULTS
from app.main.utils.state import attach_streamlit_logging, init_state

_log = get_logger(__name__)
_HEATMAP_ORIGIN_FIELD = "heatmap_origin"
_RUN_LOG_HEIGHT_PX = 260


def _init_page_state() -> None:
    st.session_state.setdefault(_HEATMAP_ORIGIN_FIELD, str(DEFAULT_ORIGIN))
    st.session_state.setdefault("heatmap_cargo", float(DEFAULTS["cargo_t"]))
    st.session_state.setdefault("heatmap_metric", HEATMAP_DEFAULT_METRIC)
    st.session_state.setdefault("heatmap_show_points", False)
    st.session_state.setdefault("heatmap_dataset", None)
    st.session_state.setdefault("heatmap_destination_set_id", HEATMAP_DESTINATION_SET_ID)


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
        cargo_t=float(st.session_state.get("heatmap_cargo", float(DEFAULTS["cargo_t"]))),
        truck_key=str(st.session_state.get("truck_key", "")),
        ors_profile="driving-car",
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


def _format_metric_scale(metric: str, value: float) -> str:
    if metric == "emissions":
        return f"{value:,.1f} kg CO2e"
    return f"R$ {value:,.2f}"


def _format_height_scale(surface: HeatmapSurface) -> str:
    return _format_metric_scale(surface.metric, surface.elevation_scale)


def _format_color_scale(surface: HeatmapSurface) -> str:
    negative_scale = max(float(surface.negative_color_scale), 0.0)
    positive_scale = max(float(surface.positive_color_scale), 0.0)
    if negative_scale > 0.0 and positive_scale > 0.0:
        return (
            f"red={_format_metric_scale(surface.metric, negative_scale)} / "
            f"green={_format_metric_scale(surface.metric, positive_scale)}"
        )
    if negative_scale > 0.0:
        return f"red={_format_metric_scale(surface.metric, negative_scale)}"
    if positive_scale > 0.0:
        return f"green={_format_metric_scale(surface.metric, positive_scale)}"
    return _format_metric_scale(surface.metric, surface.color_scale)


def _format_failure_counts(records: Iterable[Any], attr_name: str, *, max_items: int = 8) -> str:
    counts: dict[str, int] = {}
    for record in records:
        key = str(getattr(record, attr_name, None) or "").strip() or "unknown"
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return "none"
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{key}={count}" for key, count in ordered[:max_items])


def _failure_table(records: Iterable[Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "destination": record.destination,
                "failed_leg": record.failed_leg,
                "failed_step": record.failed_step,
                "failure_reason": record.failure_reason,
                "failure_detail": record.failure_detail,
                "port_origin": record.port_origin,
                "port_destiny": record.port_destiny,
                "retryable": record.retryable,
                "provider": record.provider,
                "provider_operation": record.provider_operation,
            }
            for record in records
        ]
    )


def _render_header() -> None:
    st.markdown(
        f"""
        <section style='padding: 1.4rem 1.5rem; border-radius: 24px; background: linear-gradient(135deg, rgba(233, 247, 235, 0.98), rgba(255, 244, 224, 0.96)); border: 1px solid rgba(22, 101, 52, 0.12); margin-bottom: 1rem;'>
            <p style='margin: 0 0 0.35rem 0; text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.78rem; color: #3b5d2a;'>Supabase-backed heatmap</p>
            <h1 style='margin: 0; font-size: 2rem; color: #142312;'>{escape(HEATMAP_PAGE_TITLE)}</h1>
            <p style='margin: 0.65rem 0 0 0; max-width: 48rem; color: #334155;'>
                Explore the current Brazil-wide 3D comparison surface. Color and elevation both follow the signed quantitative difference around a neutral zero plane.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _clear_loaded_dataset_if_stale(scenario: HeatmapScenario, destination_set_id: str) -> None:
    dataset = st.session_state.get("heatmap_dataset")
    if not isinstance(dataset, HeatmapDataset):
        return
    if dataset.scenario != scenario or str(dataset.run.destination_set_id) != str(destination_set_id):
        _log.debug(
            (
                "Clearing stale heatmap dataset cached_origin=%s cached_cargo_t=%.3f cached_destination_set=%s "
                "selected_origin=%s selected_cargo_t=%.3f selected_destination_set=%s"
            ),
            dataset.scenario.origin_name,
            float(dataset.scenario.cargo_t),
            dataset.run.destination_set_id,
            scenario.origin_name,
            float(scenario.cargo_t),
            destination_set_id,
        )
        st.session_state.heatmap_dataset = None


def _format_countdown(value: Any) -> str:
    return _shared_format_countdown(value)


def _status_card(message: str, *, tone: str = "info") -> str:
    return _shared_status_card(message, tone=tone)


def _log_level_class(line: str) -> str:
    if "[CRITICAL]" in line or "[ERROR]" in line:
        return "error"
    if "[WARNING]" in line:
        return "warning"
    if "[DEBUG]" in line:
        return "debug"
    return "info"


def _render_live_run_logs(log_box: Any) -> None:
    _shared_render_live_run_logs(log_box)


def _inject_run_feedback_css() -> None:
    _shared_inject_run_feedback_css()


def _progress_callback(progress_bar: Any, status_box: Any, cooldown_box: Any, log_box: Any):
    return _shared_make_progress_callback(progress_bar, status_box, cooldown_box, log_box)


def _render_dataset(dataset: HeatmapDataset) -> None:
    metric = st.radio(
        "Color metric",
        options=list(HEATMAP_METRICS),
        format_func=lambda value: "Cost" if value == "cost" else "Emissions",
        horizontal=True,
        key="heatmap_metric",
    )
    show_points = bool(st.session_state.get("heatmap_show_points", False))

    surface = build_surface(dataset, metric)
    diagnostics = dataset.diagnostics
    render_heatmap_map(
        dataset,
        metric,
        show_points=bool(show_points),
        surface=surface,
    )
    st.caption(
        f"{diagnostics.plottable_points} destination points currently shape the 3D surface from all stored sources for this origin/cargo."
    )
    _render_dataset_diagnostics(dataset, surface)


def _render_dataset_diagnostics(dataset: HeatmapDataset, surface: HeatmapSurface) -> None:
    diagnostics = dataset.diagnostics
    latest_failed_destinations = max(dataset.run.pending_count - dataset.run.missing_count, 0)
    loaded_from_route_cache = diagnostics.loaded_route_cache_rows > 0

    with st.expander("Diagnostics", expanded=False):
        diag_cols = st.columns(5)
        diag_cols[0].metric("Successful latest", f"{dataset.run.success_count}")
        diag_cols[1].metric("Failed latest", f"{dataset.run.fail_count}")
        diag_cols[2].metric("Missing rows", f"{dataset.run.missing_count}")
        diag_cols[3].metric("Surface cells", f"{len(surface.cells)}")
        diag_cols[4].metric("Unique coordinates", f"{surface.unique_source_coordinate_count}")

        if dataset.run.updated_timestamp is not None:
            st.caption(f"Latest stored update: {_format_timestamp(dataset.run.updated_timestamp)}")
        if dataset.run.run_id:
            st.caption(f"Latest run id: `{dataset.run.run_id}`")
        if dataset.run.duration_s is not None:
            st.caption(f"Run duration: {float(dataset.run.duration_s):,.1f} s")

        if loaded_from_route_cache:
            st.caption(
                (
                    f"Loaded {diagnostics.plottable_points} plottable points from {diagnostics.loaded_route_cache_rows} "
                    f"cached direct-road routes for this origin/cargo, recalculating multimodal costs and emissions "
                    f"without calling routing providers. Robust scales: color +/- {_format_color_scale(surface)} "
                    f"and height +/- {_format_height_scale(surface)}."
                )
            )
            st.caption(
                (
                    f"Selected run file {heatmap_destination_label(dataset.run.destination_set_id)} still controls "
                    f"Run missing / Rerun all. Loaded row sources: route_cache={diagnostics.loaded_route_cache_rows}, "
                    f"bulk={diagnostics.loaded_bulk_rows}, single_compare={diagnostics.loaded_single_compare_rows}."
                )
            )
        else:
            st.caption(
                (
                    f"Loaded {diagnostics.plottable_points} plottable points from {diagnostics.successful_rows} latest stored rows "
                    f"for this origin/cargo across bulk runs, destination files, and single compares. "
                    f"Robust scales: color +/- {_format_color_scale(surface)} and height +/- {_format_height_scale(surface)}."
                )
            )
            st.caption(
                (
                    f"Selected run file {heatmap_destination_label(dataset.run.destination_set_id)} still controls Run missing / Rerun all. "
                    f"Loaded row sources: bulk={diagnostics.loaded_bulk_rows}, single_compare={diagnostics.loaded_single_compare_rows}."
                )
            )

        if latest_failed_destinations > 0:
            st.caption(f"Latest failed destinations queued by Run missing: {latest_failed_destinations}")
        if diagnostics.failed_destinations:
            st.caption(
                "Latest run failure counts by step: "
                + _format_failure_counts(diagnostics.failed_destinations, "failed_step")
            )
            st.caption(
                "Latest run failure counts by leg: "
                + _format_failure_counts(diagnostics.failed_destinations, "failed_leg")
            )
            st.caption(
                "Latest run failure counts by reason: "
                + _format_failure_counts(diagnostics.failed_destinations, "failure_reason")
            )
            st.dataframe(_failure_table(diagnostics.failed_destinations), hide_index=True, width="stretch")
        if diagnostics.skipped_total > 0:
            st.caption(
                (
                    f"Skipped successful rows with incomplete map values: total={diagnostics.skipped_total} "
                    f"(coords={diagnostics.skipped_missing_coordinates}, costs={diagnostics.skipped_missing_costs}, "
                    f"emissions={diagnostics.skipped_missing_emissions})."
                )
            )
        if dataset.run.success_count != diagnostics.successful_rows:
            st.caption(
                (
                    f"Stored success summary and loaded success rows differ "
                    f"({dataset.run.success_count} vs {diagnostics.successful_rows})."
                )
            )
        if surface.unique_source_coordinate_count < diagnostics.plottable_points:
            st.caption(
                (
                    f"{diagnostics.plottable_points - surface.unique_source_coordinate_count} plottable rows share "
                    "coordinates, so the interpolated surface uses fewer unique vertices."
                )
            )
        if loaded_from_route_cache:
            st.caption(
                "This page reused the normalized routes cache and recalculated evaluation outputs in memory; it did not call routing providers or overwrite the routes cache."
            )
        else:
            st.caption(
                "This page reads the normalized bulk comparison tables only; it does not overwrite the canonical routes cache."
            )


def render_page() -> None:
    init_state()
    _init_page_state()
    inject_css()
    _inject_run_feedback_css()

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

    destination_set_id = str(st.session_state.get("heatmap_destination_set_id", HEATMAP_DESTINATION_SET_ID))
    destination_set_options = list(list_heatmap_destination_sets())
    if destination_set_id not in destination_set_options:
        destination_set_options = sorted(set(destination_set_options + [destination_set_id]))

    render_sidebar(
        origin_field_key=_HEATMAP_ORIGIN_FIELD,
        destination_set_options=destination_set_options,
        class_options=class_options,
        port_ops_scenarios=port_ops_scenarios,
    )

    _render_header()

    scenario = _current_scenario()
    destination_set_id = str(st.session_state.get("heatmap_destination_set_id", HEATMAP_DESTINATION_SET_ID))
    _clear_loaded_dataset_if_stale(scenario, destination_set_id)

    if location_is_loading(_HEATMAP_ORIGIN_FIELD):
        st.info("Resolving origin...")
        return

    if not scenario.origin_name:
        st.info("Select an origin in the sidebar to inspect current heatmap rows or launch a run.")
        return

    dataset = st.session_state.get("heatmap_dataset")
    load_clicked, run_missing_clicked, rerun_clicked = render_run_actions(
        has_origin=bool(scenario.origin_name),
        has_loaded_dataset=isinstance(dataset, HeatmapDataset),
    )

    if load_clicked:
        _log.info(
            "Heatmap UI requested cache-backed surface load origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        st.session_state.ui_logs = []
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        cooldown_box = st.empty()
        log_box = st.empty()
        progress_callback = _progress_callback(progress_bar, status_box, cooldown_box, log_box)
        status_box.markdown(
            _status_card("Loading cached-route surface...", tone="info"),
            unsafe_allow_html=True,
        )
        _render_live_run_logs(log_box)
        try:
            dataset = load_cached_surface_dataset(
                scenario,
                destination_set_id=destination_set_id,
                progress_callback=progress_callback,
            )
        except HeatmapConfigurationError as exc:
            _log.error(
                "Heatmap route-cache surface load unavailable due to configuration origin=%s cargo_t=%.3f error=%s",
                scenario.origin_name,
                scenario.cargo_t,
                exc,
            )
            progress_bar.empty()
            cooldown_box.empty()
            _render_live_run_logs(log_box)
            status_box.markdown(_status_card("Cached-route load failed.", tone="error"), unsafe_allow_html=True)
            st.error(str(exc))
            st.session_state.heatmap_dataset = None
        except HeatmapDataError as exc:
            _log.warning(
                "Cached-route heatmap load produced no plottable surface origin=%s cargo_t=%.3f error=%s",
                scenario.origin_name,
                scenario.cargo_t,
                exc,
            )
            progress_bar.empty()
            cooldown_box.empty()
            _render_live_run_logs(log_box)
            status_box.markdown(_status_card("Cached-route load failed.", tone="error"), unsafe_allow_html=True)
            st.warning(str(exc))
            st.session_state.heatmap_dataset = None
        except Exception as exc:
            _log.exception(
                "Failed to load cache-backed heatmap surface origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            progress_bar.empty()
            cooldown_box.empty()
            _render_live_run_logs(log_box)
            status_box.markdown(_status_card("Cached-route load failed.", tone="error"), unsafe_allow_html=True)
            st.error(f"Failed to load the cached-route heatmap surface: {exc}")
            st.session_state.heatmap_dataset = None
        else:
            if dataset is None:
                progress_bar.empty()
                cooldown_box.empty()
                log_box.empty()
                status_box.markdown(
                    _status_card("No cached heatmap routes were found for this origin yet.", tone="warning"),
                    unsafe_allow_html=True,
                )
                st.info(
                    "No cached direct routes were found for this origin across the tracked heatmap cities yet. "
                    "Use Run missing or Rerun all to trace them first."
                )
                st.session_state.heatmap_dataset = None
            else:
                progress_bar.progress(1.0)
                cooldown_box.empty()
                log_box.empty()
                status_box.markdown(
                    _status_card("Cached-route surface loaded.", tone="success"),
                    unsafe_allow_html=True,
                )
                st.session_state.heatmap_dataset = dataset

    if run_missing_clicked:
        _log.info(
            "Heatmap UI requested run-missing origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        st.session_state.ui_logs = []
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        cooldown_box = st.empty()
        log_box = st.empty()
        progress_callback = _progress_callback(progress_bar, status_box, cooldown_box, log_box)
        status_box.markdown(_status_card("Starting run missing...", tone="info"), unsafe_allow_html=True)
        _render_live_run_logs(log_box)
        try:
            if bool(st.session_state.get("refresh_antaq_before_run", False)):
                run_antaq_refresh_for_app(progress_callback=progress_callback)
            dataset = run_heatmap(
                scenario,
                rerun=False,
                progress_callback=progress_callback,
                destination_set_id=destination_set_id,
            )
        except Exception as exc:
            _log.exception(
                "Heatmap run-missing failed origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            progress_bar.empty()
            cooldown_box.empty()
            _render_live_run_logs(log_box)
            status_box.markdown(_status_card("Heatmap run failed.", tone="error"), unsafe_allow_html=True)
            st.error(f"Heatmap run failed: {exc}")
        else:
            progress_bar.progress(1.0)
            cooldown_box.empty()
            log_box.empty()
            status_box.markdown(
                _status_card("Run missing completed. Comparison table refreshed.", tone="success"),
                unsafe_allow_html=True,
            )
            st.session_state.heatmap_dataset = dataset

    if rerun_clicked:
        _log.info(
            "Heatmap UI requested rerun-all origin=%s cargo_t=%.3f",
            scenario.origin_name,
            scenario.cargo_t,
        )
        st.session_state.ui_logs = []
        progress_bar = st.progress(0.0)
        status_box = st.empty()
        cooldown_box = st.empty()
        log_box = st.empty()
        progress_callback = _progress_callback(progress_bar, status_box, cooldown_box, log_box)
        status_box.markdown(_status_card("Starting rerun...", tone="info"), unsafe_allow_html=True)
        _render_live_run_logs(log_box)
        try:
            if bool(st.session_state.get("refresh_antaq_before_run", False)):
                run_antaq_refresh_for_app(progress_callback=progress_callback)
            dataset = rerun_heatmap(
                scenario,
                progress_callback=progress_callback,
                destination_set_id=destination_set_id,
            )
        except Exception as exc:
            _log.exception(
                "Heatmap rerun-all failed origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            progress_bar.empty()
            cooldown_box.empty()
            _render_live_run_logs(log_box)
            status_box.markdown(_status_card("Heatmap rerun failed.", tone="error"), unsafe_allow_html=True)
            st.error(f"Heatmap rerun failed: {exc}")
        else:
            progress_bar.progress(1.0)
            cooldown_box.empty()
            log_box.empty()
            status_box.markdown(
                _status_card("Rerun completed. Comparison table overwritten for this scenario.", tone="success"),
                unsafe_allow_html=True,
            )
            st.session_state.heatmap_dataset = dataset

    dataset = st.session_state.get("heatmap_dataset")
    if isinstance(dataset, HeatmapDataset):
        _render_dataset(dataset)
