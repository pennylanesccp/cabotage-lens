from __future__ import annotations

import streamlit as st

BASE_CSS = """
<style>
    :root {
        --cl-bg: #101820;
        --cl-surface: #f8fafc;
        --cl-surface-muted: #edf2f7;
        --cl-ink: #10202b;
        --cl-ink-muted: #4b5f70;
        --cl-line: rgba(16, 32, 43, 0.12);
        --cl-navy: #123047;
        --cl-green: #0f766e;
        --cl-amber: #b7791f;
        --cl-blue: #2563eb;
        --cl-red: #b91c1c;
        --cl-radius: 8px;
    }
    .stApp {
        background:
            linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(236, 242, 247, 0.98)),
            #f3f6f9;
        color: var(--cl-ink);
    }
    .main .block-container {
        width: min(100%, 1180px);
        max-width: 1180px;
        padding: 1.35rem 1.6rem 2rem 1.6rem;
        margin: 0 auto;
        color: var(--cl-ink);
    }
    div[data-testid="stMainBlockContainer"],
    .stMain .block-container {
        width: min(100%, 1180px) !important;
        max-width: 1180px !important;
        padding: 1.35rem 1.6rem 2rem 1.6rem !important;
        margin: 0 auto !important;
        color: var(--cl-ink);
    }
    .main .block-container h1,
    .main .block-container h2,
    .main .block-container h3,
    .main .block-container h4,
    .main .block-container h5,
    .main .block-container h6,
    .main .block-container p,
    .main .block-container label,
    .main .block-container span {
        letter-spacing: 0;
    }
    div[data-testid="stMainBlockContainer"] h1,
    div[data-testid="stMainBlockContainer"] h2,
    div[data-testid="stMainBlockContainer"] h3,
    div[data-testid="stMainBlockContainer"] h4,
    div[data-testid="stMainBlockContainer"] h5,
    div[data-testid="stMainBlockContainer"] h6,
    div[data-testid="stMainBlockContainer"] p,
    div[data-testid="stMainBlockContainer"] label,
    div[data-testid="stMainBlockContainer"] span {
        letter-spacing: 0;
    }
    .main .block-container h1,
    .main .block-container h2,
    .main .block-container h3 {
        color: var(--cl-ink);
    }
    div[data-testid="stMainBlockContainer"] h1,
    div[data-testid="stMainBlockContainer"] h2,
    div[data-testid="stMainBlockContainer"] h3 {
        color: var(--cl-ink);
    }
    .main .block-container p,
    .main .block-container label {
        color: var(--cl-ink-muted);
    }
    div[data-testid="stMainBlockContainer"] p,
    div[data-testid="stMainBlockContainer"] label {
        color: var(--cl-ink-muted);
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
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(16, 32, 43, 0.16);
        background:
            linear-gradient(180deg, rgba(16, 32, 43, 0.98), rgba(18, 48, 71, 0.96)),
            #10202b;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: #e2e8f0;
        letter-spacing: 0;
    }
    .sidebar-brand {
        padding: 0.15rem 0 0.55rem 0;
    }
    .sidebar-brand__title {
        margin: 0;
        color: #f8fafc;
        font-size: 1.02rem;
        font-weight: 750;
    }
    .sidebar-brand__subtitle {
        margin: 0.35rem 0 0 0;
        color: #cbd5e1;
        font-size: 0.84rem;
        line-height: 1.45;
    }
    .sidebar-section-label {
        margin: 0.9rem 0 0.35rem 0;
        color: #e2e8f0;
        font-size: 0.72rem;
        font-weight: 750;
        text-transform: uppercase;
    }
    .page-header {
        margin: 0 0 1rem 0;
        padding: 1.15rem 1.25rem;
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.97), rgba(243, 248, 246, 0.96)),
            #ffffff;
        box-shadow: 0 14px 34px rgba(16, 32, 43, 0.08);
    }
    .page-header h1 {
        margin: 0;
        color: var(--cl-ink);
        font-size: clamp(1.45rem, 2vw, 2rem);
        line-height: 1.15;
    }
    .page-header p {
        margin: 0.55rem 0 0 0;
        color: var(--cl-ink-muted);
        font-size: 0.95rem;
        line-height: 1.5;
        max-width: 58rem;
    }
    .page-header__kicker {
        margin: 0 0 0.38rem 0;
        color: var(--cl-green);
        font-size: 0.72rem;
        font-weight: 750;
        text-transform: uppercase;
    }
    .page-header__meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.85rem;
    }
    .meta-chip {
        display: inline-flex;
        align-items: center;
        min-height: 1.7rem;
        padding: 0.18rem 0.55rem;
        border: 1px solid rgba(15, 118, 110, 0.18);
        border-radius: var(--cl-radius);
        background: rgba(15, 118, 110, 0.08);
        color: var(--cl-ink);
        font-size: 0.78rem;
        font-weight: 650;
        overflow-wrap: anywhere;
    }
    .section-heading {
        margin: 1.05rem 0 0.55rem 0;
    }
    .section-heading__kicker {
        margin: 0;
        color: var(--cl-green);
        font-size: 0.72rem;
        font-weight: 750;
        text-transform: uppercase;
    }
    .section-heading h2,
    .section-heading h3 {
        margin: 0.15rem 0 0 0;
        color: var(--cl-ink);
        font-size: 1.15rem;
    }
    .section-heading p {
        margin: 0.25rem 0 0 0;
        color: var(--cl-ink-muted);
        font-size: 0.9rem;
        line-height: 1.45;
    }
    .insight-strip {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.7rem;
        margin: 0.55rem 0 0.85rem 0;
    }
    .insight-card {
        min-width: 0;
        padding: 0.8rem 0.9rem;
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background: #ffffff;
    }
    .insight-card__label {
        margin: 0;
        color: var(--cl-ink-muted);
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .insight-card__value {
        margin: 0.25rem 0 0 0;
        color: var(--cl-ink);
        font-size: 0.98rem;
        font-weight: 720;
        line-height: 1.3;
    }
    .insight-card__note {
        margin: 0.2rem 0 0 0;
        color: var(--cl-ink-muted);
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .summary-panels {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.55rem 0 0.9rem 0;
    }
    .summary-panel {
        min-width: 0;
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background: #ffffff;
        padding: 0.9rem;
        box-shadow: 0 12px 26px rgba(16, 32, 43, 0.07);
    }
    .summary-panel[data-accent="multimodal"] {
        border-top: 4px solid var(--cl-green);
    }
    .summary-panel[data-accent="road"] {
        border-top: 4px solid var(--cl-amber);
    }
    .summary-panel__header {
        margin-bottom: 0.7rem;
    }
    .summary-panel__eyebrow {
        margin: 0;
        color: var(--cl-ink);
        font-size: 0.78rem;
        font-weight: 750;
        text-transform: uppercase;
    }
    .summary-panel__subhead {
        margin: 0.18rem 0 0 0;
        color: var(--cl-ink-muted);
        font-size: 0.78rem;
        line-height: 1.35;
    }
    .summary-panel__metrics {
        display: grid;
        grid-template-columns: repeat(3, minmax(6.6rem, 1fr));
        align-items: stretch;
        gap: 0.55rem;
    }
    .summary-panel__metric {
        min-width: 0;
        padding: 0.55rem;
        border: 1px solid rgba(16, 32, 43, 0.08);
        border-radius: var(--cl-radius);
        background: #f8fafc;
    }
    .summary-panel__label {
        margin: 0 0 0.25rem 0;
        color: var(--cl-ink-muted);
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .summary-panel__value {
        color: var(--cl-ink);
        font-size: 1.05rem;
        font-weight: 760;
        line-height: 1.15;
        margin: 0;
        overflow-wrap: anywhere;
    }
    .quality-note {
        margin: 0.7rem 0;
        padding: 0.8rem 0.9rem;
        border: 1px solid rgba(183, 121, 31, 0.25);
        border-radius: var(--cl-radius);
        background: rgba(255, 251, 235, 0.92);
        color: #5f3a06;
        line-height: 1.45;
    }
    .quality-note strong {
        color: #7c4a03;
    }
    .quality-note p {
        margin: 0.35rem 0 0 0;
        color: #5f3a06;
    }
    .quality-note ul {
        margin: 0.45rem 0 0 1.1rem;
        padding: 0;
    }
    .quality-note li {
        margin: 0.22rem 0;
        color: #5f3a06;
    }
    .empty-state {
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background: #ffffff;
        padding: 0.95rem 1rem;
        color: var(--cl-ink-muted);
        line-height: 1.45;
    }
    .map-shell {
        min-height: clamp(320px, 46vh, 480px);
        display: grid;
        place-items: center;
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background:
            linear-gradient(135deg, rgba(18, 48, 71, 0.94), rgba(15, 118, 110, 0.84)),
            #123047;
        box-shadow: 0 16px 34px rgba(16, 32, 43, 0.12);
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
        color: #a7f3d0;
        font-size: 0.76rem;
        font-weight: 750;
        text-transform: uppercase;
    }
    .map-shell h3 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.35rem;
    }
    .map-shell p {
        margin: 0.5rem 0 0 0;
        color: #e2e8f0;
        font-size: 0.94rem;
        line-height: 1.5;
    }
    .data-panel {
        padding: 0.9rem 1rem;
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background: #ffffff;
        margin: 0.65rem 0 0.85rem 0;
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
    div[data-testid="stMetric"] {
        border: 1px solid var(--cl-line);
        border-radius: var(--cl-radius);
        background: #ffffff;
        padding: 0.65rem 0.75rem;
    }
    div[data-testid="stMetric"] label {
        color: var(--cl-ink-muted);
    }
    div[data-testid="stMetricValue"] {
        color: var(--cl-ink);
    }
    div[data-testid="stExpander"] {
        border-color: var(--cl-line);
        border-radius: var(--cl-radius);
        background: rgba(255, 255, 255, 0.82);
    }
    div[data-testid="stDataFrame"] {
        border-radius: var(--cl-radius);
        overflow: hidden;
    }
    iframe {
        border-radius: var(--cl-radius) !important;
    }
    @media (max-width: 1250px) {
        .summary-panels,
        .insight-strip {
            grid-template-columns: 1fr;
        }
    }
    @media (max-width: 980px) {
        .summary-panel__metrics {
            grid-template-columns: 1fr;
        }
        .summary-panel__metric {
            padding: 0.75rem 0.2rem;
        }
        .summary-panel__metric + .summary-panel__metric {
            border-left: 0;
        }
    }
    @media (max-width: 720px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        div[data-testid="stMainBlockContainer"],
        .stMain .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .page-header {
            padding: 1rem;
        }
    }
</style>
"""


def inject_css() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
