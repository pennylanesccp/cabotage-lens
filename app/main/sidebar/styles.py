from __future__ import annotations

import streamlit as st


def apply_sidebar_styles(*, origin_loading: bool = False, destiny_loading: bool = False) -> None:
    loading_rules: list[str] = []
    for field_name, is_loading in (("origin", origin_loading), ("destiny", destiny_loading)):
        if not is_loading:
            continue

        container_selector = f"section[data-testid=\"stSidebar\"] .st-key-{field_name}"
        loading_rules.append(
            f"""
            {container_selector} div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
                position: relative;
            }}
            {container_selector} div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {{
                opacity: 0 !important;
                visibility: hidden !important;
            }}
            {container_selector} div[data-testid="stSelectbox"] div[data-baseweb="select"]::after {{
                content: "";
                position: absolute;
                top: 50%;
                right: 0.85rem;
                z-index: 2;
                width: 0.95rem;
                height: 0.95rem;
                margin-top: -0.475rem;
                border-radius: 999px;
                border: 2px solid rgba(148, 163, 184, 0.28);
                border-top-color: #f8fafc;
                animation: sidebar-field-spinner 0.75s linear infinite;
                pointer-events: none;
            }}
            """
        )

    st.markdown(
        f"""
        <style>
            @keyframes sidebar-field-spinner {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            {''.join(loading_rules)}
        </style>
        """,
        unsafe_allow_html=True,
    )
