import unittest
from pathlib import Path
from unittest.mock import patch

from modules.costs.diesel_prices import DieselPriceLookup
from modules.fuel import cabotage_fuel_service
from modules.multimodal import evaluator
from modules.multimodal.container_efficiency import VesselClassEfficiency
from modules.multimodal.hoteling import HotelingRateSelection
from modules.multimodal.port_ops import (
    PortOpsScenarioSelection,
    estimate_port_ops,
    resolve_port_ops_intensity,
)


class PortOpsFallbackTests(unittest.TestCase):
    def _empty_selection(self) -> PortOpsScenarioSelection:
        return PortOpsScenarioSelection(
            requested_scenario="test",
            resolved_scenario="test",
            source_path=Path("port_ops.json"),
            default_port_calls=2,
            default_port_moves_per_call={"p10": 1.0, "median": 1.0, "p90": 1.0},
            t_per_teu_default=14.0,
            diesel_density_kg_per_l=0.85,
            diesel_fuel_type="diesel",
            electricity_kg_co2e_per_kwh=0.0,
            electricity_price_brl_per_kwh=0.0,
            equipment={},
        )

    def _documented_selection(self) -> PortOpsScenarioSelection:
        return PortOpsScenarioSelection(
            requested_scenario="test",
            resolved_scenario="test",
            source_path=Path("port_ops.json"),
            default_port_calls=2,
            default_port_moves_per_call={"p10": 1.0, "median": 1.0, "p90": 1.0},
            t_per_teu_default=14.0,
            diesel_density_kg_per_l=0.85,
            diesel_fuel_type="diesel",
            electricity_kg_co2e_per_kwh=0.0,
            electricity_price_brl_per_kwh=0.0,
            equipment={
                "documented_terminal_truck": {
                    "moves_per_container": 1.0,
                    "diesel_l_per_move": {"p10": 2.0, "median": 2.0, "p90": 2.0},
                    "electricity_kwh_per_move": {"p10": 0.0, "median": 0.0, "p90": 0.0},
                }
            },
        )

    def test_observed_port_uses_direct_intensity(self) -> None:
        resolved = resolve_port_ops_intensity(
            port_name="Porto de Santos",
            denominator=3.0,
            denominator_unit="teu",
            metric_key="fuel_kg",
            observed_port_ops=[
                {"port_name": "Porto de Santos", "fuel_kg": 20.0, "cargo_teu": 2.0},
            ],
        )

        self.assertEqual(resolved["source_level"], "observed")
        self.assertAlmostEqual(resolved["intensity"], 10.0)
        self.assertAlmostEqual(resolved["value"], 30.0)
        self.assertIsNone(resolved["warning"])

    def test_missing_port_uses_weighted_observed_average(self) -> None:
        resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=20.0,
            denominator_unit="teu",
            metric_key="fuel_kg",
            observed_port_ops=[
                {"port_name": "Small Port", "fuel_kg": 100.0, "cargo_teu": 10.0},
                {"port_name": "Large Port", "fuel_kg": 900.0, "cargo_teu": 300.0},
            ],
        )

        weighted_intensity = 1000.0 / 310.0
        simple_average_intensity = ((100.0 / 10.0) + (900.0 / 300.0)) / 2.0

        self.assertEqual(resolved["source_level"], "estimated_port_average")
        self.assertAlmostEqual(resolved["intensity"], weighted_intensity)
        self.assertAlmostEqual(resolved["value"], weighted_intensity * 20.0)
        self.assertNotAlmostEqual(resolved["value"], simple_average_intensity * 20.0)
        self.assertEqual(resolved["observed_ports_used"], 2)
        self.assertAlmostEqual(resolved["total_denominator"], 310.0)

    def test_tonne_based_resolution_does_not_use_teu_denominator(self) -> None:
        resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=50.0,
            denominator_unit="tonne",
            metric_key="fuel_kg",
            observed_port_ops=[
                {"port_name": "Peer Port", "fuel_kg": 25.0, "cargo_t": 100.0},
            ],
        )

        self.assertEqual(resolved["denominator_unit"], "tonne")
        self.assertEqual(resolved["intensity_unit"], "kg_fuel_per_tonne")
        self.assertEqual(resolved["source_level"], "estimated_port_average")
        self.assertAlmostEqual(resolved["value"], 12.5)

    def test_denominator_units_are_isolated_for_peer_average(self) -> None:
        records = [
            {"port_name": "Tonne Port", "fuel_kg": 100.0, "denominator": 10.0, "denominator_unit": "tonne"},
            {"port_name": "TEU Port", "fuel_kg": 20.0, "cargo_teu": 2.0},
            {"port_name": "Move Port", "fuel_kg": 50.0, "moves": 5.0},
        ]

        teu_resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=3.0,
            denominator_unit="teu",
            metric_key="fuel_kg",
            observed_port_ops=records,
        )
        move_resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=3.0,
            denominator_unit="move",
            metric_key="fuel_kg",
            observed_port_ops=records,
        )

        self.assertEqual(teu_resolved["denominator_unit"], "teu")
        self.assertEqual(move_resolved["denominator_unit"], "move")
        self.assertAlmostEqual(teu_resolved["intensity"], 10.0)
        self.assertAlmostEqual(move_resolved["intensity"], 10.0)
        self.assertEqual(teu_resolved["observed_ports_used"], 1)
        self.assertEqual(move_resolved["observed_ports_used"], 1)

    def test_unavailable_when_no_observed_peer_or_default(self) -> None:
        resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=10.0,
            denominator_unit="teu",
            metric_key="fuel_kg",
            observed_port_ops=[],
        )

        self.assertEqual(resolved["source_level"], "unavailable")
        self.assertIsNone(resolved["value"])
        self.assertFalse(resolved["available"])
        self.assertTrue(resolved["excluded_from_total"])
        self.assertIn("no valid observed peer", resolved["warning"])

    def test_literature_default_requires_positive_documented_intensity(self) -> None:
        resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=10.0,
            denominator_unit="teu",
            metric_key="fuel_kg",
            observed_port_ops=[],
            literature_default_intensity=2.5,
            literature_default_basis="documented_test_default",
        )

        self.assertEqual(resolved["source_level"], "literature_default")
        self.assertEqual(resolved["basis"], "documented_test_default")
        self.assertAlmostEqual(resolved["value"], 25.0)
        self.assertIn("documented default", resolved["warning"])

    def test_zero_activity_is_explicit_not_missing_data(self) -> None:
        resolved = resolve_port_ops_intensity(
            port_name="Missing Port",
            denominator=0.0,
            denominator_unit="teu",
            metric_key="fuel_kg",
            observed_port_ops=[],
        )
        result = estimate_port_ops(
            port_calls=0,
            cargo_teu=1.0,
            selection=self._empty_selection(),
        )

        self.assertEqual(resolved["source_level"], "zero_activity")
        self.assertEqual(resolved["basis"], "zero_activity")
        self.assertEqual(resolved["value"], 0.0)
        self.assertTrue(resolved["available"])
        self.assertEqual(result["source_level"], "zero_activity")
        self.assertTrue(result["zero_activity"])
        self.assertEqual(result["totals"]["fuel_kg"], 0.0)

    def test_estimate_port_ops_mixes_observed_and_weighted_missing_calls(self) -> None:
        result = estimate_port_ops(
            port_calls=2,
            cargo_teu=1.0,
            selection=self._empty_selection(),
            port_names=["Observed Port", "Missing Port"],
            observed_port_ops=[
                {"port_name": "Observed Port", "fuel_kg": 8.0, "cargo_teu": 1.0},
                {"port_name": "Large Peer", "fuel_kg": 20.0, "cargo_teu": 10.0},
            ],
        )

        weighted_intensity = 28.0 / 11.0
        expected_fuel = 8.0 + weighted_intensity

        self.assertAlmostEqual(result["totals"]["fuel_kg"], expected_fuel)
        self.assertEqual(result["source_level"], "estimated_port_average")
        self.assertEqual(result["source_level_counts"], {"observed": 1, "estimated_port_average": 1})
        self.assertEqual(result["port_call_breakdown"][0]["source_level"], "observed")
        self.assertEqual(result["port_call_breakdown"][1]["source_level"], "estimated_port_average")
        self.assertGreater(result["totals"]["co2e_kg"], 0.0)

    def test_default_santos_scenario_total_is_unchanged_with_metadata(self) -> None:
        result = estimate_port_ops(port_calls=2, cargo_teu=1.0)

        expected_fuel_kg = (
            (2.0 * 4.0 * 0.35514808238636364)
            + (2.0 * 2.0 * 0.4946705433238636)
        ) * 0.85

        self.assertAlmostEqual(result["totals"]["fuel_kg"], expected_fuel_kg)
        self.assertEqual(result["source_level"], "literature_default")
        self.assertEqual(result["source_level_counts"], {"literature_default": 2})
        self.assertTrue(result["has_unavailable_port_ops"])
        self.assertFalse(result["totals_complete"])
        self.assertIn("warnings", result)


