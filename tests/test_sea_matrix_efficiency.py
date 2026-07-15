import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.cabotage.sea_matrix_efficiency import (
    _build_port_lookup,
    _resolve_matrix_port_name,
    enrich_sea_matrix_with_efficiency,
)


class SeaMatrixEfficiencyTests(unittest.TestCase):
    def test_existing_local_base_matrix_is_not_replaced_by_remote_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            matrix_path = root / "sea_matrix.json"
            voyages_path = root / "voyages.csv"
            stops_path = root / "stops.csv"
            mrv_path = root / "mrv.json"

            matrix_path.write_text(
                json.dumps(
                    {
                        "ports": [
                            {"name": "Port A", "slug": "port-a"},
                            {"name": "Port B", "slug": "port-b"},
                        ],
                        "matrix": {
                            "Port A": {"Port B": 185.2},
                            "Port B": {"Port A": 185.2},
                        },
                    }
                ),
                encoding="utf-8",
            )
            self._write_csv(
                voyages_path,
                ["voyage_id", "imo"],
                [["voyage-1", "1234567"]],
            )
            self._write_csv(
                stops_path,
                [
                    "voyage_id",
                    "sequence",
                    "port_name",
                    "net_weight_t",
                    "net_teu",
                ],
                [
                    ["voyage-1", 0, "Port A", 100.0, 5.0],
                    ["voyage-1", 1, "Port B", -100.0, -5.0],
                ],
            )
            mrv_path.write_text(
                json.dumps(
                    {
                        "ships": [
                            {
                                "imo": "1234567",
                                "records": [
                                    {
                                        "reporting_period": 2024,
                                        "average_fuel_consumption_per_transport_work_g_per_tonne_nmile": 7.5,
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def resolve_non_matrix_asset(candidate: Path | str) -> Path:
                resolved_candidate = Path(candidate).resolve()
                self.assertNotEqual(resolved_candidate, matrix_path.resolve())
                return resolved_candidate

            with patch(
                "modules.cabotage.sea_matrix_efficiency.resolve_data_asset_path",
                side_effect=resolve_non_matrix_asset,
            ):
                payload, summary = enrich_sea_matrix_with_efficiency(
                    sea_matrix_path=matrix_path,
                    voyages_csv_path=voyages_path,
                    stops_csv_path=stops_path,
                    mrv_json_path=mrv_path,
                    possible_pairs_only=False,
                    matched_pairs_only=True,
                    prefer_local_voyage_inputs=True,
                )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["fuel_g_per_tnm_weighted_mean"], 7.5)
        self.assertEqual(stats["matched_segment_count"], 1)
        self.assertEqual(summary["directional_pairs"], 1)

    def test_base_matrix_maps_manaus_terminal_names_and_codes(self) -> None:
        matrix_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "processed"
            / "cabotage_data"
            / "sea_matrix.json"
        )
        payload = json.loads(matrix_path.read_text(encoding="utf-8-sig"))
        lookup = _build_port_lookup(payload)

        for row in (
            {"port_name": "Porto Chibatão"},
            {"port_name": "Super Terminais Comércio e Indústria"},
            {"port_code": "BRAM006"},
            {"port_code": "BRAM012"},
        ):
            with self.subTest(row=row):
                self.assertEqual(
                    _resolve_matrix_port_name(row, lookup),
                    "Porto de Manaus",
                )

    @staticmethod
    def _write_csv(path: Path, columns: list[str], rows: list[list[object]]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
