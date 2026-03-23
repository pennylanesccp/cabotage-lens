#!/usr/bin/env python3
# app/app_streamlit.py
# -*- coding: utf-8 -*-

"""CabotageLens Streamlit entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from app.access import require_app_access
from app.heatmap.config import HEATMAP_PAGE_ICON
from app.main.styles import inject_css
from app.main.utils.constants import APP_NAME, PAGE_ICON, PAGE_LAYOUT


def _render_router_page() -> None:
    from app.main.page import render_page

    render_page()


def _render_heatmap_page() -> None:
    from app.heatmap.page import render_page

    render_page()


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon=PAGE_ICON, layout=PAGE_LAYOUT)
    inject_css()
    require_app_access()

    navigation = st.navigation(
        [
            st.Page(_render_router_page, title="Router", icon=PAGE_ICON, default=True),
            st.Page(_render_heatmap_page, title="Heatmap", icon=HEATMAP_PAGE_ICON),
        ],
        position="sidebar",
    )
    navigation.run()


if __name__ == "__main__":
    main()
