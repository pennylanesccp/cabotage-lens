import unittest
from unittest.mock import patch

from modules.fuel.truck_specs import AUTO_BY_WEIGHT_TRUCK_KEY
from modules.multimodal.gustavo_benchmark import (
    WorkbookBenchmarkPair,
    _evaluate_pair,
    compare_gustavo_pairs_with_model,
)


class GustavoBenchmarkTests(unittest.TestCase):
    def test_batch_prepares_context_with_automatic_truck_selection(self):
        pair = WorkbookBenchmarkPair(
            origin_city="Manaus",
            destiny_city="Fortaleza",
            origin_query="Manaus, AM",
            destiny_query="Fortaleza, CE",
            workbook_road_kg_co2e_per_container=100.0,
            workbook_cabotage_kg_co2e_per_container=50.0,
            workbook_savings_pct=50.0,
        )

        with (
            patch(
                "modules.multimodal.gustavo_benchmark.load_routing_assets",
                return_value=(object(), [], {}, None),
            ),
            patch(
                "modules.multimodal.gustavo_benchmark.prepare_evaluation_context",
                return_value=object(),
            ) as prepare_context,
            patch(
                "modules.multimodal.gustavo_benchmark._evaluate_pair",
                return_value={"model_savings_pct": 50.0},
            ),
        ):
            rows = compare_gustavo_pairs_with_model([pair])

        self.assertEqual(rows[0]["status"], "ok")
        self.assertEqual(
            prepare_context.call_args.kwargs["truck_key"],
            AUTO_BY_WEIGHT_TRUCK_KEY,
        )

    def test_pair_passes_automatic_truck_selection_to_evaluator(self):
        pair = WorkbookBenchmarkPair(
            origin_city="Manaus",
            destiny_city="Fortaleza",
            origin_query="Manaus, AM",
            destiny_query="Fortaleza, CE",
            workbook_road_kg_co2e_per_container=100.0,
            workbook_cabotage_kg_co2e_per_container=50.0,
            workbook_savings_pct=50.0,
        )
        point = {"label": "point"}
        geometry = {
            "status": "ok",
            "origin": {"label": "Manaus, AM"},
            "destiny": {"label": "Fortaleza, CE"},
            "port_origin": {"name": "Porto de Manaus"},
            "port_destiny": {"name": "Porto de Fortaleza"},
            "road_direct": {"distance_km": 10.0},
            "sea_leg": {"distance_km": 20.0},
        }
        evaluation = {
            "road_only": {
                "co2e": 100.0,
                "cost": 10.0,
                "trips": 1,
                "liters": 1.0,
                "km_per_liter": 2.3,
            },
            "multimodal": {
                "total_co2e": 50.0,
                "total_cost": 5.0,
                "first_mile": {
                    "distance_km": 1.0,
                    "trips": 1,
                    "liters": 0.1,
                    "km_per_liter": 2.3,
                    "co2e": 1.0,
                },
                "last_mile": {
                    "distance_km": 1.0,
                    "trips": 1,
                    "liters": 0.1,
                    "km_per_liter": 2.3,
                    "co2e": 1.0,
                },
                "sea": {
                    "fuel_kg_sailing": 10.0,
                    "fuel_kg": 10.0,
                    "fuel_kg_marine": 10.0,
                    "hoteling_fuel_kg": 0.0,
                    "port_ops_fuel_kg": 0.0,
                    "port_ops_co2e": 0.0,
                    "co2e_marine": 48.0,
                    "port_ops": {"totals": {}},
                },
            },
            "inputs": {
                "road_vehicle": {},
                "marine_ef_kg_per_kg": 3.0,
            },
        }

        with (
            patch(
                "modules.multimodal.gustavo_benchmark._resolve_benchmark_point",
                return_value=point,
            ),
            patch(
                "modules.multimodal.gustavo_benchmark.build_path_geometry_from_resolved",
                return_value=geometry,
            ),
            patch(
                "modules.multimodal.gustavo_benchmark.evaluate_path",
                return_value=evaluation,
            ) as evaluate_path,
        ):
            _evaluate_pair(
                pair,
                ors=object(),
                ports=[],
                sea_matrix={},
                db_path=None,
                point_cache={},
                prepared_context=object(),
                cargo_t=14.0,
                cargo_teu=1.0,
                t_per_teu_default=14.0,
                allocation_load_factor=0.8,
                include_hoteling=True,
                hoteling_hours_per_call=14.0,
                port_calls=2,
                include_port_ops=True,
                full_call_mode=False,
                port_ops_scenario="santos_diesel_heavy",
                vessel_class="container_feeder",
            )

        self.assertEqual(
            evaluate_path.call_args.kwargs["truck_key"],
            AUTO_BY_WEIGHT_TRUCK_KEY,
        )


if __name__ == "__main__":
    unittest.main()
