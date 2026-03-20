import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app.heatmap.surface as heatmap_surface
from app.heatmap.surface import build_surface
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapRunInfo, HeatmapScenario


class HeatmapSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        heatmap_surface._boundary_cells.cache_clear()
        heatmap_surface.load_brazil_boundary_geojson.cache_clear()
        heatmap_surface._boundary_rings.cache_clear()
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
            destination_count=2,
            found_count=2,
            success_count=2,
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
                destiny_name="Manaus",
                destiny_lat=-3.1190,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                port_destiny_name="Manaus",
                road_cost_r=15000.0,
                multimodal_cost_r=11000.0,
                cost_delta_r=4000.0,
                cost_savings_pct=26.6667,
                road_emissions_kg=9000.0,
                multimodal_emissions_kg=5200.0,
                emissions_delta_kg=3800.0,
                emissions_savings_pct=42.2222,
                road_distance_km=3900.0,
                sea_km=3400.0,
                updated_timestamp="2026-03-20 09:00:00",
            ),
            HeatmapPoint(
                destiny_name="Belem",
                destiny_lat=-1.4558,
                destiny_lon=-48.4902,
                destiny_uf="PA",
                port_destiny_name="Belem",
                road_cost_r=9000.0,
                multimodal_cost_r=9500.0,
                cost_delta_r=-500.0,
                cost_savings_pct=-5.5556,
                road_emissions_kg=5100.0,
                multimodal_emissions_kg=4700.0,
                emissions_delta_kg=400.0,
                emissions_savings_pct=7.8431,
                road_distance_km=2700.0,
                sea_km=2100.0,
                updated_timestamp="2026-03-20 09:00:00",
            ),
        ]
        return HeatmapDataset(
            scenario=scenario,
            run=run,
            points=points,
            max_abs_cost_delta=4000.0,
            max_abs_emissions_delta=3800.0,
        )

    def test_build_surface_cost_mode_uses_cost_percentage_and_absolute_height(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((-60.3, -3.4), (-59.7, -3.4), (-59.7, -2.8), (-60.3, -2.8)),
                -3.1190,
                -60.0217,
            ),
        )

        with patch("app.heatmap.surface._boundary_cells", return_value=mock_cells):
            surface = build_surface(dataset, "cost", "3d")

        self.assertEqual(surface.metric, "cost")
        self.assertEqual(surface.mode, "3d")
        self.assertEqual(len(surface.cells), 1)
        self.assertAlmostEqual(surface.cells[0].percentage_value, 26.6667, places=3)
        self.assertAlmostEqual(surface.cells[0].absolute_value, 4000.0, places=3)
        self.assertGreater(surface.cells[0].elevation_m, 0.0)
        self.assertEqual(surface.cells[0].nearest_destiny_name, "Manaus")

    def test_build_surface_emissions_mode_uses_emissions_values_and_flattens_2d(self) -> None:
        dataset = self._dataset()
        mock_cells = (
            (
                ((-48.8, -1.8), (-48.2, -1.8), (-48.2, -1.2), (-48.8, -1.2)),
                -1.4558,
                -48.4902,
            ),
        )

        with patch("app.heatmap.surface._boundary_cells", return_value=mock_cells):
            surface = build_surface(dataset, "emissions", "2d")

        self.assertEqual(surface.metric, "emissions")
        self.assertEqual(surface.mode, "2d")
        self.assertEqual(len(surface.cells), 1)
        self.assertAlmostEqual(surface.cells[0].percentage_value, 7.8431, places=3)
        self.assertAlmostEqual(surface.cells[0].absolute_value, 400.0, places=3)
        self.assertEqual(surface.cells[0].elevation_m, 0.0)
        self.assertEqual(surface.cells[0].nearest_destiny_name, "Belem")

    def test_boundary_cells_keep_only_cells_with_centers_inside_boundary(self) -> None:
        ring = (((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (0.0, 0.0)),)
        heatmap_surface._boundary_cells.cache_clear()

        with patch("app.heatmap.surface._boundary_rings", return_value=ring), patch(
            "app.heatmap.surface.HEATMAP_SURFACE_CELL_SIZE_DEGREES",
            1.0,
        ):
            cells = heatmap_surface._boundary_cells()

        self.assertEqual(len(cells), 4)
        self.assertEqual(cells[0][1:], (0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
