import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.heatmap import page
from app.main.utils.constants import DEFAULT_ORIGIN


class HeatmapPageTests(unittest.TestCase):
    def test_init_page_state_uses_shared_default_origin(self) -> None:
        fake_streamlit = SimpleNamespace(session_state={})

        with patch.object(page, "st", fake_streamlit):
            page._init_page_state()

        self.assertEqual(fake_streamlit.session_state[page._HEATMAP_ORIGIN_FIELD], DEFAULT_ORIGIN)
        self.assertEqual(fake_streamlit.session_state["heatmap_cargo"], 30.0)


if __name__ == "__main__":
    unittest.main()
