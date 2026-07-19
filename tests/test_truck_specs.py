import unittest

from modules.fuel.truck_specs import (
    AUTO_BY_WEIGHT_TRUCK_KEY,
    baseline_km_per_l_from_axles,
    resolve_truck_spec_for_cargo,
)


class AutoByWeightTruckSpecTests(unittest.TestCase):
    def test_auto_by_weight_selects_the_documented_axle_ranges(self) -> None:
        cases = [
            (18.0, 5, "semi_27t", 27.0, 2.3),
            (18.1, 6, "carreta_6ax_30t", 30.0, 2.0),
            (30.1, 7, "bitrain_7ax_36t", 36.0, 2.0),
            (40.1, 9, "rodotrem_9ax_48t", 48.0, 2.0),
        ]

        for cargo_t, axles, resolved_key, payload_t, km_per_liter in cases:
            with self.subTest(cargo_t=cargo_t):
                spec = resolve_truck_spec_for_cargo(
                    cargo_t,
                    AUTO_BY_WEIGHT_TRUCK_KEY,
                )

                self.assertEqual(spec["selection_mode"], AUTO_BY_WEIGHT_TRUCK_KEY)
                self.assertEqual(spec["axles"], axles)
                self.assertEqual(spec["resolved_key"], resolved_key)
                self.assertEqual(spec["payload_t"], payload_t)
                self.assertEqual(spec["ref_weight_t"], payload_t)
                self.assertEqual(baseline_km_per_l_from_axles(axles), km_per_liter)


if __name__ == "__main__":
    unittest.main()
