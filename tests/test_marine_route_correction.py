import unittest
from unittest.mock import patch

from app.main.map.routing.geometry_utils import point_to_segment_distance_km
from app.main.map.routing.marine_coastal_route import MARITIME_ARC_SAGITTA_KM, build_coastal_leg_points


class MarineRouteCorrectionTests(unittest.TestCase):
    def test_coastal_leg_arc_bulges_north_when_reference_water_is_north(self) -> None:
        with patch(
            "app.main.map.routing.marine_coastal_route.build_leg_reference_path",
            return_value=[(0.6, 0.0), (0.6, 2.0)],
        ):
            points = build_coastal_leg_points(
                origin_port_name="Port A",
                dest_port_name="Port B",
                leg_start_latlon=(0.0, 0.0),
                leg_end_latlon=(0.0, 2.0),
                n_points=51,
            )

        self.assertEqual(len(points), 51)
        self.assertTrue(all(point[0] > 0.0 for point in points))
        self.assertGreater(max(point[0] for point in points), 0.5)
        self.assertTrue(all(points[idx][1] < points[idx + 1][1] for idx in range(len(points) - 1)))

    def test_coastal_leg_arc_bulges_south_when_reference_water_is_south(self) -> None:
        with patch(
            "app.main.map.routing.marine_coastal_route.build_leg_reference_path",
            return_value=[(-0.6, 0.0), (-0.6, 2.0)],
        ):
            points = build_coastal_leg_points(
                origin_port_name="Port A",
                dest_port_name="Port B",
                leg_start_latlon=(0.0, 0.0),
                leg_end_latlon=(0.0, 2.0),
                n_points=51,
            )

        self.assertEqual(len(points), 51)
        self.assertTrue(all(point[0] < 0.0 for point in points))
        self.assertLess(min(point[0] for point in points), -0.5)
        self.assertTrue(all(points[idx][1] < points[idx + 1][1] for idx in range(len(points) - 1)))

    def test_coastal_leg_arc_enforces_sixty_km_sagitta(self) -> None:
        leg_start = (0.0, 0.0)
        leg_end = (0.0, 3.0)

        with patch(
            "app.main.map.routing.marine_coastal_route.build_leg_reference_path",
            return_value=[(0.6, 0.0), (0.6, 3.0)],
        ):
            points = build_coastal_leg_points(
                origin_port_name="Port A",
                dest_port_name="Port B",
                leg_start_latlon=leg_start,
                leg_end_latlon=leg_end,
                n_points=99,
            )

        max_offset_km = max(point_to_segment_distance_km(point, leg_start, leg_end) for point in points)

        self.assertAlmostEqual(max_offset_km, MARITIME_ARC_SAGITTA_KM, delta=1.0)


if __name__ == "__main__":
    unittest.main()
