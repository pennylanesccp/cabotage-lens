import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.main.cards.warnings import render_route_quality_warnings
from modules.multimodal.route_quality import build_route_quality_warnings


class RouteQualityWarningTests(unittest.TestCase):
    def _geometry(self, **overrides):
        geometry = {
            "port_origin": {"name": "Porto de Santos"},
            "port_destiny": {"name": "Porto de Santos"},
            "road_direct": {"distance_km": 77.2},
            "first_mile": {"distance_km": 86.174},
            "last_mile": {"distance_km": 9.031},
            "sea_leg": {
                "distance_km": 0.0,
                "source": "haversine",
                "distance_provenance": {"source_type": "haversine_fallback"},
            },
        }
        geometry.update(overrides)
        return geometry

    def test_same_port_zero_fallback_route_gets_cabotage_warnings(self) -> None:
        warnings = build_route_quality_warnings(self._geometry())
        codes = {warning["code"] for warning in warnings}

        self.assertIn("same_port", codes)
        self.assertIn("zero_maritime_distance", codes)
        self.assertIn("fallback_maritime_distance", codes)
        self.assertIn("access_dominates_local_cabotage", codes)

    def test_matrix_route_with_material_sea_leg_has_no_quality_warning(self) -> None:
        warnings = build_route_quality_warnings(
            self._geometry(
                port_destiny={"name": "Porto de Manaus"},
                road_direct={"distance_km": 3880.0},
                first_mile={"distance_km": 85.0},
                last_mile={"distance_km": 20.0},
                sea_leg={
                    "distance_km": 6111.6,
                    "source": "matrix",
                    "distance_provenance": {"source_type": "seamatrix"},
                },
            )
        )

        self.assertEqual(warnings, [])

    def test_warning_renderer_suppresses_fallback_warning_in_streamlit_ui(self) -> None:
        fake_streamlit = SimpleNamespace(warning=Mock())
        results = {
            "route_quality_warnings": [
                {
                    "code": "fallback_maritime_distance",
                    "title": "Cabotage route warning",
                    "message": "The maritime distance was estimated using fallback logic; treat this result as a screening estimate.",
                }
            ]
        }

        with patch("app.main.cards.warnings.st", fake_streamlit):
            render_route_quality_warnings(results)

        fake_streamlit.warning.assert_not_called()

    def test_warning_renderer_keeps_other_route_quality_warnings(self) -> None:
        fake_streamlit = SimpleNamespace(warning=Mock())
        results = {
            "route_quality_warnings": [
                {
                    "code": "same_port",
                    "title": "Cabotage route warning",
                    "message": (
                        "The selected origin and destination ports are the same, so this result should not be "
                        "interpreted as a meaningful cabotage alternative."
                    ),
                },
                {
                    "code": "fallback_maritime_distance",
                    "title": "Cabotage route warning",
                    "message": "The maritime distance was estimated using fallback logic; treat this result as a screening estimate.",
                },
            ]
        }

        with patch("app.main.cards.warnings.st", fake_streamlit):
            render_route_quality_warnings(results)

        fake_streamlit.warning.assert_called_once()
        warning_text = fake_streamlit.warning.call_args.args[0]
        self.assertIn("Route quality warning", warning_text)
        self.assertIn("same", warning_text)
        self.assertNotIn("fallback logic", warning_text)


if __name__ == "__main__":
    unittest.main()
