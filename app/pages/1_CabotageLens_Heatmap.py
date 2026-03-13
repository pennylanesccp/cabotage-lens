from __future__ import annotations

import streamlit as st

from app.heatmap.config import HEATMAP_PAGE_ICON, HEATMAP_PAGE_TITLE
from app.heatmap.page import render_page

st.set_page_config(page_title=HEATMAP_PAGE_TITLE, page_icon=HEATMAP_PAGE_ICON, layout="wide")

render_page()
