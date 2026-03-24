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
    load_current_dataset,
    rerun_heatmap,
    run_heatmap,
)
from app.heatmap.sidebar import render_run_actions, render_sidebar
from app.heatmap.types import HeatmapDataset, HeatmapScenario, HeatmapSurface
from app.main.sidebar.filters import location_is_loading
from app.main.styles import inject_css
from app.main.utils.constants import DEFAULT_ORIGIN
from app.main.utils.state import attach_streamlit_logging, init_state

_log = get_logger(__name__)
_HEATMAP_ORIGIN_FIELD = "heatmap_origin"
_RUN_LOG_HEIGHT_PX = 260


def _init_page_state() -> None:
    st.session_state.setdefault(_HEATMAP_ORIGIN_FIELD, str(DEFAULT_ORIGIN))
    st.session_state.setdefault("heatmap_cargo", 30.0)
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
        cargo_t=float(st.session_state.get("heatmap_cargo", 30.0)),
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
    try:
        total_seconds = max(int(round(float(value))), 0)
    except (TypeError, ValueError):
        total_seconds = 0
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:d}h {minutes:02d}m {seconds:02d}s"
    if minutes > 0:
        return f"{minutes:d}m {seconds:02d}s"
    return f"{seconds:d}s"


def _status_card(message: str, *, tone: str = "info") -> str:
    palette = {
        "info": ("#eff6ff", "#1d4ed8", "#1e3a8a"),
        "success": ("#ecfdf5", "#047857", "#064e3b"),
        "warning": ("#fff7ed", "#c2410c", "#7c2d12"),
        "error": ("#fef2f2", "#dc2626", "#7f1d1d"),
    }
    background, border, text = palette.get(tone, palette["info"])
    return (
        f"<section style='padding:0.75rem 0.95rem;border-radius:16px;border:1px solid {border};"
        f"background:{background};color:{text};font-weight:600;margin:0.4rem 0 0.55rem 0;'>"
        f"{escape(message)}</section>"
    )


def _log_level_class(line: str) -> str:
    if "[CRITICAL]" in line or "[ERROR]" in line:
        return "error"
    if "[WARNING]" in line:
        return "warning"
    if "[DEBUG]" in line:
        return "debug"
    return "info"


def _render_live_run_logs(log_box: Any) -> None:
    shown = list(st.session_state.get("ui_logs", []))[-int(st.session_state.get("log_last_n", 300)) :]
    lines = [
        (
            f"<div class='heatmap-run-log__line heatmap-run-log__line--{_log_level_class(line)}'>"
            f"{escape(line)}</div>"
        )
        for line in shown
    ]
    if not lines:
        lines = ["<div class='heatmap-run-log__empty'>Waiting for live logs...</div>"]
    log_box.markdown(
        (
            "<section class='heatmap-run-log'>"
            "<div class='heatmap-run-log__title'>Live evaluation log</div>"
            f"<div class='heatmap-run-log__body' style='max-height:{_RUN_LOG_HEIGHT_PX}px;'>"
            + "".join(lines)
            + "</div></section>"
        ),
        unsafe_allow_html=True,
    )


