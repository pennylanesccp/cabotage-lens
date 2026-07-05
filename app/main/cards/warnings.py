from __future__ import annotations

from html import escape
from typing import Any, Mapping

import streamlit as st

_ROUTE_QUALITY_WARNING_TITLE = "Route quality warning"
_SUPPRESSED_ROUTE_QUALITY_WARNING_CODES = {"fallback_maritime_distance"}


def _route_quality_warnings(results: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not results:
        return []
    raw = results.get("route_quality_warnings") or []
    if not isinstance(raw, list):
        return []

    warnings: list[Mapping[str, Any]] = []
    seen_codes: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        message = str(item.get("message") or "").strip()
        if not message:
            continue
        code = str(item.get("code") or message).strip()
        if code in _SUPPRESSED_ROUTE_QUALITY_WARNING_CODES:
            continue
        if code in seen_codes:
            continue
        seen_codes.add(code)
        warnings.append(item)
    return warnings


def render_route_quality_warnings(results: Mapping[str, Any] | None) -> None:
    warnings = _route_quality_warnings(results)
    if not warnings:
        return

    if len(warnings) == 1:
        warning = warnings[0]
        title = str(warning.get("title") or _ROUTE_QUALITY_WARNING_TITLE).strip()
        if title == "Cabotage route warning":
            title = _ROUTE_QUALITY_WARNING_TITLE
        st.markdown(
            (
                "<section class='quality-note'>"
                f"<strong>{escape(title)}</strong>"
                f"<p>{escape(str(warning['message']))}</p>"
                "</section>"
            ),
            unsafe_allow_html=True,
        )
        return

    items = "".join(f"<li>{escape(str(warning['message']))}</li>" for warning in warnings)
    st.markdown(
        (
            "<section class='quality-note'>"
            "<strong>Route quality warnings</strong>"
            f"<ul>{items}</ul>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )
