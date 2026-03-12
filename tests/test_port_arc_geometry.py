import math
import unittest

from app.main.map.routing.marine_master_route import load_master_route_ports
from app.main.map.routing.water_validation import build_leg_reference_path
from modules.plot.maritime_arc_geometry import (
    CENTRAL_ANGLE_RADIANS,
    build_port_to_port_arc,
    compute_candidate_arc_centers,
    sample_circular_arc,
)


class PortArcGeometryTests(unittest.TestCase):
    def test_candidate_centers_form_sixty_degree_isosceles_triangle(self) -> None:
        construction = compute_candidate_arc_centers((0.0, 0.0), (0.0, 1.0))

        self.assertGreater(construction.radius_km, 0.0)
        self.assertAlmostEqual(construction.radius_km, self._distance(construction.port_a_xy, construction.port_b_xy), places=6)

        for center_xy in (construction.center_a_xy, construction.center_b_xy):
            radius_a = self._distance(center_xy, construction.port_a_xy)
            radius_b = self._distance(center_xy, construction.port_b_xy)
            self.assertAlmostEqual(radius_a, construction.radius_km, places=6)
            self.assertAlmostEqual(radius_b, construction.radius_km, places=6)

            vec_a = (
                construction.port_a_xy[0] - center_xy[0],
                construction.port_a_xy[1] - center_xy[1],
            )
            vec_b = (
                construction.port_b_xy[0] - center_xy[0],
                construction.port_b_xy[1] - center_xy[1],
            )
            dot = (vec_a[0] * vec_b[0]) + (vec_a[1] * vec_b[1])
            angle = math.acos(dot / (radius_a * radius_b))
            self.assertAlmostEqual(angle, CENTRAL_ANGLE_RADIANS, places=6)

    def test_sampled_arc_preserves_requested_endpoints(self) -> None:
        construction = compute_candidate_arc_centers((0.0, 0.0), (0.0, 1.0))
        points = sample_circular_arc(
            (0.0, 0.0),
            (0.0, 1.0),
            construction.center_a_latlon,
            n_points=17,
        )

        self.assertEqual(len(points), 17)
        self.assertEqual(points[0], (0.0, 0.0))
        self.assertEqual(points[-1], (0.0, 1.0))

    def test_reference_path_controls_arc_bulge_side(self) -> None:
        geometry = build_port_to_port_arc(
            (0.0, 0.0),
            (0.0, 2.0),
            reference_path_latlon=[(0.0, 0.0), (0.8, 1.0), (0.0, 2.0)],
            n_points=41,
        )

        self.assertEqual(len(geometry.arc_points_latlon), 41)
        self.assertAlmostEqual(geometry.central_angle_radians, CENTRAL_ANGLE_RADIANS, places=9)
        self.assertGreater(geometry.midpoint_latlon[0], 0.0)

    def test_santos_to_sao_sebastiao_bends_offshore(self) -> None:
        ports = {port.name: port.latlon for port in load_master_route_ports()}
        origin = ports["Porto de Santos"]
        dest = ports["Porto de Sao Sebastiao"]
        reference_path = build_leg_reference_path(
            origin_port_name="Porto de Santos",
            dest_port_name="Porto de Sao Sebastiao",
            origin_latlon=origin,
            dest_latlon=dest,
        )
        geometry = build_port_to_port_arc(
            origin,
            dest,
            reference_path_latlon=reference_path,
            clutter_points_latlon=tuple(ports.values()),
            n_points=61,
        )

        self.assertGreater(geometry.midpoint_latlon[1], max(origin[1], dest[1]))
        self.assertAlmostEqual(geometry.central_angle_radians, CENTRAL_ANGLE_RADIANS, places=9)

    @staticmethod
    def _distance(a_xy: tuple[float, float], b_xy: tuple[float, float]) -> float:
        return math.hypot(a_xy[0] - b_xy[0], a_xy[1] - b_xy[1])


if __name__ == "__main__":
    unittest.main()
