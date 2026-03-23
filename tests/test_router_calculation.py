import unittest
from unittest.mock import Mock, call

from modules.road.ors.structures import NoRoute, ORSError
from modules.road.router import _calculate_route


class RouterCalculationTests(unittest.TestCase):
    def test_calculate_route_falls_back_to_car_when_hgv_has_no_route(self) -> None:
        ors = Mock()
        ors.route_road.side_effect = [
            NoRoute("No route for hgv"),
            {
                "distance_m": 1200.0,
                "duration_s": 180.0,
                "profile_used": "driving-car",
                "source": "ors",
            },
        ]

        profile_used, distance_km, route_source = _calculate_route(
            ors,
            {"lat": -23.5, "lon": -46.6},
            {"lat": -23.9, "lon": -46.3},
            "driving-hgv",
            True,
        )

        self.assertEqual(profile_used, "driving-car")
        self.assertAlmostEqual(distance_km or 0.0, 1.2)
        self.assertEqual(route_source, "ors")
        self.assertEqual(
            ors.route_road.call_args_list,
            [
                call({"lat": -23.5, "lon": -46.6}, {"lat": -23.9, "lon": -46.3}, profile="driving-hgv"),
                call({"lat": -23.5, "lon": -46.6}, {"lat": -23.9, "lon": -46.3}, profile="driving-car"),
            ],
        )

    def test_calculate_route_falls_back_to_car_when_hgv_request_errors(self) -> None:
        ors = Mock()
        ors.route_road.side_effect = [
            ORSError("timeout"),
            {
                "distance_m": 2400.0,
                "duration_s": 240.0,
                "profile_used": "driving-car",
                "source": "ors",
            },
        ]

        profile_used, distance_km, route_source = _calculate_route(
            ors,
            {"lat": -23.5, "lon": -46.6},
            {"lat": -23.9, "lon": -46.3},
            "driving-hgv",
            True,
        )

        self.assertEqual(profile_used, "driving-car")
        self.assertAlmostEqual(distance_km or 0.0, 2.4)
        self.assertEqual(route_source, "ors")
        self.assertEqual(ors.route_road.call_count, 2)


if __name__ == "__main__":
    unittest.main()
