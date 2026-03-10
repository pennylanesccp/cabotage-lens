import unittest
from unittest.mock import patch

from app.main.sidebar.filters import route_endpoint_options


class SidebarFiltersTests(unittest.TestCase):
    def test_route_endpoint_options_uses_same_cached_places_as_main_page(self) -> None:
        with patch(
            "app.main.sidebar.filters._db_route_place_names",
            return_value=["Manaus, AM", "Belem, PA"],
        ):
            options = route_endpoint_options(
                current_values=[" Pelotas, RS ", "", "-23.55, -46.63"],
            )

        self.assertEqual(options, ["Belem, PA", "Manaus, AM", "Pelotas, RS"])


if __name__ == "__main__":
    unittest.main()
