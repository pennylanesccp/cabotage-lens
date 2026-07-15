import unittest
from unittest.mock import Mock, patch

from app.components.deck import inject_modifier_wheel_zoom, render_deck_chart


class DeckComponentTests(unittest.TestCase):
    def test_inject_modifier_wheel_zoom_adds_shared_style_and_script(self) -> None:
        original_html = "<html><head></head><body><script>const deckInstance = createDeck({});\n\n  </script>\n</html>"

        injected_html = inject_modifier_wheel_zoom(original_html)

        self.assertIn("window.__ecoFreightDeck = createDeck({", injected_html)
        self.assertIn("enableModifierWheelZoom", injected_html)
        self.assertIn("map.scrollZoom.disable()", injected_html)
        self.assertIn("<style>", injected_html)

    def test_render_deck_chart_passes_large_raw_html_to_streamlit_iframe(self) -> None:
        deck = Mock()
        large_payload = "x" * (2 * 1024 * 1024)
        deck.to_html.return_value = (
            "<html><head></head><body>"
            f"{large_payload}"
            "<script>const deckInstance = createDeck({});\n\n  </script></html>"
        )

        with patch("app.components.deck.st.iframe") as iframe:
            render_deck_chart(deck, height=620, require_ctrl_for_wheel_zoom=True)

        embedded_html = iframe.call_args.args[0]
        self.assertTrue(embedded_html.startswith("<html>"))
        self.assertNotIn("data:text/html", embedded_html)
        self.assertIn("window.__ecoFreightDeck = createDeck({", embedded_html)
        iframe.assert_called_once_with(embedded_html, height=620)


if __name__ == "__main__":
    unittest.main()
