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
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stMultiSelect"] div[data-baseweb="select"],
    div[data-testid="stSelect"] div[data-baseweb="select"],
    div[data-testid="stSelectbox"] [aria-haspopup="listbox"],
    div[data-testid="stMultiSelect"] [aria-haspopup="listbox"],
    div[data-testid="stSelect"] [aria-haspopup="listbox"],
    [role="listbox"] [role="option"],
    [data-baseweb="menu"] [role="option"],
    [data-testid="stBaseButton"],
    button,
    [role="button"],
    [role="tab"],
    a[href] {
        cursor: pointer;
    }
    input:not([readonly]):not([disabled]),
    textarea:not([readonly]):not([disabled]),
    [contenteditable="true"] {
        cursor: text;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] svg,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] svg,
    div[data-testid="stSelect"] div[data-baseweb="select"] svg {
        cursor: pointer;
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
    .summary-panels {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.9rem;
        margin: 0.55rem 0 0.9rem 0;
    }
    .summary-panel {
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: 22px;
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(9, 14, 26, 0.92)),
            #0f172a;
        padding: 0.95rem 1.1rem 1.05rem 1.1rem;
        box-shadow: 0 18px 38px rgba(2, 6, 23, 0.22);
    }
    .summary-panel[data-accent="multimodal"] {
        border-color: rgba(45, 212, 191, 0.34);
        box-shadow: inset 0 1px 0 rgba(94, 234, 212, 0.1), 0 18px 38px rgba(2, 6, 23, 0.22);
    }
    .summary-panel[data-accent="road"] {
        border-color: rgba(251, 191, 36, 0.28);
        box-shadow: inset 0 1px 0 rgba(252, 211, 77, 0.08), 0 18px 38px rgba(2, 6, 23, 0.22);
    }
    .summary-panel__header {
        margin-bottom: 0.8rem;
    }
    .summary-panel__eyebrow {
        margin: 0;
        color: #e2e8f0;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }
    .summary-panel__metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        align-items: stretch;
        gap: 0;
    }
    .summary-panel__metric {
        min-width: 0;
        padding: 0.15rem 0.95rem;
        text-align: center;
    }
    .summary-panel__metric + .summary-panel__metric {
        border-left: 1px solid rgba(148, 163, 184, 0.18);
    }
    .summary-panel__label {
        margin: 0 0 0.38rem 0;
        color: #94a3b8;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .summary-panel__value {
        color: #f8fafc;
        font-size: 1.16rem;
        font-weight: 700;
        line-height: 1.15;
        margin: 0;
    }
    .map-shell {
        min-height: 560px;
        display: grid;
        place-items: center;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 22px;
        background:
            radial-gradient(420px 180px at 20% 10%, rgba(56, 189, 248, 0.12), transparent 60%),
            radial-gradient(360px 220px at 85% 15%, rgba(45, 212, 191, 0.11), transparent 55%),
            linear-gradient(180deg, rgba(15, 23, 42, 0.94), rgba(8, 15, 29, 0.98)),
            #0f172a;
        box-shadow: inset 0 1px 0 rgba(148, 163, 184, 0.08), 0 18px 42px rgba(2, 6, 23, 0.24);
        margin-bottom: 1rem;
        overflow: hidden;
    }
    .map-shell__content {
        max-width: 28rem;
        padding: 1.4rem;
        text-align: center;
    }
    .map-shell__eyebrow {
        margin: 0 0 0.35rem 0;
        color: #38bdf8;
        font-size: 0.76rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }
    .map-shell h3 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.35rem;
    }
    .map-shell p {
        margin: 0.5rem 0 0 0;
        color: #cbd5e1;
        font-size: 0.94rem;
        line-height: 1.5;
    }
    .details-placeholder {
        color: #cbd5e1;
        font-size: 0.92rem;
        line-height: 1.5;
        margin: 0.15rem 0;
    }
    .details-placeholder strong {
        color: #f8fafc;
    }
    @media (max-width: 1100px) {
        .summary-panel__metrics {
            grid-template-columns: 1fr;
        }
        .summary-panel__metric {
            padding: 0.75rem 0.2rem;
        }
        .summary-panel__metric + .summary-panel__metric {
            border-left: 0;
            border-top: 1px solid rgba(148, 163, 184, 0.18);
        }
    }
    @media (max-width: 720px) {
        .summary-panels {
            grid-template-columns: 1fr;
        }
    }
</style>
"""


def inject_css() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
