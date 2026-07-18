import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modules.costs import fuel_price_refresh


class _FakeStorageClient:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.uploads: list[dict[str, object]] = []

    def upload_bytes(
        self,
        *,
        bucket,
        object_path,
        payload,
        content_type,
        upsert=True,
        timeout_s=30.0,
    ) -> None:
        if self.error is not None:
            raise self.error
        self.uploads.append(
            {
                "bucket": bucket,
                "object_path": object_path,
                "payload": payload,
                "content_type": content_type,
                "upsert": upsert,
                "timeout_s": timeout_s,
            }
        )


class FuelPriceRefreshTests(unittest.TestCase):
    def test_refresh_updates_both_runtime_price_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fallback_diesel = root / "fallback-diesel.csv"
            fallback_bunker = root / "fallback-bunker.txt"
            runtime_diesel = root / "runtime" / "latest_diesel_prices.csv"
            runtime_bunker = root / "runtime" / "santos_bunker_brl.txt"
            fallback_diesel.write_text("UF,price\nSP,6.000\n", encoding="utf-8")
            fallback_bunker.write_text("2026-01-01\tJan 1\t3000.00\t4000.00\t5.000000\n", encoding="utf-8")
            storage_settings = SimpleNamespace(data_bucket="cabotage-lens")
            storage_client = _FakeStorageClient()

            def _download(_url, path, *, timeout):
                self.assertEqual(timeout, 12.0)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"excel")
                return True

            def _process(_excel_path, output_path):
                output_path.write_text("UF,price\nSP,6.500\n", encoding="utf-8")

            def _write_bunker(_prices, *, output_path, append):
                self.assertFalse(append)
                Path(output_path).write_text(
                    "2026-07-15\tJul 15\t3250.00\t4300.00\t5.000000\n",
                    encoding="utf-8",
                )
                return str(output_path)

            with patch.object(fuel_price_refresh, "_RUNTIME_DIR", runtime_diesel.parent), patch.object(
                fuel_price_refresh,
                "_RUNTIME_DIESEL_CSV",
                runtime_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_RUNTIME_BUNKER_TXT",
                runtime_bunker,
            ), patch.object(
                fuel_price_refresh,
                "_active_diesel_path",
                return_value=fallback_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_active_bunker_path",
                return_value=fallback_bunker,
            ), patch.object(
                fuel_price_refresh,
                "get_bunker_price",
                return_value=3000.0,
            ), patch.object(
                fuel_price_refresh,
                "download_anp_file",
                side_effect=_download,
            ), patch.object(
                fuel_price_refresh,
                "process_anp_excel",
                side_effect=_process,
            ), patch.object(
                fuel_price_refresh,
                "load_data_assets_settings",
                return_value=storage_settings,
            ), patch.object(
                fuel_price_refresh,
                "build_data_assets_client",
                return_value=storage_client,
            ), patch.object(
                fuel_price_refresh,
                "fetch_santos_prices",
                return_value={"vlsfo_usd_per_mt": 650.0, "mgo_usd_per_mt": 860.0},
            ), patch.object(
                fuel_price_refresh,
                "apply_fx_brl",
                return_value={"vlsfo_brl_per_mt": 3250.0},
            ), patch.object(
                fuel_price_refresh,
                "write_prices_txt",
                side_effect=_write_bunker,
            ):
                result = fuel_price_refresh.refresh_fuel_prices(timeout_s=12.0)

            self.assertTrue(result.diesel_updated)
            self.assertTrue(result.bunker_updated)
            self.assertTrue(result.prices_changed)
            self.assertTrue(result.diesel_price_assets_archived)
            self.assertEqual(result.diesel_csv_path, runtime_diesel.resolve())
            self.assertEqual(result.bunker_price_brl_mt, 3250.0)
            self.assertEqual(result.warnings, ())
            self.assertEqual(len(storage_client.uploads), 2)
            workbook_upload, diesel_prices_upload = storage_client.uploads
            self.assertEqual(workbook_upload["bucket"], "cabotage-lens")
            self.assertEqual(
                workbook_upload["object_path"],
                "data/raw/road_data/semanal-estados-desde-2013.xlsx",
            )
            self.assertEqual(workbook_upload["payload"], b"excel")
            self.assertEqual(
                workbook_upload["content_type"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            self.assertTrue(workbook_upload["upsert"])
            self.assertEqual(workbook_upload["timeout_s"], 12.0)
            self.assertEqual(diesel_prices_upload["bucket"], "cabotage-lens")
            self.assertEqual(
                diesel_prices_upload["object_path"],
                "data/processed/road_data/latest_diesel_prices.csv",
            )
            self.assertEqual(
                diesel_prices_upload["payload"].replace(b"\r\n", b"\n"),
                b"UF,price\nSP,6.500\n",
            )
            self.assertEqual(diesel_prices_upload["content_type"], "text/csv; charset=utf-8")
            self.assertTrue(diesel_prices_upload["upsert"])
            self.assertEqual(diesel_prices_upload["timeout_s"], 12.0)

    def test_refresh_keeps_new_diesel_prices_when_storage_upload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fallback_diesel = root / "fallback-diesel.csv"
            fallback_bunker = root / "fallback-bunker.txt"
            runtime_diesel = root / "runtime" / "latest_diesel_prices.csv"
            runtime_bunker = root / "runtime" / "santos_bunker_brl.txt"
            fallback_diesel.write_text("UF,price\nSP,6.000\n", encoding="utf-8")
            fallback_bunker.write_text("2026-01-01\tJan 1\t3000.00\t4000.00\t5.000000\n", encoding="utf-8")

            def _download(_url, path, *, timeout):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"excel")
                return True

            def _process(_excel_path, output_path):
                output_path.write_text("UF,price\nSP,6.500\n", encoding="utf-8")

            with patch.object(fuel_price_refresh, "_RUNTIME_DIR", runtime_diesel.parent), patch.object(
                fuel_price_refresh,
                "_RUNTIME_DIESEL_CSV",
                runtime_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_RUNTIME_BUNKER_TXT",
                runtime_bunker,
            ), patch.object(
                fuel_price_refresh,
                "_active_diesel_path",
                return_value=fallback_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_active_bunker_path",
                return_value=fallback_bunker,
            ), patch.object(
                fuel_price_refresh,
                "get_bunker_price",
                return_value=3000.0,
            ), patch.object(
                fuel_price_refresh,
                "download_anp_file",
                side_effect=_download,
            ), patch.object(
                fuel_price_refresh,
                "process_anp_excel",
                side_effect=_process,
            ), patch.object(
                fuel_price_refresh,
                "load_data_assets_settings",
                return_value=SimpleNamespace(data_bucket="cabotage-lens"),
            ), patch.object(
                fuel_price_refresh,
                "build_data_assets_client",
                return_value=_FakeStorageClient(error=RuntimeError("storage offline")),
            ), patch.object(
                fuel_price_refresh,
                "fetch_santos_prices",
                side_effect=RuntimeError("offline"),
            ):
                result = fuel_price_refresh.refresh_fuel_prices(timeout_s=12.0)

            self.assertTrue(result.diesel_updated)
            self.assertTrue(result.prices_changed)
            self.assertFalse(result.diesel_price_assets_archived)
            self.assertEqual(result.diesel_csv_path, runtime_diesel.resolve())
            self.assertEqual(runtime_diesel.read_text(encoding="utf-8"), "UF,price\nSP,6.500\n")
            self.assertTrue(
                any("ANP price-file archive failed" in warning for warning in result.warnings),
            )

    def test_refresh_does_not_archive_anp_workbook_without_a_valid_price_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fallback_diesel = root / "fallback-diesel.csv"
            fallback_bunker = root / "fallback-bunker.txt"
            runtime_diesel = root / "runtime" / "latest_diesel_prices.csv"
            runtime_bunker = root / "runtime" / "santos_bunker_brl.txt"
            fallback_diesel.write_text("UF,price\nSP,6.000\n", encoding="utf-8")
            fallback_bunker.write_text("2026-01-01\tJan 1\t3000.00\t4000.00\t5.000000\n", encoding="utf-8")
            storage_client = _FakeStorageClient()

            def _download(_url, path, *, timeout):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"invalid-excel")
                return True

            with patch.object(fuel_price_refresh, "_RUNTIME_DIR", runtime_diesel.parent), patch.object(
                fuel_price_refresh,
                "_RUNTIME_DIESEL_CSV",
                runtime_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_RUNTIME_BUNKER_TXT",
                runtime_bunker,
            ), patch.object(
                fuel_price_refresh,
                "_active_diesel_path",
                return_value=fallback_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_active_bunker_path",
                return_value=fallback_bunker,
            ), patch.object(
                fuel_price_refresh,
                "get_bunker_price",
                return_value=3000.0,
            ), patch.object(
                fuel_price_refresh,
                "download_anp_file",
                side_effect=_download,
            ), patch.object(
                fuel_price_refresh,
                "process_anp_excel",
                return_value=None,
            ), patch.object(
                fuel_price_refresh,
                "load_data_assets_settings",
                return_value=SimpleNamespace(data_bucket="cabotage-lens"),
            ), patch.object(
                fuel_price_refresh,
                "build_data_assets_client",
                return_value=storage_client,
            ), patch.object(
                fuel_price_refresh,
                "fetch_santos_prices",
                side_effect=RuntimeError("offline"),
            ):
                result = fuel_price_refresh.refresh_fuel_prices(timeout_s=12.0)

            self.assertFalse(result.diesel_updated)
            self.assertFalse(result.diesel_price_assets_archived)
            self.assertEqual(result.diesel_csv_path, fallback_diesel)
            self.assertEqual(storage_client.uploads, [])
            self.assertTrue(
                any("produced no usable price table" in warning for warning in result.warnings),
            )

    def test_refresh_keeps_previous_inputs_when_sources_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fallback_diesel = root / "fallback-diesel.csv"
            fallback_bunker = root / "fallback-bunker.txt"
            fallback_diesel.write_text("UF,price\nSP,6.000\n", encoding="utf-8")
            fallback_bunker.write_text("2026-01-01\tJan 1\t3000.00\t4000.00\t5.000000\n", encoding="utf-8")

            with patch.object(fuel_price_refresh, "_RUNTIME_DIR", root / "runtime"), patch.object(
                fuel_price_refresh,
                "_RUNTIME_DIESEL_CSV",
                root / "runtime" / "diesel.csv",
            ), patch.object(
                fuel_price_refresh,
                "_RUNTIME_BUNKER_TXT",
                root / "runtime" / "bunker.txt",
            ), patch.object(
                fuel_price_refresh,
                "_active_diesel_path",
                return_value=fallback_diesel,
            ), patch.object(
                fuel_price_refresh,
                "_active_bunker_path",
                return_value=fallback_bunker,
            ), patch.object(
                fuel_price_refresh,
                "get_bunker_price",
                return_value=3000.0,
            ), patch.object(
                fuel_price_refresh,
                "download_anp_file",
                return_value=False,
            ), patch.object(
                fuel_price_refresh,
                "fetch_santos_prices",
                side_effect=RuntimeError("offline"),
            ):
                result = fuel_price_refresh.refresh_fuel_prices()

            self.assertFalse(result.diesel_updated)
            self.assertFalse(result.bunker_updated)
            self.assertFalse(result.prices_changed)
            self.assertEqual(result.diesel_csv_path, fallback_diesel)
            self.assertEqual(result.bunker_price_brl_mt, 3000.0)
            self.assertEqual(len(result.warnings), 2)


if __name__ == "__main__":
    unittest.main()
