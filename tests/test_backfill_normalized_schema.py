import tempfile
import unittest
from pathlib import Path

from calcs.backfill_normalized_schema import (
    BackfillContext,
    ColumnFingerprint,
    MigrationReport,
    TableFingerprint,
    TargetTables,
    _candidate_aliases,
    _match_shapes,
    _record_bulk_item_write,
    _record_bulk_run_write,
    _record_route_write,
    validate_target_tables,
)


class _DummyAnomalies:
    def record(self, **_kwargs) -> None:
        return None


def _fingerprint(table_name: str, columns: list[str]) -> TableFingerprint:
    return TableFingerprint(
        table_name=table_name,
        row_count=0,
        columns=[
            ColumnFingerprint(
                name=column,
                data_type="text",
                udt_name="text",
                is_nullable=True,
                ordinal_position=index,
            )
            for index, column in enumerate(columns, start=1)
        ],
        matches=_match_shapes(set(columns)),
    )


class BackfillNormalizedSchemaTests(unittest.TestCase):
    def test_shape_classifier_uses_table_columns_not_table_name(self) -> None:
        fingerprint = _fingerprint(
            "mystery_table",
            [
                "id",
                "origin_key",
                "origin_name",
                "origin_lat",
                "origin_lon",
                "destiny_key",
                "destiny_name",
                "destiny_lat",
                "destiny_lon",
                "profile_requested",
                "distance_km",
            ],
        )

        self.assertTrue(fingerprint.matches_spec("legacy_routes"))
        self.assertEqual(fingerprint.primary_match.spec_name, "legacy_routes")

    def test_validate_target_tables_rejects_wrong_shape_even_when_name_matches(self) -> None:
        targets = TargetTables().validated()
        fingerprints = {
            targets.locations: _fingerprint(targets.locations, ["id", "lat6", "lon6", "label"]),
            targets.aliases: _fingerprint(targets.aliases, ["place_key", "alias_label", "location_id"]),
            targets.route_cache: _fingerprint(
                targets.route_cache,
                [
                    "id",
                    "origin_key",
                    "origin_name",
                    "origin_lat",
                    "origin_lon",
                    "destiny_key",
                    "destiny_name",
                    "destiny_lat",
                    "destiny_lon",
                    "profile_requested",
                    "distance_km",
                ],
            ),
            targets.bulk_runs: _fingerprint(
                targets.bulk_runs,
                ["run_id", "selector_hash", "origin_location_id", "destination_set_id", "status"],
            ),
            targets.bulk_items: _fingerprint(
                targets.bulk_items,
                ["run_id", "scenario_key", "input_destiny", "status", "destination_location_id"],
            ),
        }

        with self.assertRaises(RuntimeError) as exc:
            validate_target_tables(fingerprints, targets)

        self.assertIn("normalized_route_cache", str(exc.exception))

    def test_write_counters_dedupe_repeated_target_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            report = MigrationReport(
                mode="dry-run",
                database_target="test",
                targets=TargetTables(),
                fingerprint_path=Path(tmp_dir) / "fingerprint.json",
                summary_path=Path(tmp_dir) / "summary.json",
                anomaly_path=Path(tmp_dir) / "anomalies.jsonl",
            )
            context = BackfillContext(
                conn=None,  # type: ignore[arg-type]
                dry_run=True,
                targets=TargetTables(),
                port_index={},
                report=report,
                anomalies=_DummyAnomalies(),
            )

            _record_route_write(context, origin_location_id=1, destiny_location_id=2, is_hgv=True, existed=False)
            _record_route_write(context, origin_location_id=1, destiny_location_id=2, is_hgv=True, existed=False)
            _record_bulk_run_write(context, run_id="run-1", existed=True)
            _record_bulk_run_write(context, run_id="run-1", existed=True)
            _record_bulk_item_write(context, run_id="run-1", scenario_key="a", existed=False)
            _record_bulk_item_write(context, run_id="run-1", scenario_key="a", existed=False)

            self.assertEqual(report.phase("routes").rows_created, 1)
            self.assertEqual(report.phase("bulk_runs").rows_reused, 1)
            self.assertEqual(report.phase("bulk_run_items").rows_created, 1)

    def test_candidate_aliases_normalize_and_dedupe_variants(self) -> None:
        aliases = _candidate_aliases("Pelotas, RS", "pelotas, rs", "Pelotas, Brasil", "Pelotas")
        self.assertEqual(aliases, ["Pelotas, RS", "Pelotas"])


if __name__ == "__main__":
    unittest.main()
