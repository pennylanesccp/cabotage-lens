import math
import unittest
from unittest.mock import patch

from app.main.map.routing.marine_master_route import load_master_route_ports
from app.main.map.routing.water_validation import build_leg_reference_path
from modules.plot.maritime_arc_overrides import LEG_ARC_OVERRIDES
from modules.plot.maritime_arc_geometry import (
    CENTRAL_ANGLE_RADIANS,
    RouteArcPort,
    build_arc_for_leg,
    build_leg_arc_debug_payload,
    build_port_to_port_arc,
    build_route_arc_path,
    build_route_arc_debug_payloads,
    build_route_arcs_from_port_sequence,
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

    def test_route_arc_chain_keeps_intermediate_ports(self) -> None:
        ports = [
            RouteArcPort(name="Port A", latlon=(0.0, 0.0)),
            RouteArcPort(name="Port B", latlon=(0.0, 2.0)),
            RouteArcPort(name="Port C", latlon=(0.0, 4.0)),
        ]

        route_arcs = build_route_arcs_from_port_sequence(
            ports,
            reference_path_builder=lambda start_port, end_port: (
                start_port.latlon,
                (0.8, (start_port.latlon[1] + end_port.latlon[1]) / 2.0),
                end_port.latlon,
            ),
            n_points_per_leg=21,
        )
        route_path = build_route_arc_path(
            ports,
            reference_path_builder=lambda start_port, end_port: (
                start_port.latlon,
                (0.8, (start_port.latlon[1] + end_port.latlon[1]) / 2.0),
                end_port.latlon,
            ),
            n_points_per_leg=21,
        )

        self.assertEqual(len(route_arcs), 2)
        self.assertEqual(route_arcs[0].port_a_latlon, ports[0].latlon)
        self.assertEqual(route_arcs[0].port_b_latlon, ports[1].latlon)
        self.assertEqual(route_arcs[1].port_a_latlon, ports[1].latlon)
        self.assertEqual(route_arcs[1].port_b_latlon, ports[2].latlon)
        self.assertEqual(route_path[0], ports[0].latlon)
        self.assertEqual(route_path[-1], ports[2].latlon)
        self.assertEqual(sum(1 for point in route_path if point == ports[1].latlon), 1)

    def test_leg_override_changes_central_angle_from_default(self) -> None:
        with patch.dict(
            LEG_ARC_OVERRIDES,
            {("port-a", "port-b"): {"central_angle_deg": 48.0}},
            clear=True,
        ):
            geometry = build_arc_for_leg(
                RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
                RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
                reference_path_latlon=[(0.0, 0.0), (0.8, 1.0), (0.0, 2.0)],
                n_points=41,
            )

        self.assertAlmostEqual(geometry.central_angle_degrees, 48.0, places=9)
        self.assertAlmostEqual(geometry.central_angle_radians, math.radians(48.0), places=9)
        self.assertEqual(geometry.angle_source, "override")

    def test_manual_side_override_forces_arc_orientation(self) -> None:
        with patch.dict(
            LEG_ARC_OVERRIDES,
            {("port-a", "port-b"): {"side": "right"}},
            clear=True,
        ):
            geometry = build_arc_for_leg(
                RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
                RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
                reference_path_latlon=[(0.0, 0.0), (0.8, 1.0), (0.0, 2.0)],
                n_points=41,
            )

        self.assertEqual(geometry.side, "right")
        self.assertEqual(geometry.side_source, "manual")
        self.assertLess(geometry.midpoint_latlon[0], 0.0)

    def test_reverse_traversal_reuses_same_physical_arc_override(self) -> None:
        with patch.dict(
            LEG_ARC_OVERRIDES,
            {("port-a", "port-b"): {"central_angle_deg": 48.0, "side": "right"}},
            clear=True,
        ):
            forward = build_arc_for_leg(
                RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
                RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
                reference_path_latlon=[(0.0, 0.0), (0.8, 1.0), (0.0, 2.0)],
                n_points=41,
            )
            reverse = build_arc_for_leg(
                RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
                RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
                reference_path_latlon=[(0.0, 2.0), (0.8, 1.0), (0.0, 0.0)],
                n_points=41,
            )

        self.assertAlmostEqual(forward.central_angle_degrees, 48.0, places=9)
        self.assertAlmostEqual(reverse.central_angle_degrees, 48.0, places=9)
        self.assertEqual(forward.side_source, "manual")
        self.assertEqual(reverse.side_source, "manual")
        self.assertEqual(forward.side, "right")
        self.assertEqual(reverse.side, "left")
        self.assertLess(forward.midpoint_latlon[0], 0.0)
        self.assertLess(reverse.midpoint_latlon[0], 0.0)

    def test_duplicate_reverse_entries_for_same_leg_raise(self) -> None:
        with patch.dict(
            LEG_ARC_OVERRIDES,
            {
                ("port-a", "port-b"): {"side": "right"},
                ("port-b", "port-a"): {"side": "left"},
            },
            clear=True,
        ):
            with self.assertRaises(ValueError):
                build_arc_for_leg(
                    RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
                    RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
                    reference_path_latlon=[(0.0, 0.0), (0.8, 1.0), (0.0, 2.0)],
                    n_points=41,
                )

    def test_neighbor_context_can_guide_auto_side_selection(self) -> None:
        ports = [
            RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
            RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
            RouteArcPort(name="Port C", key="port-c", latlon=(0.8, 4.0)),
        ]

        route_arcs = build_route_arcs_from_port_sequence(
            ports,
            reference_path_builder=None,
            clutter_points_latlon=(),
            n_points_per_leg=31,
        )

        self.assertEqual(route_arcs[0].side, "left")
        self.assertEqual(route_arcs[0].side_source, "auto")

    def test_debug_payload_reports_override_and_candidates(self) -> None:
        with patch.dict(
            LEG_ARC_OVERRIDES,
            {("port-a", "port-b"): {"central_angle_deg": 55.0, "side": "left"}},
            clear=True,
        ):
            payload = build_leg_arc_debug_payload(
                RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
                RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
                reference_path_latlon=[(0.0, 0.0), (0.8, 1.0), (0.0, 2.0)],
                n_points=31,
            )

        self.assertEqual(payload.leg_key, ("port-a", "port-b"))
        self.assertAlmostEqual(payload.central_angle_deg, 55.0, places=9)
        self.assertEqual(payload.angle_source, "override")
        self.assertEqual(payload.side_override, "left")
        self.assertEqual(payload.configured_side_override, "left")
        self.assertEqual(payload.override_key, ("port-a", "port-b"))
        self.assertFalse(payload.override_reverse_traversal)
        self.assertEqual(payload.side_source, "manual")
        self.assertEqual(len(payload.candidates), 2)

    def test_route_debug_payload_filter_returns_only_requested_leg(self) -> None:
        ports = [
            RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
            RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
            RouteArcPort(name="Port C", key="port-c", latlon=(0.0, 4.0)),
        ]

        payloads = build_route_arc_debug_payloads(
            ports,
            reference_path_builder=lambda start_port, end_port: (
                start_port.latlon,
                (0.8, (start_port.latlon[1] + end_port.latlon[1]) / 2.0),
                end_port.latlon,
            ),
            n_points_per_leg=21,
            debug_leg_key=("port-b", "port-c"),
        )

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0].leg_key, ("port-b", "port-c"))

    def test_route_debug_payload_filter_accepts_reverse_leg_key(self) -> None:
        ports = [
            RouteArcPort(name="Port A", key="port-a", latlon=(0.0, 0.0)),
            RouteArcPort(name="Port B", key="port-b", latlon=(0.0, 2.0)),
            RouteArcPort(name="Port C", key="port-c", latlon=(0.0, 4.0)),
        ]

        payloads = build_route_arc_debug_payloads(
            ports,
            reference_path_builder=lambda start_port, end_port: (
                start_port.latlon,
                (0.8, (start_port.latlon[1] + end_port.latlon[1]) / 2.0),
                end_port.latlon,
            ),
            n_points_per_leg=21,
            debug_leg_key=("port-c", "port-b"),
        )

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0].leg_key, ("port-b", "port-c"))

    @staticmethod
    def _distance(a_xy: tuple[float, float], b_xy: tuple[float, float]) -> float:
        return math.hypot(a_xy[0] - b_xy[0], a_xy[1] - b_xy[1])


if __name__ == "__main__":
    unittest.main()
