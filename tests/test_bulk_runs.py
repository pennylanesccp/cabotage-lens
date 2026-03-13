import unittest
from collections import deque
from unittest.mock import patch

from modules.infra.db.bulk_results import BulkResultSummary, list_results, summarize_results, upsert_result as upsert_bulk_result
from modules.infra.db.bulk_runs import (
    BulkRunSelector,
    finish_run,
    insert_run_result,
    start_run,
)


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
        self._rows = deque([(row, rows or [])])

    def queue(self, *, row=None, rows=None) -> None:
        self._rows.append((row, rows or []))

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        row, rows = self._rows.popleft() if self._rows else (None, [])
        return _FakeCursor(row=row, rows=rows)


class BulkRunPersistenceTests(unittest.TestCase):
    def _selector(self) -> BulkRunSelector:
        return BulkRunSelector(
            origin_key="pelotas, rs",
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

    def test_start_run_and_finish_run_issue_postgres_writes(self) -> None:
        conn = _RecordingConnection()
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
        self.assertIn("INSERT INTO bulk_evaluation_runs", conn.statements[0][0])
        self.assertIn("UPDATE bulk_evaluation_runs", conn.statements[1][0])

    def test_insert_run_result_persists_approximation_metadata(self) -> None:
        conn = _RecordingConnection()

        with patch("modules.infra.db.bulk_runs.ensure_run_results_table"):
            insert_run_result(
                conn,
                run_id="run-123",
                scenario_key="scenario-1",
                origin_key="pelotas, rs",
                origin_name="Pelotas, RS",
                origin_lat=-31.77,
                origin_lon=-52.34,
                origin_uf="RS",
                destiny_key="manaus, am",
                destiny_name="Manaus, AM",
                destiny_lat=-3.119,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                input_origin="Pelotas, RS",
                input_destiny="Manaus, AM",
                destination_set_id="city_dests_over50k.txt",
                port_origin_name="Rio Grande",
                port_destiny_name="Manaus",
                status="ok",
                error_message=None,
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
            )

        statement, params = conn.statements[0]
        self.assertIn("INSERT INTO bulk_evaluation_run_results", statement)
        self.assertEqual(params[29], 1)
        self.assertEqual(params[30], "nearest_exact_delta_straight_line")
        self.assertEqual(params[31], "Belem, PA")
        self.assertAlmostEqual(float(params[32]), 3650.0)
        self.assertAlmostEqual(float(params[33]), 250.0)

    def test_bulk_results_summary_and_listing_map_postgres_rows(self) -> None:
        selector = self._selector()
        conn = _RecordingConnection(
            row=(2, 1, 1, "2026-03-11 09:30:00", "run-2"),
        )
        conn.queue(
            rows=[
                (
                    "scenario-1",
                    "run-2",
                    selector.destination_set_id,
                    selector.origin_key,
                    "Pelotas, RS",
                    "Manaus, AM",
                    "Manaus, AM",
                    "manaus, am",
                    selector.cargo_t,
                    selector.truck_key,
                    selector.ors_profile,
                    selector.vessel_class,
                    1,
                    selector.hoteling_hours_per_call,
                    selector.port_calls,
                    1,
                    None,
                    None,
                    selector.t_per_teu_default,
                    None,
                    selector.allocation_load_factor,
                    0,
                    selector.port_ops_scenario,
                    "ok",
                    None,
                    -3.119,
                    -60.0217,
                    "AM",
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
                    1,
                    "nearest_exact_delta_straight_line",
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
        self.assertTrue(rows[0].is_approximation)
        self.assertEqual(rows[0].route_source, "nearest_exact_delta_straight_line")

    def test_upsert_bulk_result_writes_selector_and_route_metadata(self) -> None:
        conn = _RecordingConnection()

        with patch("modules.infra.db.bulk_results.ensure_results_table"):
            upsert_bulk_result(
                conn,
                scenario_key="scenario-approx",
                run_id="run-123",
                destination_set_id="city_dests_over50k.txt",
                origin_key="pelotas, rs",
                origin_name="Pelotas, RS",
                destiny_key="manaus, am",
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
                road_fuel_cost_r=15000.0,
                road_co2e_kg=9000.0,
                total_fuel_cost_r=11000.0,
                total_co2e_kg=5200.0,
            )

        statement, params = conn.statements[0]
        self.assertIn("INSERT INTO bulk_evaluation_results", statement)
        self.assertEqual(params[42], 1)
        self.assertEqual(params[43], "nearest_exact_delta_straight_line")
        self.assertEqual(params[44], "Belem, PA")


if __name__ == "__main__":
    unittest.main()
