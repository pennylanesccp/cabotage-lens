import unittest
from unittest.mock import patch

import app.heatmap.surface as heatmap_surface
from app.heatmap.surface import build_surface
from app.heatmap.types import (
    HeatmapDataset,
    HeatmapDatasetDiagnostics,
    HeatmapPoint,
    HeatmapRunInfo,
    HeatmapScenario,
)


class HeatmapSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        heatmap_surface._hull_cells.cache_clear()
        heatmap_surface._surface_geometry_cached.cache_clear()
        heatmap_surface._build_surface_cached.cache_clear()

    def _dataset(self) -> HeatmapDataset:
        scenario = HeatmapScenario(
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            truck_key="semi_27t",
            ors_profile="driving-hgv",
            vessel_class="container_small",
            include_hoteling=True,
            hoteling_hours_per_call=14.0,
            port_calls=2,
            include_port_ops=True,
            port_moves_per_call=None,
            cargo_teu=None,
            t_per_teu_default=14.0,
            allocation_mode=None,
            allocation_load_factor=0.8,
            full_call_mode=False,
            port_ops_scenario="baseline",
        )
        run = HeatmapRunInfo(
            run_id="run-1",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=3,
            found_count=3,
            success_count=3,
            fail_count=0,
            missing_count=0,
            pending_count=0,
            duration_s=42.0,
            completed_timestamp="2026-03-20 09:00:00",
            updated_timestamp="2026-03-20 09:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        points = [
            HeatmapPoint(
                destiny_name="Alpha",
                destiny_lat=0.0,
                destiny_lon=0.0,
                destiny_uf="AA",
                port_destiny_name="Alpha Port",
                road_cost_r=1000.0,
                multimodal_cost_r=1200.0,
                cost_delta_r=-200.0,
                cost_savings_pct=0.0,
                road_emissions_kg=1000.0,
                multimodal_emissions_kg=910.0,
                emissions_delta_kg=90.0,
                emissions_savings_pct=6.0,
                road_distance_km=100.0,
                sea_km=50.0,
                updated_timestamp="2026-03-20 09:00:00",
            ),
            HeatmapPoint(
                destiny_name="Beta",
                destiny_lat=0.0,
                destiny_lon=2.0,
                destiny_uf="BB",
                port_destiny_name="Beta Port",
                road_cost_r=1000.0,
                multimodal_cost_r=800.0,
                cost_delta_r=200.0,
                cost_savings_pct=20.0,
                road_emissions_kg=1000.0,
                multimodal_emissions_kg=820.0,
                emissions_delta_kg=180.0,
                emissions_savings_pct=18.0,
                road_distance_km=110.0,
                sea_km=55.0,
                updated_timestamp="2026-03-20 09:00:00",
            ),
            HeatmapPoint(
                destiny_name="Gamma",
                destiny_lat=2.0,
                destiny_lon=0.0,
                destiny_uf="CC",
                port_destiny_name="Gamma Port",
                road_cost_r=1000.0,
                multimodal_cost_r=600.0,
                cost_delta_r=600.0,
                cost_savings_pct=40.0,
                road_emissions_kg=1000.0,
                multimodal_emissions_kg=700.0,
                emissions_delta_kg=300.0,
                emissions_savings_pct=30.0,
                road_distance_km=120.0,
                sea_km=60.0,
                updated_timestamp="2026-03-20 09:00:00",
            ),
        ]
        return HeatmapDataset(
            scenario=scenario,
            run=run,
            points=points,
            max_abs_cost_delta=600.0,
            max_abs_emissions_delta=300.0,
            diagnostics=HeatmapDatasetDiagnostics(
                successful_rows=3,
                plottable_points=3,
                skipped_missing_coordinates=0,
                skipped_missing_costs=0,
                skipped_missing_emissions=0,
            ),
        )

    def test_build_surface_cost_mode_uses_linear_triangle_interpolation(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                0.5,
                0.5,
            ),
        )

        with patch("app.heatmap.surface._hull_cells", return_value=mock_cells):
            surface = build_surface(dataset, "cost")

        self.assertEqual(surface.metric, "cost")
        self.assertEqual(surface.mode, "3d")
        self.assertEqual(len(surface.cells), 1)
        self.assertAlmostEqual(surface.cells[0].percentage_value, 15.0, places=3)
        self.assertAlmostEqual(surface.cells[0].absolute_value, 100.0, places=3)
        self.assertGreater(surface.cells[0].elevation_m, 0.0)
        self.assertEqual(surface.cells[0].nearest_destiny_name, "Alpha")
        self.assertEqual(surface.source_point_count, 3)
        self.assertEqual(surface.unique_source_coordinate_count, 3)

    def test_build_surface_emissions_mode_uses_emissions_values_and_keeps_3d_relief(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                0.5,
                0.5,
            ),
        )

        with patch("app.heatmap.surface._hull_cells", return_value=mock_cells):
            surface = build_surface(dataset, "emissions")

        self.assertEqual(surface.metric, "emissions")
        self.assertEqual(surface.mode, "3d")
        self.assertEqual(len(surface.cells), 1)
        self.assertAlmostEqual(surface.cells[0].percentage_value, 15.0, places=3)
        self.assertAlmostEqual(surface.cells[0].absolute_value, 165.0, places=3)
        self.assertGreater(surface.cells[0].elevation_m, 0.0)
        self.assertEqual(surface.cells[0].nearest_destiny_name, "Alpha")
        self.assertEqual(surface.hull_vertex_count, 3)

    def test_build_surface_3d_places_negative_values_below_zero_plane(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)),
                0.0,
                0.0,
            ),
        )

        with patch("app.heatmap.surface._hull_cells", return_value=mock_cells):
            surface = build_surface(dataset, "cost")

        self.assertEqual(len(surface.cells), 1)
        self.assertAlmostEqual(surface.cells[0].absolute_value, -200.0, places=3)
        self.assertLess(surface.cells[0].elevation_m, 0.0)

    def test_color_for_value_uses_red_yellow_green_by_signed_delta(self) -> None:
        self.assertEqual(
            heatmap_surface._color_for_value(-100.0, 100.0, 100.0),
            (*heatmap_surface.HEATMAP_COLOR_NEGATIVE, heatmap_surface.HEATMAP_SURFACE_ALPHA),
        )
        self.assertEqual(
            heatmap_surface._color_for_value(0.0, 100.0, 100.0),
            (*heatmap_surface.HEATMAP_COLOR_MID, heatmap_surface.HEATMAP_SURFACE_ALPHA),
        )
        self.assertEqual(
            heatmap_surface._color_for_value(100.0, 100.0, 100.0),
            (*heatmap_surface.HEATMAP_COLOR_POSITIVE, heatmap_surface.HEATMAP_SURFACE_ALPHA),
        )

    def test_color_for_value_uses_independent_negative_and_positive_scales(self) -> None:
        self.assertEqual(
            heatmap_surface._color_for_value(-50.0, 50.0, 500.0),
            (*heatmap_surface.HEATMAP_COLOR_NEGATIVE, heatmap_surface.HEATMAP_SURFACE_ALPHA),
        )
        self.assertEqual(
            heatmap_surface._color_for_value(500.0, 50.0, 500.0),
            (*heatmap_surface.HEATMAP_COLOR_POSITIVE, heatmap_surface.HEATMAP_SURFACE_ALPHA),
        )

    def test_build_surface_colors_follow_signed_quantitative_delta(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                0.5,
                0.5,
            ),
        )

        with patch("app.heatmap.surface._hull_cells", return_value=mock_cells), patch(
            "app.heatmap.surface._triangulated_interpolate",
            return_value=(-12.0, 250.0, "Alpha", "AA", 10.0),
        ):
            surface = build_surface(dataset, "cost")

        self.assertEqual(
            surface.cells[0].fill_color,
            heatmap_surface._color_for_value(
                surface.cells[0].absolute_value,
                surface.negative_color_scale,
                surface.positive_color_scale,
            ),
        )

    def test_build_surface_3d_keeps_moderate_values_below_peak_relief(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                0.5,
                0.5,
            ),
        )

        with patch("app.heatmap.surface._hull_cells", return_value=mock_cells):
            surface = build_surface(dataset, "cost")

        self.assertGreater(surface.cells[0].elevation_m, heatmap_surface.HEATMAP_SURFACE_MAX_ELEVATION_M * 0.2)
        self.assertLess(surface.cells[0].elevation_m, heatmap_surface.HEATMAP_SURFACE_MAX_ELEVATION_M * 0.6)

    def test_build_surface_aligns_quantitative_sign_with_percentage_direction(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
                0.5,
                0.5,
            ),
        )

        with patch("app.heatmap.surface._hull_cells", return_value=mock_cells), patch(
            "app.heatmap.surface._triangulated_interpolate",
            return_value=(-12.0, 250.0, "Alpha", "AA", 10.0),
        ):
            surface = build_surface(dataset, "cost")

        self.assertEqual(len(surface.cells), 1)
        self.assertAlmostEqual(surface.cells[0].absolute_value, -250.0, places=3)
        self.assertLess(surface.cells[0].elevation_m, 0.0)

    def test_hull_cells_keep_only_centroids_inside_convex_hull(self) -> None:
        hull_polygon = ((0.0, 0.0), (2.0, 0.0), (0.0, 2.0))
        heatmap_surface._hull_cells.cache_clear()

        with patch("app.heatmap.surface.HEATMAP_SURFACE_CELL_SIZE_DEGREES", 1.0):
            cells = heatmap_surface._hull_cells(hull_polygon)

        centers = {(cell[2], cell[1]) for cell in cells}
        self.assertNotIn((1.5, 1.5), centers)
        self.assertTrue(all((lon + lat) <= 2.0 + 1e-9 for lon, lat in centers))


if __name__ == "__main__":
    unittest.main()
