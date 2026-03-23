import unittest
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_surface_cap_rows_keep_color_on_top_face(self) -> None:
        surface = self._surface()

        rows = heatmap_map._surface_cap_rows(surface, "cost")

        self.assertEqual(rows[0]["fill_color"], list(surface.cells[0].fill_color))
        self.assertEqual(
            rows[0]["polygon"][0],
            [
                0.0,
                0.0,
                heatmap_map.HEATMAP_SURFACE_ZERO_PLANE_ELEVATION_M
                + surface.cells[0].elevation_m
                + heatmap_map.HEATMAP_SURFACE_TOP_CAP_LIFT_M,
            ],
        )
        self.assertEqual(len(rows[0]["polygon"][0]), 3)

    def test_surface_cap_rows_place_negative_cells_below_zero_plane(self) -> None:
        surface = self._surface()
        surface.cells[0].elevation_m = -12_345.0

        rows = heatmap_map._surface_cap_rows(surface, "cost")

        self.assertLess(rows[0]["polygon"][0][2], heatmap_map.HEATMAP_SURFACE_ZERO_PLANE_ELEVATION_M)

    def test_render_heatmap_map_renders_caps_only_to_avoid_body_occlusion(self) -> None:
        dataset = SimpleNamespace(points=[])
        surface = self._surface()

        with patch("app.heatmap.map._inject_heatmap_map_css"), patch(
            "app.heatmap.map.render_deck_chart"
        ) as render_mock:
            returned_surface = heatmap_map.render_heatmap_map(dataset, "cost", surface=surface)

        deck = render_mock.call_args.args[0]
        self.assertIs(returned_surface, surface)
        self.assertEqual(len(deck.layers), 1)


if __name__ == "__main__":
    unittest.main()