class LegacyHotelingFallbackTests(unittest.TestCase):
    def test_missing_hotel_city_uses_weighted_observed_average(self) -> None:
        hotel_data = {
            "entries": [
                {
                    "city": "Small City",
                    "kg_fuel_per_t": 10.0,
                    "total_hotel_fuel_kg": 100.0,
                    "total_handled_t": 10.0,
                },
                {
                    "city": "Large City",
                    "kg_fuel_per_t": 1.0,
                    "total_hotel_fuel_kg": 90.0,
                    "total_handled_t": 90.0,
                },
            ]
        }
        factor_index = cabotage_fuel_service.build_hotel_factor_index(hotel_data=hotel_data)

        resolved = cabotage_fuel_service._resolve_hotel_factor(
            city="missing city",
            hotel_data=hotel_data,
            factor_index=factor_index,
            default_hotel_kg_per_t=0.0,
        )

        self.assertEqual(resolved["source_level"], "estimated_port_average")
        self.assertAlmostEqual(resolved["value"], 190.0 / 100.0)
        self.assertNotAlmostEqual(resolved["value"], (10.0 + 1.0) / 2.0)
        self.assertEqual(resolved["observed_ports_used"], 2)
        self.assertAlmostEqual(resolved["total_denominator"], 100.0)

    def test_missing_hotel_city_without_peer_or_default_is_unavailable(self) -> None:
        resolved = cabotage_fuel_service._resolve_hotel_factor(
            city="missing city",
            hotel_data={"entries": []},
            factor_index={},
            default_hotel_kg_per_t=0.0,
        )

        self.assertEqual(resolved["source_level"], "unavailable")
        self.assertIsNone(resolved["value"])
        self.assertIn("no observed peer", resolved["warning"])


