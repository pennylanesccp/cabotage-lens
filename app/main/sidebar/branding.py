from __future__ import annotations

import streamlit as st

from app.main.utils.constants import APP_NAME, APP_TAGLINE


def render_sidebar_brand() -> None:
    st.markdown(f"### {APP_NAME}")
    st.caption(APP_TAGLINE)
