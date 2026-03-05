import unittest

from modules.multimodal.evaluator import compute_cargo_allocation_share


class CargoAllocationShareTests(unittest.TestCase):
    def test_teu_share_simple_sanity(self) -> None:
        share, debug = compute_cargo_allocation_share(
            inputs={
                "cargo_t": 14.0,
                "cargo_teu": 1,
                "t_per_teu_default": 14.0,
                "allocation_mode": "teu_share",
                "load_factor": 1.0,
            },
            vessel_meta={
                "vessel_class": "container_feeder",
                "size_proxy_t_median": 30_000.0,
                "teu_capacity": 30,
            },
        )

        self.assertAlmostEqual(share, 1.0 / 30.0, places=9)
        self.assertEqual(debug["allocation_mode_used"], "teu_share")
        self.assertEqual(debug["cargo_teu_resolved"], 1)

    def test_teu_share_realistic(self) -> None:
        share, debug = compute_cargo_allocation_share(
            inputs={
                "cargo_t": 42.0,
                "cargo_teu": 3,
                "t_per_teu_default": 14.0,
                "allocation_mode": "teu_share",
                "load_factor": 0.8,
            },
            vessel_meta={
                "vessel_class": "container_feeder",
                "size_proxy_t_median": 30_000.0,
                "teu_capacity": 1600,
            },
        )

        self.assertAlmostEqual(share, 3.0 / 1280.0, places=9)
        self.assertAlmostEqual(float(debug["share_new_teu"]), 3.0 / 1280.0, places=9)

    def test_default_mode_for_container_is_teu_share(self) -> None:
        share, debug = compute_cargo_allocation_share(
            inputs={
                "cargo_t": 28.0,
                "cargo_teu": 2,
                "t_per_teu_default": 14.0,
                "allocation_mode": None,
                "load_factor": 0.8,
            },
            vessel_meta={
                "vessel_class": "container_small",
                "size_proxy_t_median": 20_000.0,
                "teu_capacity": 1000,
            },
        )

        self.assertEqual(debug["allocation_mode_used"], "teu_share")
        self.assertAlmostEqual(share, 2.0 / 800.0, places=9)


if __name__ == "__main__":
    unittest.main()
