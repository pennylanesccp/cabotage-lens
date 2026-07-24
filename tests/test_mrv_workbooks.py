import argparse
import tempfile
import unittest
from pathlib import Path

from calcs.extract_mrv_average_efficiency_by_imo import _load_requested_imos
from calcs.mrv_workbooks import discover_mrv_workbooks


class MrvWorkbookDiscoveryTests(unittest.TestCase):
    def test_discovers_one_workbook_per_year_in_chronological_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            names = [
                "2025-v18-EU MRV Publication of information.xlsx",
                "2022-v241-EU MRV Publication of information.xlsx",
                "notes.xlsx",
            ]
            for name in names:
                (raw_dir / name).touch()

            discovered = discover_mrv_workbooks(raw_dir)

            self.assertEqual(
                [path.name for path in discovered],
                [
                    "2022-v241-EU MRV Publication of information.xlsx",
                    "2025-v18-EU MRV Publication of information.xlsx",
                ],
            )

    def test_rejects_duplicate_workbooks_for_same_year(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            for name in (
                "2024-v184-EU MRV Publication of information.xlsx",
                "2024-v230-EU MRV Publication of information.xlsx",
            ):
                (raw_dir / name).touch()

            with self.assertRaisesRegex(ValueError, "2024"):
                discover_mrv_workbooks(raw_dir)

    def test_loads_unique_imos_from_normalized_voyages_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            voyages_csv = Path(tmpdir) / "voyages.csv"
            voyages_csv.write_text(
                "voyage_id,imo\nvoyage-1,1234567\nvoyage-2,7654321\n"
                "voyage-3,1234567\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(
                imo=[],
                imo_file=None,
                from_antaq_json=None,
                from_voyages_csv=voyages_csv,
            )

            self.assertEqual(
                _load_requested_imos(args),
                ["1234567", "7654321"],
            )


if __name__ == "__main__":
    unittest.main()
