import unittest

from calcs.migrate_normalized_cache_and_bulk import _find_port, _port_lookup, _selector_from_legacy_row, _synthetic_run_id


class NormalizedMigrationTests(unittest.TestCase):
    def test_selector_from_legacy_row_uses_origin_location_id(self) -> None:
        selector = _selector_from_legacy_row(
            {
                "cargo_t": 30.0,
                "truck_key": "semi_27t",
                "ors_profile": "driving-hgv",
                "vessel_class": "container_small",
                "include_hoteling": True,
                "hoteling_hours_per_call": 14.0,
                "port_calls": 2,
                "include_port_ops": True,
                "t_per_teu_default": 14.0,
                "allocation_load_factor": 0.8,
                "full_call_mode": False,
                "port_ops_scenario": "baseline",
                "destination_set_id": "city_dests_over50k.txt",
            },
            origin_location_id=17,
        )

        self.assertEqual(selector.origin_location_id, 17)
        self.assertEqual(selector.truck_key, "semi_27t")
        self.assertEqual(selector.destination_set_id, "city_dests_over50k.txt")

    def test_synthetic_run_id_is_stable_for_same_selector_payload(self) -> None:
        row = {
            "origin_name": "Pelotas, RS",
            "input_origin": "Pelotas, RS",
            "cargo_t": 30.0,
            "truck_key": "semi_27t",
            "ors_profile": "driving-hgv",
            "vessel_class": "container_small",
            "include_hoteling": True,
            "hoteling_hours_per_call": 14.0,
            "port_calls": 2,
            "include_port_ops": True,
            "t_per_teu_default": 14.0,
            "allocation_load_factor": 0.8,
            "full_call_mode": False,
            "port_ops_scenario": "baseline",
            "destination_set_id": "city_dests_over50k.txt",
        }

        self.assertEqual(_synthetic_run_id(row, origin_location_id=17), _synthetic_run_id(row, origin_location_id=17))

    def test_port_lookup_matches_port_aliases(self) -> None:
        lookup = _port_lookup()
        self.assertIsNotNone(_find_port(lookup, "Porto de Santos"))


if __name__ == "__main__":
    unittest.main()
