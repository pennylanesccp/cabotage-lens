import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.main.utils import antaq


class AntaqAppRefreshTests(unittest.TestCase):
    def test_portal_failure_without_local_raw_returns_nonfatal_summary(self) -> None:
        portal_error = RuntimeError(
            "Failed to reach the ANTAQ download portal. Check internet access or rerun with --skip-download."
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch.object(antaq, "DEFAULT_RAW_DIR", Path(tmpdir)),
                patch.object(antaq, "load_data_assets_settings", return_value=None),
                patch.object(antaq, "refresh_antaq_pipeline", side_effect=portal_error),
            ):
                summary = antaq.run_antaq_refresh_for_app(start_year=2026)

        self.assertFalse(summary["app_refresh_status"]["ok"])
        self.assertEqual(summary["app_refresh_status"]["reason"], "portal_unavailable_no_local_raw")
        self.assertTrue(summary["download"]["skipped"])

    def test_portal_failure_retries_with_skip_download_when_local_raw_exists(self) -> None:
        portal_error = RuntimeError("Failed to reach the ANTAQ download portal.")
        successful_summary = {"download": {"skipped": True}, "voyages_build": {}, "materialize": {}, "sea_matrix": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            for table in antaq.DEFAULT_REQUIRED_TABLES:
                (raw_dir / f"2026{table}.txt").write_text("placeholder\n", encoding="utf-8")
            with (
                patch.object(antaq, "DEFAULT_RAW_DIR", raw_dir),
                patch.object(antaq, "load_data_assets_settings", return_value=None),
                patch.object(
                    antaq,
                    "refresh_antaq_pipeline",
                    side_effect=[portal_error, successful_summary],
                ) as mocked_refresh,
                patch.object(antaq, "_seed_local_refresh_outputs_into_cache"),
                patch.object(antaq, "invalidate_routing_asset_caches"),
            ):
                summary = antaq.run_antaq_refresh_for_app(start_year=2026)

        self.assertTrue(summary["app_refresh_status"]["ok"])
        self.assertTrue(summary["app_refresh_status"]["used_local_raw_fallback"])
        self.assertEqual(mocked_refresh.call_count, 2)
        self.assertTrue(mocked_refresh.call_args.kwargs["skip_download"])


if __name__ == "__main__":
    unittest.main()
