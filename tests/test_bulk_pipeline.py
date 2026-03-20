import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from modules.multimodal import bulk
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


if __name__ == "__main__":
    unittest.main()
