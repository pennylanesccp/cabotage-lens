import unittest
from unittest.mock import patch

from app.main.map.routing.marine_route_builder import build_marine_route_polyline


class MarineRouteCorrectionTests(unittest.TestCase):
    def test_rendered_path_is_single_arc_not_reference_waypoints(self) -> None:
        origin = (0.0, 0.0)
        dest = (0.0, 2.0)
        reference_path = [
            origin,
            (0.75, 0.55),
            (0.85, 1.45),
            dest,
        ]

        with patch(
            "app.main.map.routing.marine_route_builder.build_leg_reference_path",
            return_value=reference_path,
        ), patch(
            "app.main.map.routing.marine_route_builder._peer_port_latlons",
            return_value=(origin, dest, (1.0, 1.0)),
        ):
            points = build_marine_route_polyline(
                origin_port_name="Port A",
                dest_port_name="Port B",
                origin_latlon=origin,
                dest_latlon=dest,
                n_points=33,
            )

        self.assertEqual(len(points), 33)
        self.assertEqual(points[0], [0.0, 0.0])
        self.assertEqual(points[-1], [2.0, 0.0])
        self.assertNotIn([0.55, 0.75], points[1:-1])
        self.assertNotIn([1.45, 0.85], points[1:-1])
        self.assertTrue(any(point[1] > 0.0 for point in points[1:-1]))

    def test_amazon_reference_corridor_still_renders_as_single_arc(self) -> None:
        origin = (-1.4558, -48.5039)
        dest = (-3.1567, -60.0079)
        reference_path = [
            origin,
            (-0.0988306, -49.7292619),
            (-2.4220, -54.7190),
            (-2.1728258, -56.1543641),
            dest,
        ]

        with patch(
            "app.main.map.routing.marine_route_builder.build_leg_reference_path",
            return_value=reference_path,
        ), patch(
            "app.main.map.routing.marine_route_builder._peer_port_latlons",
            return_value=(origin, dest, (-2.4220, -54.7190)),
        ):
            points = build_marine_route_polyline(
                origin_port_name="Porto de Belem",
                dest_port_name="Porto de Manaus",
                origin_latlon=origin,
                dest_latlon=dest,
                n_points=55,
            )

        self.assertEqual(len(points), 55)
        self.assertEqual(points[0], [origin[1], origin[0]])
        self.assertEqual(points[-1], [dest[1], dest[0]])
        self.assertNotIn([-49.7292619, -0.0988306], points[1:-1])
        self.assertNotIn([-54.7190, -2.4220], points[1:-1])


if __name__ == "__main__":
    unittest.main()
