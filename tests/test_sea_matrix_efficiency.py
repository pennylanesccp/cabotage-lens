import csv
import json
import tempfile
import unittest
from pathlib import Path
from typing import Iterable
from unittest.mock import patch

from modules.cabotage.sea_matrix_efficiency import (
    CORRIDOR_SELECTION_CRITERION,
    MARITIME_INTENSITY_SCHEMA_VERSION,
    PAIR_INTENSITY_METHOD,
    PAIR_INTENSITY_SCOPE,
    PAIR_INTENSITY_ZERO_WORK_SOURCE,
    ROUTE_OBSERVATION_MODE,
    _build_port_lookup,
    _collapse_consecutive_canonical_stops,
    _robust_fallback_statistic,
    _resolve_matrix_port_name,
    enrich_sea_matrix_with_efficiency,
    validate_enriched_sea_matrix_payload,
)


class SeaMatrixEfficiencyTests(unittest.TestCase):
    def test_direct_observed_voyage_uses_latest_exact_imo_intensity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, summary = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B"],
                matrix=self._symmetric_matrix({("Port A", "Port B"): 185.2}),
                voyages=[{"voyage_id": "voyage-1", "imo": "1234567"}],
                stops=[
                    self._stop("voyage-1", 0, "Port A", 100.0, 5.0),
                    self._stop("voyage-1", 1, "Port B", -100.0, -5.0),
                ],
                ships=[
                    self._ship(
                        "1234567",
                        [
                            self._record(2022, 99.0, source_file="old.xlsx"),
                            self._record(2024, 7.5, source_file="latest.xlsx"),
                        ],
                    )
                ],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["fuel_g_per_tnm_weighted_mean"], 7.5)
        self.assertEqual(stats["pair_intensity_g_per_tnm"], 7.5)
        self.assertEqual(stats["pair_intensity_method"], PAIR_INTENSITY_METHOD)
        self.assertEqual(stats["pair_intensity_scope"], PAIR_INTENSITY_SCOPE)
        self.assertEqual(stats["observed_transport_work_tnm"], 10000.0)
        self.assertEqual(stats["observed_fuel_kg"], 75.0)
        self.assertEqual(stats["matched_segment_count"], 1)
        self.assertEqual(stats["resolved_segment_count"], 1)
        self.assertEqual(stats["imo_intensity_voyage_count"], 1)
        self.assertEqual(
            stats["scenario_distance_method"],
            "arithmetic_mean_complete_observed_voyage_distances",
        )
        self.assertEqual(stats["scenario_distance_observation_count"], 1)
        self.assertEqual(stats["distance_km"], 185.2)
        self.assertEqual(
            stats["corridor_options"][0]["corridor_port_path"],
            ["Port A", "Port B"],
        )
        self.assertEqual(stats["route_observation_mode"], ROUTE_OBSERVATION_MODE)
        self.assertEqual(
            payload["voyage_fuel_g_per_tnm_directional_meta"][
                "maritime_intensity_schema_version"
            ],
            MARITIME_INTENSITY_SCHEMA_VERSION,
        )
        self.assertEqual(summary["directional_pairs"], 1)

        provenance = payload["voyage_intensity_provenance"]["voyage-1"]
        self.assertEqual(provenance["intensity_source"], "eu_mrv_imo_latest")
        self.assertEqual(provenance["reporting_period"], 2024)
        self.assertEqual(provenance["source_file"], "latest.xlsx")
        self.assertFalse(provenance["is_fallback"])

    def test_multistop_voyage_sums_variable_onboard_cargo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port X", "Port B"],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port X"): 185.2,
                        ("Port X", "Port B"): 92.6,
                        ("Port A", "Port B"): 277.8,
                    }
                ),
                voyages=[{"voyage_id": "voyage-multi", "imo": "1111111"}],
                stops=[
                    self._stop("voyage-multi", 0, "Port A", 100.0, 10.0),
                    self._stop("voyage-multi", 1, "Port X", -40.0, -4.0),
                    self._stop("voyage-multi", 2, "Port B", -60.0, -6.0),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["distance_km"], 277.8)
        self.assertEqual(stats["scenario_distance_observation_count"], 1)
        self.assertEqual(stats["segment_count"], 2)
        self.assertEqual(stats["voyage_count"], 1)
        self.assertEqual(stats["unique_imo_count"], 1)
        self.assertEqual(stats["observed_transport_work_tnm"], 13000.0)
        self.assertEqual(stats["observed_fuel_kg"], 130.0)

        selected_option = next(
            option
            for option in stats["corridor_options"]
            if option["corridor_port_path"] == ["Port A", "Port X", "Port B"]
        )
        self.assertEqual(selected_option["candidate_voyage_ids"], ["voyage-multi"])

    def test_debug_audit_exposes_real_multistop_reconstruction_values(self) -> None:
        voyage_id = "voyage_9612791_00011"
        real_stops = [
            {
                **self._stop(voyage_id, 0, "Porto de Santos", 9881.860, 866.0),
                "loaded_weight_t": 9881.860,
                "unloaded_weight_t": 0.0,
            },
            {
                **self._stop(voyage_id, 1, "Porto de Suape", 3859.579, 77.0),
                "loaded_weight_t": 11862.199,
                "unloaded_weight_t": 8002.620,
            },
            {
                **self._stop(voyage_id, 2, "Porto do Pecém", -4392.433, -354.0),
                "loaded_weight_t": 3231.914,
                "unloaded_weight_t": 7624.347,
            },
            {
                **self._stop(voyage_id, 3, "Porto de Manaus", -12325.900, -1018.0),
                "loaded_weight_t": 7571.660,
                "unloaded_weight_t": 19897.560,
            },
            {
                **self._stop(voyage_id, 4, "Porto de Santos", 1387.424, -48.0),
                "loaded_weight_t": 8038.360,
                "unloaded_weight_t": 6650.936,
            },
        ]

        enrichment_inputs = {
            "ports": [
                "Porto de Santos",
                "Porto de Suape",
                "Porto do Pecém",
                "Porto de Manaus",
            ],
            "matrix": self._symmetric_matrix(
                {
                    ("Porto de Santos", "Porto de Suape"): 2332.0,
                    ("Porto de Suape", "Porto do Pecém"): 940.4575739530403,
                    ("Porto do Pecém", "Porto de Manaus"): 2195.7202985863305,
                    ("Porto de Manaus", "Porto de Santos"): 6112.0,
                }
            ),
            "voyages": [{"voyage_id": voyage_id, "imo": "9612791"}],
            "stops": real_stops,
            "ships": [self._ship("9612791", [self._record(2023, 7.43)])],
        }

        with tempfile.TemporaryDirectory() as baseline_tmpdir:
            baseline_payload, baseline_summary = self._run_enrichment(
                Path(baseline_tmpdir),
                **enrichment_inputs,
            )

        with tempfile.TemporaryDirectory() as tmpdir, self.assertLogs(
            "modules.cabotage.sea_matrix_efficiency",
            level="DEBUG",
        ) as captured:
            payload, summary = self._run_enrichment(
                Path(tmpdir),
                **enrichment_inputs,
                audit_voyage_ids=voyage_id,
            )

        for candidate in (payload, baseline_payload):
            candidate["voyage_fuel_g_per_tnm_directional_meta"].pop(
                "generated_at",
                None,
            )
        self.assertEqual(payload, baseline_payload)
        self.assertEqual(summary, baseline_summary)

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Porto de Santos"][
            "Porto de Manaus"
        ]
        self.assertAlmostEqual(stats["observed_transport_work_tnm"], 39294668.494)
        self.assertAlmostEqual(stats["observed_fuel_kg"], 291959.386907)

        log_text = "\n".join(captured.output)
        self.assertIn(
            "maritime_voyage_reconstruction "
            "voyage_id=voyage_9612791_00011 imo=9612791",
            log_text,
        )
        self.assertIn("initial_onboard_weight_t=2976.894000", log_text)
        self.assertIn(
            "maritime_segment_reconstruction "
            "voyage_id=voyage_9612791_00011 imo=9612791 "
            "canonical_segment_index=0 origin_stop_sequence=0 "
            "destination_stop_sequence=1",
            log_text,
        )
        self.assertIn("departure_net_weight_t=9881.860000", log_text)
        self.assertIn("cargo_onboard_weight_t=12858.754000", log_text)
        self.assertIn("transport_work_tnm=16191476.419006", log_text)
        self.assertIn("fuel_consumption_kg=120302.669793", log_text)
        self.assertIn("distance_source=sea_matrix", log_text)
        self.assertIn("intensity_source=eu_mrv_imo_latest", log_text)
        self.assertIn(
            "canonical_segment_index=1 origin_stop_sequence=1 "
            "destination_stop_sequence=2",
            log_text,
        )
        self.assertIn("cargo_onboard_weight_t=16718.333000", log_text)
        self.assertIn("transport_work_tnm=8489677.588401", log_text)
        self.assertIn("fuel_consumption_kg=63078.304482", log_text)
        self.assertIn(
            "canonical_segment_index=2 origin_stop_sequence=2 "
            "destination_stop_sequence=3",
            log_text,
        )
        self.assertIn("cargo_onboard_weight_t=12325.900000", log_text)
        self.assertIn("transport_work_tnm=14613514.486148", log_text)
        self.assertIn("fuel_consumption_kg=108578.412632", log_text)
        self.assertIn(
            "maritime_voyage_subroute voyage_id=voyage_9612791_00011 "
            "imo=9612791 origin_sequence=0 destination_sequence=3 direct=False",
            log_text,
        )
        self.assertIn("transport_work_tnm=39294668.493555", log_text)
        self.assertIn("fuel_consumption_kg=291959.386907", log_text)
        self.assertIn(
            "maritime_pair_intensity origin='Porto de Santos' "
            "destination='Porto de Manaus'",
            log_text,
        )
        self.assertIn(
            "transport_work_weighted_mean_g_per_tnm=7.429999999999999",
            log_text,
        )
        self.assertIn("effective_source_counts={'eu_mrv_imo_latest': 1}", log_text)

    def test_collapsed_calls_preserve_loaded_and_unloaded_audit_totals(self) -> None:
        rows = [
            {
                "sequence": "0",
                "port_name": "Terminal A",
                "loaded_weight_t": "10",
                "unloaded_weight_t": "2",
                "net_weight_t": "8",
                "loaded_teu": "4",
                "unloaded_teu": "1",
                "net_teu": "3",
            },
            {
                "sequence": "1",
                "port_name": "Terminal B",
                "loaded_weight_t": "5",
                "unloaded_weight_t": "4",
                "net_weight_t": "1",
                "loaded_teu": "2",
                "unloaded_teu": "1",
                "net_teu": "1",
            },
        ]

        collapsed, collapsed_count = _collapse_consecutive_canonical_stops(
            rows,
            {"terminal a": "Porto A", "terminal b": "Porto A"},
        )

        self.assertEqual(collapsed_count, 1)
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0]["_source_sequences"], [0, 1])
        self.assertEqual(collapsed[0]["loaded_weight_t"], 15.0)
        self.assertEqual(collapsed[0]["unloaded_weight_t"], 6.0)
        self.assertEqual(collapsed[0]["net_weight_t"], 9.0)
        self.assertEqual(collapsed[0]["loaded_teu"], 6.0)
        self.assertEqual(collapsed[0]["unloaded_teu"], 2.0)
        self.assertEqual(collapsed[0]["net_teu"], 4.0)

    def test_same_corridor_sums_voyages_with_mixed_intensity_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B"],
                matrix=self._symmetric_matrix({("Port A", "Port B"): 185.2}),
                voyages=[
                    {"voyage_id": "exact", "imo": "1111111"},
                    {
                        "voyage_id": "class-fallback",
                        "imo": "2222222",
                        "vessel_class": "container_feeder",
                    },
                ],
                stops=[
                    self._stop("exact", 0, "Port A", 100.0, 10.0),
                    self._stop("exact", 1, "Port B", -100.0, -10.0),
                    self._stop("class-fallback", 0, "Port A", 50.0, 5.0),
                    self._stop("class-fallback", 1, "Port B", -50.0, -5.0),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
                class_payload={
                    "container_feeder": {
                        "fuel_g_per_tnm": {
                            "mean": 6.5,
                            "median": 6.1,
                            "trimmed_mean_1pct": 6.0,
                            "count": 10,
                        },
                    }
                },
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["candidate_voyage_count"], 2)
        self.assertEqual(stats["observed_transport_work_tnm"], 15000.0)
        self.assertEqual(stats["observed_fuel_kg"], 130.0)
        self.assertAlmostEqual(stats["fuel_g_per_tnm_weighted_mean"], 8.666667)
        self.assertEqual(stats["pair_intensity_positive_weight_voyage_count"], 2)
        self.assertEqual(stats["pair_intensity_effective_voyage_count"], 2)
        self.assertEqual(stats["pair_intensity_method"], PAIR_INTENSITY_METHOD)
        self.assertEqual(
            stats["intensity_source_counts"],
            {
                "eu_mrv_imo_latest": 1,
                "eu_mrv_vessel_class_trimmed_mean_1pct": 1,
            },
        )

    def test_robust_fallback_trims_one_percent_per_tail(self) -> None:
        values = [10.0] * 196 + [0.1, 0.2, 1000.0, 2000.0]

        robust = _robust_fallback_statistic(values)

        self.assertEqual(robust["intensity_g_per_tnm"], 10.0)
        self.assertEqual(robust["trim_count_each_tail"], 2)
        self.assertEqual(robust["excluded_sample_size"], 4)
        self.assertEqual(robust["retained_sample_size"], 196)
        self.assertEqual(
            robust["outlier_rule"],
            "symmetric_trim_1pct_each_tail_floor_count",
        )
        self.assertGreater(robust["raw_arithmetic_mean_g_per_tnm"], 20.0)

    def test_robust_fallback_uses_median_for_small_samples(self) -> None:
        robust = _robust_fallback_statistic([4.0, 10.0, 12.0])

        self.assertEqual(robust["intensity_g_per_tnm"], 10.0)
        self.assertEqual(robust["trim_count_each_tail"], 0)
        self.assertEqual(
            robust["statistic"],
            "median_of_latest_positive_per_imo_small_sample",
        )

    def test_extreme_exact_imo_uses_same_type_robust_estimate(self) -> None:
        ships = [
            self._ship(str(1000000 + index), [self._record(2024, 5.0)])
            for index in range(19)
        ]
        ships.append(self._ship("9999999", [self._record(2024, 100.0)]))

        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B"],
                matrix=self._symmetric_matrix({("Port A", "Port B"): 185.2}),
                voyages=[{"voyage_id": "outlier", "imo": "9999999"}],
                stops=[
                    self._stop("outlier", 0, "Port A", 100.0, 10.0),
                    self._stop("outlier", 1, "Port B", -100.0, -10.0),
                ],
                ships=ships,
            )

        provenance = payload["voyage_intensity_provenance"]["outlier"]
        self.assertEqual(
            provenance["intensity_source"],
            "eu_mrv_imo_outlier_replaced_by_ship_type",
        )
        self.assertEqual(provenance["matched_imo"], "9999999")
        self.assertEqual(provenance["matched_imo_intensity_g_per_tnm"], 100.0)
        self.assertEqual(provenance["outlier_upper_quantile"], 0.95)
        self.assertLess(provenance["outlier_upper_threshold_g_per_tnm"], 100.0)
        self.assertEqual(provenance["intensity_g_per_tnm"], 5.0)

    def test_negative_prefix_reconstructs_initial_cargo_and_keeps_zero_leg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port X", "Port B"],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port X"): 185.2,
                        ("Port X", "Port B"): 92.6,
                        ("Port A", "Port B"): 277.8,
                    }
                ),
                voyages=[{"voyage_id": "voyage-prefix", "imo": "1111111"}],
                stops=[
                    self._stop("voyage-prefix", 0, "Port A", -40.0, -4.0),
                    self._stop("voyage-prefix", 1, "Port X", 100.0, 10.0),
                    self._stop("voyage-prefix", 2, "Port B", -60.0, -6.0),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        segment_summary = payload["voyage_fuel_g_per_tnm_directional_meta"][
            "segment_summary"
        ]
        self.assertEqual(segment_summary["voyages_with_reconstructed_initial_cargo"], 1)
        self.assertEqual(
            segment_summary["reconstructed_initial_onboard_weight_t_total"], 40.0
        )
        self.assertEqual(stats["segment_count"], 2)
        self.assertEqual(stats["observed_transport_work_tnm"], 5000.0)
        self.assertEqual(stats["observed_fuel_kg"], 50.0)

    def test_scenario_distance_averages_complete_voyages_without_synthetic_path(self) -> None:
        ports = ["Port A", "Port Suape", "Port Recife", "Port X", "Port B"]
        matrix = self._symmetric_matrix(
            {
                ("Port A", "Port Suape"): 185.2,
                ("Port Suape", "Port B"): 185.2,
                ("Port A", "Port Recife"): 111.12,
                ("Port Recife", "Port B"): 111.12,
                ("Port A", "Port X"): 37.04,
                ("Port X", "Port B"): 37.04,
                ("Port A", "Port B"): 500.0,
            }
        )
        voyages = [
            {"voyage_id": "via-suape", "imo": "1111111"},
            {"voyage_id": "via-recife", "imo": "1111111"},
            {"voyage_id": "a-to-x-only", "imo": "1111111"},
            {"voyage_id": "x-to-b-only", "imo": "1111111"},
        ]
        stops = [
            *self._three_stop_voyage("via-suape", "Port A", "Port Suape", "Port B"),
            *self._three_stop_voyage("via-recife", "Port A", "Port Recife", "Port B"),
            self._stop("a-to-x-only", 0, "Port A", 100.0, 10.0),
            self._stop("a-to-x-only", 1, "Port X", -100.0, -10.0),
            self._stop("x-to-b-only", 0, "Port X", 100.0, 10.0),
            self._stop("x-to-b-only", 1, "Port B", -100.0, -10.0),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=ports,
                matrix=matrix,
                voyages=voyages,
                stops=stops,
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["corridor_count"], 2)
        self.assertEqual(stats["scenario_distance_observation_count"], 2)
        self.assertEqual(stats["distance_km"], 296.32)
        self.assertEqual(
            stats["scenario_distance_method"], CORRIDOR_SELECTION_CRITERION
        )
        option_paths = [option["corridor_port_path"] for option in stats["corridor_options"]]
        self.assertIn(["Port A", "Port Suape", "Port B"], option_paths)
        self.assertIn(["Port A", "Port Recife", "Port B"], option_paths)
        self.assertNotIn(["Port A", "Port X", "Port B"], option_paths)

    def test_scenario_distance_averages_direct_and_multistop_voyages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port Recife", "Port B"],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port B"): 555.6,
                        ("Port A", "Port Recife"): 111.12,
                        ("Port Recife", "Port B"): 111.12,
                    }
                ),
                voyages=[
                    {"voyage_id": "direct", "imo": "1111111"},
                    {"voyage_id": "indirect", "imo": "1111111"},
                ],
                stops=[
                    self._stop("direct", 0, "Port A", 100.0, 10.0),
                    self._stop("direct", 1, "Port B", -100.0, -10.0),
                    *self._three_stop_voyage(
                        "indirect", "Port A", "Port Recife", "Port B"
                    ),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["corridor_count"], 2)
        self.assertEqual(stats["direct_voyage_count"], 1)
        self.assertEqual(stats["multistop_voyage_count"], 1)
        self.assertEqual(stats["distance_km"], 388.92)

    def test_pair_intensity_and_distance_use_all_complete_voyages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port X", "Port B"],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port B"): 555.6,
                        ("Port A", "Port X"): 185.2,
                        ("Port X", "Port B"): 185.2,
                    }
                ),
                voyages=[
                    {"voyage_id": "direct", "imo": "1111111"},
                    {"voyage_id": "multistop", "imo": "2222222"},
                ],
                stops=[
                    self._stop("direct", 0, "Port A", 10.0, 1.0),
                    self._stop("direct", 1, "Port B", -10.0, -1.0),
                    *self._three_stop_voyage(
                        "multistop", "Port A", "Port X", "Port B"
                    ),
                ],
                ships=[
                    self._ship("1111111", [self._record(2024, 30.0)]),
                    self._ship("2222222", [self._record(2024, 5.0)]),
                ],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["distance_km"], 463.0)
        self.assertEqual(stats["scenario_distance_observation_count"], 2)
        self.assertAlmostEqual(stats["pair_intensity_g_per_tnm"], 8.26087)
        self.assertAlmostEqual(stats["fuel_g_per_tnm_weighted_mean"], 8.26087)
        self.assertEqual(stats["pair_intensity_candidate_voyage_count"], 2)
        self.assertEqual(stats["pair_intensity_positive_weight_voyage_count"], 2)

    def test_zero_transport_work_direct_preserves_resolved_intensity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port X", "Port B"],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port B"): 500.0,
                        ("Port A", "Port X"): 100.0,
                        ("Port X", "Port B"): 100.0,
                    }
                ),
                voyages=[
                    {"voyage_id": "zero-direct", "imo": "1111111"},
                    {"voyage_id": "usable-multistop", "imo": "1111111"},
                ],
                stops=[
                    self._stop("zero-direct", 0, "Port A", 0.0, 0.0),
                    self._stop("zero-direct", 1, "Port B", 0.0, 0.0),
                    *self._three_stop_voyage(
                        "usable-multistop", "Port A", "Port X", "Port B"
                    ),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["corridor_count"], 2)
        self.assertEqual(stats["candidate_voyage_count"], 2)
        self.assertEqual(stats["distance_km"], 350.0)
        self.assertEqual(stats["fuel_g_per_tnm_weighted_mean"], 10.0)
        self.assertGreater(stats["observed_fuel_kg"], 0.0)
        self.assertEqual(
            stats["intensity_weighting"],
            "transport_work_weighted_mean",
        )
        direct_option = next(
            option
            for option in stats["corridor_options"]
            if option["corridor_port_path"] == ["Port A", "Port B"]
        )
        self.assertEqual(direct_option["fuel_g_per_tnm_weighted_mean"], 10.0)

    def test_pair_intensity_uses_unweighted_mean_when_all_work_is_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B"],
                matrix=self._symmetric_matrix({("Port A", "Port B"): 185.2}),
                voyages=[
                    {"voyage_id": "low", "imo": "1111111"},
                    {"voyage_id": "high", "imo": "2222222"},
                ],
                stops=[
                    self._stop("low", 0, "Port A", 0.0, 0.0),
                    self._stop("low", 1, "Port B", 0.0, 0.0),
                    self._stop("high", 0, "Port A", 0.0, 0.0),
                    self._stop("high", 1, "Port B", 0.0, 0.0),
                ],
                ships=[
                    self._ship("1111111", [self._record(2024, 4.0)]),
                    self._ship("2222222", [self._record(2024, 12.0)]),
                ],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["pair_intensity_g_per_tnm"], 8.0)
        self.assertEqual(stats["pair_intensity_positive_weight_voyage_count"], 0)
        self.assertEqual(stats["pair_intensity_zero_weight_voyage_count"], 2)
        self.assertEqual(
            stats["pair_intensity_method"],
            "unweighted_mean_resolved_same_od_voyages_zero_transport_work",
        )
        self.assertEqual(
            stats["pair_intensity_source"],
            PAIR_INTENSITY_ZERO_WORK_SOURCE,
        )
        self.assertEqual(stats["pair_intensity_effective_voyage_count"], 2)
        self.assertEqual(
            stats["pair_intensity_effective_source_counts"],
            {"eu_mrv_imo_latest": 2},
        )

        validation = validate_enriched_sea_matrix_payload(
            payload,
            required_route=("Port A", "Port B"),
        )
        self.assertEqual(
            validation["required_route"]["pair_intensity_method"],
            "unweighted_mean_resolved_same_od_voyages_zero_transport_work",
        )

    def test_pair_intensity_uses_weighted_mean_for_equal_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B"],
                matrix=self._symmetric_matrix({("Port A", "Port B"): 185.2}),
                voyages=[
                    {"voyage_id": "low", "imo": "1111111"},
                    {"voyage_id": "high", "imo": "2222222"},
                ],
                stops=[
                    self._stop("low", 0, "Port A", 100.0, 10.0),
                    self._stop("low", 1, "Port B", -100.0, -10.0),
                    self._stop("high", 0, "Port A", 100.0, 10.0),
                    self._stop("high", 1, "Port B", -100.0, -10.0),
                ],
                ships=[
                    self._ship("1111111", [self._record(2024, 5.0)]),
                    self._ship("2222222", [self._record(2024, 15.0)]),
                ],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["pair_intensity_g_per_tnm"], 10.0)

    def test_repeated_ports_contribute_once_per_voyage_and_od(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port X", "Port B"],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port X"): 100.0,
                        ("Port X", "Port B"): 100.0,
                        ("Port A", "Port B"): 300.0,
                    }
                ),
                voyages=[{"voyage_id": "repeated", "imo": "1111111"}],
                stops=[
                    self._stop("repeated", 0, "Port A", 100.0, 10.0),
                    self._stop("repeated", 1, "Port X", 0.0, 0.0),
                    self._stop("repeated", 2, "Port B", -100.0, -10.0),
                    self._stop("repeated", 3, "Port A", 100.0, 10.0),
                    self._stop("repeated", 4, "Port B", -100.0, -10.0),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["candidate_voyage_count"], 1)
        self.assertEqual(stats["corridor_count"], 1)
        self.assertEqual(stats["scenario_distance_observation_count"], 1)
        self.assertEqual(stats["distance_km"], 300.0)
        self.assertEqual(stats["direct_voyage_count"], 1)
        summary = payload["voyage_fuel_g_per_tnm_directional_meta"]["segment_summary"]
        self.assertGreater(summary["deduplicated_subroute_occurrences"], 0)

    def test_consecutive_terminal_aliases_are_collapsed_with_all_cargo_moves(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, self.assertLogs(
            "modules.cabotage.sea_matrix_efficiency",
            level="DEBUG",
        ) as captured:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B"],
                port_records=[
                    {
                        "name": "Port A",
                        "slug": "port-a",
                        "slug_candidates": ["terminal-a"],
                        "lat": 0.0,
                        "lon": 0.0,
                    },
                    {
                        "name": "Port B",
                        "slug": "port-b",
                        "lat": 0.0,
                        "lon": 1.0,
                    },
                ],
                matrix=self._symmetric_matrix({("Port A", "Port B"): 185.2}),
                voyages=[{"voyage_id": "alias-voyage", "imo": "1111111"}],
                stops=[
                    self._stop("alias-voyage", 0, "Port A", 100.0, 10.0),
                    self._stop("alias-voyage", 1, "Terminal A", -40.0, -4.0),
                    self._stop("alias-voyage", 2, "Port B", -60.0, -6.0),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
                audit_voyage_ids="alias-voyage",
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(stats["distance_km"], 185.2)
        self.assertEqual(stats["observed_fuel_kg"], 60.0)
        summary = payload["voyage_fuel_g_per_tnm_directional_meta"]["segment_summary"]
        self.assertEqual(summary["raw_candidate_segments"], 2)
        self.assertEqual(summary["candidate_segments"], 1)
        self.assertEqual(summary["collapsed_consecutive_canonical_stop_calls"], 1)
        log_text = "\n".join(captured.output)
        self.assertIn("origin_call_sequences=[0, 1]", log_text)
        self.assertIn("destination_call_sequences=[2]", log_text)

    def test_missing_positive_matrix_distance_uses_audited_haversine_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=["Port A", "Port B", "Port C"],
                port_records=[
                    {"name": "Port A", "slug": "port-a", "lat": 0.0, "lon": 0.0},
                    {"name": "Port B", "slug": "port-b", "lat": 0.0, "lon": 1.0},
                    {"name": "Port C", "slug": "port-c", "lat": 1.0, "lon": 1.0},
                ],
                matrix=self._symmetric_matrix(
                    {
                        ("Port A", "Port B"): 0.0,
                        ("Port B", "Port C"): 10.0,
                    }
                ),
                voyages=[{"voyage_id": "fallback-distance", "imo": "1111111"}],
                stops=[
                    self._stop("fallback-distance", 0, "Port A", 100.0, 10.0),
                    self._stop("fallback-distance", 1, "Port B", -100.0, -10.0),
                ],
                ships=[self._ship("1111111", [self._record(2024, 10.0)])],
            )

        stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        self.assertEqual(
            stats["scenario_distance_source_counts"],
            {"haversine_fallback": 1},
        )
        self.assertGreater(stats["distance_km"], 111.0)
        summary = payload["voyage_fuel_g_per_tnm_directional_meta"]["segment_summary"]
        self.assertEqual(summary["haversine_fallback_segments"], 1)
        self.assertEqual(summary["skipped_missing_distance_segments"], 0)

    def test_intensity_hierarchy_and_source_counts(self) -> None:
        ports = [f"Port {letter}" for letter in "ABCDEFGH"]
        matrix = self._symmetric_matrix(
            {
                ("Port A", "Port B"): 185.2,
                ("Port C", "Port D"): 185.2,
                ("Port E", "Port F"): 185.2,
                ("Port G", "Port H"): 185.2,
            }
        )
        voyages = [
            {
                "voyage_id": "v-imo",
                "imo": "1111111",
                "vessel_class": "container_feeder",
                "ship_type": "Container ship",
            },
            {
                "voyage_id": "v-class",
                "imo": "9999999",
                "vessel_class": "container_feeder",
                "ship_type": "Container ship",
            },
            {
                "voyage_id": "v-type",
                "imo": "9999998",
                "vessel_class": "",
                "ship_type": "Container ship",
            },
            {
                "voyage_id": "v-default-type",
                "imo": "9999997",
                "vessel_class": "",
                "ship_type": "",
            },
        ]
        stops = []
        for voyage_id, origin, destination in (
            ("v-imo", "Port A", "Port B"),
            ("v-class", "Port C", "Port D"),
            ("v-type", "Port E", "Port F"),
            ("v-default-type", "Port G", "Port H"),
        ):
            stops.extend(
                [
                    self._stop(voyage_id, 0, origin, 100.0, 10.0),
                    self._stop(voyage_id, 1, destination, -100.0, -10.0),
                ]
            )
        ships = [
            self._ship(
                "1111111",
                [self._record(2022, 99.0), self._record(2024, 4.0)],
            ),
            self._ship("2222222", [self._record(2024, 10.0)]),
            self._ship("3333333", [self._record(2024, 12.0)]),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            payload, _ = self._run_enrichment(
                Path(tmpdir),
                ports=ports,
                matrix=matrix,
                voyages=voyages,
                stops=stops,
                ships=ships,
                class_payload={
                    "container_feeder": {
                        "fuel_g_per_tnm": {
                            "mean": 6.5,
                            "median": 6.3,
                            "trimmed_mean_1pct": 6.2,
                            "count": 20,
                        },
                        "sample_size": 20,
                    }
                },
            )

        provenance = payload["voyage_intensity_provenance"]
        self.assertEqual(provenance["v-imo"]["intensity_g_per_tnm"], 4.0)
        self.assertEqual(provenance["v-imo"]["intensity_source_level"], "imo")
        self.assertEqual(provenance["v-class"]["intensity_g_per_tnm"], 6.2)
        self.assertEqual(
            provenance["v-class"]["intensity_source"],
            "eu_mrv_vessel_class_trimmed_mean_1pct",
        )
        self.assertEqual(
            provenance["v-class"]["outlier_rule"],
            "class_artifact_excludes_below_p1_and_above_p99",
        )
        self.assertEqual(provenance["v-class"]["source_file"], "classes.json")

        expected_type_median = 10.0
        self.assertEqual(
            provenance["v-type"]["intensity_g_per_tnm"], expected_type_median
        )
        self.assertEqual(provenance["v-type"]["sample_size"], 3)
        self.assertEqual(
            provenance["v-type"]["intensity_source"],
            "eu_mrv_ship_type_median",
        )
        self.assertFalse(provenance["v-type"]["used_default_ship_type"])
        self.assertEqual(
            provenance["v-default-type"]["intensity_g_per_tnm"],
            expected_type_median,
        )
        self.assertTrue(provenance["v-default-type"]["used_default_ship_type"])

        exact_stats = payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        class_stats = payload["voyage_fuel_g_per_tnm_directional"]["Port C"]["Port D"]
        type_stats = payload["voyage_fuel_g_per_tnm_directional"]["Port E"]["Port F"]
        self.assertEqual(exact_stats["matched_segment_count"], 1)
        self.assertEqual(exact_stats["fallback_voyage_count"], 0)
        self.assertEqual(class_stats["matched_segment_count"], 0)
        self.assertEqual(class_stats["resolved_segment_count"], 1)
        self.assertEqual(class_stats["class_fallback_voyage_count"], 1)
        self.assertEqual(type_stats["type_fallback_voyage_count"], 1)
        self.assertEqual(
            type_stats["intensity_source_counts"],
            {"eu_mrv_ship_type_median": 1},
        )
        validation = validate_enriched_sea_matrix_payload(
            payload,
            required_route=("Port C", "Port D"),
        )
        self.assertEqual(
            validation["required_route"]["resolved_segment_count"], 1
        )
        self.assertEqual(validation["required_route"]["matched_segment_count"], 0)
        self.assertEqual(
            validation["required_route"]["intensity_resolution_rate"], 1.0
        )

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

    def test_base_matrix_maps_observed_terminal_aliases(self) -> None:
        matrix_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "processed"
            / "cabotage_data"
            / "sea_matrix.json"
        )
        payload = json.loads(matrix_path.read_text(encoding="utf-8-sig"))
        lookup = _build_port_lookup(payload)

        aliases = {
            "DP World Santos": "Porto de Santos",
            "Porto Itapoá Terminais Portuários": "Porto de Itapoá",
            "Portonave - Terminais Portuários de Navegantes": (
                "Porto de Navegantes"
            ),
            "Terminal Portuário do Pecém": "Porto do Pecém",
        }
        for port_name, expected in aliases.items():
            with self.subTest(port_name=port_name):
                self.assertEqual(
                    _resolve_matrix_port_name({"port_name": port_name}, lookup),
                    expected,
                )

    def _run_enrichment(
        self,
        root: Path,
        *,
        ports: list[str],
        matrix: dict[str, dict[str, float]],
        voyages: list[dict[str, object]],
        stops: list[dict[str, object]],
        ships: list[dict[str, object]],
        class_payload: dict[str, object] | None = None,
        port_records: list[dict[str, object]] | None = None,
        audit_voyage_ids: Iterable[str] | str | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        matrix_path = root / "sea_matrix.json"
        voyages_path = root / "voyages.csv"
        stops_path = root / "stops.csv"
        mrv_path = root / "mrv.json"
        class_path = root / "classes.json"

        matrix_path.write_text(
            json.dumps(
                {
                    "ports": port_records
                    or [
                        {"name": port, "slug": port.lower().replace(" ", "-")}
                        for port in ports
                    ],
                    "matrix": matrix,
                }
            ),
            encoding="utf-8",
        )
        self._write_dict_csv(voyages_path, voyages)
        self._write_dict_csv(stops_path, stops)
        mrv_path.write_text(json.dumps({"ships": ships}), encoding="utf-8")
        class_path.write_text(
            json.dumps(
                class_payload
                or {
                    "container_feeder": {
                        "fuel_g_per_tnm": {
                            "mean": 6.5,
                            "median": 6.1,
                            "trimmed_mean_1pct": 6.0,
                            "count": 10,
                        },
                        "sample_size": 10,
                    }
                }
            ),
            encoding="utf-8",
        )

        def resolve_local_asset(candidate: Path | str) -> Path:
            resolved_candidate = Path(candidate).resolve()
            self.assertNotEqual(resolved_candidate, matrix_path.resolve())
            return resolved_candidate

        with patch(
            "modules.cabotage.sea_matrix_efficiency.resolve_data_asset_path",
            side_effect=resolve_local_asset,
        ):
            return enrich_sea_matrix_with_efficiency(
                sea_matrix_path=matrix_path,
                voyages_csv_path=voyages_path,
                stops_csv_path=stops_path,
                mrv_json_path=mrv_path,
                class_efficiency_json_path=class_path,
                possible_pairs_only=False,
                matched_pairs_only=True,
                prefer_local_voyage_inputs=True,
                audit_voyage_ids=audit_voyage_ids,
            )

    @staticmethod
    def _ship(
        imo: str,
        records: list[dict[str, object]],
        *,
        ship_type: str = "Container ship",
        vessel_class: str | None = None,
    ) -> dict[str, object]:
        return {
            "imo": imo,
            "ship_type": ship_type,
            "vessel_class": vessel_class,
            "records": records,
        }

    @staticmethod
    def _record(
        reporting_period: int,
        intensity: float,
        *,
        source_file: str = "mrv.xlsx",
        source_sheet: str = "2024",
        metric_basis: str = "dwt",
    ) -> dict[str, object]:
        return {
            "reporting_period": reporting_period,
            "average_fuel_consumption_per_transport_work_g_per_tonne_nmile": intensity,
            "fuel_consumption_per_transport_work_source": metric_basis,
            "source_file": source_file,
            "source_sheet": source_sheet,
        }

    @staticmethod
    def _stop(
        voyage_id: str,
        sequence: int,
        port_name: str,
        net_weight_t: float,
        net_teu: float,
    ) -> dict[str, object]:
        return {
            "voyage_id": voyage_id,
            "sequence": sequence,
            "port_name": port_name,
            "port_code": "",
            "net_weight_t": net_weight_t,
            "net_teu": net_teu,
        }

    @classmethod
    def _three_stop_voyage(
        cls,
        voyage_id: str,
        origin: str,
        intermediate: str,
        destination: str,
    ) -> list[dict[str, object]]:
        return [
            cls._stop(voyage_id, 0, origin, 100.0, 10.0),
            cls._stop(voyage_id, 1, intermediate, 0.0, 0.0),
            cls._stop(voyage_id, 2, destination, -100.0, -10.0),
        ]

    @staticmethod
    def _symmetric_matrix(
        pairs: dict[tuple[str, str], float]
    ) -> dict[str, dict[str, float]]:
        matrix: dict[str, dict[str, float]] = {}
        for (origin, destination), distance in pairs.items():
            matrix.setdefault(origin, {})[destination] = distance
            matrix.setdefault(destination, {})[origin] = distance
        return matrix

    @staticmethod
    def _write_dict_csv(path: Path, rows: list[dict[str, object]]) -> None:
        columns: list[str] = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
