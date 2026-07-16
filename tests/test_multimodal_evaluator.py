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

    def test_single_eval_debug_trace_reports_calculation_sources(self) -> None:
        context = evaluator.PreparedEvaluationContext(
            truck_spec={"axles": 5, "payload_t": 27.0, "ref_weight_t": 20.0, "empty_efficiency_gain": 0.18},
            diesel_lookup=DieselPriceLookup(
                source_csv="diesel.csv",
                default_price_r_per_l=6.0,
                uf_to_price={"SP": 6.12, "RJ": 6.15},
                row_count=2,
            ),
            diesel_price_override=None,
            bunker_price_ton=2572.34,
            vessel_eff=self._fake_vessel(),
            hoteling_sel=None,
            port_ops_selection=None,
        )
        path_data = self._path_data()
        path_data["road_direct"]["source"] = "cache"
        path_data["first_mile"]["source"] = "ors"
        path_data["last_mile"]["source"] = "locationiq"
        path_data["sea_leg"].update(
            {
                "source": "directional_direct",
                "fuel_g_per_tnm": 10.5,
                "fuel_g_per_tnm_source": "sea_matrix_directional_weighted_mean",
            }
        )

        with patch.object(
            evaluator,
            "estimate_leg_liters",
            side_effect=self._estimate_leg_liters,
        ), self.assertLogs("modules.multimodal.evaluator", level="DEBUG") as captured:
            result = evaluator.evaluate_path(
                path_data,
                cargo_t=30.0,
                truck_key="semi_27t",
                include_hoteling=False,
                include_port_ops=False,
                prepared_context=context,
                debug_trace=True,
            )

        self.assertTrue(result)
        trace_text = "\n".join(captured.output)
        self.assertIn("stage=diesel_price status=complete source=latest_diesel_prices_csv", trace_text)
        self.assertIn("stage=calculate_road_direct status=complete source=cache", trace_text)
        self.assertIn(
            "stage=calculate_sea_sailing status=complete source=sea_matrix_directional_weighted_mean",
            trace_text,
        )
        self.assertIn("stage=calculate_hoteling status=complete source=disabled_by_user", trace_text)
        self.assertIn("stage=calculate_port_ops status=complete source=disabled_by_user", trace_text)
        self.assertIn("stage=evaluation status=complete source=calculated_single_eval_outputs", trace_text)

    def test_pipeline_json_reports_observed_port_pair_metrics_for_cargo(self) -> None:
        context = evaluator.PreparedEvaluationContext(
            truck_spec={"axles": 5, "payload_t": 27.0, "ref_weight_t": 20.0, "empty_efficiency_gain": 0.18},
            diesel_lookup=DieselPriceLookup(
                source_csv="diesel.csv",
                default_price_r_per_l=6.0,
                uf_to_price={"SP": 6.12, "RJ": 6.15},
                row_count=2,
            ),
            diesel_price_override=None,
            bunker_price_ton=2572.34,
            vessel_eff=self._fake_vessel(),
            hoteling_sel=None,
            port_ops_selection=None,
        )
        path_data = self._path_data()
        path_data["sea_leg"].update(
            {
                "source": "directional_direct",
                "fuel_g_per_tnm": 10.5,
                "fuel_g_per_tnm_source": "sea_matrix_directional_weighted_mean",
                "observed_port_pair_legs": [
                    {
                        "origin_port": "Port A",
                        "destination_port": "Port B",
                        "observed_segment_count": 12,
                        "matched_segment_count": 8,
                        "distinct_voyage_count": 7,
                        "matched_voyage_count": 5,
                        "distinct_imo_count": 3,
                        "matched_imo_count": 2,
                        "average_cargo_t": 200.0,
                        "distance_km": 185.2,
                        "distance_nm": 100.0,
                        "weighted_fuel_intensity_g_per_tnm": 10.5,
                    }
                ],
            }
        )

        with patch.object(
            evaluator,
            "estimate_leg_liters",
            side_effect=self._estimate_leg_liters,
        ):
            result = evaluator.evaluate_path(
                path_data,
                cargo_t=14.0,
                truck_key="semi_27t",
                include_hoteling=False,
                include_port_ops=False,
                prepared_context=context,
            )

        observed_leg = result["multimodal"]["sea"]["observed_port_pair_legs"][0]
        self.assertEqual(observed_leg["observed_segment_count"], 12)
        self.assertEqual(observed_leg["distinct_voyage_count"], 7)
        self.assertEqual(observed_leg["distinct_imo_count"], 3)
        self.assertEqual(observed_leg["average_cargo_t"], 200.0)
        self.assertEqual(observed_leg["distance_nm"], 100.0)
        self.assertEqual(observed_leg["weighted_fuel_intensity_g_per_tnm"], 10.5)
        self.assertEqual(observed_leg["attributed_cargo_t"], 14.0)
        self.assertAlmostEqual(observed_leg["attributed_vlsfo_fuel_kg"], 14.7)
        self.assertAlmostEqual(observed_leg["attributed_co2e_kg"], 45.7758)
        self.assertEqual(
            observed_leg["emission_factor_kg_co2e_per_kg_vlsfo"],
            3.114,
        )

    def test_pair_intensity_applies_to_selected_corridor_subleg_distances(self) -> None:
        context = evaluator.PreparedEvaluationContext(
            truck_spec={
                "axles": 5,
                "payload_t": 27.0,
                "ref_weight_t": 20.0,
                "empty_efficiency_gain": 0.18,
            },
            diesel_lookup=DieselPriceLookup(
                source_csv="diesel.csv",
                default_price_r_per_l=6.0,
                uf_to_price={"SP": 6.12, "RJ": 6.15},
                row_count=2,
            ),
            diesel_price_override=None,
            bunker_price_ton=2572.34,
            vessel_eff=self._fake_vessel(),
            hoteling_sel=None,
            port_ops_selection=None,
        )
        path_data = self._path_data()
        path_data["sea_leg"] = {
            "distance_km": 277.8,
            "source": "observed_voyage_corridor",
            "route_observation_mode": "observed_voyage_corridors",
            "fuel_g_per_tnm": 9.0,
            "fuel_g_per_tnm_source": "antaq_mrv_same_od_transport_work_weighted_median",
            "pair_intensity_g_per_tnm": 9.0,
            "pair_intensity_method": "transport_work_weighted_median",
            "pair_intensity_scope": (
                "all_eligible_same_od_voyage_observations_across_corridors"
            ),
            "pair_intensity_weight": "observed_transport_work_tnm",
            "pair_intensity_source": (
                "antaq_mrv_same_od_transport_work_weighted_median"
            ),
            "pair_intensity_candidate_voyage_count": 4,
            "pair_intensity_resolved_voyage_count": 3,
            "pair_intensity_positive_weight_voyage_count": 3,
            "pair_intensity_zero_weight_voyage_count": 0,
            "pair_intensity_unresolved_voyage_count": 1,
            "pair_intensity_transport_work_tnm": 26000.0,
            "pair_intensity_source_counts": {
                "eu_mrv_imo_latest": 2,
                "eu_mrv_vessel_class_mean": 1,
            },
            "selected_corridor_fuel_g_per_tnm_weighted_mean": 9.333333333333334,
            "corridor_count": 3,
            "candidate_voyage_count": 4,
            "selected_corridor_candidate_voyage_count": 2,
            "direct_voyage_count": 1,
            "multistop_voyage_count": 3,
            "selection_criterion": "direct_first_then_shortest_distance_km",
            "selected_corridor_id": "voyage-42",
            "resolved_voyage_count": 3,
            "imo_intensity_voyage_count": 2,
            "class_fallback_voyage_count": 1,
            "type_fallback_voyage_count": 0,
            "fallback_voyage_count": 1,
            "unresolved_intensity_voyage_count": 1,
            "intensity_source_counts": {
                "eu_mrv_imo_latest": 2,
                "eu_mrv_vessel_class_mean": 1,
                "unavailable": 1,
            },
            "distance_source_counts": {
                "sea_matrix": 6,
                "haversine_fallback": 1,
            },
            "selected_corridor_distance_source_counts": {
                "sea_matrix": 1,
                "haversine_fallback": 1,
            },
            "corridor_leg_count": 2,
            "corridor_port_path": ["Port A", "Port X", "Port B"],
            "observed_transport_work_tnm": 13000.0,
            "observed_fuel_kg": 116.0,
            "candidate_observed_transport_work_tnm": 26000.0,
            "candidate_observed_fuel_kg": 231.0,
            "selected_corridor_sublegs": [
                {
                    "origin_port": "Port A",
                    "destination_port": "Port X",
                    "distance_km": 185.2,
                    "distance_nm": 100.0,
                    "distance_source": "sea_matrix",
                    "observed_cargo_t": 100.0,
                    "transport_work_tnm": 10000.0,
                    "fuel_g_per_tnm": 8.0,
                    "intensity_source": "eu_mrv_imo_latest",
                    "intensity_source_level": "imo",
                    "observed_fuel_kg": 80.0,
                },
                {
                    "origin_port": "Port X",
                    "destination_port": "Port B",
                    "distance_km": 92.6,
                    "distance_nm": 50.0,
                    "distance_source": "haversine_fallback",
                    "observed_cargo_t": 0.0,
                    "transport_work_tnm": 0.0,
                    "fuel_g_per_tnm": 12.0,
                    "intensity_source": "eu_mrv_vessel_class_mean",
                    "intensity_source_level": "vessel_class",
                    "observed_fuel_kg": 0.0,
                },
            ],
        }

        with patch.object(
            evaluator,
            "estimate_leg_liters",
            side_effect=self._estimate_leg_liters,
        ):
            result = evaluator.evaluate_path(
                path_data,
                cargo_t=20.0,
                truck_key="semi_27t",
                include_hoteling=False,
                include_port_ops=False,
                prepared_context=context,
            )

        sea = result["multimodal"]["sea"]
        self.assertEqual(
            sea["sailing_fuel_calc_mode"],
            "same_od_transport_work_weighted_median_on_selected_corridor",
        )
        self.assertAlmostEqual(sea["fuel_kg_sailing"], 27.0)
        self.assertNotEqual(sea["fuel_kg_sailing"], sea["observed_fuel_kg"])
        self.assertAlmostEqual(sea["fuel_g_per_tnm"], 9.0)
        self.assertAlmostEqual(sea["pair_intensity_g_per_tnm"], 9.0)
        self.assertEqual(sea["pair_intensity_candidate_voyage_count"], 4)
        self.assertEqual(sea["selected_corridor_id"], "voyage-42")
        self.assertEqual(sea["candidate_voyage_count"], 4)
        self.assertEqual(sea["selected_corridor_candidate_voyage_count"], 2)
        self.assertEqual(sea["class_fallback_voyage_count"], 1)
        self.assertEqual(sea["candidate_observed_fuel_kg"], 231.0)
        self.assertEqual(
            sea["selected_corridor_distance_source_counts"][
                "haversine_fallback"
            ],
            1,
        )
        self.assertEqual(sea["selected_corridor_sublegs"][0]["scenario_cargo_t"], 20.0)
        self.assertAlmostEqual(
            sea["selected_corridor_sublegs"][0]["scenario_fuel_kg"],
            18.0,
        )
        self.assertAlmostEqual(
            sea["selected_corridor_sublegs"][1]["scenario_fuel_kg"],
            9.0,
        )
        self.assertEqual(
            sea["selected_corridor_sublegs"][0][
                "observed_corridor_fuel_g_per_tnm"
            ],
            8.0,
        )
        self.assertEqual(
            sea["selected_corridor_sublegs"][1][
                "observed_corridor_fuel_g_per_tnm"
            ],
            12.0,
        )
        self.assertEqual(
            sea["selected_corridor_sublegs"][0][
                "applied_pair_intensity_g_per_tnm"
            ],
            9.0,
        )
        first_subleg = sea["selected_corridor_sublegs"][0]
        self.assertEqual(first_subleg["fuel_g_per_tnm"], 8.0)
        self.assertEqual(first_subleg["intensity_source"], "eu_mrv_imo_latest")
        self.assertEqual(first_subleg["intensity_source_level"], "imo")
        self.assertEqual(
            first_subleg["scenario_intensity_source"],
            "antaq_mrv_same_od_transport_work_weighted_median",
        )
        self.assertEqual(first_subleg["scenario_intensity_source_level"], "od_pair")
        self.assertEqual(
            first_subleg["observed_corridor_intensity_source_level"],
            "imo",
        )
        self.assertEqual(
            result["inputs"]["sea_pair_intensity_method"],
            "transport_work_weighted_median",
        )
        self.assertEqual(
            result["inputs"]["sea_route_selected_corridor_id"],
            "voyage-42",
        )
        self.assertEqual(
            result["inputs"]["sea_route_intensity_source_counts"][
                "eu_mrv_vessel_class_mean"
            ],
            1,
        )
        self.assertEqual(
            result["inputs"]["sea_route_selected_corridor_distance_source_counts"][
                "haversine_fallback"
            ],
            1,
        )
        self.assertTrue(
            any("haversine fallback" in item for item in result["calculation_warnings"])
        )

    def test_zero_work_pair_median_has_explicit_source_and_mode(self) -> None:
        context = evaluator.PreparedEvaluationContext(
            truck_spec={
                "axles": 5,
                "payload_t": 27.0,
                "ref_weight_t": 20.0,
                "empty_efficiency_gain": 0.18,
            },
            diesel_lookup=DieselPriceLookup(
                source_csv="diesel.csv",
                default_price_r_per_l=6.0,
                uf_to_price={"SP": 6.12, "RJ": 6.15},
                row_count=2,
            ),
            diesel_price_override=None,
            bunker_price_ton=2572.34,
            vessel_eff=self._fake_vessel(),
            hoteling_sel=None,
            port_ops_selection=None,
        )
        path_data = self._path_data()
        path_data["sea_leg"] = {
            "distance_km": 185.2,
            "source": "observed_voyage_corridor",
            "route_observation_mode": "observed_voyage_corridors",
            "pair_intensity_g_per_tnm": 8.0,
            "pair_intensity_method": (
                "unweighted_median_resolved_same_od_voyages_zero_transport_work"
            ),
            "pair_intensity_source": (
                "antaq_mrv_same_od_unweighted_median_zero_transport_work"
            ),
            "pair_intensity_candidate_voyage_count": 2,
            "pair_intensity_resolved_voyage_count": 2,
            "pair_intensity_positive_weight_voyage_count": 0,
            "pair_intensity_zero_weight_voyage_count": 2,
            "pair_intensity_effective_voyage_count": 2,
            "pair_intensity_transport_work_tnm": 0.0,
            "selected_corridor_sublegs": [
                {
                    "origin_port": "Port A",
                    "destination_port": "Port B",
                    "distance_km": 185.2,
                    "distance_nm": 100.0,
                    "fuel_g_per_tnm": 4.0,
                    "intensity_source": "eu_mrv_imo_latest",
                    "intensity_source_level": "imo",
                }
            ],
        }

        with patch.object(
            evaluator,
            "estimate_leg_liters",
            side_effect=self._estimate_leg_liters,
        ):
            result = evaluator.evaluate_path(
                path_data,
                cargo_t=20.0,
                include_hoteling=False,
                include_port_ops=False,
                prepared_context=context,
            )

        sea = result["multimodal"]["sea"]
        self.assertEqual(
            sea["sailing_fuel_calc_mode"],
            "same_od_unweighted_median_zero_transport_work_on_selected_corridor",
        )
        self.assertEqual(
            sea["fuel_g_per_tnm_source"],
            "antaq_mrv_same_od_unweighted_median_zero_transport_work",
        )
        self.assertAlmostEqual(sea["fuel_kg_sailing"], 16.0)
        self.assertEqual(sea["pair_intensity_effective_voyage_count"], 2)


if __name__ == "__main__":
    unittest.main()
