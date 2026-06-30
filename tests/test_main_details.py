import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main.details.breakdown import _legs_table, _port_call_breakdown_table
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
                    },
                }
            },
        }

        table = _assumptions_table(results=results, payload={"port_ops_scenario": "santos_diesel_heavy"})
        rows = {row["Parameter"]: row for row in table.to_dict("records")}

        self.assertIn("Port ops scenario", rows)
        self.assertEqual(rows["Port ops data source"]["Value"], "Estimated from weighted average of observed ports")
        self.assertIn("Observed port-specific data: 1", rows["Port ops coverage"]["Value"])
        self.assertIn("observed records available: 2", rows["Port ops coverage"]["Value"])
        self.assertIn("fallback denominator: teu", rows["Port ops fallback basis"]["Value"])
        self.assertIn("Port-specific observed", rows["Port ops warning"]["Value"])
        self.assertEqual(rows["Hoteling data source"]["Value"], "Documented model default")
        self.assertIn("MRV class rate", rows["Hoteling basis"]["Value"])
        self.assertIn("Already covered", rows["Hoteling exclusion reason"]["Value"])

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


if __name__ == "__main__":
    unittest.main()
