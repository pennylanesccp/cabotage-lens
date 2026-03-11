import math
import unittest

from modules.plot.port_arc_geometry import (
    ARC_VISIBLE_ANGLE_RAD,
    compute_adaptive_arc_radius,
    generate_port_arc_geometry,
    get_local_corridor_context,
    infer_water_direction_from_polygon,
)


class PortArcGeometryTests(unittest.TestCase):
    def test_visible_angle_is_fixed_ten_percent(self) -> None:
        geometry = generate_port_arc_geometry(
            port_name="Port A",
            port_latlon=(0.0, 0.0),
            corridor_latlon=[(0.0, 1.0), (0.0, 2.0), (0.0, 3.0)],
            peer_port_latlons=[(0.0, 0.0), (0.0, 5.0), (3.0, 0.0)],
        )

        self.assertAlmostEqual(geometry.visible_angle_rad, ARC_VISIBLE_ANGLE_RAD, places=9)
        self.assertAlmostEqual(math.degrees(geometry.visible_angle_rad), 36.0, places=6)

    def test_radius_is_adaptive_not_fixed(self) -> None:
        corridor = [(0.0, 1.0), (0.0, 2.0), (0.0, 3.0)]
        near_geometry = generate_port_arc_geometry(
            port_name="Port A",
            port_latlon=(0.0, 0.0),
            corridor_latlon=corridor,
            peer_port_latlons=[(0.0, 0.0), (0.0, 0.8), (4.0, 4.0)],
        )
        far_geometry = generate_port_arc_geometry(
            port_name="Port A",
            port_latlon=(0.0, 0.0),
            corridor_latlon=corridor,
            peer_port_latlons=[(0.0, 0.0), (0.0, 6.0), (4.0, 4.0)],
        )

        self.assertLess(near_geometry.radius_km, far_geometry.radius_km)
        self.assertNotAlmostEqual(near_geometry.radius_km, 60.0, delta=0.5)
        self.assertNotAlmostEqual(far_geometry.radius_km, 60.0, delta=0.5)

    def test_midpoint_bulges_toward_corridor_side(self) -> None:
        geometry = generate_port_arc_geometry(
            port_name="Port A",
            port_latlon=(0.0, 0.0),
            corridor_latlon=[(0.0, 1.0), (0.0, 2.0), (0.0, 3.0)],
            peer_port_latlons=[(0.0, 0.0), (0.0, 3.0), (3.0, 0.0)],
        )

        self.assertLess(geometry.midpoint_distance_to_corridor_km, geometry.port_distance_to_corridor_km)

    def test_river_corridor_is_supported(self) -> None:
        geometry = generate_port_arc_geometry(
            port_name="Porto de Manaus",
            port_latlon=(-3.1567, -60.0079),
            corridor_latlon=[
                (-3.1500, -59.3500),
                (-2.7500, -57.5000),
                (-2.0500, -54.7000),
            ],
            peer_port_latlons=[
                (-3.1567, -60.0079),
                (-2.4220, -54.7190),
                (0.0540, -51.1740),
            ],
        )

        self.assertGreater(len(geometry.route_ordered_arc_points_latlon), 4)
        self.assertLess(geometry.midpoint_distance_to_corridor_km, geometry.port_distance_to_corridor_km)

    def test_polygon_backend_placeholder_is_explicit(self) -> None:
        with self.assertRaises(NotImplementedError):
            infer_water_direction_from_polygon(None)

    def test_adaptive_radius_uses_local_corridor_spacing(self) -> None:
        context = get_local_corridor_context(
            (0.0, 0.0),
            [(0.0, 1.0), (0.0, 1.5), (0.0, 2.0)],
        )
        radius_km, target_arc_km, _, local_spacing_km = compute_adaptive_arc_radius(
            (0.0, 0.0),
            [(0.0, 0.0), (0.0, 20.0)],
            context,
        )

        self.assertGreater(local_spacing_km, 0.0)
        self.assertGreater(target_arc_km, 0.0)
        self.assertGreater(radius_km, 0.0)


if __name__ == "__main__":
    unittest.main()
