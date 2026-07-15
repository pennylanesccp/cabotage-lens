import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.costs import fuel_price_refresh


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
            self.assertEqual(result.diesel_csv_path, runtime_diesel.resolve())
            self.assertEqual(result.bunker_price_brl_mt, 3250.0)
            self.assertEqual(result.warnings, ())

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
