from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import streamlit as st

from modules.addressing.resolver import resolve_point_null_safe
from modules.infra.database_manager import db_session, list_place_names
from modules.infra.log_manager import get_logger
from modules.road.router import ORSClient, ORSConfig

from app.main.sidebar.styles import apply_sidebar_styles
from app.main.utils.formatters import clean_place_label

_log = get_logger("streamlit_app")
_LOCATION_FIELDS: tuple[tuple[str, str], ...] = (("origin", "Origin"), ("destiny", "Destination"))
_POLL_SECONDS = 0.35


def _state_key(field_name: str, suffix: str) -> str:
    return f"_{field_name}_{suffix}"


def _loading_key(field_name: str) -> str:
    return _state_key(field_name, "loading")


def _future_key(field_name: str) -> str:
    return _state_key(field_name, "future")


def _error_key(field_name: str) -> str:
    return _state_key(field_name, "error")


def _pending_key(field_name: str) -> str:
    return _state_key(field_name, "pending_value")


@st.cache_resource
def _resolution_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="streamlit-geocode")


def _db_route_place_names(db_path_str: str) -> list[str]:
    try:
        with db_session(Path(db_path_str)) as conn:
            return [str(value).strip() for value in list_place_names(conn, limit=100_000) if str(value).strip()]
    except Exception as exc:
        _log.warning("Failed to list route place names from %s: %s", db_path_str, exc)
        return []


def _resolve_custom_location_label(value: str) -> tuple[str | None, str | None]:
    query = str(value).strip()
    if not query:
        return None, None

    api_key = str(os.getenv("ORS_API_KEY", "")).strip()
    if not api_key:
        return None, "ORS_API_KEY is not configured."

    ors = ORSClient(ORSConfig(api_key=api_key))
    point = resolve_point_null_safe(query, ors, _log)
    if not point:
        return None, "Address resolution failed."

    resolved_label = clean_place_label(point.label) or str(point.label).strip()
    return resolved_label, None


def _ensure_location_state(field_name: str) -> None:
    st.session_state.setdefault(_loading_key(field_name), False)
    st.session_state.setdefault(_future_key(field_name), None)
    st.session_state.setdefault(_error_key(field_name), None)
    st.session_state.setdefault(_pending_key(field_name), "")


def _clear_location_resolution(field_name: str, *, keep_error: bool = False) -> None:
    st.session_state[_loading_key(field_name)] = False
    st.session_state[_future_key(field_name)] = None
    st.session_state[_pending_key(field_name)] = ""
    if not keep_error:
        st.session_state[_error_key(field_name)] = None


def _canonical_option(value: str, options: list[str]) -> str | None:
    normalized = clean_place_label(value).casefold()
    for option in options:
        if clean_place_label(option).casefold() == normalized:
            return option
    return None


def _start_location_resolution(field_name: str, raw_value: str) -> None:
    value = str(raw_value).strip()
    if not value:
        _clear_location_resolution(field_name)
        return

    _log.info("Resolving %s input: %s", field_name, value)
    st.session_state[_error_key(field_name)] = None
    st.session_state[_pending_key(field_name)] = value
    st.session_state[_loading_key(field_name)] = True
    st.session_state[_future_key(field_name)] = _resolution_executor().submit(_resolve_custom_location_label, value)


def _sync_location_resolution(field_name: str) -> bool:
    future = st.session_state.get(_future_key(field_name))
    if not st.session_state.get(_loading_key(field_name)) or future is None:
        return False
    if not hasattr(future, "done") or not future.done():
        return False

    pending_value = str(st.session_state.get(_pending_key(field_name), "")).strip()
    try:
        resolved_label, error_message = future.result()
    except Exception as exc:
        resolved_label, error_message = None, f"Address resolution failed: {exc}"

    _clear_location_resolution(field_name, keep_error=True)
    if resolved_label:
        _log.info("Resolved %s input to: %s", field_name, resolved_label)
        st.session_state[field_name] = resolved_label
        st.session_state[_error_key(field_name)] = None
    else:
        _log.warning("Failed to resolve %s input: %s", field_name, error_message or "unknown error")
        st.session_state[field_name] = pending_value
        st.session_state[_error_key(field_name)] = error_message or "Address resolution failed."
    return True


def _sync_all_location_resolutions() -> bool:
    return any(_sync_location_resolution(field_name) for field_name, _ in _LOCATION_FIELDS)


def _any_location_loading() -> bool:
    return any(bool(st.session_state.get(_loading_key(field_name), False)) for field_name, _ in _LOCATION_FIELDS)


def _route_endpoint_options(db_path_str: str, current_values: list[str]) -> list[str]:
    options: set[str] = set()
    for value in current_values:
        value_clean = str(value).strip()
        if value_clean:
            options.add(value_clean)

    for value in _db_route_place_names(db_path_str):
        value_clean = str(value).strip()
        if value_clean:
            options.add(value_clean)

    return sorted(options, key=str.casefold)


def _on_location_change(field_name: str, options: list[str]) -> None:
    current_value = str(st.session_state.get(field_name, "")).strip()
    if not current_value:
        _clear_location_resolution(field_name)
        return

    canonical = _canonical_option(current_value, options)
    if canonical is not None:
        st.session_state[field_name] = canonical
        _clear_location_resolution(field_name)
        return

    _start_location_resolution(field_name, current_value)


def _render_location_field(field_name: str, label: str, options: list[str]) -> None:
    loading = bool(st.session_state.get(_loading_key(field_name), False))
    loading_attr = "true" if loading else "false"
    st.markdown(
        (
            "<span class='location-field-marker' "
            f"data-field='{field_name}' "
            f"data-loading='{loading_attr}'></span>"
        ),
        unsafe_allow_html=True,
    )
    st.selectbox(
        label,
        options=options,
        key=field_name,
        accept_new_options=True,
        format_func=clean_place_label,
        on_change=_on_location_change,
        args=(field_name, options),
    )
    error_message = str(st.session_state.get(_error_key(field_name)) or "").strip()
    if error_message:
        st.caption(error_message)


def render_filters() -> List[str]:
    for field_name, _ in _LOCATION_FIELDS:
        _ensure_location_state(field_name)

    _sync_all_location_resolutions()

    route_name_options = _route_endpoint_options(
        db_path_str=str(st.session_state.db_path_str),
        current_values=[str(st.session_state.origin), str(st.session_state.destiny)],
    )

    apply_sidebar_styles(
        origin_loading=bool(st.session_state.get(_loading_key("origin"), False)),
        destiny_loading=bool(st.session_state.get(_loading_key("destiny"), False)),
    )

    for field_name, label in _LOCATION_FIELDS:
        _render_location_field(field_name, label, route_name_options)

    st.number_input("Cargo (t)", min_value=0.0, step=0.5, key="cargo_t")

    @st.fragment(run_every=_POLL_SECONDS if _any_location_loading() else None)
    def _poll_location_resolution() -> None:
        if _sync_all_location_resolutions():
            st.rerun()

    _poll_location_resolution()
    return route_name_options
