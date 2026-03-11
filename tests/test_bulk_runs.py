import unittest

from modules.infra.db.bulk_runs import (
    BulkRunSelector,
    finish_run,
    get_latest_completed_run,
    insert_run_result,
    list_available_cargo_values,
    list_available_origins,
    list_run_results,
    start_run,
)
from modules.infra.db.bulk_results import upsert_result as upsert_bulk_result
from modules.infra.db.core import db_session


class BulkRunPersistenceTests(unittest.TestCase):
    def _selector(self, *, origin_key: str = "pelotas, rs", cargo_t: float = 30.0) -> BulkRunSelector:
        return BulkRunSelector(
            origin_key=origin_key,
            cargo_t=cargo_t,
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

    def test_run_lifecycle_and_queries(self) -> None:
        selector = self._selector()
        with db_session(":memory:", backend="sqlite") as conn:
            run_id = start_run(
                conn,
                selector=selector,
                origin_name="Pelotas, RS",
                input_origin="Pelotas, RS",
                destination_count=2,
            )
            insert_run_result(
                conn,
                run_id=run_id,
                scenario_key="scenario-1",
                origin_key=selector.origin_key,
                origin_name="Pelotas, RS",
                origin_lat=-31.7700,
                origin_lon=-52.3400,
                origin_uf="RS",
                destiny_key="manaus, am",
                destiny_name="Manaus, AM",
                destiny_lat=-3.1190,
                destiny_lon=-60.0217,
                destiny_uf="AM",
                input_origin="Pelotas, RS",
                input_destiny="Manaus, AM",
                destination_set_id=selector.destination_set_id,
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
            finish_run(
                conn,
                run_id=run_id,
                status="completed",
                success_count=1,
                fail_count=0,
                duration_s=12.5,
            )

            latest = get_latest_completed_run(conn, selector=selector)
            self.assertIsNotNone(latest)
            self.assertEqual(latest.run_id, run_id)
            self.assertEqual(latest.success_count, 1)

            rows = list_run_results(conn, run_id=run_id)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].destiny_name, "Manaus, AM")
            self.assertAlmostEqual(rows[0].cost_delta_r or 0.0, 4000.0)
            self.assertTrue(rows[0].is_approximation)
            self.assertEqual(rows[0].route_source, "nearest_exact_delta_straight_line")
            self.assertEqual(rows[0].approximation_reference_destiny, "Belem, PA")
            self.assertAlmostEqual(rows[0].approximation_reference_distance_km or 0.0, 3650.0)
            self.assertAlmostEqual(rows[0].approximation_delta_straight_line_km or 0.0, 250.0)

            origins = list_available_origins(conn, destination_set_id=selector.destination_set_id)
            self.assertEqual(origins, ["Pelotas, RS"])

            cargos = list_available_cargo_values(
                conn,
                origin_key=selector.origin_key,
                destination_set_id=selector.destination_set_id,
            )
            self.assertEqual(cargos, [30.0])

    def test_list_available_origins_orders_case_insensitively_and_skips_blank_names(self) -> None:
        with db_session(":memory:", backend="sqlite") as conn:
            for origin_name, origin_key in [
                ("santos, SP", "santos, sp"),
                ("Aracaju, SE", "aracaju, se"),
                ("santos, SP", "santos, sp"),
                ("   ", "blank"),
            ]:
                run_id = start_run(
                    conn,
                    selector=self._selector(origin_key=origin_key),
                    origin_name=origin_name,
                    input_origin=origin_name,
                    destination_count=1,
                )
                finish_run(
                    conn,
                    run_id=run_id,
                    status="completed",
                    success_count=1,
                    fail_count=0,
                    duration_s=1.0,
                )

            running_run_id = start_run(
                conn,
                selector=self._selector(origin_key="belem, pa"),
                origin_name="Belem, PA",
                input_origin="Belem, PA",
                destination_count=1,
            )
            self.assertIsInstance(running_run_id, str)

            origins = list_available_origins(conn, destination_set_id="city_dests_over50k.txt")

            self.assertEqual(origins, ["Aracaju, SE", "santos, SP"])

    def test_bulk_results_persists_approximation_metadata(self) -> None:
        with db_session(":memory:", backend="sqlite") as conn:
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

            row = conn.execute(
                """
                SELECT
                      is_approximation
                    , route_source
                    , approximation_reference_destiny
                    , approximation_reference_distance_km
                    , approximation_delta_straight_line_km
                FROM bulk_evaluation_results
                WHERE scenario_key = ?
                """,
                ("scenario-approx",),
            ).fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row[0], 1)
            self.assertEqual(row[1], "nearest_exact_delta_straight_line")
            self.assertEqual(row[2], "Belem, PA")
            self.assertAlmostEqual(float(row[3]), 3650.0)
            self.assertAlmostEqual(float(row[4]), 250.0)


if __name__ == "__main__":
    unittest.main()
