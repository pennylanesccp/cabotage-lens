from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, List

import streamlit as st

from modules.addressing.coords import parse_lat_lon_string
from modules.addressing.resolver import resolve_point_null_safe
from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.database_manager import db_session, find_place_point, list_origin_names, list_place_names
from modules.infra.db.settings import load_database_settings
from modules.infra.log_manager import get_logger
from modules.road.router import ORSClient

from app.main.sidebar.styles import apply_sidebar_styles
from app.main.utils.formatters import clean_place_label

_log = get_logger("streamlit_app")
_LOCATION_FIELDS: tuple[tuple[str, str], ...] = (("origin", "Origin"), ("destiny", "Destination"))
_POLL_SECONDS = 0.35
LOCATION_RESOLUTION_POLL_SECONDS = _POLL_SECONDS


def _is_coordinate_label(value: str) -> bool:
    return parse_lat_lon_string(str(value).strip()) is not None


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


def _resolved_key(field_name: str) -> str:
    return _state_key(field_name, "resolved_value")


@st.cache_resource
def _resolution_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="streamlit-geocode")


def _db_route_place_names() -> list[str]:
    try:
        settings = load_database_settings()
    except Exception as exc:
        _log.warning("Skipping route place-name lookup because the database runtime is invalid: %s", exc)
        return []

    collected: set[str] = set()
    try:
        with db_session() as conn:
            for value in list_place_names(conn, limit=100_000):
                value_clean = ascii_place_text(value)
                if value_clean and not _is_coordinate_label(value_clean):
                    collected.add(value_clean)
    except Exception as exc:
        _log.warning("Failed to list route place names from %s: %s", settings.display_target, exc)
    return sorted(collected, key=str.casefold)


def _db_route_origin_names() -> list[str]:
    try:
        settings = load_database_settings()
    except Exception as exc:
        _log.warning("Skipping route origin lookup because the database runtime is invalid: %s", exc)
        return []

    collected: set[str] = set()
    try:
        with db_session() as conn:
            for value in list_origin_names(conn, limit=100_000):
                value_clean = ascii_place_text(value)
                if value_clean and not _is_coordinate_label(value_clean):
                    collected.add(value_clean)
    except Exception as exc:
        _log.warning("Failed to list route origins from %s: %s", settings.display_target, exc)
    return sorted(collected, key=str.casefold)


def _resolve_custom_location_label(value: str) -> tuple[str | None, str | None]:
    query = str(value).strip()
    if not query:
        return None, None

    cached_label = _resolve_cached_location_label(query)
    if cached_label is not None:
        return cached_label, None

    ors = ORSClient()
    if not ors.has_geocoding_provider():
        return None, "No geocoding provider is configured. Set ORS_API_KEYS or LOCATIONIQ_PAT."

    point = resolve_point_null_safe(query, ors, _log)
    if not point:
        return None, "Address resolution failed."

    resolved_label = ascii_place_text(point.label) or ascii_place_text(query)
    return resolved_label, None


def _resolve_cached_location_label(value: str) -> str | None:
    query = ascii_place_text(value)
    if not query or _is_coordinate_label(query):
        return None

    try:
        with db_session() as conn:
            cached_point = find_place_point(conn, place=query)
    except Exception as exc:
        _log.debug("Routes-table lookup failed while resolving %s: %s", query, exc)
        return None

    if not cached_point:
        return None

    cached_label = ascii_place_text(cached_point.get("label") or query)
    if cached_label:
        _log.info(
            "Resolved %s input from the canonical location cache without ORS call role=%s",
            query,
            cached_point.get("role") or "<unknown>",
        )
    return cached_label or None


def _ensure_location_state(field_name: str) -> None:
    st.session_state.setdefault(_loading_key(field_name), False)
    st.session_state.setdefault(_future_key(field_name), None)
    st.session_state.setdefault(_error_key(field_name), None)
    st.session_state.setdefault(_pending_key(field_name), "")
    st.session_state.setdefault(_resolved_key(field_name), None)


def _clear_location_resolution(field_name: str, *, keep_error: bool = False) -> None:
    st.session_state[_loading_key(field_name)] = False
    st.session_state[_future_key(field_name)] = None
    st.session_state[_pending_key(field_name)] = ""
    if not keep_error:
        st.session_state[_error_key(field_name)] = None


