import unittest

from modules.fuel.emissions import estimate_fuel_emissions, get_ef_kg_per_kg


class FuelEmissionsTests(unittest.TestCase):
    def test_vlsfo_uses_selected_ttw_factor(self) -> None:
        self.assertAlmostEqual(get_ef_kg_per_kg("vlsfo"), 3.114)
        self.assertAlmostEqual(get_ef_kg_per_kg("VLSFO 0.5"), 3.114)

        result = estimate_fuel_emissions(fuel_mass_kg=10.0, fuel_type="vlsfo")

        self.assertAlmostEqual(result["ef_kg_per_kg"], 3.114)
        self.assertAlmostEqual(result["co2e_kg"], 31.14)


if __name__ == "__main__":
    unittest.main()
