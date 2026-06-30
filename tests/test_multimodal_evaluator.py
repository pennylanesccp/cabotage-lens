import unittest
from pathlib import Path
from unittest.mock import patch

from modules.costs.diesel_prices import DieselPriceLookup
from modules.multimodal import evaluator
from modules.multimodal.container_efficiency import VesselClassEfficiency
from modules.multimodal.hoteling import HotelingRateSelection
from modules.multimodal.port_ops import PortOpsScenarioSelection


class MultimodalEvaluatorContextTests(unittest.TestCase):
    def _path_data(self) -> dict:
        return {
            "status": "ok",
            "origin": {"label": "Origin, SP", "uf": "SP"},
            "destiny": {"label": "Destiny, RJ", "uf": "RJ"},
            "road_direct": {"distance_km": 1000.0},
            "first_mile": {"distance_km": 100.0},
            "last_mile": {"distance_km": 50.0},
            "sea_leg": {"distance_km": 1200.0},
        }

    def _fake_vessel(self) -> VesselClassEfficiency:
        return VesselClassEfficiency(
            requested_class="container_feeder",
            vessel_class="container_feeder",
            fuel_per_nm=800.0,
            fuel_g_per_tnm=12.0,
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

    def _fake_port_ops_selection(self) -> PortOpsScenarioSelection:
        return PortOpsScenarioSelection(
            requested_scenario="baseline",
            resolved_scenario="baseline",
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

    def _estimate_leg_liters(self, distance_km: float, **_kwargs):
        liters = float(distance_km) / 2.0
        trips = 0 if distance_km <= 0 else 1
        return liters, 0.0, 0.0, trips, 0.0, 0.0

    def test_prepared_context_reuses_expensive_artifacts(self) -> None:
        vessel_eff = self._fake_vessel()
        hoteling_sel = self._fake_hoteling()
        port_ops_sel = self._fake_port_ops_selection()
        diesel_lookup = DieselPriceLookup(
            source_csv="diesel.csv",
            default_price_r_per_l=6.0,
            uf_to_price={"SP": 6.12, "RJ": 6.15},
            row_count=2,
        )

        with patch.object(evaluator, "resolve_vessel_class_efficiency", return_value=vessel_eff) as vessel_mock, patch.object(
            evaluator,
            "resolve_hoteling_rate",
            return_value=hoteling_sel,
        ) as hoteling_mock, patch.object(
            evaluator,
            "resolve_port_ops_scenario",
            return_value=port_ops_sel,
        ) as port_ops_sel_mock, patch.object(
            evaluator,
            "build_price_lookup",
            return_value=diesel_lookup,
        ) as price_lookup_mock, patch.object(
            evaluator,
            "get_bunker_price",
            return_value=2572.34,
        ) as bunker_mock, patch.object(
            evaluator,
            "get_truck_spec",
            return_value={"axles": 5, "payload_t": 27.0, "ref_weight_t": 20.0, "empty_efficiency_gain": 0.18},
        ) as truck_mock, patch.object(
            evaluator,
            "estimate_leg_liters",
            side_effect=self._estimate_leg_liters,
        ), patch.object(
            evaluator,
            "estimate_port_ops",
            return_value={
                "source_path": "port_ops.json",
                "resolved_scenario": "baseline",
                "port_moves_per_call": 1.0,
                "cargo_teu_resolved": 3,
                "totals": {"fuel_kg": 5.0, "co2e_kg": 7.0, "cost_brl": 11.0},
            },
        ) as port_ops_mock:
            context = evaluator.prepare_evaluation_context(
                truck_key="semi_27t",
                vessel_class="container_feeder",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_ops_scenario="baseline",
            )

            result_a = evaluator.evaluate_path(
                self._path_data(),
                cargo_t=30.0,
                truck_key="semi_27t",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_ops_scenario="baseline",
                prepared_context=context,
            )
            result_b = evaluator.evaluate_path(
                self._path_data(),
                cargo_t=30.0,
                truck_key="semi_27t",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_ops_scenario="baseline",
                prepared_context=context,
            )

        self.assertEqual(vessel_mock.call_count, 1)
        self.assertEqual(hoteling_mock.call_count, 0)
        self.assertEqual(port_ops_sel_mock.call_count, 1)
        self.assertEqual(price_lookup_mock.call_count, 1)
        self.assertEqual(bunker_mock.call_count, 1)
        self.assertEqual(truck_mock.call_count, 1)
        self.assertEqual(port_ops_mock.call_count, 2)
        self.assertEqual(result_a["inputs"]["diesel_price_source"], "latest_diesel_prices_csv")
        self.assertEqual(result_a["inputs"]["hoteling_exclusion_reason"], "included_in_transport_work_intensity")
        self.assertEqual(result_b["inputs"]["bunker_price"], 2572.34)

    def test_prepared_context_preserves_evaluation_output(self) -> None:
        vessel_eff = self._fake_vessel()
        hoteling_sel = self._fake_hoteling()
        port_ops_sel = self._fake_port_ops_selection()
        diesel_lookup = DieselPriceLookup(
            source_csv="diesel.csv",
            default_price_r_per_l=6.0,
            uf_to_price={"SP": 6.12, "RJ": 6.15},
            row_count=2,
        )

        with patch.object(evaluator, "resolve_vessel_class_efficiency", return_value=vessel_eff), patch.object(
            evaluator,
            "resolve_hoteling_rate",
            return_value=hoteling_sel,
        ), patch.object(
            evaluator,
            "resolve_port_ops_scenario",
            return_value=port_ops_sel,
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
        ), patch.object(
            evaluator,
            "estimate_port_ops",
            return_value={
                "source_path": "port_ops.json",
                "resolved_scenario": "baseline",
                "port_moves_per_call": 1.0,
                "cargo_teu_resolved": 3,
                "totals": {"fuel_kg": 5.0, "co2e_kg": 7.0, "cost_brl": 11.0},
            },
        ):
            context = evaluator.prepare_evaluation_context(
                truck_key="semi_27t",
                vessel_class="container_feeder",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_ops_scenario="baseline",
            )
            prepared_result = evaluator.evaluate_path(
                self._path_data(),
                cargo_t=30.0,
                truck_key="semi_27t",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_ops_scenario="baseline",
                prepared_context=context,
            )
            plain_result = evaluator.evaluate_path(
                self._path_data(),
                cargo_t=30.0,
                truck_key="semi_27t",
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                port_ops_scenario="baseline",
            )

        self.assertEqual(prepared_result, plain_result)


if __name__ == "__main__":
    unittest.main()
