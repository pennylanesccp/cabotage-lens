from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND_PATH = Path(__file__).resolve().parent / "turnstile_frontend"
_TURNSTILE_COMPONENT = components.declare_component(
    "cabotagelens_turnstile",
    path=str(_FRONTEND_PATH),
)


def render_turnstile_widget(
    *,
    site_key: str,
    reset_nonce: int = 0,
    theme: str = "light",
    key: str | None = None,
) -> str | None:
    return _TURNSTILE_COMPONENT(
        site_key=str(site_key),
        reset_nonce=int(reset_nonce),
        theme=str(theme or "light"),
        key=key,
        default="",
    )