def _canonical_option(value: str, options: list[str]) -> str | None:
    normalized = ascii_place_key(value)
    for option in options:
        if ascii_place_key(option) == normalized:
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
    st.session_state[_resolved_key(field_name)] = None
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
        st.session_state[_resolved_key(field_name)] = resolved_label
        st.session_state[_error_key(field_name)] = None
    else:
        _log.warning("Failed to resolve %s input: %s", field_name, error_message or "unknown error")
        st.session_state[_resolved_key(field_name)] = pending_value
        st.session_state[_error_key(field_name)] = error_message or "Address resolution failed."
    return True


def _sync_all_location_resolutions() -> bool:
    return any(_sync_location_resolution(field_name) for field_name, _ in _LOCATION_FIELDS)


def _any_location_loading() -> bool:
    return any(bool(st.session_state.get(_loading_key(field_name), False)) for field_name, _ in _LOCATION_FIELDS)


def _apply_resolved_location_values() -> None:
    for field_name, _ in _LOCATION_FIELDS:
        resolved_value = st.session_state.get(_resolved_key(field_name))
        if resolved_value is None:
            continue
        st.session_state[field_name] = str(resolved_value).strip()
        st.session_state[_resolved_key(field_name)] = None


def _route_endpoint_options(current_values: list[str]) -> list[str]:
    options: set[str] = set()
    for value in current_values:
        value_clean = ascii_place_text(value)
        if value_clean and not _is_coordinate_label(value_clean):
            options.add(value_clean)

    options.update(_db_route_place_names())

    return sorted(options, key=str.casefold)


def _route_origin_options(current_values: list[str]) -> list[str]:
    options: set[str] = set()
    for value in current_values:
        value_clean = ascii_place_text(value)
        if value_clean and not _is_coordinate_label(value_clean):
            options.add(value_clean)

    options.update(_db_route_origin_names())

    return sorted(options, key=str.casefold)


def ensure_location_state(field_name: str) -> None:
    _ensure_location_state(field_name)


def sync_location_resolution(field_name: str) -> bool:
    return _sync_location_resolution(field_name)


def apply_resolved_location_values(field_names: Iterable[str]) -> None:
    for field_name in field_names:
        resolved_value = st.session_state.get(_resolved_key(field_name))
        if resolved_value is None:
            continue
        st.session_state[field_name] = str(resolved_value).strip()
        st.session_state[_resolved_key(field_name)] = None


def route_endpoint_options(current_values: list[str]) -> list[str]:
    return _route_endpoint_options(current_values)


def route_origin_options(current_values: list[str]) -> list[str]:
    return _route_origin_options(current_values)


def handle_location_change(field_name: str, options: list[str]) -> None:
    _on_location_change(field_name, options)


def location_error_message(field_name: str) -> str:
    return str(st.session_state.get(_error_key(field_name)) or "").strip()


def location_is_loading(field_name: str) -> bool:
    return bool(st.session_state.get(_loading_key(field_name), False))


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
    st.selectbox(
        label,
        options=options,
        key=field_name,
        accept_new_options=True,
        format_func=clean_place_label,
        on_change=handle_location_change,
        args=(field_name, options),
    )
    error_message = location_error_message(field_name)
    if error_message:
        st.caption(error_message)


def render_filters() -> List[str]:
    for field_name, _ in _LOCATION_FIELDS:
        _ensure_location_state(field_name)

    _sync_all_location_resolutions()
    _apply_resolved_location_values()

    origin_name_options = _route_origin_options(current_values=[str(st.session_state.origin)])
    destiny_name_options = _route_endpoint_options(current_values=[str(st.session_state.destiny)])

    apply_sidebar_styles(
        origin_loading=bool(st.session_state.get(_loading_key("origin"), False)),
        destiny_loading=bool(st.session_state.get(_loading_key("destiny"), False)),
    )

    _render_location_field("origin", "Origin", origin_name_options)
    _render_location_field("destiny", "Destination", destiny_name_options)

    st.number_input("Cargo (t)", min_value=0.0, step=0.5, format="%g", key="cargo_t")

    @st.fragment(run_every=_POLL_SECONDS if _any_location_loading() else None)
    def _poll_location_resolution() -> None:
        if _sync_all_location_resolutions():
            st.rerun()

    _poll_location_resolution()
    return destiny_name_options
