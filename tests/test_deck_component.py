import unittest

from app.components.deck import inject_modifier_wheel_zoom


class DeckComponentTests(unittest.TestCase):
    def test_inject_modifier_wheel_zoom_adds_shared_style_and_script(self) -> None:
        original_html = "<html><head></head><body><script>const deckInstance = createDeck({});\n\n  </script>\n</html>"

        injected_html = inject_modifier_wheel_zoom(original_html)

        self.assertIn("window.__ecoFreightDeck = createDeck({", injected_html)
        self.assertIn("enableModifierWheelZoom", injected_html)
        self.assertIn("map.scrollZoom.disable()", injected_html)
        self.assertIn("<style>", injected_html)


if __name__ == "__main__":
    unittest.main()
