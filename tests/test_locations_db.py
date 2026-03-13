import unittest
from unittest.mock import patch

from modules.infra.db.locations import coord_lookup_key, normalize_coordinate, upsert_alias_point


class LocationsRepositoryTests(unittest.TestCase):
    def test_coordinate_normalization_rounds_to_six_decimals(self) -> None:
        self.assertEqual(str(normalize_coordinate(-23.55052041)), "-23.550520")
        self.assertEqual(coord_lookup_key(-23.55052041, -46.63330891), ("-23.550520", "-46.633309"))

    def test_duplicate_geocoding_labels_map_to_same_canonical_location(self) -> None:
        fake_point = {"location_id": 11, "label": "Pelotas, RS", "lat": -31.770000, "lon": -52.340000}

        with patch(
            "modules.infra.db.locations.get_or_create_location",
            return_value={"location_id": 11},
        ) as get_location_mock, patch(
            "modules.infra.db.locations.upsert_alias",
            return_value=fake_point,
        ) as upsert_alias_mock:
            point_a = upsert_alias_point(
                object(),
                place="Pelotas, RS",
                label="Pelotas, RS",
                lat=-31.7700001,
                lon=-52.3400001,
            )
            point_b = upsert_alias_point(
                object(),
                place="Pelotas, Rio Grande do Sul",
                label="Pelotas, Rio Grande do Sul",
                lat=-31.7700004,
                lon=-52.3400004,
            )

        self.assertEqual(point_a["location_id"], 11)
        self.assertEqual(point_b["location_id"], 11)
        self.assertEqual(get_location_mock.call_count, 2)
        first_call = get_location_mock.call_args_list[0].kwargs
        second_call = get_location_mock.call_args_list[1].kwargs
        self.assertEqual(coord_lookup_key(first_call["lat"], first_call["lon"]), coord_lookup_key(second_call["lat"], second_call["lon"]))
        self.assertGreaterEqual(upsert_alias_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
