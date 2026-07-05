from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main import run_feedback


def test_sanitize_ui_log_line_omits_traceback_block() -> None:
    raw = (
        "[2026-07-05 12:13:03][ERROR][app.heatmap.page] Failed to load cache-backed heatmap surface\n"
        "Traceback (most recent call last):\n"
        '  File "app/heatmap/page.py", line 435, in render_page\n'
        "RuntimeError: Supabase Postgres requires SUPABASE_DB_URL"
    )

    sanitized = run_feedback.sanitize_ui_log_line(raw)

    assert sanitized == "[2026-07-05 12:13:03][ERROR][app.heatmap.page] Failed to load cache-backed heatmap surface"
    assert "Traceback" not in sanitized
    assert 'File "app/heatmap/page.py"' not in sanitized


def test_render_live_run_logs_sanitizes_exception_records() -> None:
    fake_streamlit = SimpleNamespace(
        session_state={
            "log_last_n": 10,
            "ui_logs": [
                (
                    "[2026-07-05 12:13:03][ERROR][app.heatmap.page] Failed\n"
                    "Traceback (most recent call last):\n"
                    '  File "app/heatmap/page.py", line 435, in render_page\n'
                    "RuntimeError: failed"
                )
            ],
        }
    )
    log_box = Mock()

    with patch.object(run_feedback, "st", fake_streamlit):
        run_feedback.render_live_run_logs(log_box)

    html = log_box.markdown.call_args.args[0]
    assert "[ERROR][app.heatmap.page] Failed" in html
    assert "Traceback" not in html
    assert "app/heatmap/page.py" not in html
