import contextlib
import unittest
from unittest.mock import patch

from app.main.sidebar.filters import route_endpoint_options, route_origin_options


class SidebarFiltersTests(unittest.TestCase):
    def test_route_origin_options_use_distinct_cached_origins(self) -> None:
        with patch(
            "app.main.sidebar.filters._db_route_origin_names",
            return_value=["Manaus, AM", "Belem, PA"],
        ):
            options = route_origin_options(
                current_values=[" Pelotas, RS ", "", "-23.55, -46.63"],
            )

        self.assertEqual(options, ["Belem, PA", "Manaus, AM", "Pelotas, RS"])

    def test_route_endpoint_options_uses_cached_places_for_destiny(self) -> None:
        with patch(
            "app.main.sidebar.filters._db_route_place_names",
            return_value=["Manaus, AM", "Belem, PA"],
        ):
            options = route_endpoint_options(
                current_values=[" Pelotas, RS ", "", "-23.55, -46.63"],
            )

        self.assertEqual(options, ["Belem, PA", "Manaus, AM", "Pelotas, RS"])

    def test_custom_location_resolution_uses_routes_table_before_ors(self) -> None:
        with patch(
            "app.main.sidebar.filters.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "app.main.sidebar.filters.find_place_point",
            return_value={
                "label": "Avenida Professor Luciano Gualberto, Sao Paulo",
                "lat": -23.558808,
                "lon": -46.730357,
                "role": "origin",
            },
        ), patch(
            "app.main.sidebar.filters.resolve_point_null_safe",
        ) as resolve_mock:
            from app.main.sidebar.filters import _resolve_custom_location_label

            label, error = _resolve_custom_location_label("Avenida Professor Luciano Gualberto, Sao Paulo")

        self.assertEqual(label, "Avenida Professor Luciano Gualberto, Sao Paulo")
        self.assertIsNone(error)
        resolve_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
