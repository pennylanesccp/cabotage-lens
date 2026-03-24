import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from modules.multimodal import bulk
from modules.multimodal import bulk_pipeline
from modules.multimodal.bulk import BulkPerformanceTracker, RouteRequestCoordinator, RouteRequestSpec


class BulkPipelineCoordinatorTests(unittest.TestCase):
    def test_bounded_concurrency_deduplicates_inflight_route_requests(self) -> None:
        call_count = 0

        def fake_calculate_route(_ors, _origin, _destiny, _profile, _fallback):
            nonlocal call_count
            call_count += 1
            return "driving-hgv", 123.0, "fake"

        coordinator = RouteRequestCoordinator(
            object(),
            profile="driving-hgv",
            overwrite=False,
            perf=BulkPerformanceTracker(),
        )
        spec = RouteRequestSpec(
            leg_name="road_direct",
            origin={"label": "Origin", "lat": -31.0, "lon": -52.0},
            destiny={"label": "Destiny", "lat": -3.0, "lon": -60.0},
            profile="driving-hgv",
        )

        with patch("modules.multimodal.bulk._calculate_route", side_effect=fake_calculate_route):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(coordinator.resolve, spec) for _ in range(2)]
                results = [future.result() for future in futures]

        self.assertEqual(call_count, 1)
        self.assertTrue(all(result["distance_km"] == 123.0 for result in results))

    def test_route_cache_prime_reuses_cached_leg_without_provider_call(self) -> None:
        spec = RouteRequestSpec(
            leg_name="road_direct",
            origin={"label": "Origin", "lat": -31.0, "lon": -52.0},
            destiny={"label": "Destiny", "lat": -3.0, "lon": -60.0},
            profile="driving-hgv",
        )
        coordinator = RouteRequestCoordinator(
            object(),
            profile="driving-hgv",
            overwrite=False,
            perf=BulkPerformanceTracker(),
        )

        cached_row = {
            spec.label_key: {
                "origin": "Origin",
                "destiny": "Destiny",
                "distance_km": 456.0,
                "is_hgv": True,
                "origin_lat": -31.0,
                "origin_lon": -52.0,
                "destiny_lat": -3.0,
                "destiny_lon": -60.0,
                "profile_requested": "driving-hgv",
                "profile_used": "driving-hgv",
                "source": "ors",
            }
        }

        with patch(
            "modules.multimodal.bulk.list_runs_by_label_keys",
            return_value=cached_row,
        ), patch(
            "modules.multimodal.bulk.list_runs_by_coord_keys",
            return_value={},
        ):
            coordinator.prime(object(), [spec])

        with patch("modules.multimodal.bulk._calculate_route") as calculate_route_mock:
            leg = coordinator.resolve(spec)

        self.assertTrue(leg["cached"])
        self.assertEqual(leg["source"], "cache")
        self.assertEqual(leg["distance_km"], 456.0)
        calculate_route_mock.assert_not_called()

    def test_route_cache_prime_reuses_coord_cached_leg_with_six_decimal_keys(self) -> None:
        spec = RouteRequestSpec(
            leg_name="road_direct",
            origin={"label": "Origin", "lat": -31.0000004, "lon": -52.0000004},
            destiny={"label": "Destiny", "lat": -3.0000004, "lon": -60.0000004},
            profile="driving-hgv",
        )
        coordinator = RouteRequestCoordinator(
            object(),
            profile="driving-hgv",
            overwrite=False,
            perf=BulkPerformanceTracker(),
        )
        origin_key = bulk.coord_lookup_key(spec.origin["lat"], spec.origin["lon"])
        destiny_key = bulk.coord_lookup_key(spec.destiny["lat"], spec.destiny["lon"])
        self.assertIsNotNone(origin_key)
        self.assertIsNotNone(destiny_key)
        assert origin_key is not None
        assert destiny_key is not None
        cached_row = {
            ("driving-hgv", f"{origin_key[0]},{origin_key[1]}", f"{destiny_key[0]},{destiny_key[1]}"): {
                "origin": "Origin",
                "destiny": "Destiny",
                "distance_km": 654.0,
                "is_hgv": True,
                "origin_lat": -31.0,
                "origin_lon": -52.0,
                "destiny_lat": -3.0,
                "destiny_lon": -60.0,
                "profile_requested": "driving-hgv",
                "profile_used": "driving-hgv",
                "source": "ors",
            }
        }

        with patch(
            "modules.multimodal.bulk.list_runs_by_label_keys",
            return_value={},
        ), patch(
            "modules.multimodal.bulk.list_runs_by_coord_keys",
            return_value=cached_row,
        ):
            coordinator.prime(object(), [spec])

        with patch("modules.multimodal.bulk._calculate_route") as calculate_route_mock:
            leg = coordinator.resolve(spec)

        self.assertTrue(leg["cached"])
        self.assertEqual(leg["distance_km"], 654.0)
        calculate_route_mock.assert_not_called()


