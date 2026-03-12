import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import compare_bulk


class CompareBulkCliTests(unittest.TestCase):
    def test_main_uses_bulk_engine(self) -> None:
        argv = [
            "compare_bulk.py",
            "--origin",
            "Pelotas, RS",
            "--dests-file",
            str(Path("destinations.txt")),
        ]
        outcome = {
            "summary_rows": [],
            "success_count": 1,
            "fail_count": 0,
            "exact_success_count": 1,
            "approximated_success_count": 0,
            "unresolved_fail_count": 0,
            "duration_s": 1.5,
            "run_id": "run-1",
            "shuffle_seed_used": 10,
            "performance": {"timings_s": {}, "counts": {}, "provider_calls": {}},
        }

        with patch.object(sys, "argv", argv), patch(
            "scripts.compare_bulk.init_logging"
        ), patch(
            "scripts.compare_bulk.load_destinations",
            return_value=["Manaus, AM"],
        ), patch(
            "scripts.compare_bulk.run_bulk_evaluation",
            return_value=outcome,
        ) as run_bulk_mock, patch(
            "scripts.compare_bulk._write_summary_csv"
        ):
            exit_code = compare_bulk.main()

        self.assertEqual(exit_code, 0)
        run_bulk_mock.assert_called_once()
        self.assertEqual(run_bulk_mock.call_args.kwargs["origin"], "Pelotas, RS")
        self.assertEqual(run_bulk_mock.call_args.kwargs["dest_list"], ["Manaus, AM"])
