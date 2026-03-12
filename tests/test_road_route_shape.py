import math
import unittest

from app.main.map.routing.road_route_shape import build_shaped_road_path


class RoadRouteShapeTests(unittest.TestCase):
    def test_parabola_style_keeps_points_on_one_side_of_chord(self) -> None:
        path = build_shaped_road_path(
            (0.0, 0.0),
            (0.0, 4.0),
            preferred_path=None,
            n_points=41,
            smooth_window=5,
            style="parabola",
        )

        signed_distances = [self._signed_distance(point, path[0], path[-1]) for point in path[1:-1]]
        significant = [distance for distance in signed_distances if abs(distance) > 1e-4]

        self.assertTrue(significant)
        first_sign = math.copysign(1.0, significant[0])
        self.assertTrue(all(math.copysign(1.0, distance) == first_sign for distance in significant))

    def test_preferred_path_with_real_shape_is_preserved(self) -> None:
        preferred = [
            [0.0, 0.0],
            [1.0, 0.8],
            [2.0, 0.4],
            [3.0, 0.2],
        ]

        path = build_shaped_road_path(
            (0.0, 0.0),
            (0.2, 3.0),
            preferred_path=preferred,
            style="parabola",
        )

        self.assertEqual(path, preferred)

    def test_preserve_preferred_path_can_be_disabled_for_visual_only_direct_route(self) -> None:
        preferred = [
            [0.0, 0.0],
            [1.0, 0.8],
            [2.0, 0.4],
            [3.0, 0.2],
        ]

        path = build_shaped_road_path(
            (0.0, 0.0),
            (0.2, 3.0),
            preferred_path=preferred,
            style="parabola",
            preserve_preferred_path=False,
        )

        self.assertNotEqual(path, preferred)
        signed_distances = [self._signed_distance(point, path[0], path[-1]) for point in path[1:-1]]
        significant = [distance for distance in signed_distances if abs(distance) > 1e-4]
        self.assertTrue(significant)
        first_sign = math.copysign(1.0, significant[0])
        self.assertTrue(all(math.copysign(1.0, distance) == first_sign for distance in significant))

    @staticmethod
    def _signed_distance(
        point_lonlat: list[float],
        start_lonlat: list[float],
        end_lonlat: list[float],
    ) -> float:
        px, py = float(point_lonlat[0]), float(point_lonlat[1])
        x0, y0 = float(start_lonlat[0]), float(start_lonlat[1])
        x1, y1 = float(end_lonlat[0]), float(end_lonlat[1])
        dx = x1 - x0
        dy = y1 - y0
        segment_length = math.hypot(dx, dy)
        if segment_length <= 1e-9:
            return 0.0
        return ((dx * (py - y0)) - (dy * (px - x0))) / segment_length


if __name__ == "__main__":
    unittest.main()
