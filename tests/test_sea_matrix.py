import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.cabotage.sea_matrix import SeaMatrix
from modules.cabotage.sea_matrix_efficiency import (
    DEPLOYMENT_REQUIRED_ROUTE,
    validate_enriched_sea_matrix_payload,
)
from modules.multimodal.builder import build_path_geometry_from_resolved


class SeaMatrixFileLoadingTests(unittest.TestCase):
    def test_existing_empty_matrix_file_is_rejected(self) -> None:
        payload = {
            "ports": [],
            "matrix": {},
            "voyage_fuel_g_per_tnm_directional": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sea_matrix.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            self.assertTrue(path.is_file())
            with self.assertRaisesRegex(
                ValueError,
                "contains no usable positive port-pair distances",
            ):
                SeaMatrix.from_json_path(path)

    def test_invalid_remote_cache_falls_back_to_valid_local_matrix(self) -> None:
        empty_payload = {
            "ports": [],
            "matrix": {},
            "voyage_fuel_g_per_tnm_directional": {},
        }
        valid_payload = {
            "matrix": {
                "Porto de Santos": {"Porto de Manaus": 6112.0},
                "Porto de Manaus": {"Porto de Santos": 6112.0},
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_path = root / "sea_matrix.json"
            cache_path = root / "cache" / "sea_matrix.json"
            cache_path.parent.mkdir()
            local_path.write_text(json.dumps(valid_payload), encoding="utf-8")
            cache_path.write_text(json.dumps(empty_payload), encoding="utf-8")

            with patch(
                "modules.cabotage.sea_matrix.resolve_data_asset_path",
                return_value=cache_path,
            ):
                sea_matrix = SeaMatrix.from_json_path(local_path)

        self.assertEqual(sea_matrix.get("Porto de Santos", "Porto de Manaus"), 6112.0)

    def test_tracked_matrix_supports_santos_manaus_directional_route(self) -> None:
        matrix_path = Path(__file__).resolve().parents[1] / "data" / "sea_matrix.json"
        payload = json.loads(matrix_path.read_text(encoding="utf-8-sig"))

        validation = validate_enriched_sea_matrix_payload(
            payload,
            required_route=DEPLOYMENT_REQUIRED_ROUTE,
        )

        route = validation["required_route"]
        self.assertGreater(route["distance_km"], 0.0)
        self.assertGreater(route["fuel_g_per_tnm_weighted_mean"], 0.0)
        self.assertGreater(route["segment_count"], 0)
        self.assertGreater(route["matched_segment_count"], 0)
        self.assertGreater(route["unique_imo_count"], 0)
        self.assertGreater(route["matched_imo_count"], 0)

    def test_santos_manaus_geometry_uses_directional_distance_and_coverage(self) -> None:
        matrix_path = Path(__file__).resolve().parents[1] / "data" / "sea_matrix.json"
        sea_matrix = SeaMatrix.from_json_dict(
            json.loads(matrix_path.read_text(encoding="utf-8-sig"))
        )
        expected = sea_matrix.best_directional_stats(*DEPLOYMENT_REQUIRED_ROUTE)
        self.assertIsNotNone(expected)

        geometry = build_path_geometry_from_resolved(
            {"label": "São Paulo, SP", "lat": -23.55, "lon": -46.63, "uf": "SP"},
            {"label": "Manaus, AM", "lat": -3.12, "lon": -60.02, "uf": "AM"},
            ors=object(),
            ports=[],
            sea_matrix=sea_matrix,
            port_origin={"name": "Porto de Santos", "lat": -23.96, "lon": -46.33},
            port_destiny={"name": "Porto de Manaus", "lat": -3.16, "lon": -60.01},
            first_mile_leg={"distance_km": 80.0, "source": "test"},
            route_resolver=lambda _start, _end, _name: {
                "distance_km": 100.0,
                "source": "test",
            },
        )

        self.assertIsNotNone(geometry)
        sea_leg = geometry["sea_leg"]
        assert expected is not None
        self.assertEqual(sea_leg["source"], "directional_corridor")
        self.assertEqual(
            sea_leg["fuel_g_per_tnm_source"],
            "sea_matrix_directional_corridor_weighted_mean",
        )
        self.assertEqual(sea_leg["distance_km"], expected["distance_km"])
        self.assertEqual(sea_leg["fuel_g_per_tnm"], expected["fuel_g_per_tnm_weighted_mean"])
        self.assertEqual(sea_leg["matched_segment_count"], expected["matched_segment_count"])
        self.assertEqual(sea_leg["matched_imo_count"], expected["matched_imo_count"])
        observed_legs = sea_leg["observed_port_pair_legs"]
        self.assertEqual(len(observed_legs), 2)
        self.assertEqual(observed_legs[0]["origin_port"], "Porto de Santos")
        self.assertEqual(observed_legs[0]["destination_port"], "Porto de Suape")
        self.assertEqual(observed_legs[1]["origin_port"], "Porto de Suape")
        self.assertEqual(observed_legs[1]["destination_port"], "Porto de Manaus")
        for observed_leg in observed_legs:
            self.assertGreater(observed_leg["observed_segment_count"], 0)
            self.assertGreater(observed_leg["distinct_voyage_count"], 0)
            self.assertGreater(observed_leg["distinct_imo_count"], 0)
            self.assertGreater(observed_leg["average_cargo_t"], 0.0)
            self.assertGreater(observed_leg["distance_nm"], 0.0)
            self.assertGreater(
                observed_leg["weighted_fuel_intensity_g_per_tnm"],
                0.0,
            )


if __name__ == "__main__":
    unittest.main()
