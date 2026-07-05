import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app.heatmap.sidebar as heatmap_sidebar
import app.main.sidebar.advanced as main_advanced


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _fake_streamlit() -> SimpleNamespace:
    return SimpleNamespace(
        session_state=_SessionState(
            {
                "allocation_mode": "auto",
                "map_show_sea": True,
                "db_target_str": "postgresql://***",
                "write_local_logs": False,
                "effective_archive_logs": False,
            }
        ),
        markdown=Mock(),
        caption=Mock(),
        checkbox=Mock(),
        selectbox=Mock(),
        number_input=Mock(),
        slider=Mock(),
        text_input=Mock(),
    )


class SidebarAdvancedTests(unittest.TestCase):
    def test_router_database_target_display_does_not_bind_widget_key(self) -> None:
        fake_streamlit = _fake_streamlit()

        with patch.object(main_advanced, "st", fake_streamlit):
            main_advanced.render_advanced(
                class_options=["container_feeder"],
                port_ops_scenarios=["santos_diesel_heavy"],
            )

        db_target_call = fake_streamlit.text_input.call_args
        self.assertEqual(db_target_call.args[0], "Database target")
        self.assertEqual(db_target_call.kwargs["value"], "postgresql://***")
        self.assertNotIn("key", db_target_call.kwargs)

    def test_heatmap_database_target_display_does_not_bind_widget_key(self) -> None:
        fake_streamlit = _fake_streamlit()

        with patch.object(heatmap_sidebar, "st", fake_streamlit):
            heatmap_sidebar._render_advanced(
                destination_set_options=["capitals"],
                class_options=["container_feeder"],
                port_ops_scenarios=["santos_diesel_heavy"],
            )

        db_target_call = fake_streamlit.text_input.call_args
        self.assertEqual(db_target_call.args[0], "Database target")
        self.assertEqual(db_target_call.kwargs["value"], "postgresql://***")
        self.assertNotIn("key", db_target_call.kwargs)


if __name__ == "__main__":
    unittest.main()
