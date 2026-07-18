import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.cabotage.sea_matrix import (
    OBSERVED_VOYAGE_CORRIDORS_MODE,
    SeaMatrix,
)
from modules.cabotage.sea_matrix_efficiency import (
    DEPLOYMENT_REQUIRED_ROUTE,
    validate_enriched_sea_matrix_payload,
)
from modules.multimodal.builder import build_path_geometry_from_resolved


class SeaMatrixFileLoadingTests(unittest.TestCase):
    @staticmethod
    def _observed_corridor_payload() -> dict:
        return {
            "matrix": {
                "Port A": {"Port B": 555.6, "Port X": 92.6, "Port Y": 185.2},
                "Port B": {"Port A": 555.6, "Port X": 92.6, "Port Y": 370.4},
                "Port X": {"Port A": 92.6, "Port B": 92.6},
                "Port Y": {"Port A": 185.2, "Port B": 370.4},
            },
            "voyage_fuel_g_per_tnm_directional_meta": {
                "route_observation_mode": OBSERVED_VOYAGE_CORRIDORS_MODE,
                "maritime_intensity_schema_version": 3,
                "pair_intensity_method": "transport_work_weighted_mean",
                "generated_at": "2026-07-16T12:00:00+00:00",
            },
            "voyage_fuel_g_per_tnm_directional": {
                "Port A": {
                    "Port B": {
                        "corridor_count": 3,
                        "candidate_voyage_count": 4,
                        "selected_corridor_candidate_voyage_count": 2,
                        "direct_voyage_count": 0,
                        "multistop_voyage_count": 4,
                        "selection_criterion": "direct_first_then_shortest_distance_km",
                        "selected_corridor_id": "voyage-via-y",
                        "route_observation_mode": OBSERVED_VOYAGE_CORRIDORS_MODE,
                        "resolved_voyage_count": 3,
                        "imo_intensity_voyage_count": 2,
                        "class_fallback_voyage_count": 1,
                        "type_fallback_voyage_count": 0,
                        "fallback_voyage_count": 1,
                        "unresolved_intensity_voyage_count": 1,
                        "intensity_source_counts": {
                            "eu_mrv_imo_latest": 2,
                            "eu_mrv_vessel_class_mean": 1,
                            "unavailable": 1,
                        },
                        "distance_source_counts": {
                            "sea_matrix": 6,
                            "haversine_fallback": 1,
                        },
                        "selected_corridor_distance_source_counts": {
                            "sea_matrix": 1,
                            "haversine_fallback": 1,
                        },
                        "distance_km": 555.6,
                        "distance_nm": 300.0,
                        "fuel_g_per_tnm_weighted_mean": 9.0,
                        "fuel_g_per_tnm_source": (
                            "antaq_mrv_same_od_transport_work_weighted_mean"
                        ),
                        "pair_intensity_g_per_tnm": 9.0,
                        "pair_intensity_method": "transport_work_weighted_mean",
                        "pair_intensity_scope": (
                            "all_eligible_same_od_voyage_observations_across_corridors"
                        ),
                        "pair_intensity_weight": "observed_transport_work_tnm",
                        "pair_intensity_source": (
                            "antaq_mrv_same_od_transport_work_weighted_mean"
                        ),
                        "pair_intensity_candidate_voyage_count": 4,
                        "pair_intensity_resolved_voyage_count": 3,
                        "pair_intensity_positive_weight_voyage_count": 3,
                        "pair_intensity_zero_weight_voyage_count": 0,
                        "pair_intensity_unresolved_voyage_count": 1,
                        "pair_intensity_transport_work_tnm": 75000.0,
                        "pair_intensity_source_counts": {
                            "eu_mrv_imo_latest": 2,
                            "eu_mrv_vessel_class_mean": 1,
                        },
                        "selected_corridor_fuel_g_per_tnm_weighted_mean": 10.0,
                        "selected_corridor_intensity_weighting": (
                            "observed_transport_work_tnm"
                        ),
                        "corridor_port_path": ["Port A", "Port Y", "Port B"],
                        "corridor_leg_count": 2,
                        "observed_transport_work_tnm": 38000.0,
                        "observed_fuel_kg": 380.0,
                        "candidate_observed_transport_work_tnm": 75000.0,
                        "candidate_observed_fuel_kg": 720.0,
                        "selected_corridor_sublegs": [
                            {
                                "corridor_leg_sequence": 0,
                                "origin_port": "Port A",
                                "destination_port": "Port Y",
                                "distance_km": 185.2,
                                "distance_nm": 100.0,
                                "distance_source": "sea_matrix",
                                "average_cargo_onboard_t": 200.0,
                                "observed_transport_work_tnm": 20000.0,
                                "resolved_transport_work_tnm": 20000.0,
                                "intensity_g_per_tnm": 10.0,
                                "intensity_source_counts": {
                                    "eu_mrv_imo_latest": 2,
                                },
                                "observed_fuel_kg": 200.0,
                            },
                            {
                                "corridor_leg_sequence": 1,
                                "origin_port": "Port Y",
                                "destination_port": "Port B",
                                "distance_km": 370.4,
                                "distance_nm": 200.0,
                                "distance_source": "haversine_fallback",
                                "average_cargo_onboard_t": 90.0,
                                "observed_transport_work_tnm": 18000.0,
                                "resolved_transport_work_tnm": 18000.0,
                                "intensity_g_per_tnm": 10.0,
                                "intensity_source_counts": {
                                    "eu_mrv_imo_latest": 2,
                                },
                                "observed_fuel_kg": 180.0,
                            },
                        ],
                    },
                    "Port X": {
                        "distance_km": 92.6,
                        "fuel_g_per_tnm_weighted_mean": 8.0,
                        "route_observation_mode": OBSERVED_VOYAGE_CORRIDORS_MODE,
                        "pair_intensity_g_per_tnm": 8.0,
                        "pair_intensity_method": "transport_work_weighted_mean",
                        "pair_intensity_scope": (
                            "all_eligible_same_od_voyage_observations_across_corridors"
                        ),
                        "pair_intensity_source": (
                            "antaq_mrv_same_od_transport_work_weighted_mean"
                        ),
                        "pair_intensity_candidate_voyage_count": 1,
                    },
                },
                "Port X": {
                    "Port B": {
                        "distance_km": 92.6,
                        "fuel_g_per_tnm_weighted_mean": 8.0,
                        "route_observation_mode": OBSERVED_VOYAGE_CORRIDORS_MODE,
                        "pair_intensity_g_per_tnm": 8.0,
                        "pair_intensity_method": "transport_work_weighted_mean",
                        "pair_intensity_scope": (
                            "all_eligible_same_od_voyage_observations_across_corridors"
                        ),
                        "pair_intensity_source": (
                            "antaq_mrv_same_od_transport_work_weighted_mean"
                        ),
                        "pair_intensity_candidate_voyage_count": 1,
                    }
                },
            },
        }

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

    def test_valid_legacy_remote_asset_yields_to_tracked_observed_schema(self) -> None:
        remote_payload = {
            "matrix": {
                "Port A": {"Port B": 100.0},
                "Port B": {"Port A": 100.0},
            }
        }
        local_payload = self._observed_corridor_payload()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_path = root / "sea_matrix.json"
            remote_path = root / "cache" / "sea_matrix.json"
            remote_path.parent.mkdir()
            local_path.write_text(json.dumps(local_payload), encoding="utf-8")
            remote_path.write_text(json.dumps(remote_payload), encoding="utf-8")

            with patch(
                "modules.cabotage.sea_matrix.resolve_data_asset_path",
                return_value=remote_path,
            ):
                sea_matrix = SeaMatrix.from_json_path(local_path)

        self.assertEqual(
            sea_matrix.route_observation_mode,
            OBSERVED_VOYAGE_CORRIDORS_MODE,
        )
        stats = sea_matrix.best_directional_stats("Port A", "Port B")
        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats["selected_corridor_id"], "voyage-via-y")

    def test_observed_remote_without_pair_intensity_yields_to_tracked_schema(self) -> None:
        local_payload = self._observed_corridor_payload()
        remote_payload = json.loads(json.dumps(local_payload))
        remote_payload["voyage_fuel_g_per_tnm_directional_meta"].pop(
            "pair_intensity_method"
        )
        remote_stats = remote_payload["voyage_fuel_g_per_tnm_directional"][
            "Port A"
        ]["Port B"]
        for key in list(remote_stats):
            if key.startswith("pair_intensity_"):
                remote_stats.pop(key)
        remote_stats["fuel_g_per_tnm_weighted_mean"] = 10.0
        remote_stats["fuel_g_per_tnm_source"] = "observed_voyage_corridor_sublegs"

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_path = root / "sea_matrix.json"
            remote_path = root / "cache" / "sea_matrix.json"
            remote_path.parent.mkdir()
            local_path.write_text(json.dumps(local_payload), encoding="utf-8")
            remote_path.write_text(json.dumps(remote_payload), encoding="utf-8")

            with patch(
                "modules.cabotage.sea_matrix.resolve_data_asset_path",
                return_value=remote_path,
            ):
                sea_matrix = SeaMatrix.from_json_path(local_path)

        stats = sea_matrix.best_directional_stats("Port A", "Port B")
        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats["pair_intensity_g_per_tnm"], 9.0)
        self.assertEqual(
            stats["pair_intensity_method"],
            "transport_work_weighted_mean",
        )

    def test_partially_upgraded_remote_yields_to_complete_tracked_schema(self) -> None:
        local_payload = self._observed_corridor_payload()
        second_stats = json.loads(
            json.dumps(
                local_payload["voyage_fuel_g_per_tnm_directional"]["Port A"][
                    "Port B"
                ]
            )
        )
        second_stats["corridor_port_path"] = ["Port A", "Port C"]
        second_stats["corridor_leg_count"] = 1
        second_stats["distance_km"] = 400.0
        local_payload["matrix"]["Port A"]["Port C"] = 400.0
        local_payload["matrix"]["Port C"] = {"Port A": 400.0}
        local_payload["voyage_fuel_g_per_tnm_directional"]["Port A"][
            "Port C"
        ] = second_stats

        remote_payload = json.loads(json.dumps(local_payload))
        remote_second = remote_payload["voyage_fuel_g_per_tnm_directional"][
            "Port A"
        ]["Port C"]
        remote_second.pop("route_observation_mode")
        for key in list(remote_second):
            if key.startswith("pair_intensity_"):
                remote_second.pop(key)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_path = root / "sea_matrix.json"
            remote_path = root / "cache" / "sea_matrix.json"
            remote_path.parent.mkdir()
            local_path.write_text(json.dumps(local_payload), encoding="utf-8")
            remote_path.write_text(json.dumps(remote_payload), encoding="utf-8")

            with patch(
                "modules.cabotage.sea_matrix.resolve_data_asset_path",
                return_value=remote_path,
            ):
                sea_matrix = SeaMatrix.from_json_path(local_path)

        stats = sea_matrix.best_directional_stats("Port A", "Port C")
        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats["pair_intensity_g_per_tnm"], 9.0)

    def test_older_complete_remote_yields_to_newer_tracked_schema(self) -> None:
        local_payload = self._observed_corridor_payload()
        remote_payload = json.loads(json.dumps(local_payload))
        remote_payload["voyage_fuel_g_per_tnm_directional_meta"][
            "generated_at"
        ] = "2026-07-15T12:00:00+00:00"
        remote_payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"][
            "pair_intensity_g_per_tnm"
        ] = 99.0

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            local_path = root / "sea_matrix.json"
            remote_path = root / "cache" / "sea_matrix.json"
            remote_path.parent.mkdir()
            local_path.write_text(json.dumps(local_payload), encoding="utf-8")
            remote_path.write_text(json.dumps(remote_payload), encoding="utf-8")

            with patch(
                "modules.cabotage.sea_matrix.resolve_data_asset_path",
                return_value=remote_path,
            ):
                sea_matrix = SeaMatrix.from_json_path(local_path)

        self.assertEqual(
            sea_matrix.directional_fuel_g_per_tnm("Port A", "Port B"),
            9.0,
        )

    def test_directional_fuel_prefers_explicit_pair_intensity(self) -> None:
        payload = self._observed_corridor_payload()
        payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"][
            "fuel_g_per_tnm_weighted_mean"
        ] = 10.0

        sea_matrix = SeaMatrix.from_json_dict(payload)

        self.assertEqual(
            sea_matrix.directional_fuel_g_per_tnm("Port A", "Port B"),
            9.0,
        )

    def test_observed_mode_uses_selected_complete_voyage_corridor(self) -> None:
        sea_matrix = SeaMatrix.from_json_dict(self._observed_corridor_payload())

        stats = sea_matrix.best_directional_stats("Port A", "Port B")

        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats["selected_corridor_id"], "voyage-via-y")
        self.assertEqual(stats["corridor_port_path"], ["Port A", "Port Y", "Port B"])
        self.assertEqual(stats["corridor_leg_count"], 2)
        self.assertEqual(stats["distance_km"], 555.6)
        self.assertEqual(len(stats["selected_corridor_sublegs"]), 2)
        self.assertEqual(stats["selected_corridor_sublegs"][0]["observed_cargo_t"], 200.0)
        self.assertEqual(
            stats["selected_corridor_sublegs"][0]["intensity_source_level"],
            "imo",
        )
        self.assertEqual(stats["observed_fuel_kg"], 380.0)

    def test_observed_mode_never_stitches_different_voyages(self) -> None:
        payload = self._observed_corridor_payload()
        del payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        sea_matrix = SeaMatrix.from_json_dict(payload)

        self.assertIsNone(sea_matrix.best_directional_stats("Port A", "Port B"))
        self.assertIsNone(sea_matrix.corridor_stats("Port A", "Port B"))

    def test_legacy_mode_preserves_directional_corridor_compatibility(self) -> None:
        payload = self._observed_corridor_payload()
        payload.pop("voyage_fuel_g_per_tnm_directional_meta")
        del payload["voyage_fuel_g_per_tnm_directional"]["Port A"]["Port B"]
        for destinations in payload["voyage_fuel_g_per_tnm_directional"].values():
            for stats in destinations.values():
                stats.pop("route_observation_mode", None)
                for key in list(stats):
                    if key.startswith("pair_intensity_"):
                        stats.pop(key)
        sea_matrix = SeaMatrix.from_json_dict(payload)

        stats = sea_matrix.best_directional_stats("Port A", "Port B")

        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats["corridor_port_path"], ["Port A", "Port X", "Port B"])
        self.assertEqual(stats["distance_source"], "directional_corridor")

    def test_builder_propagates_observed_corridor_provenance(self) -> None:
        sea_matrix = SeaMatrix.from_json_dict(self._observed_corridor_payload())

        geometry = build_path_geometry_from_resolved(
            {"label": "Origin", "lat": -23.0, "lon": -46.0},
            {"label": "Destination", "lat": -3.0, "lon": -60.0},
            ors=object(),
            ports=[],
            sea_matrix=sea_matrix,
            port_origin={"name": "Port A", "lat": -23.0, "lon": -46.0},
            port_destiny={"name": "Port B", "lat": -3.0, "lon": -60.0},
            first_mile_leg={"distance_km": 80.0, "source": "test"},
            route_resolver=lambda _start, _end, _name: {
                "distance_km": 100.0,
                "source": "test",
            },
        )

        sea_leg = geometry["sea_leg"]
        self.assertEqual(sea_leg["source"], "observed_voyage_corridor")
        self.assertEqual(
            sea_leg["fuel_g_per_tnm_source"],
            "antaq_mrv_same_od_transport_work_weighted_mean",
        )
        self.assertEqual(sea_leg["fuel_g_per_tnm"], 9.0)
        self.assertEqual(sea_leg["pair_intensity_g_per_tnm"], 9.0)
        self.assertEqual(
            sea_leg["pair_intensity_method"],
            "transport_work_weighted_mean",
        )
        self.assertEqual(
            sea_leg["selected_corridor_fuel_g_per_tnm_weighted_mean"],
            10.0,
        )
        self.assertEqual(sea_leg["candidate_voyage_count"], 4)
        self.assertEqual(
            sea_leg["selected_corridor_candidate_voyage_count"],
            2,
        )
        self.assertEqual(sea_leg["selected_corridor_id"], "voyage-via-y")
        self.assertEqual(sea_leg["fallback_voyage_count"], 1)
        self.assertEqual(sea_leg["candidate_observed_fuel_kg"], 720.0)
        self.assertEqual(
            sea_leg["intensity_source_counts"]["eu_mrv_vessel_class_mean"],
            1,
        )
        self.assertEqual(
            sea_leg["selected_corridor_distance_source_counts"][
                "haversine_fallback"
            ],
            1,
        )
        self.assertEqual(len(sea_leg["selected_corridor_sublegs"]), 2)

    def test_tracked_matrix_supports_santos_manaus_directional_route(self) -> None:
        matrix_path = Path(__file__).resolve().parents[1] / "data" / "sea_matrix.json"
        payload = json.loads(matrix_path.read_text(encoding="utf-8-sig"))

        self.assertEqual(
            payload["voyage_fuel_g_per_tnm_directional_meta"][
                "maritime_intensity_schema_version"
            ],
            4,
        )

        validation = validate_enriched_sea_matrix_payload(
            payload,
            required_route=DEPLOYMENT_REQUIRED_ROUTE,
        )

        route = validation["required_route"]
        self.assertGreater(route["distance_km"], 0.0)
        self.assertGreater(route["fuel_g_per_tnm_weighted_mean"], 0.0)
        self.assertGreater(route["segment_count"], 0)
        self.assertGreater(route["resolved_segment_count"], 0)
        self.assertGreater(route["unique_imo_count"], 0)
        self.assertGreater(route["fallback_voyage_count"], 0)
        self.assertEqual(route["unresolved_intensity_voyage_count"], 0)

        stats = payload["voyage_fuel_g_per_tnm_directional"][
            DEPLOYMENT_REQUIRED_ROUTE[0]
        ][DEPLOYMENT_REQUIRED_ROUTE[1]]
        self.assertGreater(stats["corridor_count"], 1)
        self.assertGreater(stats["direct_voyage_count"], 0)
        self.assertGreater(stats["multistop_voyage_count"], 0)
        candidate_ids = [
            voyage_id
            for option in stats["corridor_options"]
            for voyage_id in option["candidate_voyage_ids"]
        ]
        self.assertEqual(len(candidate_ids), len(set(candidate_ids)))
        self.assertEqual(len(candidate_ids), stats["candidate_voyage_count"])
        self.assertTrue(
            any(
                len(option["corridor_port_path"]) > 2
                and "Porto de Suape" not in option["corridor_port_path"]
                for option in stats["corridor_options"]
            )
        )
        self.assertAlmostEqual(
            stats["fuel_g_per_tnm_weighted_mean"],
            9.322050,
            places=6,
        )
        self.assertEqual(
            stats["pair_intensity_method"],
            "transport_work_weighted_mean",
        )
        self.assertEqual(
            stats["pair_intensity_scope"],
            "all_eligible_same_od_voyage_observations_across_corridors",
        )
        self.assertEqual(stats["pair_intensity_candidate_voyage_count"], 89)
        self.assertEqual(stats["pair_intensity_positive_weight_voyage_count"], 89)
        self.assertEqual(stats["pair_intensity_effective_voyage_count"], 89)
        self.assertEqual(
            stats["pair_intensity_effective_source_counts"],
            {
                "eu_mrv_imo_latest": 19,
                "eu_mrv_imo_outlier_replaced_by_ship_type": 21,
                "eu_mrv_ship_type_trimmed_mean_1pct": 49,
            },
        )
        self.assertAlmostEqual(
            stats["pair_intensity_transport_work_weighted_mean_g_per_tnm"],
            9.009824,
            places=6,
        )
        self.assertAlmostEqual(
            stats["selected_corridor_fuel_g_per_tnm_weighted_mean"],
            9.322050,
            places=6,
        )
        self.assertEqual(
            stats["selected_corridor_sublegs"][0]["intensity_source_counts"],
            {"eu_mrv_ship_type_trimmed_mean_1pct": 1},
        )
        selected_voyage_id = stats["selected_corridor_candidate_voyage_ids"][0]
        provenance = payload["voyage_intensity_provenance"][selected_voyage_id]
        self.assertEqual(
            provenance["outlier_rule"],
            "symmetric_trim_1pct_each_tail_floor_count",
        )
        self.assertEqual(provenance["trim_count_each_tail"], 2)
        self.assertEqual(provenance["excluded_sample_size"], 4)
        self.assertGreater(
            provenance["raw_arithmetic_mean_g_per_tnm"],
            provenance["intensity_g_per_tnm"],
        )

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
        self.assertEqual(sea_leg["source"], "observed_voyage_corridor")
        self.assertEqual(
            sea_leg["fuel_g_per_tnm_source"],
            "antaq_mrv_same_od_transport_work_weighted_mean",
        )
        self.assertEqual(sea_leg["distance_km"], expected["distance_km"])
        self.assertEqual(
            sea_leg["fuel_g_per_tnm"],
            expected["pair_intensity_g_per_tnm"],
        )
        self.assertEqual(
            sea_leg["pair_intensity_method"],
            "transport_work_weighted_mean",
        )
        self.assertEqual(sea_leg["pair_intensity_candidate_voyage_count"], 89)
        self.assertEqual(sea_leg["matched_segment_count"], expected["matched_segment_count"])
        self.assertEqual(sea_leg["matched_imo_count"], expected["matched_imo_count"])
        observed_legs = sea_leg["selected_corridor_sublegs"]
        self.assertEqual(len(observed_legs), sea_leg["corridor_leg_count"])
        self.assertEqual(observed_legs[0]["origin_port"], "Porto de Santos")
        self.assertEqual(observed_legs[-1]["destination_port"], "Porto de Manaus")
        for current, following in zip(observed_legs[:-1], observed_legs[1:]):
            self.assertEqual(
                current["destination_port"],
                following["origin_port"],
            )
        for observed_leg in observed_legs:
            self.assertGreater(observed_leg["observed_segment_count"], 0)
            self.assertGreater(observed_leg["resolved_segment_count"], 0)
            self.assertGreater(observed_leg["average_cargo_onboard_t"], 0.0)
            self.assertGreater(observed_leg["distance_nm"], 0.0)
            self.assertGreater(
                observed_leg["intensity_g_per_tnm"],
                0.0,
            )

    def test_tracked_matrix_keeps_one_voyage_per_od_and_current_selection_rule(
        self,
    ) -> None:
        matrix_path = Path(__file__).resolve().parents[1] / "data" / "sea_matrix.json"
        payload = json.loads(matrix_path.read_text(encoding="utf-8-sig"))
        directional = payload["voyage_fuel_g_per_tnm_directional"]
        serialized_candidate_voyages = 0

        for origin, destinations in directional.items():
            for destination, stats in destinations.items():
                with self.subTest(origin=origin, destination=destination):
                    options = stats["corridor_options"]
                    candidate_ids = [
                        voyage_id
                        for option in options
                        for voyage_id in option["candidate_voyage_ids"]
                    ]
                    self.assertEqual(len(candidate_ids), len(set(candidate_ids)))
                    self.assertEqual(
                        len(candidate_ids),
                        stats["candidate_voyage_count"],
                    )
                    serialized_candidate_voyages += len(candidate_ids)
                    for option in options:
                        self.assertEqual(option["corridor_port_path"][0], origin)
                        self.assertEqual(
                            option["corridor_port_path"][-1], destination
                        )

                    direct = [
                        option
                        for option in options
                        if len(option["corridor_port_path"]) == 2
                    ]
                    selectable = direct or options
                    expected = min(
                        selectable,
                        key=lambda option: (
                            float(option["distance_km"]),
                            len(option["corridor_port_path"]),
                            tuple(option["corridor_port_path"]),
                        ),
                    )
                    self.assertEqual(
                        stats["corridor_port_path"],
                        expected["corridor_port_path"],
                    )

        segment_summary = payload["voyage_fuel_g_per_tnm_directional_meta"][
            "segment_summary"
        ]
        self.assertEqual(
            serialized_candidate_voyages,
            segment_summary["observed_same_voyage_subroutes"],
        )


if __name__ == "__main__":
    unittest.main()
