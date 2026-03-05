from __future__ import annotations

from pathlib import Path
from typing import List

import streamlit as st

from modules.infra.database_manager import db_session, list_place_names

from app.main.utils.formatters import clean_place_label


def _route_endpoint_options(db_path_str: str, current_values: list[str]) -> list[str]:
    options: set[str] = set()

    for value in current_values:
        value_clean = str(value).strip()
        if value_clean:
            options.add(value_clean)

    try:
        with db_session(Path(db_path_str)) as conn:
            for value in list_place_names(conn):
                value_clean = str(value).strip()
                if value_clean:
                    options.add(value_clean)
    except Exception:
        pass

    return sorted(options, key=str.casefold)


def render_filters() -> List[str]:
    route_name_options = _route_endpoint_options(
        db_path_str=str(st.session_state.db_path_str),
        current_values=[str(st.session_state.origin), str(st.session_state.destiny)],
    )

    st.selectbox(
        "Origin",
        options=route_name_options,
        key="origin",
        accept_new_options=True,
        format_func=clean_place_label,
    )
    st.selectbox(
        "Destination",
        options=route_name_options,
        key="destiny",
        accept_new_options=True,
        format_func=clean_place_label,
    )
    st.number_input("Cargo (t)", min_value=0.0, step=0.5, key="cargo_t")
    return route_name_options
