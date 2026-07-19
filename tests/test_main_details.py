import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main.details.breakdown import (
    _legs_table,
    _port_call_breakdown_table,
    _selected_corridor_sublegs_table,
)
from app.main.details.provenance import source_level_label
from app.main.details.assumptions import _assumptions_table
from app.main.details import render_details


class MainDetailsTests(unittest.TestCase):
    def test_render_details_hides_empty_sections_before_results(self) -> None:
        fake_streamlit = SimpleNamespace(
            markdown=Mock(),
            expander=Mock(return_value=contextlib.nullcontext()),
        )

        with patch("app.main.details.st", fake_streamlit):
            render_details(payload={}, geo=None, results=None)

        fake_streamlit.markdown.assert_not_called()
        fake_streamlit.expander.assert_not_called()

    def test_assumptions_show_maritime_distance_provenance(self) -> None:
        results = {
            "inputs": {},
            "multimodal": {
                "sea": {
                    "distance_source": "SeaMatrix haversine fallback",
                    "distance_provenance": {
                        "source": "SeaMatrix haversine fallback",
                        "source_type": "haversine_fallback",
                    },
                }
            },
        }

        table = _assumptions_table(results=results, payload={})
        rows = {row["Parameter"]: row for row in table.to_dict("records")}

        self.assertIn("Maritime distance source", rows)
        self.assertIn("Fallback estimate", rows["Maritime distance source"]["Value"])
        self.assertIn("haversine_fallback", rows["Maritime distance source"]["Value"])
        self.assertIn("route confidence", rows["Maritime distance source"]["Description"])
        self.assertIn("Maritime distance note", rows)
        self.assertIn("Fallback estimate", rows["Maritime distance note"]["Value"])

    def test_source_level_labels_are_human_readable(self) -> None:
        self.assertEqual(source_level_label("zero_activity"), "Zero activity")
        self.assertEqual(source_level_label("observed"), "Observed port-specific data")
        self.assertEqual(
            source_level_label("estimated_port_average"),
            "Estimated from weighted average of observed ports",
        )
        self.assertEqual(source_level_label("literature_default"), "Documented model default")
        self.assertEqual(
            source_level_label("unavailable"),
            "Unavailable / not included without defensible data",
        )
        self.assertIsNone(source_level_label(None))
        self.assertIsNone(source_level_label(""))

    def test_assumptions_include_port_ops_and_hoteling_provenance(self) -> None:
        results = {
            "inputs": {
                "hoteling_source_level": "literature_default",
                "hoteling_basis": "mrv_class_rate_scaled_by_emep_ratio",
                "hoteling_exclusion_reason": "included_in_transport_work_intensity",
            },
            "multimodal": {
                "sea": {
                    "port_ops_source_level": "estimated_port_average",
                    "port_ops_source_level_counts": {"observed": 1, "estimated_port_average": 1},
                    "port_ops_warnings": ["Port-specific observed port-ops data missing."],
                    "port_ops": {
                        "calculation_basis": "observed_port_ops_hierarchy",
                        "fallback_denominator_unit": "teu",
                        "observed_port_ops_record_count": 2,
                        "equipment_source_level_counts": {"literature_default": 1},
                        "totals_complete": False,
                        "has_unavailable_port_ops": True,
                        "missing_value_policy": "unavailable_values_excluded_from_numeric_totals_with_warning",
                    },
                }
            },
        }

        table = _assumptions_table(results=results, payload={"port_ops_scenario": "santos_diesel_heavy"})
        rows = {row["Parameter"]: row for row in table.to_dict("records")}

        self.assertIn("Port ops scenario", rows)
        self.assertEqual(rows["Port ops data source"]["Value"], "Estimated from weighted average of observed ports")
        self.assertIn("Observed port-specific data: 1", rows["Port ops coverage"]["Value"])
        self.assertIn("equipment factors: Documented model default: 1", rows["Port ops coverage"]["Value"])
        self.assertIn("observed records available: 2", rows["Port ops coverage"]["Value"])
        self.assertIn("incomplete", rows["Port ops completeness"]["Value"])
        self.assertIn("unavailable components are flagged", rows["Port ops completeness"]["Value"])
        self.assertIn("fallback denominator: teu", rows["Port ops fallback basis"]["Value"])
        self.assertIn("Port-specific observed", rows["Port ops warning"]["Value"])
        self.assertEqual(rows["Hoteling data source"]["Value"], "Documented model default")
        self.assertIn("MRV class rate", rows["Hoteling basis"]["Value"])
        self.assertIn("Already covered", rows["Hoteling exclusion reason"]["Value"])

    def test_assumptions_show_observed_corridor_and_intensity_coverage(self) -> None:
        results = {
            "inputs": {},
            "multimodal": {
                "sea": {
                    "route_observation_mode": "observed_voyage_corridors",
                    "route_corridor_port_path": ["Porto A", "Porto C", "Porto B"],
                    "selection_criterion": "direct_first_then_shortest_distance_km",
                    "selected_corridor_id": "corridor-a-c-b",
                    "corridor_count": 2,
                    "candidate_voyage_count": 4,
                    "direct_voyage_count": 1,
                    "multistop_voyage_count": 3,
                    "resolved_voyage_count": 4,
                    "imo_intensity_voyage_count": 2,
                    "class_fallback_voyage_count": 1,
                    "type_fallback_voyage_count": 1,
                    "unresolved_intensity_voyage_count": 0,
                    "intensity_source_counts": {
                        "eu_mrv_imo_latest": 2,
                        "eu_mrv_vessel_class_trimmed_mean_1pct": 1,
                        "eu_mrv_ship_type_trimmed_mean_1pct": 1,
                    },
                    "pair_intensity_g_per_tnm": 9.32205,
                    "pair_intensity_method": "transport_work_weighted_mean",
                    "pair_intensity_weight": "observed_transport_work_tnm",
                    "pair_intensity_source": (
                        "antaq_mrv_same_od_transport_work_weighted_mean"
                    ),
                    "pair_intensity_candidate_voyage_count": 4,
                    "pair_intensity_resolved_voyage_count": 4,
                    "pair_intensity_effective_voyage_count": 3,
                    "pair_intensity_positive_weight_voyage_count": 3,
                    "pair_intensity_zero_weight_voyage_count": 1,
                    "pair_intensity_unresolved_voyage_count": 0,
                    "pair_intensity_effective_source_counts": {
                        "eu_mrv_imo_latest": 2,
                        "eu_mrv_ship_type_trimmed_mean_1pct": 1,
                    },
                    "selected_corridor_distance_source_counts": {
                        "sea_matrix": 1,
                        "haversine_fallback": 1,
                    },
                }
            },
        }

        rows = {
            row["Parameter"]: row
            for row in _assumptions_table(results=results, payload={}).to_dict("records")
        }

        selected = rows["Selected distance corridor"]["Value"]
        self.assertIn("Porto A → Porto C → Porto B", selected)
        self.assertIn("corridor-a-c-b", selected)
        self.assertEqual(
            rows["Corridor selection criterion"]["Value"],
            "Direct observed corridor first; otherwise shortest observed distance (km)",
        )
        coverage = rows["Observed maritime coverage"]["Value"]
        self.assertIn("observed corridors: 2", coverage)
        self.assertIn("candidate voyages: 4", coverage)
        self.assertIn("direct voyages: 1", coverage)
        self.assertIn("multistop voyages: 3", coverage)
        intensity_coverage = rows["Maritime intensity coverage"]["Value"]
        self.assertIn("IMO-specific intensity: 2", intensity_coverage)
        self.assertIn("vessel-class fallback: 1", intensity_coverage)
        self.assertIn("ship-type fallback: 1", intensity_coverage)
        self.assertIn("unresolved intensity: 0", intensity_coverage)
        source_counts = rows["Maritime intensity sources"]["Value"]
        self.assertIn("EU MRV latest record by IMO: 2", source_counts)
        self.assertIn("EU MRV vessel-class 1% trimmed mean: 1", source_counts)
        self.assertIn("EU MRV ship-type 1% trimmed mean: 1", source_counts)
        estimator_coverage = rows["OD intensity estimator coverage"]["Value"]
        self.assertIn("candidate voyages: 4", estimator_coverage)
        self.assertIn("effective voyages: 3", estimator_coverage)
        self.assertIn("zero-work voyages: 1", estimator_coverage)
        estimator_sources = rows["OD intensity estimator sources"]["Value"]
        self.assertIn("EU MRV latest record by IMO: 2", estimator_sources)
        self.assertIn("EU MRV ship-type 1% trimmed mean: 1", estimator_sources)
        self.assertNotIn("vessel-class", estimator_sources)
        self.assertEqual(
            rows["OD representative maritime intensity"]["Value"],
            "9.322050 g/(t·nm)",
        )
        self.assertIn(
            "Transport-work-weighted mean",
            rows["OD intensity aggregation"]["Value"],
        )
        distance_sources = rows["Selected-corridor distance sources"]["Value"]
        self.assertIn("Sea-matrix distance: 1", distance_sources)
        self.assertIn("Coordinate haversine fallback: 1", distance_sources)

    def test_assumptions_show_mean_onboard_cargo_weighted_observed_voyage_distance(
        self,
    ) -> None:
        results = {
            "inputs": {},
            "multimodal": {
                "sea": {
                    "route_observation_mode": "observed_voyage_corridors",
                    "scenario_distance_method": (
                        "mean_onboard_cargo_weighted_mean_complete_observed_voyage_distances"
                    ),
                    "scenario_distance_weight": "mean_onboard_cargo_t",
                    "scenario_distance_mean_onboard_cargo_t_total": 375.0,
                    "scenario_distance_observation_count": 4,
                    "scenario_distance_corridor_count": 3,
                    "scenario_distance_km": 400.0,
                    "scenario_distance_source_counts": {
                        "sea_matrix": 6,
                        "haversine_fallback": 1,
                    },
                    # These fields model stale legacy data and must not be shown
                    # as the geometry of the mean-distance scenario.
                    "route_corridor_port_path": ["Porto A", "Porto C", "Porto B"],
                    "selected_corridor_id": "legacy-corridor",
                }
            },
        }

        rows = {
            row["Parameter"]: row
            for row in _assumptions_table(results=results, payload={}).to_dict(
                "records"
            )
        }

        self.assertIn("Maritime scenario distance", rows)
        value = rows["Maritime scenario distance"]["Value"]
        self.assertIn(
            "Mean-onboard-cargo-weighted mean of complete observed voyage distances",
            value,
        )
        self.assertIn("400.000 km", value)
        self.assertIn("complete voyages: 4", value)
        self.assertNotIn("Selected distance corridor", rows)
        self.assertIn("Observed-voyage distance sources", rows)
        self.assertIn(
            "Coordinate haversine fallback: 1",
            rows["Observed-voyage distance sources"]["Value"],
        )

    def test_legacy_stitched_corridor_is_not_labeled_as_observed_voyage(self) -> None:
        results = {
            "multimodal": {
                "sea": {
                    "route_corridor_port_path": ["Porto A", "Porto X", "Porto B"],
                    "selection_criterion": "shortest_distance_km",
                    "observed_port_pair_legs": [
                        {
                            "origin_port": "Porto A",
                            "destination_port": "Porto X",
                            "distance_nm": 10.0,
                        }
                    ],
                }
            }
        }

        rows = {
            row["Parameter"]
            for row in _assumptions_table(results=results, payload={}).to_dict(
                "records"
            )
        }
        self.assertNotIn("Selected observed corridor", rows)
        self.assertTrue(_selected_corridor_sublegs_table(results).empty)

    def test_breakdown_rows_include_provenance_without_requiring_metadata(self) -> None:
        results = {
            "inputs": {"bunker_price": 3500.0, "marine_ef_kg_per_kg": 3.21},
            "multimodal": {
                "first_mile": {"distance_km": 1.0, "cost": 2.0, "co2e": 3.0},
                "last_mile": {"distance_km": 4.0, "cost": 5.0, "co2e": 6.0},
                "sea": {
                    "distance_km": 100.0,
                    "fuel_kg_sailing": 10.0,
                    "hoteling_included": True,
                    "hoteling_fuel_kg": 1.0,
                    "hoteling_source_level": "literature_default",
                    "port_ops_cost": 7.0,
                    "port_ops_co2e": 8.0,
                    "port_ops_source_level": "estimated_port_average",
                },
            },
        }

        table = _legs_table(results)
        rows = {row["Leg"]: row for row in table.to_dict("records")}

        self.assertEqual(rows["Port ops"]["Data source"], "Estimated from weighted average of observed ports")
        self.assertEqual(rows["Hoteling"]["Data source"], "Documented model default")

        older_results = {
            "inputs": {"bunker_price": 3500.0, "marine_ef_kg_per_kg": 3.21},
            "multimodal": {
                "first_mile": {},
                "last_mile": {},
                "sea": {},
            },
        }
        older_table = _legs_table(older_results)
        self.assertIn("Data source", older_table.columns)

    def test_breakdown_marks_unavailable_and_excluded_components(self) -> None:
        results = {
            "inputs": {"bunker_price": 3500.0, "marine_ef_kg_per_kg": 3.21},
            "multimodal": {
                "first_mile": {"distance_km": 1.0, "cost": 2.0, "co2e": 3.0},
                "last_mile": {"distance_km": 4.0, "cost": 5.0, "co2e": 6.0},
                "sea": {
                    "distance_km": 100.0,
                    "fuel_kg_sailing": 10.0,
                    "hoteling_requested": True,
                    "hoteling_included": False,
                    "hoteling_exclusion_reason": "included_in_transport_work_intensity",
                    "hoteling_fuel_kg": 0.0,
                    "port_ops_fuel_kg": 0.0,
                    "port_ops_cost": 0.0,
                    "port_ops_co2e": 0.0,
                    "port_ops_source_level": "unavailable",
                    "port_ops_has_unavailable": True,
                    "port_ops": {
                        "source_level": "unavailable",
                        "has_unavailable_port_ops": True,
                        "missing_value_policy": "unavailable_values_excluded_from_numeric_totals_with_warning",
                    },
                },
            },
        }

        rows = {row["Leg"]: row for row in _legs_table(results).to_dict("records")}

        self.assertEqual(rows["Port ops"]["Cost estimate"], "Unavailable")
        self.assertEqual(rows["Port ops"]["TTW CO2e"], "Unavailable")
        self.assertEqual(rows["Hoteling"]["Cost estimate"], "Excluded")
        self.assertEqual(rows["Hoteling"]["TTW CO2e"], "Excluded")
        self.assertEqual(rows["Hoteling"]["Data source"], "Already covered by MRV transport-work intensity")

    def test_port_call_breakdown_table_is_compact_and_readable(self) -> None:
        results = {
            "multimodal": {
                "sea": {
                    "port_ops": {
                        "port_call_breakdown": [
                            {
                                "port_name": "Porto A",
                                "activity_value": 1.0,
                                "activity_unit": "teu",
                                "fuel_kg": 4.0,
                                "co2e_kg": 12.6,
                                "source_level": "observed",
                                "fuel_resolution": {"basis": "port_specific_observed_intensity"},
                            },
                            {
                                "port_name": "Porto B",
                                "activity_value": 1.0,
                                "activity_unit": "teu",
                                "fuel_kg": None,
                                "co2e_kg": None,
                                "source_level": "unavailable",
                                "warning": "No defensible port-operation value is available.",
                            },
                        ]
                    }
                }
            }
        }

        table = _port_call_breakdown_table(results)
        rows = table.to_dict("records")

        self.assertEqual(rows[0]["Source"], "Observed port-specific data")
        self.assertEqual(rows[1]["Source"], "Unavailable / not included without defensible data")
        self.assertEqual(rows[1]["Fuel"], "Unavailable")
        self.assertEqual(rows[1]["CO2e"], "Unavailable")

    def test_selected_corridor_sublegs_table_is_compact_and_readable(self) -> None:
        results = {
            "multimodal": {
                "sea": {
                    "selected_corridor_sublegs": [
                        {
                            "origin_port": "Porto A",
                            "destination_port": "Porto C",
                            "distance_nm": 100.0,
                            "distance_source": "sea_matrix",
                            "observed_cargo_t": 100.0,
                            "fuel_g_per_tnm": 8.0,
                            "applied_pair_intensity_g_per_tnm": 9.0,
                            "observed_corridor_fuel_g_per_tnm": 8.0,
                            "scenario_intensity_source": (
                                "antaq_mrv_same_od_transport_work_weighted_mean"
                            ),
                            "observed_corridor_intensity_source": "eu_mrv_imo_latest",
                            "observed_fuel_kg": 80.0,
                            "scenario_fuel_kg": 11.2,
                        },
                        {
                            "origin_port": "Porto C",
                            "destination_port": "Porto B",
                            "distance_nm": 50.0,
                            "observed_cargo_t": 60.0,
                            "fuel_g_per_tnm": 6.0,
                            "applied_pair_intensity_g_per_tnm": 9.0,
                            "observed_corridor_fuel_g_per_tnm": 6.0,
                            "scenario_intensity_source": (
                                "antaq_mrv_same_od_transport_work_weighted_mean"
                            ),
                            "observed_corridor_intensity_source": (
                                "eu_mrv_vessel_class_trimmed_mean_1pct"
                            ),
                            "intensity_source_counts": {
                                "eu_mrv_vessel_class_trimmed_mean_1pct": 1,
                            },
                            "observed_fuel_kg": 18.0,
                            "scenario_fuel_kg": 4.2,
                        },
                    ]
                }
            }
        }

        rows = _selected_corridor_sublegs_table(results).to_dict("records")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["From port"], "Porto A")
        self.assertEqual(rows[0]["To port"], "Porto C")
        self.assertEqual(rows[0]["Distance"], "100 nm")
        self.assertEqual(rows[0]["Distance source"], "Sea matrix")
        self.assertEqual(rows[0]["ANTAQ cargo aboard"], "100 t")
        self.assertEqual(rows[0]["Applied OD intensity"], "9.00 g/(t·nm)")
        self.assertEqual(
            rows[0]["Selected-corridor observed intensity"],
            "8.00 g/(t·nm)",
        )
        self.assertEqual(
            rows[0]["Applied intensity basis"],
            "ANTAQ + EU MRV same-OD transport-work-weighted mean",
        )
        self.assertEqual(
            rows[0]["Observed intensity basis"],
            "EU MRV latest record by IMO",
        )
        self.assertEqual(rows[0]["Observed fuel"], "80.0 kg")
        self.assertEqual(rows[0]["Scenario-attributed fuel"], "11.2 kg")
        self.assertEqual(
            rows[1]["Applied intensity basis"],
            "ANTAQ + EU MRV same-OD transport-work-weighted mean",
        )
        self.assertEqual(
            rows[1]["Observed intensity basis"],
            "EU MRV vessel-class 1% trimmed mean",
        )

    def test_selected_corridor_sublegs_table_preserves_legacy_empty_state(self) -> None:
        results = {"multimodal": {"sea": {}}}

        self.assertTrue(_selected_corridor_sublegs_table(results).empty)


if __name__ == "__main__":
    unittest.main()
