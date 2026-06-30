import unittest
from unittest.mock import patch

from app.main.utils.pipeline import build_scenario_payload, run_analysis


class MainPipelineTests(unittest.TestCase):
    def test_build_scenario_payload_forces_car_profile(self) -> None:
        payload = build_scenario_payload(
            {
                "origin": "Sao Paulo, SP",
                "destiny": "Manaus, AM",
                "cargo_t": 30.0,
                "truck_key": "semi_27t",
                "profile": "driving-car",
                "allocation_mode": "auto",
                "allocation_load_factor": 0.8,
            }
        )

        self.assertEqual(payload["ors_profile"], "driving-car")
        self.assertNotIn("port_ops_observed_ports", payload)

    def test_build_scenario_payload_preserves_optional_observed_port_ops(self) -> None:
        observed = [{"port_name": "Porto A", "fuel_kg": 10.0, "cargo_teu": 2.0}]
        payload = build_scenario_payload(
            {
                "origin": "Sao Paulo, SP",
                "destiny": "Manaus, AM",
                "cargo_t": 30.0,
                "truck_key": "semi_27t",
                "allocation_mode": "auto",
                "allocation_load_factor": 0.8,
                "port_ops_observed_ports": observed,
            }
        )

        self.assertIs(payload["port_ops_observed_ports"], observed)

    def test_run_analysis_passes_optional_observed_port_ops_to_evaluator(self) -> None:
        observed = [{"port_name": "Porto A", "fuel_kg": 10.0, "cargo_teu": 2.0}]
        payload = {
            "origin": "Sao Paulo, SP",
            "destiny": "Manaus, AM",
            "cargo_t": 14.0,
            "cargo_teu": 1.0,
            "t_per_teu_default": 14.0,
            "allocation_mode": None,
            "allocation_load_factor": 0.8,
            "truck_key": "semi_27t",
            "ors_profile": "driving-car",
            "overwrite_road": False,
            "vessel_class": "container_feeder",
            "include_hoteling": True,
            "hoteling_hours_per_call": 14.0,
            "port_calls": 2,
            "include_port_ops": True,
            "full_call_mode": False,
            "port_moves_per_call": None,
            "port_ops_scenario": "santos_diesel_heavy",
            "port_ops_observed_ports": observed,
        }
        geo = {
            "status": "ok",
            "origin": {"label": "Sao Paulo, SP"},
            "destiny": {"label": "Manaus, AM"},
            "road_direct": {"source": "cache", "distance_km": 1.0},
            "first_mile": {"source": "cache"},
            "last_mile": {"source": "cache"},
            "sea_leg": {"distance_km": 2.0},
        }
        result = {
            "comparison": {},
            "road_only": {"co2e": 100.0},
            "multimodal": {"total_co2e": 50.0},
        }

        with patch("app.main.utils.pipeline.resolve_runtime_db_target", return_value="local"), patch(
            "app.main.utils.pipeline.build_path_geometry",
            return_value=geo,
        ), patch(
            "app.main.utils.pipeline.evaluate_path",
            return_value=result,
        ) as evaluate_mock:
            returned_geo, returned_results, error, db_target = run_analysis(payload)

        self.assertIs(returned_geo, geo)
        self.assertIs(returned_results, result)
        self.assertIsNone(error)
        self.assertEqual(db_target, "local")
        self.assertIs(evaluate_mock.call_args.kwargs["port_ops_observed_ports"], observed)


if __name__ == "__main__":
    unittest.main()