def _inject_run_feedback_css() -> None:
    st.markdown(
        """
        <style>
            .heatmap-run-log {
                margin: 0.55rem 0 1rem 0;
                border: 1px solid rgba(15, 23, 42, 0.12);
                border-radius: 18px;
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.96));
                overflow: hidden;
                box-shadow: 0 18px 38px rgba(15, 23, 42, 0.14);
            }
            .heatmap-run-log__title {
                padding: 0.7rem 0.95rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.2);
                color: #e2e8f0;
                font: 700 0.9rem/1.2 ui-monospace, SFMono-Regular, Consolas, monospace;
            }
            .heatmap-run-log__body {
                overflow-y: auto;
                padding: 0.65rem 0.95rem 0.8rem 0.95rem;
            }
            .heatmap-run-log__line,
            .heatmap-run-log__empty {
                white-space: pre-wrap;
                word-break: break-word;
                font: 500 0.79rem/1.45 ui-monospace, SFMono-Regular, Consolas, monospace;
                margin-bottom: 0.2rem;
            }
            .heatmap-run-log__line--info { color: #bfdbfe; }
            .heatmap-run-log__line--debug { color: #94a3b8; }
            .heatmap-run-log__line--warning { color: #fdba74; }
            .heatmap-run-log__line--error { color: #fca5a5; }
            .heatmap-run-log__empty { color: #94a3b8; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _progress_callback(progress_bar: Any, status_box: Any, cooldown_box: Any, log_box: Any):
    def _callback(payload: dict[str, Any]) -> None:
        if "current" in payload or "total" in payload:
            total = max(int(payload.get("total") or 0), 1)
            current = min(max(int(payload.get("current") or 0), 0), total)
            progress_bar.progress(current / total)
        phase = str(payload.get("phase") or "").strip().lower()
        success_count = payload.get("success_count")
        fail_count = payload.get("fail_count")
        destination = str(payload.get("destination") or "").strip()
        message = str(payload.get("message") or "")
        if not message:
            message = "Waiting for provider cooldown to expire" if phase == "cooldown_wait" else "Working..."
        parts = [message]
        if destination:
            parts.append(destination)
        if success_count is not None or fail_count is not None:
            parts.append(f"ok={int(success_count or 0)} fail={int(fail_count or 0)}")
        tone = "error" if phase == "error" else "success" if phase == "complete" else "info"
        status_box.markdown(_status_card("  ".join(parts), tone=tone), unsafe_allow_html=True)

        if phase == "cooldown_wait" and str(payload.get("state") or "").strip().lower() != "retrying":
            provider = str(payload.get("provider") or "provider").strip()
            reason = str(payload.get("reason") or "rate_limited").strip().replace("_", " ")
            retry_in = _format_countdown(payload.get("remaining_s"))
            cooldown_box.markdown(
                _status_card(
                    f"Provider cooldown active for {provider} ({reason}). Retrying automatically in {retry_in}.",
                    tone="warning",
                ),
                unsafe_allow_html=True,
            )
        else:
            cooldown_box.empty()

        _render_live_run_logs(log_box)

    return _callback


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
        try:
            dataset = load_current_dataset(scenario, destination_set_id=destination_set_id)
        except HeatmapConfigurationError as exc:
            _log.error(
                "Heatmap surface load unavailable due to configuration origin=%s cargo_t=%.3f error=%s",
                scenario.origin_name,
                scenario.cargo_t,
                exc,
            )
            st.error(str(exc))
            st.session_state.heatmap_dataset = None
        except HeatmapDataError as exc:
            _log.warning(
                "Stored heatmap rows are not plottable origin=%s cargo_t=%.3f error=%s",
                scenario.origin_name,
                scenario.cargo_t,
                exc,
            )
            st.warning(str(exc))
            st.session_state.heatmap_dataset = None
        except Exception as exc:
            _log.exception(
                "Failed to load stored heatmap surface origin=%s cargo_t=%.3f",
                scenario.origin_name,
                scenario.cargo_t,
            )
            st.error(f"Failed to load the stored heatmap surface: {exc}")
            st.session_state.heatmap_dataset = None
        else:
            if dataset is None:
                st.info("No stored comparison rows were found for this scenario yet. Use Run missing or Rerun all.")
                st.session_state.heatmap_dataset = None
            else:
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
        status_box.markdown(_status_card("Starting run missing...", tone="info"), unsafe_allow_html=True)
        _render_live_run_logs(log_box)
        try:
            dataset = run_heatmap(
                scenario,
                rerun=False,
                progress_callback=_progress_callback(progress_bar, status_box, cooldown_box, log_box),
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
        status_box.markdown(_status_card("Starting rerun...", tone="info"), unsafe_allow_html=True)
        _render_live_run_logs(log_box)
        try:
            dataset = rerun_heatmap(
                scenario,
                progress_callback=_progress_callback(progress_bar, status_box, cooldown_box, log_box),
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
