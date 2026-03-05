from __future__ import annotations

import streamlit as st

BASE_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(900px 360px at 8% -12%, rgba(52, 152, 219, .16), transparent 55%),
            radial-gradient(900px 420px at 100% 0%, rgba(22, 160, 133, .14), transparent 45%),
            #0b1220;
    }
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1.75rem;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    section[data-testid="stSidebar"] .stButton > button {
        margin-top: 0.65rem;
    }
    section[data-testid="stSidebar"] hr {
        border: 0;
        height: 0;
        margin: 0;
    }
    .page-header {
        margin-bottom: 0.7rem;
    }
    .page-header h1 {
        margin: 0;
        font-size: 1.7rem;
        color: #e2e8f0;
        line-height: 1.2;
    }
    .page-header p {
        margin: 0.22rem 0 0 0;
        color: #cbd5e1;
        font-size: 0.96rem;
    }
</style>
"""

MAP_OVERLAY_CSS = """
<style>
body {
  margin: 0;
  overflow: hidden;
  position: relative;
  font-family: "Segoe UI", sans-serif;
}
#overlay-root {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 1000;
  pointer-events: none;
}
.map-overlay-cards {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  align-items: flex-start;
}
.overlay-card {
  pointer-events: auto;
  min-width: 210px;
  max-width: 320px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  background: rgba(12, 18, 31, 0.9);
  color: #e2e8f0;
  padding: 0.55rem 0.7rem;
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.42);
}
.overlay-card h4 {
  margin: 0 0 0.2rem 0;
  font-size: 0.84rem;
  color: #cbd5e1;
}
.overlay-card p {
  margin: 0.05rem 0;
  font-size: 0.79rem;
}
.overlay-highlight {
  border-color: rgba(251, 191, 36, 0.55);
}
.overlay-note {
  max-width: 280px;
}
@media (max-width: 840px) {
  #overlay-root {
    left: 8px;
    right: 8px;
    top: 8px;
  }
  .map-overlay-cards {
    flex-direction: column;
  }
  .overlay-card {
    min-width: 0;
    width: 100%;
    max-width: 100%;
  }
}
</style>
"""


def inject_css() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
