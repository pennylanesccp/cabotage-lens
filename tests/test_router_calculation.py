import unittest
from unittest.mock import Mock, call

from modules.road.ors.structures import NoRoute, ORSError
from modules.road.router import _calculate_route


class RouterCalculationTests(unittest.TestCase):
    def test_calculate_route_falls_back_to_car_only_when_no_route_exists(self) -> None:
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

    def test_calculate_route_does_not_fallback_to_car_on_transient_provider_error(self) -> None:
        ors = Mock()
        ors.route_road.side_effect = ORSError("timeout")

        with self.assertRaises(ORSError):
            _calculate_route(
                ors,
                {"lat": -23.5, "lon": -46.6},
                {"lat": -23.9, "lon": -46.3},
                "driving-hgv",
                True,
            )

        self.assertEqual(ors.route_road.call_count, 1)


if __name__ == "__main__":
    unittest.main()
