import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calcs.backfill_normalized_schema import (
    BackfillContext,
    ColumnFingerprint,
    MigrationReport,
    TableFingerprint,
    TargetTables,
    _candidate_aliases,
    _location_from_coords,
    _match_shapes,
    _record_bulk_item_write,
    _record_bulk_run_write,
    _record_route_write,
    _upsert_alias_with_report,
    classify_tables,
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
    def _context(self) -> BackfillContext:
        tmp_dir = Path(tempfile.mkdtemp())
        report = MigrationReport(
            mode="dry-run",
            database_target="test",
            targets=TargetTables(),
            fingerprint_path=tmp_dir / "fingerprint.json",
            summary_path=tmp_dir / "summary.json",
            anomaly_path=tmp_dir / "anomalies.jsonl",
        )
        return BackfillContext(
            conn=object(),  # type: ignore[arg-type]
            dry_run=True,
            targets=TargetTables(),
            port_index={},
            report=report,
            anomalies=_DummyAnomalies(),
        )

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

    def test_bulk_run_results_shape_prefers_run_items_not_wide_or_runs(self) -> None:
        fingerprint = _fingerprint(
            "legacy_run_results_like",
            [
                "run_id",
                "scenario_key",
                "origin_key",
                "origin_name",
                "origin_lat",
                "origin_lon",
                "origin_uf",
                "destiny_key",
                "destiny_name",
                "destiny_lat",
                "destiny_lon",
                "destiny_uf",
                "input_origin",
                "input_destiny",
                "destination_set_id",
                "port_origin_name",
                "port_destiny_name",
                "status",
                "error_message",
                "road_cost_r",
                "multimodal_cost_r",
                "cost_delta_r",
                "cost_savings_pct",
                "road_emissions_kg",
                "multimodal_emissions_kg",
                "emissions_delta_kg",
                "emissions_savings_pct",
                "road_distance_km",
                "sea_km",
                "insertion_timestamp",
                "updated_timestamp",
            ],
        )

        self.assertEqual(fingerprint.primary_match.spec_name, "legacy_bulk_run_items")
        self.assertFalse(fingerprint.matches_spec("legacy_bulk_results_wide"))
        self.assertFalse(fingerprint.matches_spec("legacy_bulk_runs"))

    def test_classify_tables_assigns_source_tables_to_single_primary_role(self) -> None:
        targets = TargetTables().validated()
        fingerprints = {
            "bulk_evaluation_runs": _fingerprint(
                "bulk_evaluation_runs",
                [
                    "run_id",
                    "origin_key",
                    "origin_name",
                    "input_origin",
                    "cargo_t",
                    "truck_key",
                    "ors_profile",
                    "destination_set_id",
                    "destination_count",
                    "success_count",
                    "fail_count",
                    "status",
                ],
            ),
            "bulk_evaluation_run_results": _fingerprint(
                "bulk_evaluation_run_results",
                [
                    "run_id",
                    "scenario_key",
                    "origin_key",
                    "destiny_key",
                    "input_destiny",
                    "status",
                    "road_cost_r",
                    "multimodal_cost_r",
                ],
            ),
            "bulk_evaluation_results": _fingerprint(
                "bulk_evaluation_results",
                [
                    "scenario_key",
                    "origin_name",
                    "destiny_name",
                    "input_origin",
                    "input_destiny",
                    "cargo_t",
                    "truck_key",
                    "ors_profile",
                    "road_fuel_cost_r",
                    "total_fuel_cost_r",
                    "status",
                ],
            ),
        }

        source_tables, _, _ = classify_tables(fingerprints, targets=targets)

        self.assertEqual(source_tables["legacy_bulk_runs"], ["bulk_evaluation_runs"])
        self.assertEqual(source_tables["legacy_bulk_run_items"], ["bulk_evaluation_run_results"])
        self.assertEqual(source_tables["legacy_bulk_results_wide"], ["bulk_evaluation_results"])

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

    def test_location_cache_skips_repeated_coord_queries(self) -> None:
        context = self._context()
        with patch(
            "calcs.backfill_normalized_schema.get_location_by_coords",
            return_value=None,
        ) as get_mock, patch(
            "calcs.backfill_normalized_schema.get_or_create_location",
            return_value={"location_id": 11, "lat": -31.77, "lon": -52.34},
        ) as create_mock:
            first = _location_from_coords(context, lat=-31.7700001, lon=-52.3400001, label="Pelotas", source="test")
            second = _location_from_coords(context, lat=-31.7700002, lon=-52.3400002, label="Pelotas", source="test")

        self.assertEqual(first["location_id"], 11)
        self.assertEqual(second["location_id"], 11)
        self.assertEqual(get_mock.call_count, 1)
        self.assertEqual(create_mock.call_count, 1)

    def test_alias_cache_skips_repeated_alias_upserts(self) -> None:
        context = self._context()
        with patch(
            "calcs.backfill_normalized_schema.find_point",
            return_value=None,
        ) as find_mock, patch(
            "calcs.backfill_normalized_schema.upsert_alias",
            return_value={"place_key": "pelotas, rs", "location_id": 11},
        ) as upsert_mock:
            _upsert_alias_with_report(context, place="Pelotas, RS", alias_label="Pelotas, RS", location_id=11, source="test")
            _upsert_alias_with_report(context, place="Pelotas, RS", alias_label="Pelotas, RS", location_id=11, source="test")

        self.assertEqual(find_mock.call_count, 1)
        self.assertEqual(upsert_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
