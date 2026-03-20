import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.heatmap import page
from app.heatmap.types import (
    HeatmapDataset,
    HeatmapDatasetDiagnostics,
    HeatmapRunInfo,
    HeatmapScenario,
)
from app.main.utils.constants import DEFAULT_ORIGIN


class HeatmapPageTests(unittest.TestCase):
    def test_init_page_state_uses_shared_default_origin(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})

        with patch.object(page, "st", fake_streamlit):
            page._init_page_state()

        self.assertEqual(fake_streamlit.session_state[page._HEATMAP_ORIGIN_FIELD], DEFAULT_ORIGIN)
        self.assertEqual(fake_streamlit.session_state["heatmap_cargo"], 30.0)
        self.assertEqual(fake_streamlit.session_state["heatmap_surface_mode"], "2d")
        self.assertFalse(fake_streamlit.session_state["heatmap_show_points"])

    def test_clear_loaded_dataset_if_outdated_resets_cached_dataset(self) -> None:
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
        fresh_status = SimpleNamespace(
            run_id="run-new",
            destination_count=608,
            found_count=96,
            success_count=48,
            fail_count=48,
            updated_timestamp="2026-03-20 13:00:00",
        )
        fake_streamlit = SimpleNamespace(session_state={"heatmap_dataset": cached_dataset})

        with patch.object(page, "st", fake_streamlit):
            page._clear_loaded_dataset_if_outdated(scenario, fresh_status)

        self.assertIsNone(fake_streamlit.session_state["heatmap_dataset"])


if __name__ == "__main__":
    unittest.main()
