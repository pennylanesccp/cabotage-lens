import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.heatmap.service import load_latest_dataset
from app.heatmap.types import HeatmapScenario


class HeatmapServiceTests(unittest.TestCase):
    def test_load_latest_dataset_builds_map_points(self) -> None:
        run_record = SimpleNamespace(
            run_id="run-123",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=2,
            success_count=2,
            fail_count=0,
            duration_s=42.0,
            completed_timestamp="2026-03-10 12:00:00",
            updated_timestamp="2026-03-10 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        result_rows = [
            SimpleNamespace(
                destiny_name="Manaus, AM",
                destiny_lat=-3.1190,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                port_destiny_name="Manaus",
                road_cost_r=15000.0,
                multimodal_cost_r=11000.0,
                cost_delta_r=4000.0,
                cost_savings_pct=26.6667,
                road_emissions_kg=9000.0,
                multimodal_emissions_kg=5200.0,
                emissions_delta_kg=3800.0,
                emissions_savings_pct=42.2222,
                road_distance_km=3900.0,
                sea_km=3400.0,
                updated_timestamp="2026-03-10 12:00:00",
            ),
            SimpleNamespace(
                destiny_name="Belem, PA",
                destiny_lat=-1.4558,
                destiny_lon=-48.4902,
                destiny_uf="PA",
                port_destiny_name="Belem",
                road_cost_r=9000.0,
                multimodal_cost_r=9500.0,
                cost_delta_r=-500.0,
                cost_savings_pct=-5.5556,
                road_emissions_kg=5100.0,
                multimodal_emissions_kg=4700.0,
                emissions_delta_kg=400.0,
                emissions_savings_pct=7.8431,
                road_distance_km=2700.0,
                sea_km=2100.0,
                updated_timestamp="2026-03-10 12:00:00",
            ),
        ]

        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.get_latest_completed_run",
            return_value=run_record,
        ), patch(
            "app.heatmap.service.list_bulk_run_results",
            return_value=result_rows,
        ):
            dataset = load_latest_dataset(HeatmapScenario(origin_name="Pelotas, RS", cargo_t=30.0))

        self.assertIsNotNone(dataset)
        assert dataset is not None
        self.assertEqual(dataset.run.run_id, "run-123")
        self.assertEqual(len(dataset.points), 2)
        self.assertAlmostEqual(dataset.max_abs_cost_delta, 4000.0)
        self.assertAlmostEqual(dataset.max_abs_emissions_delta, 3800.0)


if __name__ == "__main__":
    unittest.main()
