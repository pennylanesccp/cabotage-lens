from __future__ import annotations

from html import escape
from typing import Any, Callable

import streamlit as st

_RUN_LOG_HEIGHT_PX = 260


def format_countdown(value: Any) -> str:
    try:
        total_seconds = max(int(round(float(value))), 0)
    except (TypeError, ValueError):
        total_seconds = 0
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:d}h {minutes:02d}m {seconds:02d}s"
    if minutes > 0:
        return f"{minutes:d}m {seconds:02d}s"
    return f"{seconds:d}s"


def status_card(message: str, *, tone: str = "info") -> str:
    palette = {
        "info": ("#eff6ff", "#1d4ed8", "#1e3a8a"),
        "success": ("#ecfdf5", "#047857", "#064e3b"),
        "warning": ("#fff7ed", "#c2410c", "#7c2d12"),
        "error": ("#fef2f2", "#dc2626", "#7f1d1d"),
    }
    background, border, text = palette.get(tone, palette["info"])
    return (
        f"<section style='padding:0.75rem 0.95rem;border-radius:16px;border:1px solid {border};"
        f"background:{background};color:{text};font-weight:600;margin:0.4rem 0 0.55rem 0;'>"
        f"{escape(message)}</section>"
    )


def inject_run_feedback_css() -> None:
    st.markdown(
        """
        <style>
            .run-feedback-log {
                margin: 0.55rem 0 1rem 0;
                border: 1px solid rgba(15, 23, 42, 0.12);
                border-radius: 18px;
                background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.96));
                overflow: hidden;
                box-shadow: 0 18px 38px rgba(15, 23, 42, 0.14);
            }
            .run-feedback-log__title {
                padding: 0.7rem 0.95rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.2);
                color: #e2e8f0;
                font: 700 0.9rem/1.2 ui-monospace, SFMono-Regular, Consolas, monospace;
            }
            .run-feedback-log__body {
                overflow-y: auto;
                padding: 0.65rem 0.95rem 0.8rem 0.95rem;
            }
            .run-feedback-log__line,
            .run-feedback-log__empty {
                white-space: pre-wrap;
                word-break: break-word;
                font: 500 0.79rem/1.45 ui-monospace, SFMono-Regular, Consolas, monospace;
                margin-bottom: 0.2rem;
            }
            .run-feedback-log__line--info { color: #bfdbfe; }
            .run-feedback-log__line--debug { color: #94a3b8; }
            .run-feedback-log__line--warning { color: #fdba74; }
            .run-feedback-log__line--error { color: #fca5a5; }
            .run-feedback-log__empty { color: #94a3b8; }
            .run-feedback-cooldown {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.8rem 0.95rem;
                border-radius: 16px;
                border: 1px solid #c2410c;
                background: #fff7ed;
                color: #7c2d12;
                margin: 0.4rem 0 0.55rem 0;
            }
            .run-feedback-cooldown__spinner {
                width: 1.05rem;
                height: 1.05rem;
                border-radius: 999px;
                border: 3px solid rgba(194, 65, 12, 0.18);
                border-top-color: #c2410c;
                animation: run-feedback-spin 0.8s linear infinite;
                flex: 0 0 auto;
            }
            .run-feedback-cooldown__text {
                font-weight: 600;
            }
            @keyframes run-feedback-spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _log_level_class(line: str) -> str:
    if "[CRITICAL]" in line or "[ERROR]" in line:
        return "error"
    if "[WARNING]" in line:
        return "warning"
    if "[DEBUG]" in line:
        return "debug"
    return "info"


def render_live_run_logs(log_box: Any, *, title: str = "Live evaluation log") -> None:
    shown = list(st.session_state.get("ui_logs", []))[-int(st.session_state.get("log_last_n", 300)) :]
    lines = [
        (
            f"<div class='run-feedback-log__line run-feedback-log__line--{_log_level_class(line)}'>"
            f"{escape(line)}</div>"
        )
        for line in shown
    ]
    if not lines:
        lines = ["<div class='run-feedback-log__empty'>Waiting for live logs...</div>"]
    log_box.markdown(
        (
            "<section class='run-feedback-log'>"
            f"<div class='run-feedback-log__title'>{escape(title)}</div>"
            f"<div class='run-feedback-log__body' style='max-height:{_RUN_LOG_HEIGHT_PX}px;'>"
            + "".join(lines)
            + "</div></section>"
        ),
        unsafe_allow_html=True,
    )


def _cooldown_markup(message: str) -> str:
    return (
        "<section class='run-feedback-cooldown'>"
        "<span class='run-feedback-cooldown__spinner'></span>"
        f"<div class='run-feedback-cooldown__text'>{escape(message)}</div>"
        "</section>"
    )


def make_progress_callback(
    progress_bar: Any,
    status_box: Any,
    cooldown_box: Any,
    log_box: Any,
    *,
    default_working_message: str = "Working...",
    log_title: str = "Live evaluation log",
) -> Callable[[dict[str, Any]], None]:
    def _callback(payload: dict[str, Any]) -> None:
        if "current" in payload or "total" in payload:
            total = max(int(payload.get("total") or 0), 1)
            current = min(max(int(payload.get("current") or 0), 0), total)
            progress_bar.progress(current / total)

        phase = str(payload.get("phase") or "").strip().lower()
        success_count = payload.get("success_count")
        fail_count = payload.get("fail_count")
        destination = str(payload.get("destination") or "").strip()
        message = str(payload.get("message") or "").strip()
        if not message:
            message = "Waiting for provider cooldown to expire" if phase == "cooldown_wait" else default_working_message

        parts = [message]
        if destination:
            parts.append(destination)
        if success_count is not None or fail_count is not None:
            parts.append(f"ok={int(success_count or 0)} fail={int(fail_count or 0)}")
        tone = "error" if phase == "error" else "success" if phase == "complete" else "info"
        status_box.markdown(status_card("  ".join(parts), tone=tone), unsafe_allow_html=True)

        if phase == "cooldown_wait" and str(payload.get("state") or "").strip().lower() != "retrying":
            provider = str(payload.get("provider") or "provider").strip()
            reason = str(payload.get("reason") or "rate_limited").strip().replace("_", " ")
            retry_in = format_countdown(payload.get("remaining_s"))
            cooldown_box.markdown(
                _cooldown_markup(
                    f"Provider cooldown active for {provider} ({reason}). Retrying automatically in {retry_in}."
                ),
                unsafe_allow_html=True,
            )
        else:
            cooldown_box.empty()

        render_live_run_logs(log_box, title=log_title)

    return _callback
