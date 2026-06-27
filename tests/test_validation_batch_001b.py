import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from modules.multimodal.builder import build_path_geometry_from_resolved
from modules.validation.batch_001b import (
    ALL_OUTPUT_FIELDS,
    OUTPUT_FIELDS,
    apply_maritime_distance_override,
    build_exclusion_row,
    build_planned_row,
    build_rows,
    build_result_row,
    convert_maritime_distance,
    normalize_maritime_override,
    resolve_port,
    write_output_csv,
)


class Batch001BValidationTests(unittest.TestCase):
    def _config(self) -> dict:
        return {
            "batch_id": "Batch 001B",
            "model_defaults": {
                "cargo_t": 14.0,
                "cargo_teu": 1.0,
            },
        }

    def _geometry(self) -> dict:
        return {
            "status": "ok",
            "origin": {"label": "Origin, SP", "lat": -23.5, "lon": -46.6, "uf": "SP"},
            "destiny": {"label": "Destiny, AM", "lat": -3.1, "lon": -60.0, "uf": "AM"},
            "port_origin": {"name": "Porto de Santos", "lat": -23.9, "lon": -46.3},
            "port_destiny": {"name": "Porto de Manaus", "lat": -3.1, "lon": -60.0},
            "road_direct": {"distance_km": 1000.0, "source": "cache"},
            "first_mile": {"distance_km": 80.0, "source": "cache"},
            "sea_leg": {"distance_km": 500.0, "source": "haversine"},
            "last_mile": {"distance_km": 10.0, "source": "cache"},
        }

    def test_distance_unit_conversion_supports_nm_and_km(self) -> None:
        km, nm = convert_maritime_distance(10, "nm")
        self.assertAlmostEqual(km, 18.52)
        self.assertAlmostEqual(nm, 10.0)

        km, nm = convert_maritime_distance(18.52, "km")
        self.assertAlmostEqual(km, 18.52)
        self.assertAlmostEqual(nm, 10.0)

    def test_maritime_override_preserves_original_distance_and_source(self) -> None:
        case = {
            "maritime_distance_override": {
                "value": 10,
                "unit": "nm",
                "source": "test source",
                "provenance": "test provenance",
                "notes": "manual distance note",
                "lower_bound": 9,
                "upper_bound": 11,
                "bounds_unit": "nm",
                "scenario_type": "bounded",
                "bound_role": "high",
            }
        }
        row = build_planned_row(self._config(), case)
        updated, original = apply_maritime_distance_override(
            self._geometry(),
            normalize_maritime_override(case["maritime_distance_override"]),
        )

        self.assertAlmostEqual(row["maritime_distance_km"], 18.52)
        self.assertEqual(row["maritime_distance_source"], "test source")
        self.assertEqual(row["maritime_distance_source_type"], "manual_override")
        self.assertEqual(row["maritime_distance_provenance"], "test provenance")
        self.assertEqual(row["maritime_distance_notes"], "manual distance note")
        self.assertAlmostEqual(row["maritime_distance_lower_bound_km"], 16.668)
        self.assertAlmostEqual(row["maritime_distance_upper_bound_km"], 20.372)
        self.assertEqual(original["distance_km"], 500.0)
        self.assertEqual(original["source"], "haversine")
        self.assertEqual(original["source_type"], "haversine_fallback")
        self.assertAlmostEqual(updated["sea_leg"]["distance_km"], 18.52)
        self.assertEqual(updated["sea_leg"]["source"], "test source")
        self.assertEqual(updated["sea_leg"]["distance_provenance"]["source_type"], "manual_override")
        self.assertEqual(updated["sea_leg"]["distance_provenance"]["unit"], "nm")
        self.assertEqual(updated["sea_leg"]["original_distance_provenance"]["source_type"], "haversine_fallback")

    def test_maritime_override_can_mark_external_reference_and_bounds(self) -> None:
        override = normalize_maritime_override(
            {
                "value": 100,
                "unit": "km",
                "source_type": "external_reference",
                "source": "ANTAQ matrix reference",
                "provenance": "reference doc",
                "lower_bound_km": 95,
                "upper_bound_nm": 60,
            }
        )

        self.assertTrue(override.enabled)
        self.assertEqual(override.source_type, "external_reference")
        self.assertEqual(override.lower_bound_km, 95.0)
        self.assertAlmostEqual(override.lower_bound_nm, 95.0 / 1.852)
        self.assertAlmostEqual(override.upper_bound_km, 111.12)
        self.assertEqual(override.upper_bound_nm, 60.0)

    def test_builder_adds_structured_maritime_distance_provenance(self) -> None:
        def fake_route_resolver(_start, _end, _leg_name):
            return {"distance_km": 12.0, "source": "cache"}

        sea_matrix = SimpleNamespace(km_with_source=lambda _origin, _destiny: (456.0, "sea_matrix"))

        geometry = build_path_geometry_from_resolved(
            {"label": "Origin", "lat": -23.55, "lon": -46.63, "uf": "SP"},
            {"label": "Destiny", "lat": -22.97, "lon": -44.31, "uf": "RJ"},
            ors=object(),
            ports=[],
            sea_matrix=sea_matrix,
            port_origin={"name": "Porto de Santos", "lat": -23.96, "lon": -46.33},
            port_destiny={"name": "Porto de Angra dos Reis", "lat": -23.01, "lon": -44.32},
            first_mile_leg={"distance_km": 78.0, "source": "cache"},
            route_resolver=fake_route_resolver,
        )

        self.assertIsNotNone(geometry)
        assert geometry is not None
        provenance = geometry["sea_leg"]["distance_provenance"]
        self.assertEqual(provenance["distance_value"], 456.0)
        self.assertEqual(provenance["unit"], "km")
        self.assertEqual(provenance["source"], "sea_matrix")
        self.assertEqual(provenance["source_type"], "seamatrix")

    def test_resolve_port_matches_code_and_repaired_plain_name(self) -> None:
        ports = [
            {
                "name": "Porto do Pec\u00c3\u00a9m",
                "city": "S\u00c3\u00a3o Gon\u00c3\u00a7alo do Amarante",
                "lat": -3.54,
                "lon": -38.81,
                "aliases": ["Pec\u00c3\u00a9m", "BRPEC"],
            }
        ]

        by_code = resolve_port(ports, "BRPEC")
        by_plain_name = resolve_port(ports, "Pecem")

        self.assertEqual(by_code["name"], "Porto do Pec\u00c3\u00a9m")
        self.assertEqual(by_plain_name["name"], "Porto do Pec\u00c3\u00a9m")

    def test_exclusion_row_preserves_original_case_without_results(self) -> None:
        case = {
            "case_id": "TF-VAL-001B-004A",
            "original_case_id": "TF-VAL-004",
            "execution_mode": "record_only",
            "origin": "Brasilia, DF",
            "destination": "Salvador, BA",
            "validation_status": "excluded",
            "original_model": {
                "selected_origin_port": "Porto de Angra dos Reis",
                "selected_destination_port": "Porto de Salvador",
                "maritime_distance_km": 1273.3,
                "maritime_distance_source": "SeaMatrix haversine fallback",
            },
            "notes": "Invalid selected origin port.",
        }

        row = build_exclusion_row(self._config(), case)

        self.assertEqual(row["case_id"], "TF-VAL-001B-004A")
        self.assertEqual(row["original_case_id"], "TF-VAL-004")
        self.assertEqual(row["validation_status"], "excluded")
        self.assertEqual(row["original_maritime_distance_km"], 1273.3)
        self.assertEqual(row["road_cost_brl"], None)
        self.assertEqual(row["output_status"], "record_only")

    def test_same_port_row_flags_cabotage_inappropriate(self) -> None:
        case = {
            "case_id": "TF-VAL-001B-001",
            "original_case_id": "TF-VAL-001",
            "execution_mode": "record_only",
            "origin": "Sao Paulo, SP",
            "destination": "Santos, SP",
            "validation_status": "warning_only",
            "original_model": {
                "selected_origin_port": "Porto de Santos",
                "selected_destination_port": "Porto de Santos",
                "maritime_distance_km": 0.0,
                "maritime_distance_source": "SeaMatrix haversine fallback",
            },
        }

        row = build_exclusion_row(self._config(), case)

        self.assertTrue(row["same_port_flag"])
        self.assertTrue(row["cabotage_inappropriate_flag"])
        self.assertEqual(row["validation_status"], "warning_only")

    def test_execute_mode_keeps_planned_rows_planned(self) -> None:
        config = self._config()
        config["cases"] = [
            {
                "case_id": "TF-VAL-001B-BLOCKED",
                "execution_mode": "planned",
                "origin": "Origin, SP",
                "destination": "Destination, AM",
                "validation_status": "blocked_reference_needed",
            },
            {
                "case_id": "TF-VAL-001B-RECORD",
                "execution_mode": "record_only",
                "origin": "Origin, SP",
                "destination": "Destination, AM",
                "validation_status": "excluded",
            },
        ]

        rows = build_rows(config, execute=True)

        self.assertEqual(rows[0]["case_id"], "TF-VAL-001B-BLOCKED")
        self.assertEqual(rows[0]["output_status"], "planned")
        self.assertEqual(rows[0]["validation_status"], "blocked_reference_needed")
        self.assertEqual(rows[1]["case_id"], "TF-VAL-001B-RECORD")
        self.assertEqual(rows[1]["output_status"], "record_only")

    def test_result_row_exports_required_schema_and_override_provenance(self) -> None:
        case = {
            "case_id": "TF-VAL-001B-003B",
            "original_case_id": "TF-VAL-003",
            "origin": "Manaus, AM",
            "destination": "Fortaleza, CE",
            "port_overrides": {
                "destination": {
                    "port": "BRPEC",
                    "provenance": "correction plan",
                }
            },
            "maritime_distance_override": {
                "value": 20,
                "unit": "km",
                "source": "manual test source",
                "provenance": "manual test provenance",
            },
            "executed_validation_status": "sensitivity_executed",
        }
        geometry, original = apply_maritime_distance_override(
            self._geometry(),
            normalize_maritime_override(case["maritime_distance_override"]),
        )
        results = {
            "road_only": {"cost": 100.0, "co2e": 200.0},
            "multimodal": {"total_cost": 80.0, "total_co2e": 120.0},
        }

        row = build_result_row(
            self._config(),
            case,
            geometry=geometry,
            results=results,
            original_sea_leg=original,
            automatic_origin_port={"name": "Porto de Manaus"},
            automatic_destination_port={"name": "Porto de Fortaleza"},
            forced_destination_port={"name": "Porto do Pecem"},
        )

        for field in OUTPUT_FIELDS:
            self.assertIn(field, row)
        self.assertEqual(row["forced_destination_port"], "Porto do Pecem")
        self.assertTrue(row["destination_port_override"])
        self.assertEqual(row["destination_port_override_provenance"], "correction plan")
        self.assertTrue(row["maritime_distance_override"])
        self.assertEqual(row["maritime_distance_source"], "manual test source")
        self.assertEqual(row["maritime_distance_source_type"], "manual_override")
        self.assertEqual(row["original_maritime_distance_source_type"], "haversine_fallback")
        self.assertEqual(row["original_maritime_distance_km"], 500.0)
        self.assertIn("SeaMatrix haversine fallback", row["fallback_flags"])
        self.assertEqual(row["road_cost_brl"], 100.0)
        self.assertEqual(row["multimodal_emissions_kgco2e"], 120.0)
        self.assertEqual(row["validation_status"], "sensitivity_executed")

    def test_csv_writer_uses_full_output_header(self) -> None:
        row = {field: None for field in ALL_OUTPUT_FIELDS}
        row["case_id"] = "TF-VAL-001B-TEST"

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.csv"
            write_output_csv([row], output)
            with output.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader)
                data = next(reader)

        self.assertEqual(header, ALL_OUTPUT_FIELDS)
        self.assertEqual(data[0], "TF-VAL-001B-TEST")

    def test_tracked_batch_001b_artifact_schema_matches_output_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        template_path = repo_root / "docs" / "validation" / "tf_validation_batch_001b_output_template.csv"
        output_csv_path = repo_root / "docs" / "validation" / "tf_validation_batch_001b_output.csv"
        output_json_path = repo_root / "docs" / "validation" / "tf_validation_batch_001b_output.json"

        with template_path.open("r", encoding="utf-8", newline="") as handle:
            template_header = next(csv.reader(handle))
        with output_csv_path.open("r", encoding="utf-8", newline="") as handle:
            output_header = next(csv.reader(handle))
        with output_json_path.open("r", encoding="utf-8") as handle:
            output_rows = json.load(handle)

        self.assertEqual(template_header, ALL_OUTPUT_FIELDS)
        self.assertEqual(output_header, ALL_OUTPUT_FIELDS)
        self.assertTrue(output_rows)
        for row in output_rows:
            self.assertEqual(list(row.keys()), ALL_OUTPUT_FIELDS)


if __name__ == "__main__":
    unittest.main()
