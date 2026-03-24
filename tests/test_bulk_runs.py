import unittest
from collections import deque
from unittest.mock import patch

from modules.infra.db.bulk_results import BulkResultSummary, list_results, summarize_results, upsert_result as upsert_bulk_result
from modules.infra.db.bulk_runs import BulkRunSelector, finish_run, insert_run_result, insert_run_results, start_run


class _FakeCursor:
    def __init__(self, *, row=None, rows=None) -> None:
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _RecordingConnection:
    def __init__(self, *, row=None, rows=None) -> None:
        self.statements = []
        self.executemany_calls = []
        self._rows = deque([(row, rows or [])])

    def queue(self, *, row=None, rows=None) -> None:
        self._rows.append((row, rows or []))

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        row, rows = self._rows.popleft() if self._rows else (None, [])
        return _FakeCursor(row=row, rows=rows)

    def executemany(self, sql, rows):
        batch = [tuple(row) for row in rows]
        self.executemany_calls.append((sql, batch))
        return _FakeCursor()


class BulkRunPersistenceTests(unittest.TestCase):
    def _selector(self) -> BulkRunSelector:
        return BulkRunSelector(
            origin_location_id=17,
            cargo_t=30.0,
            truck_key="semi_27t",
            ors_profile="driving-hgv",
            vessel_class="container_small",
            include_hoteling=True,
            hoteling_hours_per_call=14.0,
            port_calls=2,
            include_port_ops=True,
            port_moves_per_call=None,
            cargo_teu=None,
            t_per_teu_default=14.0,
            allocation_mode=None,
            allocation_load_factor=0.8,
            full_call_mode=False,
            port_ops_scenario="baseline",
            destination_set_id="city_dests_over50k.txt",
        )

    def test_start_run_and_finish_run_issue_normalized_bulk_run_writes(self) -> None:
        conn = _RecordingConnection(row=("run-123",))
        selector = self._selector()

        with patch("modules.infra.db.bulk_runs.ensure_runs_table"), patch(
            "modules.infra.db.bulk_runs.uuid.uuid4",
            return_value=type("UuidStub", (), {"hex": "run-123"})(),
        ):
            run_id = start_run(
                conn,
                selector=selector,
                origin_name="Pelotas, RS",
                input_origin="Pelotas, RS",
                destination_count=2,
            )
            finish_run(
                conn,
                run_id=run_id,
                status="completed",
                success_count=2,
                fail_count=0,
                duration_s=12.5,
            )

        self.assertEqual(run_id, "run-123")
        self.assertEqual(len(conn.statements), 2)
        self.assertIn("INSERT INTO bulk_runs", conn.statements[0][0])
        self.assertIn("UPDATE bulk_runs", conn.statements[1][0])

    def test_insert_run_result_persists_normalized_refs_and_metrics(self) -> None:
        conn = _RecordingConnection()

        with patch("modules.infra.db.bulk_runs.ensure_run_results_table"), patch(
            "modules.infra.db.bulk_runs._resolve_location_id",
            side_effect=[201, 301, 401, 501],
        ), patch(
            "modules.infra.db.bulk_runs._run_origin_location_id",
            return_value=17,
        ), patch(
            "modules.infra.db.bulk_runs._resolve_route_id",
            side_effect=[901, 902, 903, 904],
        ):
            insert_run_result(
                conn,
                run_id="run-123",
                scenario_key="scenario-1",
                input_destiny="Manaus, AM",
                destiny_name="Manaus, AM",
                destiny_lat=-3.119,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                port_origin_name="Rio Grande",
                port_origin_lat=-32.035,
                port_origin_lon=-52.098,
                port_destiny_name="Manaus",
                port_destiny_lat=-3.137,
                port_destiny_lon=-60.020,
                status="ok",
                road_cost_r=15000.0,
                multimodal_cost_r=11000.0,
                cost_delta_r=4000.0,
                cost_savings_pct=26.6667,
                road_emissions_kg=9000.0,
                multimodal_emissions_kg=5200.0,
                emissions_delta_kg=3800.0,
                emissions_savings_pct=42.2222,
                road_distance_km=3900.0,
                sea_km=3400.0,
                is_approximation=True,
                route_source="nearest_exact_delta_straight_line",
                approximation_reference_destiny="Belem, PA",
                approximation_reference_distance_km=3650.0,
                approximation_delta_straight_line_km=250.0,
                approximation_notes="Approximate direct-road distance from the nearest exact destination in the same bulk run.",
                ors_profile="driving-hgv",
            )

        statement, params = conn.statements[0]
        self.assertIn("INSERT INTO bulk_run_items", statement)
        self.assertEqual(params[3], 201)
        self.assertEqual(params[4], 301)
        self.assertEqual(params[5], 401)
        self.assertEqual(params[6], 901)
        self.assertEqual(params[7], 902)
        self.assertEqual(params[8], 903)
        self.assertEqual(params[29], "nearest_exact_delta_straight_line")
        self.assertEqual(params[30], 904)

    def test_insert_run_results_batches_remote_upserts(self) -> None:
        conn = _RecordingConnection()
        rows = [
            {
                "run_id": "run-123",
                "scenario_key": "scenario-1",
                "input_destiny": "Manaus, AM",
                "destination_location_id": 201,
                "port_origin_location_id": 301,
                "port_destiny_location_id": 401,
                "road_route_id": 901,
                "first_mile_route_id": 902,
                "last_mile_route_id": 903,
                "status": "ok",
                "road_cost_r": 15000.0,
                "multimodal_cost_r": 11000.0,
                "cost_delta_r": 4000.0,
                "ors_profile": "driving-hgv",
            },
            {
                "run_id": "run-123",
                "scenario_key": "scenario-2",
                "input_destiny": "Belem, PA",
                "destination_location_id": 202,
                "port_origin_location_id": 301,
                "port_destiny_location_id": 402,
                "road_route_id": 904,
                "first_mile_route_id": 902,
                "last_mile_route_id": 905,
                "status": "timeout",
                "error_message": "routing timed out",
                "ors_profile": "driving-hgv",
            },
        ]

        with patch("modules.infra.db.bulk_runs.ensure_run_results_table"), patch(
            "modules.infra.db.bulk_runs._resolve_location_id",
            side_effect=lambda conn, **kwargs: kwargs.get("location_id"),
        ), patch("modules.infra.db.bulk_runs._run_origin_location_id") as origin_mock:
            inserted = insert_run_results(conn, rows=rows)

        self.assertEqual(inserted, 2)
        self.assertEqual(len(conn.executemany_calls), 1)
        statement, batch = conn.executemany_calls[0]
        self.assertIn("INSERT INTO bulk_run_items", statement)
        self.assertEqual(len(batch), 2)
        self.assertEqual(batch[0][0], "run-123")
        self.assertEqual(batch[0][1], "scenario-1")
        self.assertEqual(batch[1][1], "scenario-2")
        origin_mock.assert_not_called()

    def test_ensure_run_results_table_applies_backfill_alters_even_when_schema_marked_ready(self) -> None:
        conn = _RecordingConnection()

        with patch("modules.infra.db.bulk_runs.schema_is_ready", return_value=True), patch(
            "modules.infra.db.bulk_runs.ensure_runs_table"
        ), patch(
            "modules.infra.db.bulk_runs.ensure_route_cache_table"
        ), patch(
            "modules.infra.db.bulk_runs.mark_schema_ready"
        ):
            from modules.infra.db.bulk_runs import ensure_run_results_table

            ensure_run_results_table(conn)

        executed_sql = "\n".join(statement for statement, _ in conn.statements)
        self.assertIn("ALTER TABLE bulk_run_items ADD COLUMN IF NOT EXISTS failed_step TEXT;", executed_sql)
        self.assertIn("ALTER TABLE bulk_run_items ADD COLUMN IF NOT EXISTS retryable BOOLEAN NOT NULL DEFAULT FALSE;", executed_sql)
        self.assertIn("CREATE INDEX IF NOT EXISTS idx_bulk_run_items_run_failure_diag", executed_sql)

    def test_bulk_results_summary_and_listing_map_latest_normalized_rows(self) -> None:
        selector = self._selector()
        conn = _RecordingConnection(row=(2, 1, 1, "2026-03-11 09:30:00", "run-2"))
        conn.queue(
            rows=[
                (
                    "scenario-1",
                    "run-2",
                    selector.destination_set_id,
                    selector.origin_location_id,
                    "Pelotas, RS",
                    "Pelotas, RS",
                    201,
                    "Manaus, AM",
                    "Manaus, AM",
                    selector.cargo_t,
                    selector.truck_key,
                    selector.ors_profile,
                    selector.vessel_class,
                    True,
                    selector.hoteling_hours_per_call,
                    selector.port_calls,
                    True,
                    None,
                    None,
                    selector.t_per_teu_default,
                    None,
                    selector.allocation_load_factor,
                    False,
                    selector.port_ops_scenario,
                    "ok",
                    None,
                    None,
                    None,
                    None,
                    None,
                    False,
                    None,
                    None,
                    -3.119,
                    -60.0217,
                    "AM",
                    "Rio Grande",
                    "Manaus",
                    15000.0,
                    11000.0,
                    4000.0,
                    26.6667,
                    9000.0,
                    5200.0,
                    3800.0,
                    42.2222,
                    3900.0,
                    3400.0,
                    True,
                    "nearest_exact_delta_straight_line",
                    "Belem, PA",
                    3650.0,
                    250.0,
                    "Approximate direct-road distance from the nearest exact destination in the same bulk run.",
                    "2026-03-11 09:30:00",
                )
            ]
        )

        with patch("modules.infra.db.bulk_results.ensure_results_table"):
            summary = summarize_results(conn, selector=selector)
            rows = list_results(conn, selector=selector, only_success=None)

        self.assertIsInstance(summary, BulkResultSummary)
        self.assertEqual(summary.row_count, 2)
        self.assertEqual(summary.latest_run_id, "run-2")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].destiny_name, "Manaus, AM")
        self.assertEqual(rows[0].origin_name, "Pelotas, RS")
        self.assertTrue(rows[0].is_approximation)
        self.assertEqual(rows[0].route_source, "nearest_exact_delta_straight_line")
        self.assertIsNone(rows[0].failure_reason)
        self.assertAlmostEqual(float(rows[0].road_cost_r or 0.0), 15000.0)

    def test_bulk_results_listing_falls_back_when_failure_columns_are_missing(self) -> None:
        selector = self._selector()
        conn = _RecordingConnection(
            rows=[
                (
                    "scenario-1",
                    "run-2",
                    selector.destination_set_id,
                    selector.origin_location_id,
                    "Pelotas, RS",
                    "Pelotas, RS",
                    201,
                    "Manaus, AM",
                    "Manaus, AM",
                    selector.cargo_t,
                    selector.truck_key,
                    selector.ors_profile,
                    selector.vessel_class,
                    True,
                    selector.hoteling_hours_per_call,
                    selector.port_calls,
                    True,
                    None,
                    None,
                    selector.t_per_teu_default,
                    None,
                    selector.allocation_load_factor,
                    False,
                    selector.port_ops_scenario,
                    "ok",
                    None,
                    None,
                    None,
                    None,
                    None,
                    False,
                    None,
                    None,
                    -3.119,
                    -60.0217,
                    "AM",
                    "Rio Grande",
                    "Manaus",
                    15000.0,
                    11000.0,
                    4000.0,
                    26.6667,
                    9000.0,
                    5200.0,
                    3800.0,
                    42.2222,
                    3900.0,
                    3400.0,
                    True,
                    "nearest_exact_delta_straight_line",
                    "Belem, PA",
                    3650.0,
                    250.0,
                    "Approximate direct-road distance from the nearest exact destination in the same bulk run.",
                    "2026-03-11 09:30:00",
                )
            ]
        )

        legacy_columns = {
            "id",
            "run_id",
            "scenario_key",
            "input_destiny",
            "destination_location_id",
            "port_origin_location_id",
            "port_destiny_location_id",
            "road_route_id",
            "first_mile_route_id",
            "last_mile_route_id",
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
            "is_approximation",
            "route_source",
            "approximation_reference_route_id",
            "approximation_delta_straight_line_km",
            "approximation_notes",
            "insertion_timestamp",
            "updated_timestamp",
        }

        with patch("modules.infra.db.bulk_results.ensure_results_table"), patch(
            "modules.infra.db.bulk_results.table_columns",
            return_value=legacy_columns,
        ):
            rows = list_results(conn, selector=selector, only_success=None)

        statement, _ = conn.statements[0]
        self.assertIn("NULL AS failed_step", statement)
        self.assertIn("FALSE AS retryable", statement)
        self.assertNotIn("i.failed_step", statement)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].failed_step)
        self.assertFalse(rows[0].retryable)

    def test_upsert_bulk_result_uses_normalized_item_writer(self) -> None:
        conn = _RecordingConnection()

        with patch("modules.infra.db.bulk_results.insert_run_result") as insert_mock:
            upsert_bulk_result(
                conn,
                run_id="run-123",
                scenario_key="scenario-approx",
                destination_set_id="city_dests_over50k.txt",
                origin_location_id=17,
                origin_name="Pelotas, RS",
                destiny_name="Manaus, AM",
                input_origin="Pelotas, RS",
                input_destiny="Manaus, AM",
                cargo_t=30.0,
                truck_key="semi_27t",
                ors_profile="driving-hgv",
                status="ok",
                is_approximation=True,
                route_source="nearest_exact_delta_straight_line",
                approximation_reference_destiny="Belem, PA",
                approximation_reference_distance_km=3650.0,
                approximation_delta_straight_line_km=250.0,
                approximation_notes="Approximate direct-road distance from the nearest exact destination in the same bulk run.",
                road_distance_km=3900.0,
                road_cost_r=15000.0,
                road_emissions_kg=9000.0,
                multimodal_cost_r=11000.0,
                multimodal_emissions_kg=5200.0,
            )

        insert_mock.assert_called_once()
        self.assertEqual(insert_mock.call_args.kwargs["run_id"], "run-123")
        self.assertEqual(insert_mock.call_args.kwargs["scenario_key"], "scenario-approx")
        self.assertEqual(insert_mock.call_args.kwargs["input_destiny"], "Manaus, AM")


if __name__ == "__main__":
    unittest.main()
