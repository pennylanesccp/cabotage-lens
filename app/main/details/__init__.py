from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from app.main.details.assumptions import render_assumptions
from app.main.details.breakdown import render_breakdown
from app.main.details.debug import render_debug


def render_details(payload: Mapping[str, Any], geo: Mapping[str, Any] | None, results: Mapping[str, Any] | None) -> None:
    if not results:
        return

    st.markdown(
        """
        <div class='section-heading'>
            <p class='section-heading__kicker'>Audit trail</p>
            <h2>Detailed outputs</h2>
            <p>Open the tables below to review route totals, component-level provenance, and calculation inputs.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Calculation breakdown", expanded=False):
        render_breakdown(results)

    with st.expander("Assumptions and caveats", expanded=False):
        render_assumptions(results=results, payload=payload)

    with st.expander("Debug payload", expanded=False):
        render_debug(payload=payload, geo=geo, results=results)
