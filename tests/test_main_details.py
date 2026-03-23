import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    unittest.main()
