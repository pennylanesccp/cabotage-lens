import contextlib
import copy
import unittest
from unittest.mock import MagicMock, patch

from modules.multimodal import bulk


class BulkApproximationTests(unittest.TestCase):
    def _point(self, label: str, lat: float, lon: float, uf: str = "SP") -> dict:
        return {"label": label, "lat": lat, "lon": lon, "uf": uf}

    def _geo(self, origin_point: dict, destiny_point: dict, *, road_distance_km, last_mile_km: float = 45.0) -> dict:
        return {
            "origin": copy.deepcopy(origin_point),
            "destiny": copy.deepcopy(destiny_point),
            "port_origin": {"name": "Porto Origem"},
            "port_destiny": {"name": "Porto Destino"},
            "road_direct": {
                "distance_km": road_distance_km,
                "source": "api",
                "profile_requested": "driving-hgv",
                "profile_used": "driving-hgv",
                "cached": False,
            },
            "first_mile": {
                "distance_km": 12.0,
                "source": "cache",
                "profile_requested": "driving-hgv",
                "profile_used": "driving-hgv",
                "cached": True,
            },
            "last_mile": {
                "distance_km": last_mile_km,
                "source": "api",
                "profile_requested": "driving-hgv",
                "profile_used": "driving-hgv",
                "cached": False,
            },
            "sea_leg": {"distance_km": 1000.0, "source": "sea_matrix"},
            "status": "ok",
        }

    def _fake_evaluate_and_flatten(self, geo: dict, *, origin_name: str, destiny_name: str, evaluation_kwargs: dict):
        road_distance_km = float(geo["road_direct"]["distance_km"] or 0.0)
        res = {
            "comparison": {"savings_pct": 12.5},
            "inputs": {
                "diesel_price_source": "unit_test",
                "port_ops_scenario_resolved": evaluation_kwargs["port_ops_scenario"],
                "allocation_mode_used": evaluation_kwargs.get("allocation_mode") or "auto",
            },
        }
        flat = {
            "road_distance_km": road_distance_km,
            "road_fuel_liters": road_distance_km / 2.0,
            "road_fuel_kg": road_distance_km / 2.0,
            "road_fuel_cost_r": road_distance_km * 3.0,
            "road_co2e_kg": road_distance_km * 4.0,
            "mm_road_fuel_liters": 10.0,
            "mm_road_fuel_kg": 10.0,
            "mm_road_fuel_cost_r": 10.0,
            "mm_road_co2e_kg": 10.0,
            "sea_km": 1000.0,
            "sea_fuel_kg": 20.0,
            "sea_fuel_cost_r": 30.0,
            "sea_co2e_kg": 40.0,
            "total_fuel_kg": 50.0,
            "total_fuel_cost_r": road_distance_km * 2.0,
            "total_co2e_kg": road_distance_km * 1.5,
            "delta_cost_r": road_distance_km,
            "delta_co2e_kg": road_distance_km * 0.5,
        }
        return res, flat

    def _run_bulk(self, *, destinations: list[str], points_by_input: dict[str, dict], geos_by_label: dict[str, dict]):
        persisted: list[dict] = []

        def fake_resolve_point(value, _ors, **_kwargs):
            return copy.deepcopy(points_by_input.get(str(value)))

        def fake_build_geometry(origin_pt, destiny_pt, **_kwargs):
            return copy.deepcopy(geos_by_label[destiny_pt["label"]])

        get_leg_mock = MagicMock(
            return_value={
                "distance_km": 12.0,
                "source": "cache",
                "profile_requested": "driving-hgv",
                "profile_used": "driving-hgv",
                "cached": True,
            }
        )
        build_geometry_mock = MagicMock(side_effect=fake_build_geometry)
        finish_run_mock = MagicMock()

        with patch("modules.multimodal.bulk.load_routing_assets", return_value=("ors", [], "sea", ":memory:")), patch(
            "modules.multimodal.bulk.resolve_point_for_geometry",
            side_effect=fake_resolve_point,
        ), patch("modules.multimodal.bulk.find_nearest_port", return_value={"name": "Porto Teste", "lat": 1.0, "lon": 1.0}), patch(
            "modules.multimodal.bulk.get_or_create_leg",
            get_leg_mock,
        ), patch(
            "modules.multimodal.bulk.build_path_geometry_from_resolved",
            build_geometry_mock,
        ), patch(
            "modules.multimodal.bulk._evaluate_and_flatten",
            side_effect=self._fake_evaluate_and_flatten,
        ), patch(
            "modules.multimodal.bulk.db_session",
            side_effect=lambda *args, **kwargs: contextlib.nullcontext(object()),
        ), patch(
            "modules.multimodal.bulk.start_bulk_run",
            return_value="run-1",
        ), patch(
            "modules.multimodal.bulk.finish_bulk_run",
            finish_run_mock,
        ), patch(
            "modules.multimodal.bulk._safe_persist_bulk_outcome",
            side_effect=lambda destiny_input, **kwargs: persisted.append({"destiny_input": destiny_input, **kwargs}),
        ):
            outcome = bulk.run_bulk_evaluation(
                origin="Origin, SP",
                dest_list=destinations,
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
                shuffle_destinations=False,
            )

        return outcome, persisted, build_geometry_mock, get_leg_mock, finish_run_mock

    def test_shuffle_destinations_is_deterministic_with_seed(self) -> None:
        values = ["A", "B", "C", "D"]
        shuffled_a, seed_a = bulk._shuffle_destinations(values, enabled=True, seed=77)
        shuffled_b, seed_b = bulk._shuffle_destinations(values, enabled=True, seed=77)

        self.assertEqual(seed_a, 77)
        self.assertEqual(seed_b, 77)
        self.assertEqual(shuffled_a, shuffled_b)

    def test_dedupe_preserve_order_collapses_normalized_duplicates(self) -> None:
        deduped = bulk._dedupe_preserve_order(
            ["Sao Paulo, SP", "São Paulo, SP", "Curitiba, PR", "   "]
        )

        self.assertEqual(deduped, ["Sao Paulo, SP", "Curitiba, PR"])

    def test_estimate_distance_positive_signed_delta_increases_reference_distance(self) -> None:
        origin = self._point("Origin, SP", 0.0, 0.0)
        missing = self._point("Farther City", 0.0, 2.0)
        reference = bulk.ExactRoadReference(
            destiny_name="Reference City",
            destiny_lat=0.0,
            destiny_lon=1.0,
            road_distance_km=150.0,
        )

        estimated_km, meta = bulk._estimate_road_distance_from_reference(origin, missing, reference)

        self.assertGreater(meta.delta_straight_line_km, 0.0)
        self.assertGreater(estimated_km, reference.road_distance_km)

    def test_estimate_distance_negative_signed_delta_decreases_reference_distance(self) -> None:
        origin = self._point("Origin, SP", 0.0, 0.0)
        missing = self._point("Closer City", 0.0, 1.0)
        reference = bulk.ExactRoadReference(
            destiny_name="Reference City",
            destiny_lat=0.0,
            destiny_lon=2.0,
            road_distance_km=300.0,
        )

        estimated_km, meta = bulk._estimate_road_distance_from_reference(origin, missing, reference)

        self.assertLess(meta.delta_straight_line_km, 0.0)
        self.assertLess(estimated_km, reference.road_distance_km)

    def test_estimate_distance_clamps_when_signed_delta_would_go_non_positive(self) -> None:
        origin = self._point("Origin, SP", 0.0, 0.0)
        missing = self._point("Very Close City", 0.0, 0.01)
        reference = bulk.ExactRoadReference(
            destiny_name="Reference City",
            destiny_lat=0.0,
            destiny_lon=5.0,
            road_distance_km=20.0,
        )

        estimated_km, meta = bulk._estimate_road_distance_from_reference(origin, missing, reference)

        self.assertEqual(estimated_km, 1.0)
        self.assertIn("Clamped", meta.notes)

    def test_exact_route_success_keeps_row_exact(self) -> None:
        origin = self._point("Origin, SP", 0.0, 0.0)
        exact = self._point("Exact City", 0.0, 1.0)
        outcome, persisted, _build_geometry_mock, _get_leg_mock, finish_run_mock = self._run_bulk(
            destinations=["Exact City"],
            points_by_input={
                "Origin, SP": origin,
                "Exact City": exact,
            },
            geos_by_label={
                "Exact City": self._geo(origin, exact, road_distance_km=320.0),
            },
        )

        self.assertEqual(outcome["exact_success_count"], 1)
        self.assertEqual(outcome["approximated_success_count"], 0)
        self.assertEqual(outcome["fail_count"], 0)
        self.assertEqual(len(persisted), 1)
        self.assertFalse(persisted[0]["is_approximation"])
        self.assertEqual(persisted[0]["route_source"], "ors_exact")
        finish_run_mock.assert_called_once()

    def test_failed_direct_route_uses_nearest_exact_reference_and_approximations_do_not_chain(self) -> None:
        origin = self._point("Origin, SP", 0.0, 0.0)
        exact = self._point("Exact City", 0.0, 1.0)
        fail_a = self._point("Fail A", 0.0, 1.2)
        fail_b = self._point("Fail B", 0.0, 1.4)
        outcome, persisted, build_geometry_mock, get_leg_mock, _finish_run_mock = self._run_bulk(
            destinations=["Exact City", "Fail A", "Fail B"],
            points_by_input={
                "Origin, SP": origin,
                "Exact City": exact,
                "Fail A": fail_a,
                "Fail B": fail_b,
            },
            geos_by_label={
                "Exact City": self._geo(origin, exact, road_distance_km=300.0),
                "Fail A": self._geo(origin, fail_a, road_distance_km=None),
                "Fail B": self._geo(origin, fail_b, road_distance_km=None),
            },
        )

        approx_rows = [row for row in persisted if row["status"] == "ok" and row["is_approximation"]]
        self.assertEqual(outcome["exact_success_count"], 1)
        self.assertEqual(outcome["approximated_success_count"], 2)
        self.assertEqual(outcome["fail_count"], 0)
        self.assertEqual(len(approx_rows), 2)
        self.assertEqual({row["approximation_reference_destiny"] for row in approx_rows}, {"Exact City"})
        self.assertEqual({row["route_source"] for row in approx_rows}, {"nearest_exact_delta_straight_line"})
        self.assertEqual(build_geometry_mock.call_count, 3)
        self.assertEqual(get_leg_mock.call_count, 1)

    def test_failed_direct_route_without_exact_reference_stays_unresolved(self) -> None:
        origin = self._point("Origin, SP", 0.0, 0.0)
        missing = self._point("No Route City", 0.0, 2.0)
        outcome, persisted, _build_geometry_mock, _get_leg_mock, _finish_run_mock = self._run_bulk(
            destinations=["No Route City"],
            points_by_input={
                "Origin, SP": origin,
                "No Route City": missing,
            },
            geos_by_label={
                "No Route City": self._geo(origin, missing, road_distance_km=None),
            },
        )

        self.assertEqual(outcome["success_count"], 0)
        self.assertEqual(outcome["approximated_success_count"], 0)
        self.assertEqual(outcome["fail_count"], 1)
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["status"], "no_road_route")
        self.assertIn("no exact successful road routes", persisted[0]["error_message"])


if __name__ == "__main__":
    unittest.main()
