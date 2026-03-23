import unittest

from app.main.utils.pipeline import build_scenario_payload


class MainPipelineTests(unittest.TestCase):
    def test_build_scenario_payload_forces_hgv_profile(self) -> None:
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

        self.assertEqual(payload["ors_profile"], "driving-hgv")


if __name__ == "__main__":
    unittest.main()
