from __future__ import annotations

import streamlit as st


def render_run_button() -> bool:
    route_ok = bool(st.session_state.origin.strip()) and bool(st.session_state.destiny.strip())
    cargo_ok = float(st.session_state.cargo_t) > 0.0
    run_disabled = not (route_ok and cargo_ok)

    if run_disabled:
        st.caption("Fill origin, destination, and cargo above zero.")

    return st.button("Run analysis", type="primary", width="stretch", disabled=run_disabled)

