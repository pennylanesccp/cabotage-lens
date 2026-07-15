import contextlib
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import app.heatmap.service as heatmap_service
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
    def setUp(self) -> None:
        heatmap_service._canonical_origin_name.cache_clear()

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

    def test_selected_coverage_audit_reports_expected_and_missing_by_uf(self) -> None:
        plotted, rows, missing = heatmap_service._selected_coverage_audit(
            ["Manaus, AM", "Tefe, AM", "Belem, PA"],
            {
                heatmap_service._destination_identity("Manaus, Amazonas"),
                heatmap_service._destination_identity("Belem, Para"),
            },
        )

        self.assertEqual(plotted, 2)
        self.assertEqual(
            rows,
            [
                {"uf": "AM", "expected": 2, "plotted": 1, "not_plotted": 1},
                {"uf": "PA", "expected": 1, "plotted": 1, "not_plotted": 0},
            ],
        )
        self.assertEqual(missing, ["Tefe, AM"])

    def test_destination_identity_matches_uf_and_full_state_aliases(self) -> None:
        self.assertEqual(
            heatmap_service._destination_identity("Acrelandia, AC"),
            heatmap_service._destination_identity("Acrelandia, Acre"),
        )
        self.assertEqual(heatmap_service._destination_uf("Manaus, Amazonas"), "AM")

    def test_pending_destinations_refreshes_exact_success_without_route_reference(self) -> None:
        records = [
            SimpleNamespace(
                input_destiny="Belo Horizonte, MG",
                status="ok",
                is_approximation=False,
                road_distance_km=585.0,
                route_source="cache_exact",
                road_route_id=None,
            ),
            SimpleNamespace(
                input_destiny="Manaus, AM",
                status="ok",
                is_approximation=False,
                road_distance_km=3900.0,
                route_source="cache_exact",
                road_route_id=123,
            ),
        ]

        with patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Belo Horizonte, MG", "Manaus, AM"),
        ):
            pending = heatmap_service._pending_destination_list(
                records,
                destination_set_id="city_dests_over50k.txt",
            )

        self.assertEqual(pending, ["Belo Horizonte, MG"])
        self.assertEqual(heatmap_service._profile_route_refresh_count(records), 1)

    def test_cached_route_candidates_accept_selected_alias_location_id(self) -> None:
        route = {
            "destiny": "Balneario Camboriu, SC",
            "destiny_location_id": 42,
        }
        with patch(
            "app.heatmap.service._origin_name_variants",
            return_value=("Pelotas, RS",),
        ), patch(
            "app.heatmap.service.list_runs",
            return_value=[route],
        ), patch(
            "app.heatmap.service._all_heatmap_destination_keys",
            return_value=frozenset({heatmap_service._destination_identity("Camboriu, SC")}),
        ), patch(
            "app.heatmap.service._all_heatmap_destinations",
            return_value=("Camboriu, SC",),
        ), patch(
            "app.heatmap.service.list_cached_place_points",
            return_value={
                "camboriu, sc": {
                    "location_id": 42,
                    "label": "Balneario Camboriu, SC",
                }
            },
        ):
            rows = heatmap_service._load_cached_route_rows_for_surface(object(), self._scenario())

        self.assertEqual(rows, [route])

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

    def test_get_heatmap_status_queries_selector_with_origin_location_id(self) -> None:
        scenario = self._scenario()
        summary = SimpleNamespace(
            row_count=400,
            success_count=380,
            fail_count=20,
            latest_updated_timestamp="2026-03-11 09:30:00",
            latest_run_id="run-123",
            profile_route_refresh_count=0,
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
            "app.heatmap.service._origin_location_id",
            return_value=17,
        ), patch(
            "app.heatmap.service.summarize_bulk_results",
            return_value=summary,
        ) as summarize_mock, patch(
            "app.heatmap.service.get_latest_completed_run",
            return_value=latest_completed,
        ):
            status = get_heatmap_status(scenario)

        self.assertEqual(status.run_id, "run-123")
        self.assertEqual(status.found_count, 400)
        self.assertEqual(status.success_count, 380)
        self.assertEqual(status.fail_count, 20)
        self.assertEqual(status.missing_count, 208)
        self.assertEqual(status.pending_count, 228)
        self.assertEqual(summarize_mock.call_args.kwargs["selector"].origin_location_id, 17)

    def test_load_current_dataset_builds_map_points_from_normalized_rows(self) -> None:
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
            pending_count=606,
            duration_s=42.0,
            completed_timestamp="2026-03-10 12:00:00",
            updated_timestamp="2026-03-10 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        rows = [
            SimpleNamespace(
                source_kind="bulk",
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
                source_kind="bulk",
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

        with patch("app.heatmap.service.get_heatmap_status", return_value=status), patch(
            "app.heatmap.service._require_postgres"
        ), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA"),
        ), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.list_bulk_run_results",
            return_value=[],
        ), patch(
            "app.heatmap.service._load_map_rows",
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
        self.assertEqual(dataset.diagnostics.successful_rows, 2)
        self.assertEqual(dataset.diagnostics.plottable_points, 2)
        self.assertEqual(dataset.diagnostics.loaded_bulk_rows, 2)
        self.assertEqual(dataset.diagnostics.loaded_single_compare_rows, 0)
        self.assertEqual(dataset.diagnostics.skipped_total, 0)
        self.assertEqual(dataset.diagnostics.failed_destinations, [])

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
            pending_count=607,
            duration_s=10.0,
            completed_timestamp="2026-03-10 12:00:00",
            updated_timestamp="2026-03-10 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        rows = [
            SimpleNamespace(
                source_kind="bulk",
                destiny_name="Manaus, AM",
                destiny_lat=None,
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
        ]

        with patch("app.heatmap.service.get_heatmap_status", return_value=status), patch(
            "app.heatmap.service._require_postgres"
        ), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM",),
        ), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service.list_bulk_run_results",
            return_value=[],
        ), patch(
            "app.heatmap.service._load_map_rows",
            return_value=rows,
        ):
            with self.assertRaises(HeatmapDataError):
                load_current_dataset(scenario)

    def test_load_current_dataset_tracks_skipped_rows_in_diagnostics(self) -> None:
        scenario = self._scenario()
        status = SimpleNamespace(
            run_id="run-789",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=608,
            found_count=3,
            success_count=3,
            fail_count=0,
            missing_count=605,
            pending_count=605,
            duration_s=10.0,
            completed_timestamp="2026-03-10 12:00:00",
            updated_timestamp="2026-03-10 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        rows = [
            SimpleNamespace(
                source_kind="bulk",
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
                source_kind="bulk",
                destiny_name="Belem, PA",
                destiny_lat=None,
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
            SimpleNamespace(
                source_kind="bulk",
                destiny_name="Sao Luis, MA",
                destiny_lat=-2.5387,
                destiny_lon=-44.2825,
                destiny_uf="MA",
                port_destiny_name="Sao Luis",
                road_cost_r=None,
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

        with patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA", "Sao Luis, MA"),
        ), patch("app.heatmap.service.db_session", return_value=contextlib.nullcontext(object())), patch(
            "app.heatmap.service.list_bulk_run_results",
            return_value=[],
        ), patch(
            "app.heatmap.service._load_map_rows",
            return_value=rows,
        ):
            dataset = load_current_dataset(scenario, status=status)

        self.assertEqual(dataset.diagnostics.successful_rows, 3)
        self.assertEqual(dataset.diagnostics.plottable_points, 1)
        self.assertEqual(dataset.diagnostics.skipped_missing_coordinates, 1)
        self.assertEqual(dataset.diagnostics.skipped_missing_costs, 1)
        self.assertEqual(dataset.diagnostics.skipped_missing_emissions, 0)
        self.assertEqual(dataset.diagnostics.loaded_bulk_rows, 3)
        self.assertEqual(dataset.diagnostics.loaded_single_compare_rows, 0)

    def test_load_map_rows_does_not_mix_legacy_single_compare_results(self) -> None:
        bulk_row = heatmap_service._LoadedHeatmapRow(
            source_kind="bulk",
            source_detail="city_dests_over50k.txt",
            input_destiny="Rio Branco, AC",
            destiny_name="Rio Branco, AC",
            destiny_lat=-9.97499,
            destiny_lon=-67.8243,
            destiny_uf="AC",
            port_destiny_name="Manaus",
            road_cost_r=12000.0,
            multimodal_cost_r=9500.0,
            cost_delta_r=2500.0,
            cost_savings_pct=20.8333,
            road_emissions_kg=6400.0,
            multimodal_emissions_kg=4100.0,
            emissions_delta_kg=2300.0,
            emissions_savings_pct=35.9375,
            road_distance_km=3600.0,
            sea_km=2900.0,
            updated_timestamp="2026-03-24 08:00:00",
        )

        with patch(
            "app.heatmap.service._load_bulk_rows_for_map",
            return_value=[bulk_row],
        ), patch(
            "app.heatmap.service._load_single_compare_rows_for_map",
        ) as legacy_loader:
            rows = heatmap_service._load_map_rows(
                object(),
                self._scenario(),
                "city_dests_over50k.txt",
            )

        self.assertEqual(rows, [bulk_row])
        legacy_loader.assert_not_called()

    def test_list_failed_destinations_returns_selected_run_diagnostics(self) -> None:
        scenario = self._scenario()
        failure_rows = [
            SimpleNamespace(
                status="timeout",
                destiny_name="Manaus, AM",
                input_destiny="Manaus, AM",
                failed_leg="road_only",
                failed_step="routing_road_only",
                failure_reason="provider_timeout",
                failure_detail="Request timed out",
                port_origin_name="Rio Grande",
                port_destiny_name="Manaus",
                retryable=True,
                failure_provider="ors",
                failure_provider_operation="route_road",
            ),
            SimpleNamespace(status="ok", destiny_name="Belem, PA", input_destiny="Belem, PA"),
        ]

        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.heatmap.service._select_active_selector",
            return_value=(object(), SimpleNamespace(latest_run_id="run-123"), None),
        ), patch(
            "app.heatmap.service.list_bulk_run_results",
            return_value=failure_rows,
        ):
            failures = heatmap_service.list_failed_destinations(scenario)

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].destination, "Manaus, AM")
        self.assertEqual(failures[0].failed_leg, "road_only")
        self.assertEqual(failures[0].failed_step, "routing_road_only")
        self.assertEqual(failures[0].failure_reason, "provider_timeout")
        self.assertTrue(failures[0].retryable)

    def test_pending_destinations_retries_failed_and_absent_destinations(self) -> None:
        scenario = self._scenario()
        with patch("app.heatmap.service.db_session", return_value=contextlib.nullcontext(object())), patch(
            "app.heatmap.service._origin_location_id",
            return_value=17,
        ), patch(
            "app.heatmap.service.list_bulk_results",
            return_value=[
                SimpleNamespace(input_destiny="Manaus, AM", status="ok"),
                SimpleNamespace(input_destiny="Belem, PA", status="geocode_failed"),
                SimpleNamespace(input_destiny="Rio Branco, AC", status="timeout"),
            ],
        ), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA", "Rio Branco, AC", "Fortaleza, CE"),
        ):
            pending = pending_destinations(scenario)

        self.assertEqual(pending, ["Belem, PA", "Rio Branco, AC", "Fortaleza, CE"])

    def test_run_heatmap_missing_only_processes_pending_destinations(self) -> None:
        scenario = self._scenario()
        dataset = SimpleNamespace(points=[1, 2, 3])

        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service.refresh_fuel_prices",
            return_value=SimpleNamespace(
                diesel_csv_path="runtime-diesel.csv",
                bunker_price_brl_mt=3210.0,
                prices_changed=False,
            ),
        ), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA", "Rio Branco, AC"),
        ), patch(
            "app.heatmap.service.pending_destinations",
            return_value=["Belem, PA", "Rio Branco, AC"],
        ), patch(
            "app.heatmap.service.run_bulk_evaluation",
        ) as run_bulk_mock, patch(
            "app.heatmap.service.load_current_dataset",
            return_value=dataset,
        ):
            result = run_heatmap(scenario, rerun=False)

        self.assertIs(result, dataset)
        run_bulk_mock.assert_called_once()
        self.assertEqual(run_bulk_mock.call_args.kwargs["dest_list"], ["Belem, PA", "Rio Branco, AC"])
        self.assertFalse(run_bulk_mock.call_args.kwargs["overwrite_road"])
        self.assertEqual(run_bulk_mock.call_args.kwargs["max_geocode_workers"], 1)
        self.assertEqual(run_bulk_mock.call_args.kwargs["max_route_workers"], 2)
        self.assertEqual(run_bulk_mock.call_args.kwargs["diesel_csv_path"], "runtime-diesel.csv")
        self.assertEqual(run_bulk_mock.call_args.kwargs["bunker_price_override_brl_mt"], 3210.0)

    def test_run_heatmap_recalculates_all_destinations_when_fuel_prices_change(self) -> None:
        scenario = replace(self._scenario(), include_port_ops=False)
        dataset = SimpleNamespace(points=[1, 2, 3])

        with patch("app.heatmap.service._require_postgres"), patch(
            "app.heatmap.service.refresh_fuel_prices",
            return_value=SimpleNamespace(
                diesel_csv_path="runtime-diesel.csv",
                bunker_price_brl_mt=3300.0,
                prices_changed=True,
            ),
        ), patch(
            "app.heatmap.service._heatmap_destinations",
            return_value=("Manaus, AM", "Belem, PA", "Rio Branco, AC"),
        ), patch(
            "app.heatmap.service.pending_destinations",
        ) as pending_mock, patch(
            "app.heatmap.service.run_bulk_evaluation",
        ) as run_bulk_mock, patch(
            "app.heatmap.service.load_current_dataset",
            return_value=dataset,
        ):
            result = run_heatmap(scenario, rerun=False)

        self.assertIs(result, dataset)
        pending_mock.assert_not_called()
        self.assertEqual(
            run_bulk_mock.call_args.kwargs["dest_list"],
            ["Manaus, AM", "Belem, PA", "Rio Branco, AC"],
        )
        self.assertTrue(run_bulk_mock.call_args.kwargs["include_port_ops"])


if __name__ == "__main__":
    unittest.main()
