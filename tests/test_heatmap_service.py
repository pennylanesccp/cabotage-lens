import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.heatmap.service import (
    HeatmapDataError,
    get_heatmap_status,
    list_origin_options,
    load_current_dataset,
    pending_destinations,
    run_heatmap,
)
from app.heatmap.types import HeatmapScenario


class HeatmapServiceTests(unittest.TestCase):
    def _scenario(self) -> HeatmapScenario:
        return HeatmapScenario(
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            truck_key="semi_27t",
            ors_profile="driving-hgv",
            vessel_class="container_small",
            include_hoteling=True,
            hoteling_hours_per_call=14.0,
            port_calls=2,
            include_port_ops=True,
            port_moves_per_call=None,
            cargo_teu=None,
            t_per_teu_default=14.0,
            allocation_mode=None,
            allocation_load_factor=0.8,
            full_call_mode=False,
            port_ops_scenario="baseline",
        )

    def test_list_origin_options_normalizes_and_dedupes_labels(self) -> None:
        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.list_bulk_run_origins",
            return_value=["S\u00e3o Paulo, SP", "Sao Paulo, SP", "Curitiba, PR", "   "],
        ):
            origins = list_origin_options()

        self.assertEqual(origins, ["Sao Paulo, SP", "Curitiba, PR"])

    def test_get_heatmap_status_uses_comparison_table_counts(self) -> None:
        scenario = self._scenario()
        summary = SimpleNamespace(
            row_count=400,
            success_count=380,
            fail_count=20,
            latest_updated_timestamp="2026-03-11 09:30:00",
            latest_run_id="run-123",
        )
        latest_completed = SimpleNamespace(
            run_id="run-122",
            duration_s=42.0,
            completed_timestamp="2026-03-10 18:00:00",
            updated_timestamp="2026-03-10 18:00:00",
        )

        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=tuple(f"City {idx}" for idx in range(608)),
        ), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.summarize_bulk_results",
            return_value=summary,
        ), patch(
            "app.heatmap.service.get_latest_completed_run",
            return_value=latest_completed,
        ):
            status = get_heatmap_status(scenario)

        self.assertEqual(status.run_id, "run-123")
        self.assertEqual(status.found_count, 400)
        self.assertEqual(status.success_count, 380)
        self.assertEqual(status.fail_count, 20)
        self.assertEqual(status.missing_count, 208)
        self.assertEqual(status.updated_timestamp, "2026-03-11 09:30:00")
        self.assertEqual(status.completed_timestamp, "2026-03-10 18:00:00")

    def test_load_current_dataset_builds_map_points_from_comparison_rows(self) -> None:
        scenario = self._scenario()
        status = SimpleNamespace(
            run_id="run-123",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=608,
            found_count=2,
            success_count=2,
            fail_count=0,
            missing_count=606,
            duration_s=42.0,
            completed_timestamp="2026-03-10 12:00:00",
            updated_timestamp="2026-03-10 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        rows = [
            SimpleNamespace(
                destiny_name="Manaus, AM",
                destiny_lat=-3.1190,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                port_destiny_name="Manaus",
                road_fuel_cost_r=15000.0,
                total_fuel_cost_r=11000.0,
                delta_cost_r=4000.0,
                savings_pct=26.6667,
                road_co2e_kg=9000.0,
                total_co2e_kg=5200.0,
                delta_co2e_kg=3800.0,
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
                road_fuel_cost_r=9000.0,
                total_fuel_cost_r=9500.0,
                delta_cost_r=-500.0,
                savings_pct=-5.5556,
                road_co2e_kg=5100.0,
                total_co2e_kg=4700.0,
                delta_co2e_kg=400.0,
                emissions_savings_pct=7.8431,
                road_distance_km=2700.0,
                sea_km=2100.0,
                updated_timestamp="2026-03-10 12:00:00",
            ),
        ]

        with patch("app.heatmap.service.get_heatmap_status", return_value=status), patch(
            "app.heatmap.service._require_postgres"
        ), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.list_bulk_results",
            return_value=rows,
        ):
            dataset = load_current_dataset(scenario)

        self.assertIsNotNone(dataset)
        assert dataset is not None
        self.assertEqual(dataset.scenario, scenario)
        self.assertEqual(dataset.run.run_id, "run-123")
        self.assertEqual(len(dataset.points), 2)
        self.assertAlmostEqual(dataset.max_abs_cost_delta, 4000.0)
        self.assertAlmostEqual(dataset.max_abs_emissions_delta, 3800.0)

    def test_load_current_dataset_raises_when_rows_cannot_be_mapped(self) -> None:
        scenario = self._scenario()
        status = SimpleNamespace(
            run_id="run-456",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=608,
            found_count=1,
            success_count=1,
            fail_count=0,
            missing_count=607,
            duration_s=10.0,
            completed_timestamp="2026-03-10 12:00:00",
            updated_timestamp="2026-03-10 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        rows = [
            SimpleNamespace(
                destiny_name="Manaus, AM",
                destiny_lat=None,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                port_destiny_name="Manaus",
                road_fuel_cost_r=15000.0,
                total_fuel_cost_r=11000.0,
                delta_cost_r=4000.0,
                savings_pct=26.6667,
                road_co2e_kg=9000.0,
                total_co2e_kg=5200.0,
                delta_co2e_kg=3800.0,
                emissions_savings_pct=42.2222,
                road_distance_km=3900.0,
                sea_km=3400.0,
                updated_timestamp="2026-03-10 12:00:00",
            ),
        ]

        with patch("app.heatmap.service.get_heatmap_status", return_value=status), patch(
            "app.heatmap.service._require_postgres"
        ), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.list_bulk_results",
            return_value=rows,
        ):
            with self.assertRaises(HeatmapDataError):
                load_current_dataset(scenario)

    def test_pending_destinations_skips_existing_comparison_rows(self) -> None:
        scenario = self._scenario()
        rows = [
            SimpleNamespace(input_destiny="Manaus, AM"),
            SimpleNamespace(input_destiny="Belem, PA"),
        ]

        with patch("app.heatmap.service.db_session", return_value=contextlib.nullcontext(object())), patch(
            "app.heatmap.service.list_bulk_results",
            return_value=rows,
        ), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA", "Rio Branco, AC"),
        ):
            pending = pending_destinations(scenario)

        self.assertEqual(pending, ["Rio Branco, AC"])

    def test_run_heatmap_missing_only_processes_only_unfound_destinations(self) -> None:
        scenario = self._scenario()
        dataset = SimpleNamespace(points=[1, 2, 3])

        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA", "Rio Branco, AC"),
        ), patch(
            "app.heatmap.service.pending_destinations",
            return_value=["Rio Branco, AC"],
        ), patch(
            "app.heatmap.service.run_bulk_evaluation",
        ) as run_bulk_mock, patch(
            "app.heatmap.service.load_current_dataset",
            return_value=dataset,
        ):
            result = run_heatmap(scenario, rerun=False)

        self.assertIs(result, dataset)
        run_bulk_mock.assert_called_once()
        self.assertEqual(run_bulk_mock.call_args.kwargs["dest_list"], ["Rio Branco, AC"])
        self.assertFalse(run_bulk_mock.call_args.kwargs["overwrite_road"])


if __name__ == "__main__":
    unittest.main()
