from __future__ import annotations

from typing import Iterable

import streamlit as st

from app.main.sidebar.advanced import render_advanced
from app.main.sidebar.filters import render_filters
from app.main.sidebar.run_button import render_run_button
from app.main.sidebar.styles import apply_sidebar_styles


def render_sidebar(class_options: Iterable[str], port_ops_scenarios: Iterable[str]) -> bool:
    with st.sidebar:
        apply_sidebar_styles()
        st.subheader("Scenario")
        render_filters()
        with st.expander("Advanced", expanded=False):
            render_advanced(class_options=class_options, port_ops_scenarios=port_ops_scenarios)
        return render_run_button()
