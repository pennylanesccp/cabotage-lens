import logging
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

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

    def test_init_state_defaults_local_file_logging_policy(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})

        with patch.object(state, "st", fake_streamlit), patch.object(
            state,
            "resolve_runtime_db_target",
            return_value="postgresql://postgres:***@example.supabase.co:5432/postgres",
        ), patch.object(
            state,
            "detect_runtime_environment",
            return_value="local",
        ), patch.object(
            state,
            "secret_value",
            side_effect=lambda key, default=None: default,
        ):
            state.init_state()

        self.assertEqual(fake_streamlit.session_state["runtime_environment"], "local")
        self.assertTrue(fake_streamlit.session_state["write_local_logs"])
        self.assertFalse(fake_streamlit.session_state["archive_logs"])

    def test_attach_streamlit_logging_passes_local_log_policy(self) -> None:
        fake_streamlit = SimpleNamespace(
            session_state={
                "runtime_environment": "local",
                "write_local_logs": True,
                "archive_logs": False,
            }
        )
        fake_root = SimpleNamespace(handlers=[], addHandler=Mock())

        with patch.object(state, "st", fake_streamlit), patch.object(
            state,
            "init_logging",
        ) as init_logging_mock, patch.object(
            state,
            "get_current_local_log_path",
            return_value="C:/repo/logs/session.log",
        ), patch.object(
            state,
            "get_current_archive_object_path",
            return_value=None,
        ), patch.object(
            state.logging,
            "getLogger",
            return_value=fake_root,
        ):
            state.attach_streamlit_logging(level="INFO", archive_to_storage=False)

        init_logging_mock.assert_called_once()
        self.assertEqual(init_logging_mock.call_args.kwargs["archive_to_local_file"], True)
        self.assertEqual(fake_streamlit.session_state["local_log_path"], "C:/repo/logs/session.log")

    def test_attach_streamlit_logging_records_effective_fallback_policy(self) -> None:
        fake_streamlit = SimpleNamespace(
            session_state={
                "runtime_environment": "local",
                "write_local_logs": True,
                "archive_logs": True,
            }
        )
        fake_root = SimpleNamespace(handlers=[], addHandler=Mock())

        with patch.object(state, "st", fake_streamlit), patch.object(
            state,
            "init_logging",
            side_effect=[RuntimeError("storage offline"), None],
        ) as init_logging_mock, patch.object(
            state,
            "get_current_local_log_path",
            return_value="C:/repo/logs/session.log",
        ), patch.object(
            state,
            "get_current_archive_object_path",
            return_value=None,
        ), patch.object(
            state.logging,
            "getLogger",
            return_value=fake_root,
        ):
            state.attach_streamlit_logging(level="INFO", archive_to_storage=True)

        self.assertEqual(init_logging_mock.call_count, 2)
        self.assertFalse(fake_streamlit.session_state["archive_logs"])
        self.assertTrue(fake_streamlit.session_state["write_local_logs"])

    def test_init_state_defaults_hosted_archival_policy(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})

        with patch.object(state, "st", fake_streamlit), patch.object(
            state,
            "resolve_runtime_db_target",
            return_value="postgresql://postgres:***@example.supabase.co:5432/postgres",
        ), patch.object(
            state,
            "detect_runtime_environment",
            return_value="hosted",
        ), patch.object(
            state,
            "secret_value",
            side_effect=lambda key, default=None: default,
        ):
            state.init_state()

        self.assertEqual(fake_streamlit.session_state["runtime_environment"], "hosted")
        self.assertFalse(fake_streamlit.session_state["write_local_logs"])
        self.assertTrue(fake_streamlit.session_state["archive_logs"])


if __name__ == "__main__":
    unittest.main()
