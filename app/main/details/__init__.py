from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from app.main.details.assumptions import render_assumptions
from app.main.details.breakdown import render_breakdown
from app.main.details.debug import render_debug


def render_details(payload: Mapping[str, Any], geo: Mapping[str, Any] | None, results: Mapping[str, Any] | None) -> None:
    st.markdown("### Details")

    if not results:
        with st.expander("Breakdown", expanded=True):
            st.markdown(
                "<p class='details-placeholder'><strong>Breakdown pending.</strong> Run an analysis to populate route totals and leg-level comparisons.</p>",
                unsafe_allow_html=True,
            )

        with st.expander("Assumptions", expanded=False):
            st.markdown(
                "<p class='details-placeholder'><strong>Assumptions pending.</strong> The parameter descriptions will appear here after the first successful scenario run.</p>",
                unsafe_allow_html=True,
            )

        with st.expander("Debug", expanded=False):
            st.markdown(
                "<p class='details-placeholder'><strong>Debug pending.</strong> Execution logs, payload details, and geometry diagnostics will appear here after a run.</p>",
                unsafe_allow_html=True,
            )
        return

    with st.expander("Breakdown", expanded=True):
        render_breakdown(results)

    with st.expander("Assumptions", expanded=False):
        render_assumptions(results=results, payload=payload)

    with st.expander("Debug", expanded=False):
        render_debug(payload=payload, geo=geo, results=results)
