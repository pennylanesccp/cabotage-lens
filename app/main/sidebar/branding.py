from __future__ import annotations

from html import escape

import streamlit as st

from app.main.utils.constants import APP_NAME, APP_TAGLINE


def render_sidebar_brand() -> None:
    st.markdown(
        f"""
        <div class='sidebar-brand'>
            <p class='sidebar-brand__title'>{escape(APP_NAME)}</p>
            <p class='sidebar-brand__subtitle'>{escape(APP_TAGLINE)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
