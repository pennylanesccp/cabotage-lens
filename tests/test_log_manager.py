import gzip
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.infra.log_manager import (
    detect_runtime_environment,
    bind_log_context,
    get_current_archive_object_path,
    get_current_local_log_path,
    get_logger,
    init_logging,
    local_file_logging_enabled_by_default,
    storage_archival_enabled_by_default,
)


class _FakeStorageClient:
    def __init__(self) -> None:
        self.uploads = []

    def upload_bytes(self, *, object_path, payload, content_type, upsert=True, timeout_s=30.0) -> None:
        self.uploads.append(
            {
                "object_path": object_path,
                "payload": payload,
                "content_type": content_type,
                "upsert": upsert,
                "timeout_s": timeout_s,
            }
        )


class LogManagerTests(unittest.TestCase):
    def tearDown(self) -> None:
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    def test_init_logging_without_archive_keeps_console_only(self) -> None:
        init_logging(level="INFO", archive_to_storage=False, force_clean=True)

        self.assertIsNone(get_current_archive_object_path())
        self.assertIsNone(get_current_local_log_path())
        self.assertGreaterEqual(len(logging.getLogger().handlers), 2)

    def test_init_logging_archives_jsonl_gz_to_supabase_storage(self) -> None:
        fake_client = _FakeStorageClient()

        with patch(
            "modules.infra.log_manager.SupabaseStorageClient",
            return_value=fake_client,
        ), patch(
            "modules.infra.log_manager.build_log_archive_object_path",
            return_value="logs/prod/2026/03/13/run-123.jsonl.gz",
        ):
            init_logging(
                level="INFO",
                archive_to_storage=True,
                archive_run_id="run-123",
                environment="prod",
                force_clean=True,
            )
            with bind_log_context(run_id="bulk-999", scenario_key="scenario-1"):
                get_logger("carbon.tests").info("bulk evaluation complete")

            root = logging.getLogger()
            for handler in list(root.handlers):
                handler.close()
                root.removeHandler(handler)

        self.assertEqual(get_current_archive_object_path(), "logs/prod/2026/03/13/run-123.jsonl.gz")
        self.assertIsNone(get_current_local_log_path())
        self.assertEqual(len(fake_client.uploads), 1)
        upload = fake_client.uploads[0]
        self.assertEqual(upload["content_type"], "application/gzip")
        payload = gzip.decompress(upload["payload"]).decode("utf-8").strip().splitlines()
        self.assertEqual(len(payload), 1)
        entry = json.loads(payload[0])
        self.assertEqual(entry["module"], "carbon.tests")
        self.assertEqual(entry["message"], "bulk evaluation complete")
        self.assertEqual(entry["run_id"], "bulk-999")
        self.assertEqual(entry["scenario_key"], "scenario-1")

    def test_init_logging_writes_local_log_file_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            init_logging(
                level="INFO",
                archive_to_storage=False,
                archive_to_local_file=True,
                archive_run_id="ui-session",
                local_logs_dir=tmpdir,
                force_clean=True,
            )
            get_logger("carbon.tests").info("local file logging works")

            root = logging.getLogger()
            for handler in list(root.handlers):
                handler.close()
                root.removeHandler(handler)

            local_path = get_current_local_log_path()
            self.assertIsNotNone(local_path)
            assert local_path is not None
            local_file = Path(local_path)
            self.assertTrue(local_file.exists())
            self.assertEqual(local_file.parent.name, Path(tmpdir).name)
            self.assertIn("ui-session__", local_file.name)
            self.assertIn("local file logging works", local_file.read_text(encoding="utf-8"))

    def test_runtime_environment_defaults_local_logging_policy(self) -> None:
        with patch("modules.infra.log_manager._LOCAL_SECRETS_PATH.exists", return_value=True), patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            environment = detect_runtime_environment()

        self.assertEqual(environment, "local")
        self.assertTrue(local_file_logging_enabled_by_default(environment))
        self.assertFalse(storage_archival_enabled_by_default(environment))

    def test_runtime_environment_defaults_hosted_archival_policy(self) -> None:
        with patch("modules.infra.log_manager._LOCAL_SECRETS_PATH.exists", return_value=False), patch.dict(
            "os.environ",
            {"IS_STREAMLIT_CLOUD": "true"},
            clear=True,
        ):
            environment = detect_runtime_environment()

        self.assertEqual(environment, "hosted")
        self.assertFalse(local_file_logging_enabled_by_default(environment))
        self.assertTrue(storage_archival_enabled_by_default(environment))


if __name__ == "__main__":
    unittest.main()