class EvaluatorPortOpsIntegrationTests(unittest.TestCase):
    _DEFAULT_OBSERVED = object()

    def _path_data(
        self,
        *,
        road_direct_km: float = 1000.0,
        first_mile_km: float = 100.0,
        last_mile_km: float = 50.0,
        sea_km: float = 1200.0,
        port_origin_name: str = "Observed Port",
        port_destiny_name: str = "Missing Port",
    ) -> dict:
        return {
            "status": "ok",
            "origin": {"label": "Origin, SP", "uf": "SP"},
            "destiny": {"label": "Destiny, RJ", "uf": "RJ"},
            "port_origin": {"name": port_origin_name},
            "port_destiny": {"name": port_destiny_name},
            "road_direct": {"distance_km": road_direct_km},
            "first_mile": {"distance_km": first_mile_km},
            "last_mile": {"distance_km": last_mile_km},
            "sea_leg": {"distance_km": sea_km},
        }

    def _fake_vessel(self, *, transport_work_intensity: bool = True) -> VesselClassEfficiency:
        return VesselClassEfficiency(
            requested_class="container_feeder",
            vessel_class="container_feeder",
            fuel_per_nm=800.0,
            fuel_g_per_tnm=12.0 if transport_work_intensity else None,
            size_proxy_t_median=12000.0,
            teu_capacity=1200.0,
            lightship_t=8000.0,
            sample_size=10,
            source_path=Path("vessel.json"),
        )

    def _fake_hoteling(self) -> HotelingRateSelection:
        return HotelingRateSelection(
            requested_class="container_feeder",
            vessel_class="container_feeder",
            fuel_rate_hoteling_t_per_h=0.2,
            sample_size=5,
            ratio_used=0.4,
            aux_main_ratio=0.1,
            source_path=Path("hoteling.json"),
        )

    def _documented_selection(self) -> PortOpsScenarioSelection:
        return PortOpsScenarioSelection(
            requested_scenario="test",
            resolved_scenario="test",
            source_path=Path("port_ops.json"),
            default_port_calls=2,
            default_port_moves_per_call={"p10": 1.0, "median": 1.0, "p90": 1.0},
            t_per_teu_default=14.0,
            diesel_density_kg_per_l=0.85,
            diesel_fuel_type="diesel",
            electricity_kg_co2e_per_kwh=0.0,
            electricity_price_brl_per_kwh=0.0,
            equipment={
                "documented_terminal_truck": {
                    "moves_per_container": 1.0,
                    "diesel_l_per_move": {"p10": 2.0, "median": 2.0, "p90": 2.0},
                    "electricity_kwh_per_move": {"p10": 0.0, "median": 0.0, "p90": 0.0},
                }
            },
        )

    def _estimate_leg_liters(self, distance_km: float, **_kwargs):
        liters = float(distance_km) / 2.0
        trips = 0 if distance_km <= 0 else 1
        return liters, 0.0, 0.0, trips, 0.0, 0.0

    def _run_evaluator(
        self,
        *,
        include_port_ops: bool,
        observed_port_ops: object = _DEFAULT_OBSERVED,
        path_data: dict | None = None,
        selection: PortOpsScenarioSelection | None = None,
        vessel: VesselClassEfficiency | None = None,
    ) -> dict:
        diesel_lookup = DieselPriceLookup(
            source_csv="diesel.csv",
            default_price_r_per_l=6.0,
            uf_to_price={"SP": 6.12, "RJ": 6.15},
            row_count=2,
        )
        if observed_port_ops is self._DEFAULT_OBSERVED:
            observed = [
                {"port_name": "Observed Port", "fuel_kg": 8.0, "cargo_teu": 1.0},
                {"port_name": "Large Peer", "fuel_kg": 20.0, "cargo_teu": 10.0},
            ]
        else:
            observed = observed_port_ops

        selection = selection or PortOpsScenarioSelection(
            requested_scenario="test",
            resolved_scenario="test",
            source_path=Path("port_ops.json"),
            default_port_calls=2,
            default_port_moves_per_call={"p10": 1.0, "median": 1.0, "p90": 1.0},
            t_per_teu_default=14.0,
            diesel_density_kg_per_l=0.85,
            diesel_fuel_type="diesel",
            electricity_kg_co2e_per_kwh=0.0,
            electricity_price_brl_per_kwh=0.0,
            equipment={},
        )
        vessel = vessel or self._fake_vessel()

        with patch.object(evaluator, "resolve_vessel_class_efficiency", return_value=vessel), patch.object(
            evaluator,
            "resolve_hoteling_rate",
            return_value=self._fake_hoteling(),
        ), patch.object(
            evaluator,
            "resolve_port_ops_scenario",
            return_value=selection,
        ), patch.object(
            evaluator,
            "build_price_lookup",
            return_value=diesel_lookup,
        ), patch.object(
            evaluator,
            "get_bunker_price",
            return_value=2572.34,
        ), patch.object(
            evaluator,
            "get_truck_spec",
            return_value={"axles": 5, "payload_t": 27.0, "ref_weight_t": 20.0, "empty_efficiency_gain": 0.18},
        ), patch.object(
            evaluator,
            "estimate_leg_liters",
            side_effect=self._estimate_leg_liters,
        ):
            return evaluator.evaluate_path(
                path_data or self._path_data(),
                cargo_t=14.0,
                cargo_teu=1.0,
                truck_key="semi_27t",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=include_port_ops,
                port_ops_scenario="test",
                port_ops_observed_ports=observed,
            )

    def _assert_component_totals_match(self, result: dict) -> None:
        multimodal = result["multimodal"]
        sea = multimodal["sea"]
        marine_ef = float(result["inputs"]["marine_ef_kg_per_kg"])

        expected_marine_co2e = (
            float(sea["fuel_kg_sailing"]) + float(sea["hoteling_fuel_kg"])
        ) * marine_ef
        expected_marine_cost = (float(sea["fuel_kg_marine"]) / 1000.0) * float(result["inputs"]["bunker_price"])
        self.assertAlmostEqual(sea["co2e_marine"], expected_marine_co2e)
        self.assertAlmostEqual(sea["fuel_kg_marine"], sea["fuel_kg_sailing"] + sea["hoteling_fuel_kg"])
        self.assertAlmostEqual(sea["fuel_kg"], sea["fuel_kg_marine"] + sea["port_ops_fuel_kg"])
        self.assertAlmostEqual(sea["cost_marine"], expected_marine_cost)
        self.assertAlmostEqual(sea["cost"], sea["cost_marine"] + sea["port_ops_cost"])
        self.assertAlmostEqual(sea["co2e"], sea["co2e_marine"] + sea["port_ops_co2e"])
        self.assertAlmostEqual(
            multimodal["total_co2e"],
            multimodal["first_mile"]["co2e"] + sea["co2e"] + multimodal["last_mile"]["co2e"],
        )
        self.assertAlmostEqual(
            multimodal["total_cost"],
            multimodal["first_mile"]["cost"] + sea["cost"] + multimodal["last_mile"]["cost"],
        )
        numeric_values = [
            result["road_only"]["cost"],
            result["road_only"]["co2e"],
            multimodal["total_cost"],
            multimodal["total_co2e"],
            sea["fuel_kg"],
            sea["cost"],
            sea["co2e"],
        ]
        for value in numeric_values:
            self.assertGreaterEqual(float(value), 0.0)

    def test_route_total_uses_complete_observed_port_data(self) -> None:
        result = self._run_evaluator(
            include_port_ops=True,
            path_data=self._path_data(port_destiny_name="Destination Port"),
            observed_port_ops=[
                {"port_name": "Observed Port", "fuel_kg": 8.0, "cargo_teu": 1.0},
                {"port_name": "Destination Port", "fuel_kg": 6.0, "cargo_teu": 1.0},
            ],
        )

        sea = result["multimodal"]["sea"]

        self.assertAlmostEqual(sea["port_ops_fuel_kg"], 14.0)
        self.assertEqual(sea["port_ops_source_level"], "observed")
        self.assertEqual(sea["port_ops_source_level_counts"], {"observed": 2})
        self.assertFalse(sea["port_ops_has_unavailable"])
        self.assertTrue(sea["port_ops_totals_complete"])
        self.assertLess(result["multimodal"]["total_co2e"], result["road_only"]["co2e"])
        self._assert_component_totals_match(result)

    def test_route_total_includes_estimated_missing_port_call(self) -> None:
        with_port_ops = self._run_evaluator(include_port_ops=True)
        without_port_ops = self._run_evaluator(include_port_ops=False)

        sea = with_port_ops["multimodal"]["sea"]
        weighted_intensity = 28.0 / 11.0

        self.assertAlmostEqual(sea["port_ops_fuel_kg"], 8.0 + weighted_intensity)
        self.assertEqual(sea["port_ops_source_level"], "estimated_port_average")
        self.assertEqual(sea["port_ops_source_level_counts"], {"observed": 1, "estimated_port_average": 1})
        self.assertIn("teu-weighted average", "; ".join(sea["port_ops_warnings"]))
        self.assertGreater(
            with_port_ops["multimodal"]["total_co2e"],
            without_port_ops["multimodal"]["total_co2e"],
        )
        self.assertLess(with_port_ops["multimodal"]["total_co2e"], with_port_ops["road_only"]["co2e"])
        self._assert_component_totals_match(with_port_ops)

    def test_no_observed_data_uses_documented_scenario(self) -> None:
        result = self._run_evaluator(
            include_port_ops=True,
            observed_port_ops=None,
            selection=self._documented_selection(),
        )
        sea = result["multimodal"]["sea"]

        self.assertAlmostEqual(sea["port_ops_fuel_kg"], 2.0 * 0.85 * 2.0)
        self.assertEqual(sea["port_ops_source_level"], "literature_default")
        self.assertEqual(sea["port_ops_source_level_counts"], {"literature_default": 2})
        self.assertIn("documented moves-based scenario", "; ".join(sea["port_ops_warnings"]))
        self._assert_component_totals_match(result)

    def test_unavailable_port_ops_are_not_silent_zeroes(self) -> None:
        result = self._run_evaluator(
            include_port_ops=True,
            observed_port_ops=[],
            selection=PortOpsScenarioSelection(
                requested_scenario="empty",
                resolved_scenario="empty",
                source_path=Path("port_ops.json"),
                default_port_calls=2,
                default_port_moves_per_call={"p10": 1.0, "median": 1.0, "p90": 1.0},
                t_per_teu_default=14.0,
                diesel_density_kg_per_l=0.85,
                diesel_fuel_type="diesel",
                electricity_kg_co2e_per_kwh=0.0,
                electricity_price_brl_per_kwh=0.0,
                equipment={},
            ),
        )
        sea = result["multimodal"]["sea"]
        calls = sea["port_ops"]["port_call_breakdown"]

        self.assertEqual(sea["port_ops_source_level"], "unavailable")
        self.assertTrue(sea["port_ops_has_unavailable"])
        self.assertFalse(sea["port_ops_totals_complete"])
        self.assertEqual(sea["port_ops_fuel_kg"], 0.0)
        self.assertIsNone(calls[0]["fuel_kg"])
        self.assertTrue(calls[0]["excluded_from_total"])
        self.assertIn("No observed port-ops records", "; ".join(sea["port_ops_warnings"]))
        self._assert_component_totals_match(result)

    def test_hoteling_added_when_transport_work_intensity_absent(self) -> None:
        result = self._run_evaluator(
            include_port_ops=True,
            vessel=self._fake_vessel(transport_work_intensity=False),
        )
        sea = result["multimodal"]["sea"]

        self.assertTrue(sea["hoteling_requested"])
        self.assertTrue(sea["hoteling_included"])
        self.assertEqual(sea["hoteling_source_level"], "literature_default")
        self.assertEqual(sea["hoteling_basis"], "mrv_class_rate_scaled_by_emep_ratio")
        self.assertEqual(sea["hoteling_hours_per_call"], 14.0)
        self.assertEqual(sea["port_calls"], 2)
        self.assertEqual(sea["hoteling_hours_total"], 28.0)
        self.assertGreater(sea["hoteling_fuel_kg"], 0.0)
        self.assertGreater(sea["hoteling_co2e"], 0.0)
        self._assert_component_totals_match(result)

    def test_hoteling_excluded_when_transport_work_intensity_used(self) -> None:
        result = self._run_evaluator(include_port_ops=True)
        sea = result["multimodal"]["sea"]

        self.assertTrue(sea["hoteling_requested"])
        self.assertFalse(sea["hoteling_included"])
        self.assertEqual(sea["hoteling_exclusion_reason"], "included_in_transport_work_intensity")
        self.assertEqual(sea["hoteling_fuel_kg"], 0.0)
        self.assertEqual(sea["hoteling_co2e"], 0.0)
        self._assert_component_totals_match(result)

    def test_short_road_route_can_remain_lower_than_multimodal(self) -> None:
        result = self._run_evaluator(
            include_port_ops=True,
            path_data=self._path_data(road_direct_km=100.0),
        )

        self.assertLessEqual(result["road_only"]["co2e"], result["multimodal"]["total_co2e"])
        self._assert_component_totals_match(result)

    def test_controlled_long_route_can_have_lower_multimodal_emissions(self) -> None:
        result = self._run_evaluator(
            include_port_ops=True,
            path_data=self._path_data(road_direct_km=3000.0, first_mile_km=50.0, last_mile_km=50.0, sea_km=1200.0),
        )

        self.assertLess(result["multimodal"]["total_co2e"], result["road_only"]["co2e"])
        self._assert_component_totals_match(result)


if __name__ == "__main__":
    unittest.main()
