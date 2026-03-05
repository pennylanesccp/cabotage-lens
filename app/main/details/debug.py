from __future__ import annotations

import json
from typing import Any, Mapping

import streamlit as st


def render_debug(payload: Mapping[str, Any], geo: Mapping[str, Any] | None, results: Mapping[str, Any] | None) -> None:
    with st.expander("Raw logs", expanded=False):
        logs = list(st.session_state.get("ui_logs", []))
        shown = logs[-int(st.session_state.get("log_last_n", 300)):]
        st.text_area("Logs", value="\n".join(shown), height=220)

    with st.expander("Pipeline JSON", expanded=False):
        pipeline_blob = {
            "scenario": payload,
            "geo": geo,
            "results": results,
        }
        st.code(json.dumps(pipeline_blob, ensure_ascii=False, indent=2), language="json")
