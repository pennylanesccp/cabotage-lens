import unittest
from types import SimpleNamespace

from app.heatmap import map as heatmap_map


class HeatmapMapTests(unittest.TestCase):
    def _surface(self) -> SimpleNamespace:
        cell = SimpleNamespace(
            polygon=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            fill_color=(82, 158, 79, 210),
            elevation_m=123_456.0,
            percentage_value=18.4,
            absolute_value=410.0,
            nearest_destiny_name="Alpha",
            nearest_destiny_uf="AA",
            nearest_distance_km=24.0,
        )
        return SimpleNamespace(cells=[cell])

    def test_surface_body_rows_keep_side_walls_muted(self) -> None:
        surface = self._surface()

        rows = heatmap_map._surface_body_rows(surface, "cost")

        self.assertEqual(rows[0]["polygon"], [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        self.assertNotEqual(rows[0]["fill_color"][:3], list(surface.cells[0].fill_color[:3]))
        self.assertEqual(rows[0]["fill_color"][3], heatmap_map.HEATMAP_SURFACE_SIDE_WALL_ALPHA)
        self.assertEqual(rows[0]["elevation"], surface.cells[0].elevation_m)

    def test_surface_cap_rows_keep_color_on_top_face(self) -> None:
        surface = self._surface()

        rows = heatmap_map._surface_cap_rows(surface, "cost")

        self.assertEqual(rows[0]["fill_color"], list(surface.cells[0].fill_color))
        self.assertEqual(
            rows[0]["polygon"][0],
            [0.0, 0.0, surface.cells[0].elevation_m + heatmap_map.HEATMAP_SURFACE_TOP_CAP_LIFT_M],
        )
        self.assertEqual(len(rows[0]["polygon"][0]), 3)


if __name__ == "__main__":
    unittest.main()
