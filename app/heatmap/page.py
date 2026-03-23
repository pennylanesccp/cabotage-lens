from __future__ import annotations

from html import escape
from typing import Any, Iterable

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
from app.heatmap.map import render_heatmap_map, render_legend
from app.heatmap.surface import build_surface
from app.heatmap.service import (
    HeatmapConfigurationError,
    HeatmapDataError,
    list_cargo_options,
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


def _format_height_scale(surface: HeatmapSurface) -> str:
    if surface.metric == "emissions":
        return f"{surface.elevation_scale:,.1f} kg CO2e"
    return f"R$ {surface.elevation_scale:,.2f}"


def _render_header() -> None:
    st.markdown(
        f"""
        <section style='padding: 1.4rem 1.5rem; border-radius: 24px; background: linear-gradient(135deg, rgba(233, 247, 235, 0.98), rgba(255, 244, 224, 0.96)); border: 1px solid rgba(22, 101, 52, 0.12); margin-bottom: 1rem;'>
            <p style='margin: 0 0 0.35rem 0; text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.78rem; color: #3b5d2a;'>Supabase-backed heatmap</p>
            <h1 style='margin: 0; font-size: 2rem; color: #142312;'>{escape(HEATMAP_PAGE_TITLE)}</h1>
            <p style='margin: 0.65rem 0 0 0; max-width: 48rem; color: #334155;'>
                Explore the current Brazil-wide 3D comparison surface. Color shows relative advantage and elevation shows signed magnitude around a neutral zero plane.
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
    control_cols = st.columns([1.35, 1.0])
    with control_cols[0]:
        metric = st.radio(
            "Color metric",
            options=list(HEATMAP_METRICS),
            format_func=lambda value: "Cost" if value == "cost" else "Emissions",
            horizontal=True,
            key="heatmap_metric",
        )
    with control_cols[1]:
        with st.expander("Display options", expanded=False):
            show_points = st.toggle(
                "Show destination points",
                key="heatmap_show_points",
                help="Overlay the source destination-city points for hover inspection.",
            )

    surface = build_surface(dataset, metric)
    diagnostics = dataset.diagnostics
    render_heatmap_map(
        dataset,
        metric,
        show_points=bool(show_points),
        surface=surface,
    )
    st.caption(
        f"{diagnostics.plottable_points} destination points currently shape the 3D surface from {heatmap_destination_label(dataset.run.destination_set_id)}."
    )
    render_legend(metric, surface)
    _render_dataset_diagnostics(dataset, surface)


def _render_dataset_diagnostics(dataset: HeatmapDataset, surface: HeatmapSurface) -> None:
    diagnostics = dataset.diagnostics
    retryable_failures = max(dataset.run.pending_count - dataset.run.missing_count, 0)

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
                f"{heatmap_destination_label(dataset.run.destination_set_id)}: loaded {diagnostics.plottable_points} plottable points from "
                f"{diagnostics.successful_rows} successful latest rows. "
                f"Robust scales: color +/- {surface.color_scale:,.1f}% and height +/- {_format_height_scale(surface)}."
            )
        )

        if retryable_failures > 0:
            st.caption(f"Retryable latest failures: {retryable_failures}")
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


def _render_unloaded_state(origin_name: str, destination_set_id: str) -> None:
    st.markdown(
        f"""
        <section style='padding: 1.05rem 1.15rem; border-radius: 20px; border: 1px solid rgba(148, 163, 184, 0.12); background: rgba(248, 250, 252, 0.74);'>
            <p style='margin: 0 0 0.3rem 0; text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.76rem; color: #64748b;'>3D surface</p>
            <h3 style='margin: 0; color: #0f172a;'>Surface not loaded</h3>
            <p style='margin: 0.55rem 0 0 0; color: #334155; max-width: 46rem;'>
                Load the stored surface for <strong>{escape(origin_name)}</strong> using <strong>{escape(heatmap_destination_label(destination_set_id))}</strong>, or run missing / rerun all if you want fresh comparison rows.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


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

    destination_set_id = str(st.session_state.get("heatmap_destination_set_id", HEATMAP_DESTINATION_SET_ID))
    destination_set_options = list(list_heatmap_destination_sets())
    if destination_set_id not in destination_set_options:
        destination_set_options = sorted(set(destination_set_options + [destination_set_id]))

    cargo_options = [float(st.session_state.get("heatmap_cargo", 30.0))]
    try:
        cargo_options = list_cargo_options(
            str(st.session_state.get(_HEATMAP_ORIGIN_FIELD, "")).strip(),
            destination_set_id=destination_set_id,
        )
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
                destination_set_id=destination_set_id,
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
                destination_set_id=destination_set_id,
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

    _render_unloaded_state(scenario.origin_name, destination_set_id)
