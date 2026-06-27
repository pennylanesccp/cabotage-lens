import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main.details.assumptions import _assumptions_table
from app.main.details import render_details


class MainDetailsTests(unittest.TestCase):
    def test_render_details_hides_empty_sections_before_results(self) -> None:
        fake_streamlit = SimpleNamespace(
            markdown=Mock(),
            expander=Mock(return_value=contextlib.nullcontext()),
        )

        with patch("app.main.details.st", fake_streamlit):
            render_details(payload={}, geo=None, results=None)

        fake_streamlit.markdown.assert_not_called()
        fake_streamlit.expander.assert_not_called()

    def test_assumptions_show_maritime_distance_provenance(self) -> None:
        results = {
            "inputs": {},
            "multimodal": {
                "sea": {
                    "distance_source": "SeaMatrix haversine fallback",
                    "distance_provenance": {
                        "source": "SeaMatrix haversine fallback",
                        "source_type": "haversine_fallback",
                    },
                }
            },
        }

        table = _assumptions_table(results=results, payload={})
        rows = {row["Parameter"]: row for row in table.to_dict("records")}

        self.assertIn("Maritime distance source", rows)
        self.assertIn("Fallback estimate", rows["Maritime distance source"]["Value"])
        self.assertIn("haversine_fallback", rows["Maritime distance source"]["Value"])
        self.assertIn("route confidence", rows["Maritime distance source"]["Description"])
        self.assertIn("Maritime distance note", rows)
        self.assertIn("Fallback estimate", rows["Maritime distance note"]["Value"])


if __name__ == "__main__":
    unittest.main()
