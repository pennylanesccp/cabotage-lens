import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app.heatmap.sidebar as heatmap_sidebar
import app.main.sidebar as main_sidebar


class SidebarLogoutTests(unittest.TestCase):
    def test_router_sidebar_renders_logout_control(self) -> None:
        fake_streamlit = SimpleNamespace(
            sidebar=contextlib.nullcontext(),
            subheader=Mock(),
            expander=Mock(return_value=contextlib.nullcontext()),
        )

        with patch.object(main_sidebar, "st", fake_streamlit), patch.object(
            main_sidebar,
            "render_sidebar_brand",
        ), patch.object(
            main_sidebar,
            "render_filters",
        ), patch.object(
            main_sidebar,
            "render_advanced",
        ), patch.object(
            main_sidebar,
            "render_run_button",
            return_value=True,
        ), patch.object(
            main_sidebar,
            "render_logout_control",
        ) as logout_mock:
            clicked = main_sidebar.render_sidebar([], [])

        self.assertTrue(clicked)
        logout_mock.assert_called_once_with()

    def test_heatmap_sidebar_renders_logout_control_after_actions(self) -> None:
        fake_streamlit = SimpleNamespace(
            sidebar=contextlib.nullcontext(),
            markdown=Mock(),
            button=Mock(side_effect=[False, False]),
        )

        with patch.object(heatmap_sidebar, "st", fake_streamlit), patch.object(
            heatmap_sidebar,
            "render_logout_control",
        ) as logout_mock:
            run_missing, rerun = heatmap_sidebar.render_run_actions(found_count=0, pending_count=10)

        self.assertFalse(run_missing)
        self.assertFalse(rerun)
        logout_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