class BulkPipelineExecutionTests(unittest.TestCase):
    def test_point_from_result_record_reuses_coordinates_from_latest_bulk_rows(self) -> None:
        record = SimpleNamespace(
            destiny_name="Manaus, AM",
            input_destiny="Manaus, AM",
            destiny_lat=-3.1190,
            destiny_lon=-60.0217,
            destiny_uf="AM",
            destination_location_id=42,
        )

        point = bulk._point_from_result_record(record)

        assert point is not None
        self.assertEqual(point["label"], "Manaus, AM")
        self.assertEqual(point["uf"], "AM")
        self.assertEqual(point["location_id"], 42)
        self.assertAlmostEqual(point["lat"], -3.1190)
        self.assertAlmostEqual(point["lon"], -60.0217)

    def test_apply_destination_point_reuse_uses_historical_bulk_points_before_geocoding(self) -> None:
        perf = BulkPerformanceTracker()
        work_item = bulk.DestinationWorkItem(
            index=1,
            destiny_input="Manaus, AM",
            normalized_input="Manaus, AM",
            scenario_key="scenario-1",
            scenario_payload={"input_destiny": "Manaus, AM"},
            destiny_name="Manaus, AM",
        )
        point_rows_to_persist: list[dict[str, object]] = []

        bulk_pipeline._apply_destination_point_reuse(
            [work_item],
            cached_points={},
            latest_result_points={},
            historical_result_points={
                "manaus, am": {
                    "label": "Manaus, AM",
                    "lat": -3.1190,
                    "lon": -60.0217,
                    "uf": "AM",
                    "location_id": 42,
                }
            },
            perf=perf,
            point_rows_to_persist=point_rows_to_persist,
        )

        self.assertIsNotNone(work_item.point)
        assert work_item.point is not None
        self.assertEqual(work_item.point["label"], "Manaus, AM")
        self.assertEqual(work_item.point_source, "bulk_result_history")
        self.assertEqual(perf.counters["destination_cache_hits"], 1.0)
        self.assertEqual(perf.counters["destination_history_hits"], 1.0)
        self.assertNotIn("destination_cache_misses", perf.counters)
        self.assertEqual(point_rows_to_persist[0]["source"], "bulk_result_history")

    def test_run_bulk_evaluation_delegates_to_pipeline(self) -> None:
        expected = {"success_count": 1}

        with patch(
            "modules.multimodal.bulk_pipeline.run_bulk_evaluation_pipeline",
            return_value=expected,
        ) as pipeline_mock:
            outcome = bulk.run_bulk_evaluation(
                origin="Pelotas, RS",
                dest_list=["Manaus, AM"],
                cargo_t=30.0,
                truck_key="semi_27t",
                profile="driving-hgv",
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
                destination_set_id="city_dests_over50k.txt",
            )

        self.assertIs(outcome, expected)
        pipeline_mock.assert_called_once()

    def test_log_destination_failure_context_includes_route_details(self) -> None:
        item = bulk.DestinationWorkItem(
            index=1,
            destiny_input="Manaus, AM",
            normalized_input="Manaus, AM",
            scenario_key="scenario-1",
            scenario_payload={"input_destiny": "Manaus, AM"},
            destiny_name="Manaus, AM",
            point={"label": "Manaus, AM", "lat": -3.1190, "lon": -60.0217},
            point_source="location_alias_cache",
            port_destiny={"name": "Porto de Manaus"},
            failure_step="routing_road_only",
            failure_system="routing",
            failure_provider="ors",
        )
        geo = {
            "road_direct": {
                "source": "cache",
                "distance_km": 3950.4,
                "profile_used": "driving-hgv",
                "cached": True,
            },
            "last_mile": {
                "source": "ors",
                "distance_km": 12.6,
                "profile_used": "driving-hgv",
                "cached": False,
            },
        }

        with self.assertLogs("modules.multimodal.bulk_pipeline", level="WARNING") as captured:
            bulk_pipeline._log_destination_failure_context(
                phase="geometry",
                origin_pt={"label": "Sao Paulo, SP", "lat": -23.5505, "lon": -46.6333},
                origin_port={"name": "Porto de Santos"},
                item=item,
                status="timeout",
                error_message="Request timed out",
                geo=geo,
            )

        joined = "\n".join(captured.output)
        self.assertIn("Sao Paulo, SP@", joined)
        self.assertIn("Manaus, AM@", joined)
        self.assertIn("step=routing_road_only", joined)
        self.assertIn("system=routing", joined)
        self.assertIn("provider=ors", joined)
        self.assertIn("ports=Porto de Santos -> Porto de Manaus", joined)
        self.assertIn("road_direct[source=cache km=3950.4 profile=driving-hgv cached=true]", joined)
        self.assertIn("last_mile[source=ors km=12.6 profile=driving-hgv cached=false]", joined)
        self.assertIn("status=timeout", joined)
        self.assertIn("error=Request timed out", joined)

    def test_format_failed_destinies_includes_actual_destination_names(self) -> None:
        rows = [
            {
                "status": "timeout",
                "failure_step": "routing_road_only",
                "destiny_name": "Manaus, AM",
                "input_destiny": "Manaus, AM",
            },
            {
                "status": "timeout",
                "failure_step": "routing_road_only",
                "destiny_name": "Recife, PE",
                "input_destiny": "Recife, PE",
            },
            {
                "status": "rate_limited",
                "failure_step": "destination_geocoding",
                "destiny_name": "",
                "input_destiny": "Olinda, PE",
            },
            {"status": "ok", "destiny_name": "Curitiba, PR", "input_destiny": "Curitiba, PR"},
        ]

        summary = bulk_pipeline._format_failed_destinies(rows, max_statuses=5, max_destinies_per_status=5)

        self.assertIn("routing road only/timeout=[Manaus, AM; Recife, PE]", summary)
        self.assertIn("destination geocoding/rate_limited=[Olinda, PE]", summary)
        self.assertNotIn("Curitiba, PR", summary)

    def test_bulk_persistence_buffer_reconnects_before_flush(self) -> None:
        conn = SimpleNamespace(
            ping=unittest.mock.MagicMock(side_effect=RuntimeError("connection lost")),
            reconnect=unittest.mock.MagicMock(),
            commit=unittest.mock.MagicMock(),
        )
        persistence = bulk.BulkPersistenceBuffer(
            conn,
            results_table="bulk_results",
            run_results_table="bulk_run_results",
            batch_size=2,
            perf=BulkPerformanceTracker(),
        )
        bulk_row = {"scenario_key": "scenario-a"}
        run_row = {"run_id": "run-a"}

        persistence.add(bulk_row, run_row)

        with patch("modules.multimodal.bulk.upsert_bulk_results") as upsert_mock, patch(
            "modules.multimodal.bulk.insert_bulk_run_results"
        ) as insert_mock:
            persistence.flush()

        conn.ping.assert_called_once_with()
        conn.reconnect.assert_called_once_with()
        upsert_mock.assert_called_once()
        insert_mock.assert_called_once()
        conn.commit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
