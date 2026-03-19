import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main.utils import state


class StreamlitStateTests(unittest.TestCase):
    def test_streamlit_log_handler_writes_when_script_context_exists(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})
        handler = state.StreamlitLogHandler(max_lines=5)
        handler.setFormatter(logging.Formatter("{message}", style="{"))
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="hello from script thread",
            args=(),
            exc_info=None,
        )

        with patch.object(state, "st", fake_streamlit), patch.object(
            state,
            "get_script_run_ctx",
            return_value=object(),
        ):
            handler.emit(record)

        self.assertEqual(fake_streamlit.session_state["ui_logs"], ["hello from script thread"])

    def test_streamlit_log_handler_skips_threads_without_script_context(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})
        handler = state.StreamlitLogHandler(max_lines=5)
        handler.setFormatter(logging.Formatter("{message}", style="{"))
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=30,
            msg="background thread log",
            args=(),
            exc_info=None,
        )

        with patch.object(state, "st", fake_streamlit), patch.object(
            state,
            "get_script_run_ctx",
            return_value=None,
        ):
            handler.emit(record)

        self.assertEqual(fake_streamlit.session_state, {})


if __name__ == "__main__":
    unittest.main()
