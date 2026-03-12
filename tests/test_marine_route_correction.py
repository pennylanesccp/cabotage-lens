import unittest
from unittest.mock import patch

from app.main.map.routing.marine_route_builder import build_marine_route_polyline
from app.main.map.routing.marine_master_route import MarineRoutePort


class MarineRouteCorrectionTests(unittest.TestCase):
    def test_rendered_path_chains_one_arc_per_port_leg(self) -> None:
        port_a = MarineRoutePort(name="Port A", key="port-a", latlon=(0.0, 0.0))
        port_b = MarineRoutePort(name="Port B", key="port-b", latlon=(0.0, 2.0))
        port_c = MarineRoutePort(name="Port C", key="port-c", latlon=(0.0, 4.0))

        with patch(
            "app.main.map.routing.marine_route_builder.build_leg_reference_path",
            side_effect=[
                [port_a.latlon, (0.75, 1.0), port_b.latlon],
                [port_b.latlon, (0.75, 3.0), port_c.latlon],
            ],
        ), patch(
            "app.main.map.routing.marine_route_builder.resolve_master_route_slice",
            return_value=[port_a, port_b, port_c],
        ), patch(
            "app.main.map.routing.marine_route_builder._peer_port_latlons",
            return_value=(port_a.latlon, port_b.latlon, port_c.latlon),
        ):
            points = build_marine_route_polyline(
                origin_port_name="Port A",
                dest_port_name="Port C",
                origin_latlon=port_a.latlon,
                dest_latlon=port_c.latlon,
                n_points=33,
            )

        self.assertEqual(len(points), 65)
        self.assertEqual(points[0], [0.0, 0.0])
        self.assertEqual(points[-1], [4.0, 0.0])
        self.assertEqual(sum(1 for point in points if point == [2.0, 0.0]), 1)
        self.assertNotIn([1.0, 0.75], points[1:-1])
        self.assertNotIn([3.0, 0.75], points[1:-1])
        self.assertTrue(any(point[1] > 0.0 for point in points[1:-1]))

    def test_amazon_reference_corridor_keeps_intermediate_ports(self) -> None:
        port_a = MarineRoutePort(name="Porto de Belem", key="porto-de-belem", latlon=(-1.4558, -48.5039))
        port_b = MarineRoutePort(name="Porto de Santarem", key="porto-de-santarem", latlon=(-2.4220, -54.7190))
        port_c = MarineRoutePort(name="Porto de Manaus", key="porto-de-manaus", latlon=(-3.1567, -60.0079))

        with patch(
            "app.main.map.routing.marine_route_builder.build_leg_reference_path",
            side_effect=[
                [port_a.latlon, (-0.0988306, -49.7292619), port_b.latlon],
                [port_b.latlon, (-2.1728258, -56.1543641), port_c.latlon],
            ],
        ), patch(
            "app.main.map.routing.marine_route_builder.resolve_master_route_slice",
            return_value=[port_a, port_b, port_c],
        ), patch(
            "app.main.map.routing.marine_route_builder._peer_port_latlons",
            return_value=(port_a.latlon, port_b.latlon, port_c.latlon),
        ):
            points = build_marine_route_polyline(
                origin_port_name="Porto de Belem",
                dest_port_name="Porto de Manaus",
                origin_latlon=port_a.latlon,
                dest_latlon=port_c.latlon,
                n_points=27,
            )

        self.assertEqual(len(points), 53)
        self.assertEqual(points[0], [port_a.latlon[1], port_a.latlon[0]])
        self.assertEqual(points[-1], [port_c.latlon[1], port_c.latlon[0]])
        self.assertEqual(sum(1 for point in points if point == [port_b.latlon[1], port_b.latlon[0]]), 1)
        self.assertNotIn([-49.7292619, -0.0988306], points[1:-1])
        self.assertNotIn([-56.1543641, -2.1728258], points[1:-1])


if __name__ == "__main__":
    unittest.main()
