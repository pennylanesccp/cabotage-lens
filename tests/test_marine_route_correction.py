import unittest
from unittest.mock import patch

from app.main.map.routing.marine_coastal_route import build_coastal_leg_points
from app.main.map.routing.marine_leg_interpolation import interpolate_leg_intermediate_points
from app.main.map.routing.marine_point_correction import correct_point_to_water_result


class MarineRouteCorrectionTests(unittest.TestCase):
    def test_point_already_on_reference_water_is_kept(self) -> None:
        result = correct_point_to_water_result(
            point_latlon=(0.0, 0.5),
            leg_start_latlon=(0.0, 0.0),
            leg_end_latlon=(0.0, 1.0),
            reference_path=[(0.0, 0.0), (0.0, 1.0)],
            tolerance_km=0.15,
            step_km=0.1,
            max_search_km=20.0,
            max_iterations=200,
        )

        self.assertTrue(result.was_on_water)
        self.assertTrue(result.reached_water)
        self.assertIsNone(result.selected_side)
        self.assertEqual(result.corrected_point_latlon, (0.0, 0.5))

    def test_land_point_moves_to_left_side_when_water_is_north(self) -> None:
        result = correct_point_to_water_result(
            point_latlon=(0.0, 0.5),
            leg_start_latlon=(0.0, 0.0),
            leg_end_latlon=(0.0, 1.0),
            reference_path=[(0.08, 0.0), (0.08, 1.0)],
            tolerance_km=0.15,
            step_km=0.1,
            max_search_km=20.0,
            max_iterations=200,
        )

        self.assertFalse(result.was_on_water)
        self.assertTrue(result.reached_water)
        self.assertEqual(result.selected_side, "left")
        self.assertGreater(result.corrected_point_latlon[0], 0.07)

    def test_land_point_moves_to_right_side_when_water_is_south(self) -> None:
        result = correct_point_to_water_result(
            point_latlon=(0.0, 0.5),
            leg_start_latlon=(0.0, 0.0),
            leg_end_latlon=(0.0, 1.0),
            reference_path=[(-0.06, 0.0), (-0.06, 1.0)],
            tolerance_km=0.15,
            step_km=0.1,
            max_search_km=20.0,
            max_iterations=200,
        )

        self.assertFalse(result.was_on_water)
        self.assertTrue(result.reached_water)
        self.assertEqual(result.selected_side, "right")
        self.assertLess(result.corrected_point_latlon[0], -0.05)

    def test_no_water_within_limits_keeps_best_fallback_candidate(self) -> None:
        result = correct_point_to_water_result(
            point_latlon=(0.0, 0.5),
            leg_start_latlon=(0.0, 0.0),
            leg_end_latlon=(0.0, 1.0),
            reference_path=[(1.0, 0.0), (1.0, 1.0)],
            tolerance_km=0.15,
            step_km=0.1,
            max_search_km=1.0,
            max_iterations=10,
        )

        self.assertFalse(result.was_on_water)
        self.assertFalse(result.reached_water)
        self.assertEqual(result.selected_side, "left")
        self.assertGreater(result.corrected_point_latlon[0], 0.0)
        self.assertLess(result.best_distance_to_water_km, 111.5)

    def test_coastal_leg_builder_returns_corrected_polyline_points(self) -> None:
        leg_start = (0.0, 0.0)
        leg_end = (0.0, 1.0)
        base_points = interpolate_leg_intermediate_points(leg_start, leg_end, n_points=5)

        with patch(
            "app.main.map.routing.marine_coastal_route.build_leg_reference_path",
            return_value=[(0.08, 0.0), (0.08, 1.0)],
        ):
            corrected_points = build_coastal_leg_points(
                origin_port_name="Port A",
                dest_port_name="Port B",
                leg_start_latlon=leg_start,
                leg_end_latlon=leg_end,
                n_points=5,
                smooth_window=5,
            )

        self.assertEqual(len(corrected_points), len(base_points))
        self.assertNotEqual(corrected_points, base_points)
        self.assertTrue(all(point[0] > 0.0 for point in corrected_points))
        self.assertGreater(max(point[0] for point in corrected_points), 0.05)


if __name__ == "__main__":
    unittest.main()
