import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.heatmap import page
from app.heatmap.config import heatmap_destination_label
from app.heatmap.types import (
    HeatmapDataset,
    HeatmapDatasetDiagnostics,
    HeatmapRunInfo,
    HeatmapScenario,
)
from app.main.utils.constants import DEFAULT_ORIGIN, DEFAULTS


class HeatmapPageTests(unittest.TestCase):
    def _empty_dataset(self) -> HeatmapDataset:
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
            run_id="run-test",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=0,
            found_count=0,
            success_count=0,
            fail_count=0,
            missing_count=0,
            pending_count=0,
            duration_s=0.0,
            completed_timestamp=None,
            updated_timestamp=None,
            destination_set_id="city_dests_over50k.txt",
        )
        return HeatmapDataset(
            scenario=scenario,
            run=run,
            points=[],
            max_abs_cost_delta=1.0,
            max_abs_emissions_delta=1.0,
            diagnostics=HeatmapDatasetDiagnostics(
                successful_rows=0,
                plottable_points=0,
                skipped_missing_coordinates=0,
                skipped_missing_costs=0,
                skipped_missing_emissions=0,
            ),
        )

    def test_init_page_state_uses_shared_default_origin(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})

        with patch.object(page, "st", fake_streamlit):
            page._init_page_state()

        self.assertEqual(fake_streamlit.session_state[page._HEATMAP_ORIGIN_FIELD], DEFAULT_ORIGIN)
        self.assertEqual(fake_streamlit.session_state["heatmap_cargo"], float(DEFAULTS["cargo_t"]))
        self.assertEqual(fake_streamlit.session_state[page._HEATMAP_METRIC_FIELD], "emissions")
        self.assertEqual(fake_streamlit.session_state["heatmap_destination_set_id"], "city_dests_over50k.txt")

    def test_init_page_state_does_not_reuse_legacy_cost_metric(self) -> None:
        fake_streamlit = SimpleNamespace(
            session_state={
                "heatmap_metric": "cost",
                page._HEATMAP_METRIC_FIELD: "cost",
                page._HEATMAP_METRIC_STATE_VERSION_FIELD: 2,
            }
        )

        with patch.object(page, "st", fake_streamlit):
            page._init_page_state()

        self.assertEqual(fake_streamlit.session_state[page._HEATMAP_METRIC_FIELD], "emissions")

        fake_streamlit.session_state[page._HEATMAP_METRIC_FIELD] = "cost"
        with patch.object(page, "st", fake_streamlit):
            page._init_page_state()

        self.assertEqual(fake_streamlit.session_state[page._HEATMAP_METRIC_FIELD], "cost")

    def test_emissions_is_the_first_color_metric_option(self) -> None:
        self.assertEqual(page.HEATMAP_METRICS[0], "emissions")

    def test_current_scenario_ignores_legacy_advanced_state(self) -> None:
        fake_streamlit = SimpleNamespace(
            session_state={
                page._HEATMAP_ORIGIN_FIELD: "Pelotas, RS",
                "heatmap_cargo": 30.0,
                "include_port_ops": False,
                "truck_key": "legacy-truck",
                "vessel_class": "legacy-vessel",
                "allocation_mode": "dwt_share",
            }
        )

        with patch.object(page, "st", fake_streamlit):
            scenario = page._current_scenario()

        self.assertTrue(scenario.include_port_ops)
        self.assertEqual(scenario.truck_key, str(DEFAULTS["truck_key"]))
        self.assertEqual(scenario.vessel_class, page.DEFAULT_VESSEL_CLASS)
        self.assertIsNone(scenario.allocation_mode)
        self.assertEqual(scenario.ors_profile, "driving-car")

    def test_render_dataset_builds_and_renders_surface(self) -> None:
        dataset = self._empty_dataset()
        fake_streamlit = SimpleNamespace(
            session_state={},
            markdown=Mock(),
            radio=Mock(return_value="emissions"),
            caption=Mock(),
        )
        surface = SimpleNamespace(
            unique_source_coordinate_count=0,
            dense_cell_count=0,
            sparse_cell_count=0,
            very_sparse_cell_count=0,
        )

        with patch.object(page, "st", fake_streamlit), patch.object(
            page, "build_surface", return_value=surface
        ) as build_mock, patch.object(page, "render_heatmap_map") as render_mock, patch.object(
            page, "_render_dataset_diagnostics"
        ) as diagnostics_mock:
            page._render_dataset(dataset)

        build_mock.assert_called_once_with(dataset, "emissions", log_route_details=False)
        render_mock.assert_called_once_with(dataset, "emissions", show_points=False, surface=surface)
        diagnostics_mock.assert_called_once_with(dataset, surface)

    def test_clear_loaded_dataset_if_stale_resets_cached_dataset_when_destination_set_changes(self) -> None:
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
        cached_run = HeatmapRunInfo(
            run_id="run-old",
            origin_name="Pelotas, RS",
            cargo_t=30.0,
            destination_count=608,
            found_count=24,
            success_count=24,
            fail_count=0,
            missing_count=584,
            pending_count=584,
            duration_s=42.0,
            completed_timestamp="2026-03-20 12:00:00",
            updated_timestamp="2026-03-20 12:00:00",
            destination_set_id="city_dests_over50k.txt",
        )
        cached_dataset = HeatmapDataset(
            scenario=scenario,
            run=cached_run,
            points=[],
            max_abs_cost_delta=1.0,
            max_abs_emissions_delta=1.0,
            diagnostics=HeatmapDatasetDiagnostics(
                successful_rows=24,
                plottable_points=24,
                skipped_missing_coordinates=0,
                skipped_missing_costs=0,
                skipped_missing_emissions=0,
            ),
        )
        fake_streamlit = SimpleNamespace(session_state={"heatmap_dataset": cached_dataset})

        with patch.object(page, "st", fake_streamlit):
            page._clear_loaded_dataset_if_stale(scenario, "city_dests_over350k.txt")

        self.assertIsNone(fake_streamlit.session_state["heatmap_dataset"])

    def test_format_height_scale_uses_metric_specific_units(self) -> None:
        cost_surface = SimpleNamespace(metric="cost", elevation_scale=1234.5)
        emissions_surface = SimpleNamespace(metric="emissions", elevation_scale=678.9)

        self.assertEqual(page._format_height_scale(cost_surface), "R$ 1,234.50")
        self.assertEqual(page._format_height_scale(emissions_surface), "678.9 kg CO2e")

    def test_destination_set_aliases_cover_known_files(self) -> None:
        self.assertEqual(heatmap_destination_label("city_dests.txt"), "All tracked cities")
        self.assertEqual(heatmap_destination_label("city_dests_borders.txt"), "Border and remote cities")
        self.assertEqual(heatmap_destination_label("city_dests_over350k.txt"), "Cities with population over 350k")
        self.assertEqual(heatmap_destination_label("city_dests_over50k.txt"), "Cities with population over 50k")


if __name__ == "__main__":
    unittest.main()
