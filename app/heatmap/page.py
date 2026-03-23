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
                CabotageLens interpolates the current Supabase comparison table into a continuous signed 3D surface between the available destination cities. Color shows relative multimodal advantage, while elevation shows the signed absolute magnitude so regional terrain differences are immediately visible.
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


def _same_timestamp(left: Any, right: Any) -> bool:
    return str(left or "").strip() == str(right or "").strip()


def _dataset_matches_status(dataset: HeatmapDataset, status: Any) -> bool:
    return (
        dataset.run.run_id == status.run_id
        and dataset.run.destination_count == status.destination_count
        and dataset.run.found_count == status.found_count
        and dataset.run.success_count == status.success_count
        and dataset.run.fail_count == status.fail_count
        and _same_timestamp(dataset.run.updated_timestamp, status.updated_timestamp)
    )


def _clear_loaded_dataset_if_outdated(scenario: HeatmapScenario, status: Any) -> None:
    dataset = st.session_state.get("heatmap_dataset")
    if not isinstance(dataset, HeatmapDataset):
        return
    if dataset.scenario != scenario:
        return
    if _dataset_matches_status(dataset, status):
        return
    _log.info(
        (
            "Clearing outdated heatmap dataset origin=%s cargo_t=%.3f cached_run_id=%s current_run_id=%s "
            "cached_found=%d current_found=%d cached_success=%d current_success=%d"
        ),
        scenario.origin_name,
        scenario.cargo_t,
        dataset.run.run_id or "<none>",
        status.run_id or "<none>",
        dataset.run.found_count,
        status.found_count,
        dataset.run.success_count,
        status.success_count,
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
    control_cols = st.columns([1.5, 1.0])
    with control_cols[0]:
        metric = st.radio(
            "Color metric",
            options=list(HEATMAP_METRICS),
            format_func=lambda value: "Cost" if value == "cost" else "Emissions",
            horizontal=True,
            key="heatmap_metric",
        )
    with control_cols[1]:
        show_points = st.toggle(
            "Show destination points",
            key="heatmap_show_points",
            help="Overlay the source destination-city points for debugging and hover inspection.",
        )

    surface = build_surface(dataset, metric)
    diagnostics = dataset.diagnostics
    cols = st.columns(5)
    cols[0].metric("Latest stored rows", f"{dataset.run.found_count}/{dataset.run.destination_count}")
    cols[1].metric("Successful latest", f"{dataset.run.success_count}")
    cols[2].metric("Failed latest", f"{dataset.run.fail_count}")
    cols[3].metric("Plottable points", f"{diagnostics.plottable_points}")
    cols[4].metric("Missing rows", f"{dataset.run.missing_count}")
    retryable_failures = max(dataset.run.pending_count - dataset.run.missing_count, 0)
    st.caption(
        (
            f"Loaded {diagnostics.plottable_points} plottable destination points from "
            f"{diagnostics.successful_rows} successful latest rows in {HEATMAP_DESTINATION_LABEL}. "
            f"The 3D surface interpolates {surface.unique_source_coordinate_count} unique source coordinates into "
            f"{len(surface.cells)} rendered cells."
        )
    )
    if retryable_failures > 0:
        st.info(
            f"{retryable_failures} latest failed rows are marked retryable and will be revisited by Run missing."
        )
    if dataset.run.pending_count > 0 and retryable_failures == 0 and dataset.run.missing_count > 0:
        st.info(f"{dataset.run.missing_count} destinations still have no latest stored row for this scenario.")
    if dataset.run.success_count != diagnostics.successful_rows:
        st.warning(
            (
                f"Heatmap summary/load mismatch: expected {dataset.run.success_count} successful latest rows, "
                f"but loaded {diagnostics.successful_rows} rows for plotting. Check the runtime logs for selector details."
            )
        )
    if diagnostics.skipped_total > 0:
        st.warning(
            (
                f"Loaded {diagnostics.plottable_points} plottable destination points from "
                f"{diagnostics.successful_rows} successful latest rows. "
                f"Skipped {diagnostics.skipped_total} successful rows due to missing map values "
                f"(coords={diagnostics.skipped_missing_coordinates}, costs={diagnostics.skipped_missing_costs}, "
                f"emissions={diagnostics.skipped_missing_emissions})."
            )
        )
    if dataset.run.fail_count > 0:
        st.info(
            f"The heatmap excludes {dataset.run.fail_count} latest failed rows; only successful latest rows are eligible for plotting."
        )
    if surface.unique_source_coordinate_count < diagnostics.plottable_points:
        st.caption(
            (
                f"{diagnostics.plottable_points - surface.unique_source_coordinate_count} plottable rows share coordinates, "
                "so the interpolation surface collapses them into fewer unique source vertices."
            )
        )
    render_legend(metric, surface)
    render_heatmap_map(
        dataset,
        metric,
        show_points=bool(show_points),
        surface=surface,
    )


def _load_dataset_into_session(scenario: HeatmapScenario, *, status: Any | None = None) -> None:
    dataset = load_current_dataset(scenario, status=status)
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

    _clear_loaded_dataset_if_outdated(scenario, status)

    if st.session_state.get("heatmap_dataset") is None and status.found_count > 0:
        try:
            _load_dataset_into_session(scenario, status=status)
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
                "Pending counts only missing rows plus retryable transient failures; terminal failed rows stay out of Run missing until rerun all."
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
