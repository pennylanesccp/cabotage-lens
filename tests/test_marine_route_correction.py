import unittest
from unittest.mock import patch

from app.main.map.routing.marine_coastal_route import build_coastal_leg_points
from app.main.map.routing.marine_river_route import build_river_leg_points


class MarineRouteCorrectionTests(unittest.TestCase):
    def test_coastal_leg_builds_corridor_based_curve(self) -> None:
        with patch(
            "app.main.map.routing.marine_coastal_route.build_leg_reference_path",
            return_value=[
                (0.0, 0.0),
                (0.4, 0.8),
                (0.5, 1.6),
                (0.0, 2.0),
            ],
        ):
            points = build_coastal_leg_points(
                origin_port_name="Port A",
                dest_port_name="Port B",
                leg_start_latlon=(0.0, 0.0),
                leg_end_latlon=(0.0, 2.0),
                n_points=41,
            )

        self.assertGreaterEqual(len(points), 41)
        self.assertTrue(any(point[0] > 0.1 for point in points))
        self.assertGreater(points[-1][1], points[0][1])
        self.assertGreater(max(point[1] for point in points) - min(point[1] for point in points), 1.0)

    def test_river_leg_uses_same_port_arc_logic(self) -> None:
        with patch(
            "app.main.map.routing.marine_river_route.build_river_leg_anchor_path",
            return_value=[
                (-3.16, -60.00),
                (-3.10, -59.60),
                (-2.95, -58.70),
                (-2.75, -57.50),
            ],
        ):
            points = build_river_leg_points(
                origin_port_name="Porto de Manaus",
                dest_port_name="Porto de Santarem",
                leg_start_latlon=(-3.16, -60.00),
                leg_end_latlon=(-2.75, -57.50),
                n_points=41,
            )

        self.assertGreaterEqual(len(points), 41)
        self.assertTrue(any(point[1] > -59.8 for point in points))
        self.assertGreater(points[-1][1], points[0][1])


if __name__ == "__main__":
    unittest.main()
