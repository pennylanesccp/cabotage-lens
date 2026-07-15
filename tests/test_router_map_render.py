import json
import unittest

from app.main.map.render import build_map_deck


class RouterMapRenderTests(unittest.TestCase):
    def test_text_layer_alignment_values_are_serialized_as_constants(self) -> None:
        geo = {
            "origin": {"lat": -23.5505, "lon": -46.6333, "label": "Sao Paulo, SP"},
            "destiny": {"lat": -9.975, "lon": -67.8243, "label": "Rio Branco, AC"},
            "port_origin": {"lat": -23.95, "lon": -46.32, "name": "Porto de Santos"},
            "port_destiny": {"lat": -23.95, "lon": -46.32, "name": "Porto de Santos"},
            "road_direct": {},
            "first_mile": {},
            "last_mile": {},
        }
        state = {
            "map_style": "Voyager",
            "map_center_lat": -15.0,
            "map_center_lon": -55.0,
            "map_zoom": 3.8,
            "map_show_first_last": False,
            "map_show_sea": False,
            "map_show_direct": True,
            "map_show_ports": True,
            "map_show_labels": True,
        }

        spec = json.loads(build_map_deck(geo, results={}, state=state).to_json())
        text_layers = [layer for layer in spec["layers"] if layer["@@type"] == "TextLayer"]

        self.assertEqual(len(text_layers), 2)
        self.assertEqual(text_layers[0]["getTextAnchor"], "middle")
        self.assertEqual(text_layers[0]["getAlignmentBaseline"], "center")
        self.assertEqual(text_layers[1]["getTextAnchor"], "middle")
        self.assertEqual(text_layers[1]["getAlignmentBaseline"], "bottom")


if __name__ == "__main__":
    unittest.main()
