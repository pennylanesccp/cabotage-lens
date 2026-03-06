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
    .summary-groups {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.9rem;
        margin: 0.55rem 0 0.9rem 0;
    }
    .summary-card {
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 18px;
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(9, 14, 26, 0.92)),
            #0f172a;
        padding: 0.95rem 1rem 1rem 1rem;
        box-shadow: 0 18px 38px rgba(2, 6, 23, 0.22);
    }
    .summary-card[data-accent="multimodal"] {
        border-color: rgba(45, 212, 191, 0.34);
        box-shadow: inset 0 1px 0 rgba(94, 234, 212, 0.1), 0 18px 38px rgba(2, 6, 23, 0.22);
    }
    .summary-card[data-accent="road"] {
        border-color: rgba(251, 191, 36, 0.28);
        box-shadow: inset 0 1px 0 rgba(252, 211, 77, 0.08), 0 18px 38px rgba(2, 6, 23, 0.22);
    }
    .summary-card__eyebrow {
        margin: 0 0 0.18rem 0;
        color: #94a3b8;
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .summary-card h3 {
        margin: 0 0 0.8rem 0;
        color: #f8fafc;
        font-size: 1.08rem;
        line-height: 1.2;
    }
    .summary-card__metrics {
        display: grid;
        gap: 0.55rem;
    }
    .summary-card__row {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        padding-top: 0.45rem;
        border-top: 1px solid rgba(148, 163, 184, 0.16);
    }
    .summary-card__row:first-child {
        padding-top: 0;
        border-top: 0;
    }
    .summary-card__label {
        color: #cbd5e1;
        font-size: 0.86rem;
    }
    .summary-card__value {
        color: #f8fafc;
        font-size: 1rem;
        font-weight: 600;
        text-align: right;
    }
    @media (max-width: 900px) {
        .summary-groups {
            grid-template-columns: 1fr;
        }
    }
</style>
"""


def inject_css() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
