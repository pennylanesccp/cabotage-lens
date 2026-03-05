from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from app.main.details.assumptions import render_assumptions
from app.main.details.breakdown import render_breakdown
from app.main.details.debug import render_debug


def render_details(payload: Mapping[str, Any], geo: Mapping[str, Any] | None, results: Mapping[str, Any] | None) -> None:
    st.markdown("### Details")

    if not results:
        st.info("Run an analysis to populate breakdown, assumptions, and debug details.")
        return

    with st.expander("Breakdown", expanded=True):
        render_breakdown(results)

    with st.expander("Assumptions", expanded=False):
        render_assumptions(results=results, payload=payload)

    with st.expander("Debug", expanded=False):
        render_debug(payload=payload, geo=geo, results=results)
