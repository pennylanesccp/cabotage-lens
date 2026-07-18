from __future__ import annotations

import csv
import json
import logging
import math
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from modules.cabotage.sea_matrix import SeaMatrix
from modules.infra.data_assets import resolve_data_asset_path
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEA_MATRIX_PATH = Path("data/sea_matrix.json")
DEFAULT_VOYAGES_CSV_PATH = Path("data/processed/cabotage_data/tabular/antaq_voyages.csv")
DEFAULT_STOPS_CSV_PATH = Path("data/processed/cabotage_data/tabular/antaq_voyage_stops.csv")
DEFAULT_MRV_JSON_PATH = Path("data/processed/cabotage_data/mrv_average_efficiency_by_imo.json")
DEFAULT_CLASS_EFFICIENCY_JSON_PATH = Path(
    "data/processed/cabotage_data/container_ship_efficiency_classes.json"
)
DEFAULT_SHIP_TYPE = "Container ship"
PARSER_VERSION = "sea_matrix_efficiency_v4"
MARITIME_INTENSITY_SCHEMA_VERSION = 5
_KM_PER_NAUTICAL_MILE = 1.852
DEPLOYMENT_REQUIRED_ROUTE = ("Porto de Santos", "Porto de Manaus")
ROUTE_OBSERVATION_MODE = "observed_voyage_corridors"
SCENARIO_DISTANCE_METHOD = "arithmetic_mean_complete_observed_voyage_distances"
SCENARIO_DISTANCE_SCOPE = "one_complete_ordered_od_observation_per_voyage"
SCENARIO_DISTANCE_SOURCE = "observed_complete_voyage_distance_mean"
# Compatibility alias for callers that imported the former name. It no longer
# denotes a selected corridor; it identifies the scenario-distance rule.
CORRIDOR_SELECTION_CRITERION = SCENARIO_DISTANCE_METHOD
FALLBACK_TRIM_FRACTION_EACH_TAIL = 0.01
FALLBACK_OUTLIER_RULE = "symmetric_trim_1pct_each_tail_floor_count"
MRV_IMO_OUTLIER_UPPER_QUANTILE = 0.95
MRV_IMO_OUTLIER_MIN_SAMPLE_SIZE = 20
MRV_IMO_OUTLIER_RULE = "above_ship_type_p95_latest_positive_per_imo"
PAIR_INTENSITY_METHOD = "transport_work_weighted_mean"
PAIR_INTENSITY_SCOPE = "all_eligible_same_od_voyage_observations_across_corridors"
PAIR_INTENSITY_WEIGHT = "observed_transport_work_tnm"
PAIR_INTENSITY_SOURCE = "antaq_mrv_same_od_transport_work_weighted_mean"
PAIR_INTENSITY_ZERO_WORK_SOURCE = (
    "antaq_mrv_same_od_unweighted_mean_zero_transport_work"
)
PAIR_INTENSITY_UNAVAILABLE_SOURCE = (
    "antaq_mrv_same_od_representative_intensity_unavailable"
)
_EMPTY_AUDIT_IDS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class VoyageSegment:
    voyage_id: str
    imo: str
    from_port_name: str
    to_port_name: str
    from_port_code: str | None
    to_port_code: str | None
    segment_sequence: int
    cargo_weight_t: float
    cargo_teu: float
    distance_km: float
    distance_nm: float
    distance_source: str
    tonne_nm: float
    fuel_g_per_tnm: float | None
    fuel_consumption_g: float | None
    intensity_source: str
    intensity_source_level: str
    initial_onboard_weight_t: float
    initial_onboard_teu: float
    cargo_reconstruction_rule: str
    cargo_reconstruction_status: str
    calculation_status: str


@dataclass(frozen=True)
class VoyageSubroute:
    voyage_id: str
    imo: str
    origin_sequence: int
    destination_sequence: int
    corridor_port_path: tuple[str, ...]
    segments: tuple[VoyageSegment, ...]
    intensity_provenance: dict[str, Any]

    @property
    def distance_km(self) -> float:
        return sum(segment.distance_km for segment in self.segments)

    @property
    def distance_nm(self) -> float:
        return sum(segment.distance_nm for segment in self.segments)

    @property
    def transport_work_tnm(self) -> float:
        return sum(segment.tonne_nm for segment in self.segments)

    @property
    def fuel_consumption_g(self) -> float | None:
        values = [segment.fuel_consumption_g for segment in self.segments]
        if any(value is None for value in values):
            return None
        return sum(float(value) for value in values if value is not None)

    @property
    def is_direct(self) -> bool:
        return len(self.segments) == 1


def enrich_sea_matrix_with_efficiency(
    *,
    sea_matrix_path: Path | str = DEFAULT_SEA_MATRIX_PATH,
    voyages_csv_path: Path | str = DEFAULT_VOYAGES_CSV_PATH,
    stops_csv_path: Path | str = DEFAULT_STOPS_CSV_PATH,
    mrv_json_path: Path | str = DEFAULT_MRV_JSON_PATH,
    class_efficiency_json_path: Path | str = DEFAULT_CLASS_EFFICIENCY_JSON_PATH,
    default_ship_type: str = DEFAULT_SHIP_TYPE,
    possible_pairs_only: bool = True,
    matched_pairs_only: bool = True,
    prefer_local_voyage_inputs: bool = False,
    audit_voyage_ids: Iterable[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sea_matrix_candidate = Path(sea_matrix_path)
    sea_matrix_resolved = (
        sea_matrix_candidate.resolve()
        if sea_matrix_candidate.is_file()
        else resolve_data_asset_path(sea_matrix_candidate)
    )
    mrv_resolved = resolve_data_asset_path(mrv_json_path)
    class_efficiency_resolved = resolve_data_asset_path(class_efficiency_json_path)
    if prefer_local_voyage_inputs:
        voyages_resolved = Path(voyages_csv_path).resolve()
        stops_resolved = Path(stops_csv_path).resolve()
    else:
        voyages_resolved = resolve_data_asset_path(voyages_csv_path)
        stops_resolved = resolve_data_asset_path(stops_csv_path)

    payload = json.loads(Path(sea_matrix_resolved).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("matrix"), dict):
        raise ValueError(f"Invalid sea matrix payload: {sea_matrix_resolved}")

    voyages = _load_csv_rows(voyages_resolved)
    stops = _load_csv_rows(stops_resolved)
    mrv_catalog = _load_mrv_intensity_catalog(mrv_resolved)
    class_fallbacks = _load_class_efficiency_fallbacks(
        class_efficiency_resolved,
        source_label=_metadata_input_path(class_efficiency_json_path),
    )
    voyage_rows = {
        str(row.get("voyage_id") or "").strip(): row
        for row in voyages
        if str(row.get("voyage_id") or "").strip()
    }
    raw_audit_voyage_ids = (
        (audit_voyage_ids,)
        if isinstance(audit_voyage_ids, str)
        else (audit_voyage_ids or ())
    )
    audit_voyage_id_set = {
        str(voyage_id).strip()
        for voyage_id in raw_audit_voyage_ids
        if str(voyage_id).strip()
    }
    audit_logging_enabled = bool(audit_voyage_id_set) and _log.isEnabledFor(
        logging.DEBUG
    )
    effective_audit_voyage_ids = (
        audit_voyage_id_set if audit_logging_enabled else set()
    )
    if audit_logging_enabled:
        stop_voyage_ids = {
            str(row.get("voyage_id") or "").strip()
            for row in stops
            if str(row.get("voyage_id") or "").strip()
        }
        _log.debug(
            "maritime_audit_requested voyage_ids=%s "
            "missing_from_voyages_csv=%s missing_from_stops_csv=%s",
            sorted(audit_voyage_id_set),
            sorted(audit_voyage_id_set - voyage_rows.keys()),
            sorted(audit_voyage_id_set - stop_voyage_ids),
        )
    voyage_intensity_provenance = {
        voyage_id: _resolve_voyage_intensity(
            voyage,
            mrv_catalog=mrv_catalog,
            class_means=class_fallbacks,
            default_ship_type=default_ship_type,
        )
        for voyage_id, voyage in voyage_rows.items()
    }
    port_lookup = _build_port_lookup(payload)
    port_coordinates = _build_port_coordinates(payload)
    matrix = payload.get("matrix") or {}
    coastline_factor = _float_or_none(payload.get("coastline_factor")) or 1.0

    segments, subroutes, segment_meta = _build_segments(
        stops=stops,
        voyage_rows=voyage_rows,
        voyage_intensity_provenance=voyage_intensity_provenance,
        port_lookup=port_lookup,
        port_coordinates=port_coordinates,
        matrix=matrix,
        coastline_factor=coastline_factor,
        audit_voyage_ids=effective_audit_voyage_ids,
    )
    directional_stats = _aggregate_subroute_stats(
        subroutes,
        audit_voyage_ids=effective_audit_voyage_ids,
    )
    if matched_pairs_only:
        directional_stats = _filter_directional_stats_to_matched(directional_stats)
    possible_pairs_meta = None
    if possible_pairs_only:
        possible_pairs_meta = _prune_matrix_to_possible_pairs(
            payload,
            directional_stats,
        )

    payload["voyage_fuel_g_per_tnm_directional"] = directional_stats
    payload["voyage_intensity_provenance"] = voyage_intensity_provenance
    payload["voyage_fuel_g_per_tnm_directional_meta"] = {
        "parser_version": PARSER_VERSION,
        "maritime_intensity_schema_version": MARITIME_INTENSITY_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": (
            "ANTAQ observed same-voyage corridors + EU MRV latest IMO intensity with "
            "explicit IMO outlier replacement and robust vessel-class and ship-type "
            "estimates; same-OD transport-work-weighted intensity and arithmetic "
            "mean distance across complete observed voyages"
        ),
        "route_observation_mode": ROUTE_OBSERVATION_MODE,
        "scenario_distance_method": SCENARIO_DISTANCE_METHOD,
        "scenario_distance_scope": SCENARIO_DISTANCE_SCOPE,
        "weighting": "tonne_nm",
        "pair_intensity_method": PAIR_INTENSITY_METHOD,
        "pair_intensity_scope": PAIR_INTENSITY_SCOPE,
        "pair_intensity_weight": PAIR_INTENSITY_WEIGHT,
        "pair_intensity_source": PAIR_INTENSITY_SOURCE,
        "pair_intensity_zero_weight_source": PAIR_INTENSITY_ZERO_WORK_SOURCE,
        "pair_intensity_positive_weight_rule": (
            "sum(intensity_g_per_tnm * transport_work_tnm) / "
            "sum(transport_work_tnm)"
        ),
        "pair_intensity_zero_weight_rule": (
            "exclude_zero_weight_when_positive_transport_work_exists; otherwise use "
            "unweighted_mean_of_resolved_same_od_voyages"
        ),
        "segment_cargo_rule": (
            "minimum nonnegative onboard reconstruction: initial onboard equals max(0, "
            "-minimum cumulative net cargo), then each stop net is applied to the following leg"
        ),
        "cargo_reconstruction_rule": "minimum_nonnegative_prefix_offset",
        "distance_resolution_rule": (
            "positive sea-matrix distance first; coordinate haversine fallback for "
            "distinct canonical ports when the matrix value is missing or nonpositive"
        ),
        "intensity_resolution_hierarchy": [
            "eu_mrv_imo_latest",
            "eu_mrv_imo_outlier_replaced_by_vessel_class_or_ship_type",
            "eu_mrv_vessel_class_trimmed_mean_1pct_or_median",
            "eu_mrv_ship_type_trimmed_mean_1pct_or_median",
            "eu_mrv_ship_type_robust_default_container_ship",
            "unavailable",
        ],
        "fallback_outlier_policy": {
            "exact_imo_values": {
                "rule": MRV_IMO_OUTLIER_RULE,
                "upper_quantile": MRV_IMO_OUTLIER_UPPER_QUANTILE,
                "minimum_same_type_sample_size": MRV_IMO_OUTLIER_MIN_SAMPLE_SIZE,
                "replacement": (
                    "vessel_class_robust_statistic_when_available_else_"
                    "ship_type_robust_statistic"
                ),
            },
            "ship_type": FALLBACK_OUTLIER_RULE,
            "vessel_class": (
                "use artifact trimmed_mean_1pct; median when trimmed mean is unavailable"
            ),
            "trim_fraction_each_tail": FALLBACK_TRIM_FRACTION_EACH_TAIL,
        },
        "default_ship_type": str(default_ship_type or DEFAULT_SHIP_TYPE),
        "possible_pairs_only": bool(possible_pairs_only),
        "matched_pairs_only": bool(matched_pairs_only),
        "inputs": {
            "sea_matrix_path": _metadata_input_path(sea_matrix_path),
            "voyages_csv_path": _metadata_input_path(voyages_csv_path),
            "stops_csv_path": _metadata_input_path(stops_csv_path),
            "mrv_json_path": _metadata_input_path(mrv_json_path),
            "class_efficiency_json_path": _metadata_input_path(
                class_efficiency_json_path
            ),
        },
        "segment_summary": segment_meta,
        "voyage_intensity_source_counts": dict(
            sorted(
                Counter(
                    str(item.get("intensity_source") or "unavailable")
                    for item in voyage_intensity_provenance.values()
                ).items()
            )
        ),
        "mrv_catalog_summary": mrv_catalog["summary"],
        "possible_pairs_summary": possible_pairs_meta,
    }

    validate_enriched_sea_matrix_payload(payload)

    summary = {
        "directional_pairs": sum(len(v) for v in directional_stats.values()),
        "segments_contributing": sum(
            stats.get("resolved_segment_count", 0)
            for destinations in directional_stats.values()
            for stats in destinations.values()
        ),
        "segment_summary": segment_meta,
        "possible_pairs_summary": possible_pairs_meta,
    }
    return payload, summary


def write_enriched_sea_matrix(
    payload: dict[str, Any],
    *,
    output_path: Path | str = DEFAULT_SEA_MATRIX_PATH,
) -> Path:
    validate_enriched_sea_matrix_payload(payload)
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def validate_enriched_sea_matrix_payload(
    payload: dict[str, Any],
    *,
    required_route: tuple[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Sea matrix payload must be a JSON object.")

    sea_matrix = SeaMatrix.from_json_dict(payload)
    usable_distance_pairs = sum(
        1
        for origin, destinations in sea_matrix.matrix.items()
        for destination, distance_km in destinations.items()
        if _norm(origin) != _norm(destination) and _float_or_none(distance_km) is not None
        and float(distance_km) > 0.0
    )
    if usable_distance_pairs <= 0:
        raise ValueError("Sea matrix payload contains no usable positive port-pair distances.")

    usable_directional_pairs = sum(
        1
        for destinations in sea_matrix.directional_efficiency.values()
        for stats in destinations.values()
        if _float_or_none(stats.get("distance_km")) is not None
        and float(stats["distance_km"]) > 0.0
        and _float_or_none(stats.get("fuel_g_per_tnm_weighted_mean")) is not None
        and float(stats["fuel_g_per_tnm_weighted_mean"]) > 0.0
    )
    if usable_directional_pairs <= 0:
        raise ValueError(
            "Sea matrix payload contains no usable ANTAQ+MRV directional efficiency pairs."
        )

    result: dict[str, Any] = {
        "usable_distance_pairs": usable_distance_pairs,
        "usable_directional_pairs": usable_directional_pairs,
    }
    if required_route is None:
        return result

    origin, destination = required_route
    stats = sea_matrix.best_directional_stats(origin, destination)
    if not stats:
        raise ValueError(
            f"Sea matrix payload has no usable ANTAQ+MRV directional route for "
            f"{origin} -> {destination}."
        )

    directional_meta = payload.get("voyage_fuel_g_per_tnm_directional_meta")
    meta_route_mode = (
        directional_meta.get("route_observation_mode")
        if isinstance(directional_meta, dict)
        else None
    )
    route_observation_mode = (
        stats.get("route_observation_mode") or meta_route_mode
    )
    if route_observation_mode == ROUTE_OBSERVATION_MODE:
        required_positive_fields = [
            "segment_count",
            "resolved_segment_count",
            "resolved_voyage_count",
            "intensity_resolution_rate",
            "pair_intensity_g_per_tnm",
        ]
        if (
            str(stats.get("pair_intensity_method") or "").strip()
            == PAIR_INTENSITY_METHOD
        ):
            required_positive_fields.extend(
                (
                    "pair_intensity_positive_weight_voyage_count",
                    "pair_intensity_transport_work_tnm",
                )
            )
        coverage_label = "resolved-intensity"
    else:
        required_positive_fields = [
            "segment_count",
            "matched_segment_count",
            "unique_imo_count",
            "matched_imo_count",
            "match_rate_segments",
            "match_rate_tonne_nm",
        ]
        coverage_label = "segment/IMO"
    missing_coverage = [
        field
        for field in required_positive_fields
        if _float_or_none(stats.get(field)) is None or float(stats[field]) <= 0.0
    ]
    if missing_coverage:
        raise ValueError(
            f"Sea matrix directional route {origin} -> {destination} is missing positive "
            f"{coverage_label} coverage fields: {', '.join(missing_coverage)}."
        )

    result["required_route"] = {
        "origin": origin,
        "destination": destination,
        "route_observation_mode": route_observation_mode,
        "distance_km": stats.get("distance_km"),
        "scenario_distance_method": stats.get("scenario_distance_method"),
        "scenario_distance_scope": stats.get("scenario_distance_scope"),
        "scenario_distance_observation_count": stats.get(
            "scenario_distance_observation_count"
        ),
        "scenario_distance_corridor_count": stats.get(
            "scenario_distance_corridor_count"
        ),
        "scenario_distance_nm": stats.get("scenario_distance_nm"),
        "scenario_distance_min_km": stats.get("scenario_distance_min_km"),
        "scenario_distance_max_km": stats.get("scenario_distance_max_km"),
        "scenario_distance_source_counts": stats.get(
            "scenario_distance_source_counts"
        ),
        "fuel_g_per_tnm_weighted_mean": stats.get("fuel_g_per_tnm_weighted_mean"),
        "pair_intensity_g_per_tnm": stats.get("pair_intensity_g_per_tnm"),
        "pair_intensity_method": stats.get("pair_intensity_method"),
        "pair_intensity_scope": stats.get("pair_intensity_scope"),
        "pair_intensity_weight": stats.get("pair_intensity_weight"),
        "pair_intensity_source": stats.get("pair_intensity_source"),
        "pair_intensity_candidate_voyage_count": stats.get(
            "pair_intensity_candidate_voyage_count"
        ),
        "pair_intensity_positive_weight_voyage_count": stats.get(
            "pair_intensity_positive_weight_voyage_count"
        ),
        "pair_intensity_transport_work_tnm": stats.get(
            "pair_intensity_transport_work_tnm"
        ),
        "selected_corridor_fuel_g_per_tnm_weighted_mean": stats.get(
            "selected_corridor_fuel_g_per_tnm_weighted_mean"
        ),
        "segment_count": stats.get("segment_count"),
        "resolved_segment_count": stats.get("resolved_segment_count"),
        "resolved_voyage_count": stats.get("resolved_voyage_count"),
        "intensity_resolution_rate": stats.get("intensity_resolution_rate"),
        "imo_intensity_voyage_count": stats.get("imo_intensity_voyage_count"),
        "class_fallback_voyage_count": stats.get("class_fallback_voyage_count"),
        "type_fallback_voyage_count": stats.get("type_fallback_voyage_count"),
        "fallback_voyage_count": stats.get("fallback_voyage_count"),
        "unresolved_intensity_voyage_count": stats.get(
            "unresolved_intensity_voyage_count"
        ),
        "intensity_source_counts": stats.get("intensity_source_counts"),
        "matched_segment_count": stats.get("matched_segment_count"),
        "unique_imo_count": stats.get("unique_imo_count"),
        "matched_imo_count": stats.get("matched_imo_count"),
        "match_rate_segments": stats.get("match_rate_segments"),
        "match_rate_tonne_nm": stats.get("match_rate_tonne_nm"),
        "corridor_leg_count": stats.get("corridor_leg_count"),
        "corridor_port_path": stats.get("corridor_port_path"),
        "corridor_count": stats.get("corridor_count"),
        "selection_criterion": stats.get("selection_criterion"),
    }
    return result


def _load_csv_rows(path: Path | str) -> list[dict[str, str]]:
    resolved = Path(path)
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _metadata_input_path(path: Path | str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return candidate.name


def _robust_fallback_statistic(values: list[float]) -> dict[str, Any]:
    """Return an auditable robust fallback statistic for positive MRV values."""
    ordered = sorted(float(value) for value in values if float(value) > 0.0)
    if not ordered:
        raise ValueError("Robust MRV fallback requires at least one positive value.")

    raw_sample_size = len(ordered)
    trim_count_each_tail = int(
        math.floor(raw_sample_size * FALLBACK_TRIM_FRACTION_EACH_TAIL)
    )
    can_trim = (
        trim_count_each_tail > 0
        and (2 * trim_count_each_tail) < raw_sample_size
    )
    if can_trim:
        retained = ordered[
            trim_count_each_tail : raw_sample_size - trim_count_each_tail
        ]
        value = statistics.fmean(retained)
        statistic = "symmetric_trimmed_mean_1pct_of_latest_positive_per_imo"
        outlier_rule = FALLBACK_OUTLIER_RULE
    else:
        retained = ordered
        value = statistics.median(retained)
        statistic = "median_of_latest_positive_per_imo_small_sample"
        outlier_rule = "median_when_1pct_trim_removes_no_observation"
        trim_count_each_tail = 0

    return {
        "intensity_g_per_tnm": float(value),
        "statistic": statistic,
        "outlier_rule": outlier_rule,
        "trim_fraction_each_tail": FALLBACK_TRIM_FRACTION_EACH_TAIL,
        "trim_count_each_tail": trim_count_each_tail,
        "raw_sample_size": raw_sample_size,
        "retained_sample_size": len(retained),
        "excluded_sample_size": raw_sample_size - len(retained),
        "lower_retained_bound_g_per_tnm": float(retained[0]),
        "upper_retained_bound_g_per_tnm": float(retained[-1]),
        "raw_arithmetic_mean_g_per_tnm": float(statistics.fmean(ordered)),
        "raw_median_g_per_tnm": float(statistics.median(ordered)),
    }


def _linear_percentile(values: list[float], quantile: float) -> float:
    """Return an inclusive linear percentile without adding a dependency."""
    ordered = sorted(float(value) for value in values if float(value) > 0.0)
    if not ordered:
        raise ValueError("Percentile requires at least one positive MRV value.")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("Percentile quantile must be between zero and one.")

    position = (len(ordered) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return float(ordered[lower_index])
    fraction = position - lower_index
    return float(
        ordered[lower_index]
        + fraction * (ordered[upper_index] - ordered[lower_index])
    )


def _load_mrv_intensity_catalog(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    ships = payload.get("ships") if isinstance(payload, dict) else None
    if not isinstance(ships, list):
        raise ValueError(f"Invalid MRV efficiency payload: {path}")

    by_imo: dict[str, dict[str, Any]] = {}
    ship_metadata: dict[str, dict[str, str | None]] = {}
    for ship in ships:
        if not isinstance(ship, dict):
            continue
        imo = str(ship.get("imo") or "").strip()
        if not imo:
            continue

        ship_type = _text_or_none(ship.get("ship_type"))
        vessel_class = _text_or_none(ship.get("vessel_class"))
        ship_metadata[imo] = {
            "ship_type": ship_type,
            "vessel_class": vessel_class,
        }

        records = ship.get("records") if isinstance(ship.get("records"), list) else []
        selected: dict[str, Any] | None = None
        selected_period = -1
        for record in records:
            if not isinstance(record, dict):
                continue
            value = _float_or_none(
                record.get(
                    "average_fuel_consumption_per_transport_work_g_per_tonne_nmile"
                )
            )
            if value is None or value <= 0:
                continue
            reporting_period = _int_or_zero(record.get("reporting_period"))
            if selected is None or reporting_period > selected_period:
                selected = record
                selected_period = reporting_period

        if selected is None:
            continue

        by_imo[imo] = {
            "intensity_g_per_tnm": float(
                selected[
                    "average_fuel_consumption_per_transport_work_g_per_tonne_nmile"
                ]
            ),
            "intensity_source": "eu_mrv_imo_latest",
            "intensity_source_level": "imo",
            "source_key": imo,
            "statistic": "latest_positive",
            "sample_size": 1,
            "reporting_period": selected_period or None,
            "source_file": _text_or_none(selected.get("source_file")),
            "source_sheet": _text_or_none(selected.get("source_sheet")),
            "metric_basis": _text_or_none(
                selected.get("fuel_consumption_per_transport_work_source")
            ),
            "ship_type": ship_type,
            "vessel_class": vessel_class,
            "is_fallback": False,
            "used_default_ship_type": False,
        }

    type_members: dict[str, list[dict[str, Any]]] = {}
    type_labels: dict[str, str] = {}
    for imo, item in by_imo.items():
        ship_type = _text_or_none(item.get("ship_type"))
        if not ship_type:
            continue
        key = _norm(ship_type)
        type_labels.setdefault(key, ship_type)
        type_members.setdefault(key, []).append({"imo": imo, **item})

    ship_type_fallbacks: dict[str, dict[str, Any]] = {}
    ship_type_outlier_profiles: dict[str, dict[str, Any]] = {}
    for key, members in type_members.items():
        values = [float(member["intensity_g_per_tnm"]) for member in members]
        robust = _robust_fallback_statistic(values)
        source_files = sorted(
            {
                str(member["source_file"])
                for member in members
                if _text_or_none(member.get("source_file"))
            }
        )
        source_sheets = sorted(
            {
                str(member["source_sheet"])
                for member in members
                if _text_or_none(member.get("source_sheet"))
            }
        )
        basis_counts = Counter(
            str(member.get("metric_basis") or "unspecified") for member in members
        )
        source_suffix = (
            "trimmed_mean_1pct"
            if robust["trim_count_each_tail"] > 0
            else "median"
        )
        ship_type_fallbacks[key] = {
            **robust,
            "intensity_source": f"eu_mrv_ship_type_{source_suffix}",
            "intensity_source_level": "ship_type",
            "source_key": type_labels[key],
            "sample_size": len(values),
            "reporting_period": None,
            "source_file": source_files[0] if len(source_files) == 1 else None,
            "source_sheet": source_sheets[0] if len(source_sheets) == 1 else None,
            "source_files": source_files,
            "source_sheets": source_sheets,
            "metric_basis": "mixed" if len(basis_counts) > 1 else next(iter(basis_counts), None),
            "metric_basis_counts": dict(sorted(basis_counts.items())),
            "ship_type": type_labels[key],
            "vessel_class": None,
            "is_fallback": True,
            "used_default_ship_type": False,
        }
        if len(values) >= MRV_IMO_OUTLIER_MIN_SAMPLE_SIZE:
            ship_type_outlier_profiles[key] = {
                "ship_type": type_labels[key],
                "sample_size": len(values),
                "upper_quantile": MRV_IMO_OUTLIER_UPPER_QUANTILE,
                "upper_threshold_g_per_tnm": _linear_percentile(
                    values,
                    MRV_IMO_OUTLIER_UPPER_QUANTILE,
                ),
                "outlier_rule": MRV_IMO_OUTLIER_RULE,
            }

    return {
        "by_imo": by_imo,
        "ship_metadata": ship_metadata,
        "ship_type_fallbacks": ship_type_fallbacks,
        "ship_type_outlier_profiles": ship_type_outlier_profiles,
        "summary": {
            "ship_records": len(ships),
            "latest_positive_imo_count": len(by_imo),
            "ship_type_fallback_count": len(ship_type_fallbacks),
            "ship_type_latest_imo_counts": {
                type_labels[key]: len(members)
                for key, members in sorted(type_members.items())
            },
        },
    }


def _load_latest_imo_efficiency(path: Path | str) -> dict[str, float]:
    """Compatibility wrapper returning the latest positive value by IMO."""
    catalog = _load_mrv_intensity_catalog(path)
    return {
        imo: float(item["intensity_g_per_tnm"])
        for imo, item in catalog["by_imo"].items()
    }


def _load_class_efficiency_fallbacks(
    path: Path | str,
    *,
    source_label: str | None = None,
) -> dict[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid vessel-class efficiency payload: {path}")

    out: dict[str, dict[str, Any]] = {}
    for class_name, entry in payload.items():
        if not isinstance(entry, dict):
            continue
        stats = entry.get("fuel_g_per_tnm")
        if not isinstance(stats, dict):
            continue
        trimmed_mean = _float_or_none(stats.get("trimmed_mean_1pct"))
        median = _float_or_none(stats.get("median") or stats.get("p50"))
        if trimmed_mean is not None and trimmed_mean > 0:
            robust_value = trimmed_mean
            source_suffix = "trimmed_mean_1pct"
            statistic = "symmetric_trimmed_mean_1pct_from_class_artifact"
            outlier_rule = "class_artifact_excludes_below_p1_and_above_p99"
        elif median is not None and median > 0:
            robust_value = median
            source_suffix = "median"
            statistic = "median_from_class_artifact"
            outlier_rule = "median_robust_no_tail_weighting"
        else:
            continue
        sample_size = _int_or_zero(stats.get("count") or entry.get("sample_size"))
        class_label = str(class_name).strip()
        out[_norm(class_label)] = {
            "intensity_g_per_tnm": float(robust_value),
            "intensity_source": f"eu_mrv_vessel_class_{source_suffix}",
            "intensity_source_level": "vessel_class",
            "source_key": class_label,
            "statistic": statistic,
            "outlier_rule": outlier_rule,
            "trim_fraction_each_tail": (
                FALLBACK_TRIM_FRACTION_EACH_TAIL
                if source_suffix == "trimmed_mean_1pct"
                else 0.0
            ),
            "sample_size": sample_size,
            "raw_sample_size": sample_size,
            "reporting_period": None,
            "source_file": source_label or _metadata_input_path(path),
            "source_sheet": None,
            "metric_basis": "class_robust_statistic_artifact",
            "ship_type": None,
            "vessel_class": class_label,
            "is_fallback": True,
            "used_default_ship_type": False,
        }
    return out


def _resolve_voyage_intensity(
    voyage: dict[str, str],
    *,
    mrv_catalog: dict[str, Any],
    class_means: dict[str, dict[str, Any]],
    default_ship_type: str,
) -> dict[str, Any]:
    imo = str(voyage.get("imo") or "").strip()
    direct = mrv_catalog["by_imo"].get(imo)
    if isinstance(direct, dict):
        ship_type = _text_or_none(voyage.get("ship_type")) or _text_or_none(
            direct.get("ship_type")
        )
        outlier_profile = (
            mrv_catalog.get("ship_type_outlier_profiles", {}).get(
                _norm(ship_type)
            )
            if ship_type
            else None
        )
        direct_intensity = _float_or_none(direct.get("intensity_g_per_tnm"))
        upper_threshold = (
            _float_or_none(outlier_profile.get("upper_threshold_g_per_tnm"))
            if isinstance(outlier_profile, dict)
            else None
        )
        if (
            direct_intensity is not None
            and upper_threshold is not None
            and direct_intensity > upper_threshold
        ):
            vessel_class = _text_or_none(voyage.get("vessel_class")) or _text_or_none(
                direct.get("vessel_class")
            )
            class_mean = (
                class_means.get(_norm(vessel_class)) if vessel_class else None
            )
            replacement = (
                dict(class_mean)
                if isinstance(class_mean, dict)
                else dict(
                    mrv_catalog["ship_type_fallbacks"].get(_norm(ship_type)) or {}
                )
            )
            if replacement:
                replacement_level = str(
                    replacement.get("intensity_source_level") or "ship_type"
                )
                replacement["intensity_source"] = (
                    "eu_mrv_imo_outlier_replaced_by_vessel_class"
                    if replacement_level == "vessel_class"
                    else "eu_mrv_imo_outlier_replaced_by_ship_type"
                )
                replacement["intensity_source_level"] = replacement_level
                replacement["is_fallback"] = True
                replacement["used_default_ship_type"] = False
                replacement["ship_type"] = ship_type
                replacement["vessel_class"] = vessel_class
                replacement["matched_imo"] = imo
                replacement["matched_imo_intensity_g_per_tnm"] = direct_intensity
                replacement["matched_imo_reporting_period"] = direct.get(
                    "reporting_period"
                )
                replacement["matched_imo_source_file"] = direct.get("source_file")
                replacement["outlier_rule"] = str(
                    outlier_profile.get("outlier_rule")
                    or MRV_IMO_OUTLIER_RULE
                )
                replacement["outlier_upper_quantile"] = outlier_profile.get(
                    "upper_quantile"
                )
                replacement["outlier_upper_threshold_g_per_tnm"] = upper_threshold
                replacement["outlier_reference_sample_size"] = outlier_profile.get(
                    "sample_size"
                )
                return replacement
        return dict(direct)

    metadata = mrv_catalog["ship_metadata"].get(imo) or {}
    vessel_class = _text_or_none(voyage.get("vessel_class")) or _text_or_none(
        metadata.get("vessel_class")
    )
    ship_type = _text_or_none(voyage.get("ship_type")) or _text_or_none(
        metadata.get("ship_type")
    )

    if vessel_class:
        class_mean = class_means.get(_norm(vessel_class))
        if isinstance(class_mean, dict):
            resolved = dict(class_mean)
            resolved["ship_type"] = ship_type
            resolved["vessel_class"] = vessel_class
            return resolved

    type_candidates: list[tuple[str, bool]] = []
    if ship_type:
        type_candidates.append((ship_type, False))
    normalized_default = str(default_ship_type or DEFAULT_SHIP_TYPE).strip() or DEFAULT_SHIP_TYPE
    if not ship_type or _norm(ship_type) != _norm(normalized_default):
        type_candidates.append((normalized_default, True))

    for candidate, used_default in type_candidates:
        type_fallback = mrv_catalog["ship_type_fallbacks"].get(_norm(candidate))
        if not isinstance(type_fallback, dict):
            continue
        resolved = dict(type_fallback)
        resolved["source_key"] = candidate
        resolved["ship_type"] = candidate
        resolved["vessel_class"] = vessel_class
        resolved["used_default_ship_type"] = bool(used_default)
        return resolved

    return {
        "intensity_g_per_tnm": None,
        "intensity_source": "unavailable",
        "intensity_source_level": "unresolved",
        "source_key": imo or None,
        "statistic": None,
        "sample_size": 0,
        "reporting_period": None,
        "source_file": None,
        "source_sheet": None,
        "metric_basis": None,
        "ship_type": ship_type or normalized_default,
        "vessel_class": vessel_class,
        "is_fallback": False,
        "used_default_ship_type": not bool(ship_type),
    }


def _build_port_lookup(payload: dict[str, Any]) -> dict[str, str]:
    ports = payload.get("ports") if isinstance(payload.get("ports"), list) else []
    lookup: dict[str, str] = {}
    for port in ports:
        if not isinstance(port, dict):
            continue
        name = str(port.get("name") or "").strip()
        if not name:
            continue
        lookup.setdefault(_norm(name), name)
        slug = str(port.get("slug") or "").strip()
        if slug:
            lookup.setdefault(_norm(slug), name)
        for candidate in port.get("slug_candidates") or []:
            text = str(candidate or "").strip()
            if text:
                lookup.setdefault(_norm(text), name)
    return lookup


def _build_port_coordinates(
    payload: dict[str, Any],
) -> dict[str, tuple[float, float]]:
    ports = payload.get("ports") if isinstance(payload.get("ports"), list) else []
    coordinates: dict[str, tuple[float, float]] = {}
    for port in ports:
        if not isinstance(port, dict):
            continue
        name = _text_or_none(port.get("name"))
        lat = _float_or_none(port.get("lat"))
        lon = _float_or_none(port.get("lon"))
        if name and lat is not None and lon is not None:
            coordinates[name] = (lat, lon)
    return coordinates


def _collapse_consecutive_canonical_stops(
    rows: list[dict[str, str]],
    port_lookup: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    """Merge adjacent terminal calls that resolve to the same canonical port."""
    collapsed: list[dict[str, Any]] = []
    collapsed_call_count = 0
    for row in rows:
        item: dict[str, Any] = dict(row)
        item["_source_sequences"] = [
            _int_or_zero(row.get("sequence"))
        ]
        canonical_port = _resolve_matrix_port_name(row, port_lookup)
        item["_resolved_matrix_port_name"] = canonical_port
        if (
            collapsed
            and canonical_port is not None
            and collapsed[-1].get("_resolved_matrix_port_name") == canonical_port
        ):
            for field in (
                "loaded_weight_t",
                "unloaded_weight_t",
                "net_weight_t",
                "loaded_teu",
                "unloaded_teu",
                "net_teu",
            ):
                collapsed[-1][field] = _float_or_zero(collapsed[-1].get(field)) + (
                    _float_or_zero(item.get(field))
                )
            collapsed[-1].setdefault("_source_sequences", []).extend(
                item["_source_sequences"]
            )
            collapsed_call_count += 1
            continue
        collapsed.append(item)
    return collapsed, collapsed_call_count


def _haversine_distance_km(
    from_coordinates: tuple[float, float],
    to_coordinates: tuple[float, float],
) -> float:
    lat1, lon1 = from_coordinates
    lat2, lon2 = to_coordinates
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    value = min(max(value, 0.0), 1.0)
    return 6371.0088 * 2.0 * math.atan2(math.sqrt(value), math.sqrt(1.0 - value))


def _resolve_segment_distance_km(
    matrix: dict[str, Any],
    port_coordinates: dict[str, tuple[float, float]],
    from_port: str,
    to_port: str,
    *,
    coastline_factor: float,
) -> tuple[float | None, str]:
    matrix_distance = _matrix_distance_km(matrix, from_port, to_port)
    if matrix_distance is not None and matrix_distance > 0.0:
        return matrix_distance, "sea_matrix"

    if _norm(from_port) == _norm(to_port):
        return None, "same_canonical_port"

    from_coordinates = port_coordinates.get(from_port)
    to_coordinates = port_coordinates.get(to_port)
    if from_coordinates is None or to_coordinates is None:
        return None, "unavailable"

    distance_km = _haversine_distance_km(from_coordinates, to_coordinates) * max(
        float(coastline_factor), 1.0
    )
    if distance_km <= 0.0:
        return None, "unavailable"
    return distance_km, "haversine_fallback"


def _minimum_nonnegative_initial(net_changes: list[float]) -> float:
    cumulative = 0.0
    minimum = 0.0
    for change in net_changes:
        cumulative += float(change)
        minimum = min(minimum, cumulative)
    return max(-minimum, 0.0)


def _build_segments(
    *,
    stops: list[dict[str, str]],
    voyage_rows: dict[str, dict[str, str]],
    voyage_intensity_provenance: dict[str, dict[str, Any]],
    port_lookup: dict[str, str],
    port_coordinates: dict[str, tuple[float, float]],
    matrix: dict[str, Any],
    coastline_factor: float,
    audit_voyage_ids: set[str] | None = None,
) -> tuple[list[VoyageSegment], list[VoyageSubroute], dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in stops:
        voyage_id = str(row.get("voyage_id") or "").strip()
        if not voyage_id:
            continue
        grouped.setdefault(voyage_id, []).append(row)

    segments: list[VoyageSegment] = []
    subroutes: list[VoyageSubroute] = []
    raw_candidate_segments = 0
    total_candidate_segments = 0
    collapsed_consecutive_stop_calls = 0
    positive_cargo_segments = 0
    mapped_segments = 0
    matrix_distance_segments = 0
    haversine_fallback_segments = 0
    matched_segments = 0
    resolved_segments = 0
    fallback_segments = 0
    skipped_unmapped_ports = 0
    skipped_missing_distance = 0
    nonpositive_cargo_segments = 0
    candidate_subroutes = 0
    eligible_subroute_occurrences = 0
    deduplicated_subroute_occurrences = 0
    skipped_incomplete_subroutes = 0
    skipped_same_port_subroutes = 0
    voyages_with_reconstructed_initial_cargo = 0
    reconstructed_initial_onboard_weight_t_total = 0.0
    reconstructed_initial_onboard_teu_total = 0.0
    audit_ids = audit_voyage_ids or _EMPTY_AUDIT_IDS

    for voyage_id, voyage_stops in grouped.items():
        raw_rows = sorted(
            voyage_stops,
            key=lambda row: _int_or_zero(row.get("sequence")),
        )
        raw_candidate_segments += max(len(raw_rows) - 1, 0)
        voyage = voyage_rows.get(voyage_id) or {}
        imo = str(voyage.get("imo") or "").strip()
        intensity_provenance = voyage_intensity_provenance.get(voyage_id) or {
            "intensity_g_per_tnm": None,
            "intensity_source": "unavailable",
            "intensity_source_level": "unresolved",
            "is_fallback": False,
        }
        fuel_g_per_tnm = _float_or_none(
            intensity_provenance.get("intensity_g_per_tnm")
        )
        intensity_source = str(
            intensity_provenance.get("intensity_source") or "unavailable"
        )
        intensity_source_level = str(
            intensity_provenance.get("intensity_source_level") or "unresolved"
        )
        initial_onboard_weight_t = _minimum_nonnegative_initial(
            [_float_or_zero(row.get("net_weight_t")) for row in raw_rows]
        )
        initial_onboard_teu = _minimum_nonnegative_initial(
            [_float_or_zero(row.get("net_teu")) for row in raw_rows]
        )
        rows, collapsed_calls = _collapse_consecutive_canonical_stops(
            raw_rows,
            port_lookup,
        )
        audit_this_voyage = voyage_id in audit_ids
        if audit_this_voyage:
            _log.debug(
                "maritime_voyage_reconstruction voyage_id=%s imo=%s "
                "raw_stop_count=%d canonical_stop_count=%d "
                "initial_onboard_weight_t=%.6f initial_onboard_teu=%.6f "
                "intensity_g_per_tnm=%s intensity_source=%s "
                "intensity_source_level=%s canonical_path=%s",
                voyage_id,
                imo,
                len(raw_rows),
                len(rows),
                initial_onboard_weight_t,
                initial_onboard_teu,
                fuel_g_per_tnm,
                intensity_source,
                intensity_source_level,
                " -> ".join(
                    str(
                        row.get("_resolved_matrix_port_name")
                        or row.get("port_name")
                        or "unmapped"
                    )
                    for row in rows
                ),
            )
        collapsed_consecutive_stop_calls += collapsed_calls
        if initial_onboard_weight_t > 0 or initial_onboard_teu > 0:
            voyages_with_reconstructed_initial_cargo += 1
            reconstructed_initial_onboard_weight_t_total += initial_onboard_weight_t
            reconstructed_initial_onboard_teu_total += initial_onboard_teu
        cumulative_weight_t = initial_onboard_weight_t
        cumulative_teu = initial_onboard_teu
        voyage_segment_slots: list[VoyageSegment | None] = []
        voyage_subroute_options: list[VoyageSubroute] = []

        for idx in range(len(rows) - 1):
            current = rows[idx]
            nxt = rows[idx + 1]
            total_candidate_segments += 1

            cumulative_weight_t += _float_or_zero(current.get("net_weight_t"))
            cumulative_teu += _float_or_zero(current.get("net_teu"))
            cargo_weight_t = max(cumulative_weight_t, 0.0)
            cargo_teu = max(cumulative_teu, 0.0)
            cargo_reconstruction_status = (
                "reconstructed_initial_onboard"
                if initial_onboard_weight_t > 0 or initial_onboard_teu > 0
                else ("zero_activity" if cargo_weight_t <= 0 else "observed_net_cumulative")
            )
            if cargo_weight_t <= 0:
                nonpositive_cargo_segments += 1
            else:
                positive_cargo_segments += 1

            from_port = _text_or_none(current.get("_resolved_matrix_port_name"))
            to_port = _text_or_none(nxt.get("_resolved_matrix_port_name"))
            if from_port is None or to_port is None:
                skipped_unmapped_ports += 1
                if audit_this_voyage:
                    _log.debug(
                        "maritime_segment_skipped voyage_id=%s imo=%s "
                        "canonical_segment_index=%d origin_stop_sequence=%s "
                        "destination_stop_sequence=%s "
                        "origin_call_sequences=%s destination_call_sequences=%s "
                        "reason=unmapped_port "
                        "raw_origin=%r raw_destination=%r",
                        voyage_id,
                        imo,
                        idx,
                        current.get("sequence"),
                        nxt.get("sequence"),
                        current.get("_source_sequences"),
                        nxt.get("_source_sequences"),
                        current.get("port_name"),
                        nxt.get("port_name"),
                    )
                voyage_segment_slots.append(None)
                continue

            distance_km, distance_source = _resolve_segment_distance_km(
                matrix,
                port_coordinates,
                from_port,
                to_port,
                coastline_factor=coastline_factor,
            )
            if distance_km is None:
                skipped_missing_distance += 1
                if audit_this_voyage:
                    _log.debug(
                        "maritime_segment_skipped voyage_id=%s imo=%s "
                        "canonical_segment_index=%d origin_stop_sequence=%s "
                        "destination_stop_sequence=%s "
                        "origin_call_sequences=%s destination_call_sequences=%s "
                        "reason=missing_distance "
                        "origin=%r destination=%r",
                        voyage_id,
                        imo,
                        idx,
                        current.get("sequence"),
                        nxt.get("sequence"),
                        current.get("_source_sequences"),
                        nxt.get("_source_sequences"),
                        from_port,
                        to_port,
                    )
                voyage_segment_slots.append(None)
                continue

            mapped_segments += 1
            if distance_source == "sea_matrix":
                matrix_distance_segments += 1
            elif distance_source == "haversine_fallback":
                haversine_fallback_segments += 1
            distance_nm = distance_km / _KM_PER_NAUTICAL_MILE
            tonne_nm = cargo_weight_t * distance_nm
            resolved = fuel_g_per_tnm is not None and fuel_g_per_tnm > 0
            if resolved:
                resolved_segments += 1
            if intensity_source_level == "imo" and resolved:
                matched_segments += 1
            elif bool(intensity_provenance.get("is_fallback")) and resolved:
                fallback_segments += 1

            segment = VoyageSegment(
                voyage_id=voyage_id,
                imo=imo,
                from_port_name=from_port,
                to_port_name=to_port,
                from_port_code=_text_or_none(current.get("port_code")),
                to_port_code=_text_or_none(nxt.get("port_code")),
                segment_sequence=idx,
                cargo_weight_t=cargo_weight_t,
                cargo_teu=cargo_teu,
                distance_km=distance_km,
                distance_nm=distance_nm,
                distance_source=distance_source,
                tonne_nm=tonne_nm,
                fuel_g_per_tnm=fuel_g_per_tnm,
                fuel_consumption_g=(
                    fuel_g_per_tnm * tonne_nm if resolved else None
                ),
                intensity_source=intensity_source,
                intensity_source_level=intensity_source_level,
                initial_onboard_weight_t=initial_onboard_weight_t,
                initial_onboard_teu=initial_onboard_teu,
                cargo_reconstruction_rule="minimum_nonnegative_prefix_offset",
                cargo_reconstruction_status=cargo_reconstruction_status,
                calculation_status=(
                    "complete" if resolved else "partial_missing_intensity"
                ),
            )
            segments.append(segment)
            voyage_segment_slots.append(segment)
            if audit_this_voyage:
                _log.debug(
                    "maritime_segment_reconstruction voyage_id=%s imo=%s "
                    "canonical_segment_index=%d origin_stop_sequence=%s "
                    "destination_stop_sequence=%s "
                    "origin_call_sequences=%s destination_call_sequences=%s "
                    "origin=%r destination=%r "
                    "departure_loaded_weight_t=%.6f "
                    "departure_unloaded_weight_t=%.6f "
                    "departure_net_weight_t=%.6f "
                    "initial_onboard_weight_t=%.6f cargo_onboard_weight_t=%.6f "
                    "cargo_onboard_teu=%.6f distance_km=%.6f distance_nm=%.6f "
                    "distance_source=%s transport_work_tnm=%.6f "
                    "intensity_g_per_tnm=%s intensity_source=%s "
                    "intensity_source_level=%s fuel_consumption_kg=%s "
                    "cargo_reconstruction_status=%s calculation_status=%s",
                    voyage_id,
                    imo,
                    idx,
                    current.get("sequence"),
                    nxt.get("sequence"),
                    current.get("_source_sequences"),
                    nxt.get("_source_sequences"),
                    from_port,
                    to_port,
                    _float_or_zero(current.get("loaded_weight_t")),
                    _float_or_zero(current.get("unloaded_weight_t")),
                    _float_or_zero(current.get("net_weight_t")),
                    initial_onboard_weight_t,
                    cargo_weight_t,
                    cargo_teu,
                    distance_km,
                    distance_nm,
                    distance_source,
                    tonne_nm,
                    fuel_g_per_tnm,
                    intensity_source,
                    intensity_source_level,
                    (
                        f"{segment.fuel_consumption_g / 1000.0:.6f}"
                        if segment.fuel_consumption_g is not None
                        else "unavailable"
                    ),
                    cargo_reconstruction_status,
                    segment.calculation_status,
                )

        for origin_idx in range(max(len(rows) - 1, 0)):
            for destination_idx in range(origin_idx + 1, len(rows)):
                candidate_subroutes += 1
                selected_slots = voyage_segment_slots[origin_idx:destination_idx]
                if not selected_slots or any(slot is None for slot in selected_slots):
                    skipped_incomplete_subroutes += 1
                    continue
                selected_segments = tuple(
                    slot for slot in selected_slots if slot is not None
                )
                corridor_path = (
                    selected_segments[0].from_port_name,
                    *(segment.to_port_name for segment in selected_segments),
                )
                if _norm(corridor_path[0]) == _norm(corridor_path[-1]):
                    skipped_same_port_subroutes += 1
                    continue
                eligible_subroute_occurrences += 1
                voyage_subroute_options.append(
                    VoyageSubroute(
                        voyage_id=voyage_id,
                        imo=imo,
                        origin_sequence=_int_or_zero(
                            rows[origin_idx].get("sequence")
                        ),
                        destination_sequence=_int_or_zero(
                            rows[destination_idx].get("sequence")
                        ),
                        corridor_port_path=tuple(corridor_path),
                        segments=selected_segments,
                        intensity_provenance=dict(intensity_provenance),
                    )
                )

        selected_by_od: dict[tuple[str, str], VoyageSubroute] = {}
        for candidate in voyage_subroute_options:
            od_key = (
                candidate.corridor_port_path[0],
                candidate.corridor_port_path[-1],
            )
            incumbent = selected_by_od.get(od_key)
            candidate_rank = (
                0 if candidate.is_direct else 1,
                candidate.distance_km,
                len(candidate.segments),
                candidate.origin_sequence,
                candidate.destination_sequence,
            )
            incumbent_rank = (
                0 if incumbent is not None and incumbent.is_direct else 1,
                incumbent.distance_km if incumbent is not None else float("inf"),
                len(incumbent.segments) if incumbent is not None else 0,
                incumbent.origin_sequence if incumbent is not None else 0,
                incumbent.destination_sequence if incumbent is not None else 0,
            )
            if incumbent is None or candidate_rank < incumbent_rank:
                selected_by_od[od_key] = candidate

        selected_voyage_subroutes = list(selected_by_od.values())
        if audit_this_voyage:
            for subroute in sorted(
                selected_voyage_subroutes,
                key=lambda item: (
                    item.origin_sequence,
                    item.destination_sequence,
                    item.corridor_port_path,
                ),
            ):
                _log.debug(
                    "maritime_voyage_subroute voyage_id=%s imo=%s "
                    "origin_sequence=%d destination_sequence=%d direct=%s "
                    "path=%s distance_nm=%.6f transport_work_tnm=%.6f "
                    "fuel_consumption_kg=%s",
                    voyage_id,
                    imo,
                    subroute.origin_sequence,
                    subroute.destination_sequence,
                    subroute.is_direct,
                    " -> ".join(subroute.corridor_port_path),
                    subroute.distance_nm,
                    subroute.transport_work_tnm,
                    (
                        f"{subroute.fuel_consumption_g / 1000.0:.6f}"
                        if subroute.fuel_consumption_g is not None
                        else "unavailable"
                    ),
                )
        deduplicated_subroute_occurrences += (
            len(voyage_subroute_options) - len(selected_voyage_subroutes)
        )
        subroutes.extend(selected_voyage_subroutes)

    meta = {
        "raw_candidate_segments": raw_candidate_segments,
        "candidate_segments": total_candidate_segments,
        "collapsed_consecutive_canonical_stop_calls": (
            collapsed_consecutive_stop_calls
        ),
        "positive_cargo_segments": positive_cargo_segments,
        "mapped_segments": mapped_segments,
        "matrix_distance_segments": matrix_distance_segments,
        "haversine_fallback_segments": haversine_fallback_segments,
        "matched_segments": matched_segments,
        "resolved_segments": resolved_segments,
        "fallback_segments": fallback_segments,
        "nonpositive_cargo_segments": nonpositive_cargo_segments,
        "skipped_nonpositive_cargo_segments": 0,
        "skipped_unmapped_port_segments": skipped_unmapped_ports,
        "skipped_missing_distance_segments": skipped_missing_distance,
        "candidate_subroutes": candidate_subroutes,
        "eligible_subroute_occurrences": eligible_subroute_occurrences,
        "deduplicated_subroute_occurrences": (
            deduplicated_subroute_occurrences
        ),
        "observed_same_voyage_subroutes": len(subroutes),
        "skipped_incomplete_subroutes": skipped_incomplete_subroutes,
        "skipped_same_port_subroutes": skipped_same_port_subroutes,
        "unusable_subroutes": skipped_incomplete_subroutes,
        "subroute_calculation_policy": "complete_leg_chain_only_no_partial_sums",
        "voyage_od_observation_policy": (
            "one_complete_observation_per_voyage_and_ordered_port_pair; "
            "direct_first_then_shortest_distance_km only resolves duplicate "
            "occurrences within the same voyage"
        ),
        "cargo_reconstruction_rule": "minimum_nonnegative_prefix_offset",
        "voyages_with_reconstructed_initial_cargo": (
            voyages_with_reconstructed_initial_cargo
        ),
        "reconstructed_initial_onboard_weight_t_total": round(
            reconstructed_initial_onboard_weight_t_total, 3
        ),
        "reconstructed_initial_onboard_teu_total": round(
            reconstructed_initial_onboard_teu_total, 3
        ),
        "imo_match_rate_on_mapped_segments": (
            round(matched_segments / mapped_segments, 6) if mapped_segments else None
        ),
        "intensity_resolution_rate_on_mapped_segments": (
            round(resolved_segments / mapped_segments, 6) if mapped_segments else None
        ),
    }
    return segments, subroutes, meta


def _aggregate_subroute_stats(
    subroutes: list[VoyageSubroute],
    *,
    audit_voyage_ids: set[str] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str, tuple[str, ...]], list[VoyageSubroute]] = {}
    pair_subroutes: dict[tuple[str, str], list[VoyageSubroute]] = {}
    for subroute in subroutes:
        pair_key = (
            subroute.corridor_port_path[0],
            subroute.corridor_port_path[-1],
        )
        pair_subroutes.setdefault(pair_key, []).append(subroute)
        key = (
            *pair_key,
            subroute.corridor_port_path,
        )
        grouped.setdefault(key, []).append(subroute)

    pair_options: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for (origin, destination, path), subset in sorted(grouped.items()):
        option = _aggregate_corridor_option(path, subset)
        pair_options.setdefault((origin, destination), []).append(option)

    out: dict[str, dict[str, dict[str, Any]]] = {}
    for (origin, destination), options in sorted(pair_options.items()):
        ordered_options = sorted(
            options,
            key=lambda item: (
                float(item["distance_km"]),
                int(item["corridor_leg_count"]),
                str(item["corridor_id"]),
            ),
        )
        pair_observations = pair_subroutes[(origin, destination)]
        distance_km_values = [
            float(subroute.distance_km) for subroute in pair_observations
        ]
        distance_nm_values = [
            float(subroute.distance_nm) for subroute in pair_observations
        ]
        mean_distance_km = statistics.fmean(distance_km_values)
        mean_distance_nm = statistics.fmean(distance_nm_values)

        # The scenario distance is an arithmetic mean over complete voyage
        # observations. A corridor repeated by several voyages therefore has
        # the same weight as that number of voyages, not one weight per unique
        # port sequence. This is intentionally separate from the transport-work
        # weighting used for the pair intensity below.
        stats: dict[str, Any] = {
            "distance_km": round(mean_distance_km, 3),
            "distance_nm": round(mean_distance_nm, 3),
            "distance_source": SCENARIO_DISTANCE_SOURCE,
            "scenario_distance_km": round(mean_distance_km, 3),
            "scenario_distance_nm": round(mean_distance_nm, 3),
            "scenario_distance_method": SCENARIO_DISTANCE_METHOD,
            "scenario_distance_scope": SCENARIO_DISTANCE_SCOPE,
            "scenario_distance_observation_count": len(pair_observations),
            "scenario_distance_corridor_count": len(ordered_options),
            "scenario_distance_min_km": round(min(distance_km_values), 3),
            "scenario_distance_max_km": round(max(distance_km_values), 3),
            "scenario_distance_stddev_km": round(
                statistics.pstdev(distance_km_values), 3
            )
            if len(distance_km_values) > 1
            else 0.0,
            "route_observation_mode": ROUTE_OBSERVATION_MODE,
            "corridor_count": len(ordered_options),
            "candidate_voyage_count": len(pair_observations),
            "candidate_voyage_observation_count": len(pair_observations),
            "direct_voyage_count": sum(
                1 for subroute in pair_observations if subroute.is_direct
            ),
            "multistop_voyage_count": sum(
                1 for subroute in pair_observations if not subroute.is_direct
            ),
        }
        option_summary_fields = (
            "corridor_port_path",
            "distance_km",
            "calculation_status",
            "candidate_voyage_ids",
            "candidate_voyage_count",
            "distance_source_counts",
            "intensity_source_counts",
            "fuel_g_per_tnm_weighted_mean",
            "intensity_weighting",
            "observed_transport_work_tnm",
            "observed_fuel_kg",
        )
        stats["corridor_options"] = [
            {
                key: option[key]
                for key in option_summary_fields
                if key in option
            }
            for option in ordered_options
        ]

        aggregate_integer_fields = (
            "segment_count",
            "matched_segment_count",
            "resolved_segment_count",
            "haversine_fallback_segment_count",
            "matched_voyage_count",
            "resolved_voyage_count",
            "imo_intensity_voyage_count",
            "class_fallback_voyage_count",
            "type_fallback_voyage_count",
            "fallback_voyage_count",
            "unresolved_intensity_voyage_count",
        )
        for field in aggregate_integer_fields:
            stats[field] = sum(int(item.get(field) or 0) for item in ordered_options)
        all_source_counts: Counter[str] = Counter()
        all_distance_source_counts: Counter[str] = Counter()
        for item in ordered_options:
            all_source_counts.update(item.get("intensity_source_counts") or {})
            all_distance_source_counts.update(
                item.get("distance_source_counts") or {}
            )
        stats["intensity_source_counts"] = dict(sorted(all_source_counts.items()))
        stats["distance_source_counts"] = dict(
            sorted(all_distance_source_counts.items())
        )
        stats["scenario_distance_source_counts"] = dict(
            sorted(all_distance_source_counts.items())
        )
        stats["candidate_observed_transport_work_tnm"] = round(
            sum(float(item.get("observed_transport_work_tnm") or 0.0) for item in ordered_options),
            3,
        )
        stats["candidate_observed_fuel_kg"] = round(
            sum(float(item.get("observed_fuel_kg") or 0.0) for item in ordered_options),
            6,
        )
        stats["observed_transport_work_tnm"] = stats[
            "candidate_observed_transport_work_tnm"
        ]
        stats["observed_fuel_kg"] = stats["candidate_observed_fuel_kg"]
        all_segments = [
            segment for subroute in pair_observations for segment in subroute.segments
        ]
        imo_matched_subroutes = [
            subroute
            for subroute in pair_observations
            if str(subroute.intensity_provenance.get("matched_imo") or "").strip()
        ]
        resolved_subroutes = [
            subroute
            for subroute in pair_observations
            if (_float_or_none(
                subroute.intensity_provenance.get("intensity_g_per_tnm")
            ) or 0.0)
            > 0.0
        ]
        matched_imos = {
            subroute.imo
            for subroute in imo_matched_subroutes
            if subroute.imo
        }
        stats["voyage_count"] = len(
            {subroute.voyage_id for subroute in pair_observations}
        )
        stats["unique_imo_count"] = len(
            {subroute.imo for subroute in pair_observations if subroute.imo}
        )
        stats["matched_imo_count"] = len(matched_imos)
        matched_transport_work_tnm = sum(
            segment.tonne_nm
            for subroute in imo_matched_subroutes
            for segment in subroute.segments
        )
        total_transport_work_tnm = sum(segment.tonne_nm for segment in all_segments)
        resolved_transport_work_tnm = sum(
            segment.tonne_nm
            for subroute in resolved_subroutes
            for segment in subroute.segments
        )
        stats["cargo_weight_t_total"] = round(
            sum(segment.cargo_weight_t for segment in all_segments), 3
        )
        stats["cargo_weight_t_matched_total"] = round(
            sum(
                segment.cargo_weight_t
                for subroute in imo_matched_subroutes
                for segment in subroute.segments
            ),
            3,
        )
        stats["tonne_nm_total"] = round(total_transport_work_tnm, 3)
        stats["tonne_nm_matched_total"] = round(matched_transport_work_tnm, 3)
        stats["tonne_nm_resolved_total"] = round(resolved_transport_work_tnm, 3)
        stats["match_rate_segments"] = (
            round(
                sum(
                    1
                    for subroute in imo_matched_subroutes
                    for _ in subroute.segments
                )
                / len(all_segments),
                6,
            )
            if all_segments
            else None
        )
        stats["match_rate_tonne_nm"] = (
            round(matched_transport_work_tnm / total_transport_work_tnm, 6)
            if total_transport_work_tnm > 0.0
            else None
        )
        stats["intensity_resolution_rate_voyages"] = round(
            len(resolved_subroutes) / len(pair_observations), 6
        )
        stats["intensity_resolution_rate"] = stats[
            "intensity_resolution_rate_voyages"
        ]
        pair_intensity = _pair_representative_intensity(
            pair_observations,
            audit_voyage_ids=audit_voyage_ids,
        )
        stats.update(pair_intensity)
        representative = _float_or_none(
            pair_intensity.get("pair_intensity_g_per_tnm")
        )
        if representative is not None and representative > 0.0:
            stats["fuel_g_per_tnm_weighted_mean"] = representative
            stats["intensity_weighting"] = pair_intensity.get(
                "pair_intensity_method"
            )
            stats["fuel_g_per_tnm_source"] = pair_intensity.get(
                "pair_intensity_source"
            )
        resolved_count = int(stats.get("resolved_voyage_count") or 0)
        if resolved_count == len(pair_observations):
            stats["calculation_status"] = (
                "complete_zero_transport_work_intensity_mean"
                if total_transport_work_tnm <= 0.0
                else "complete"
            )
        elif resolved_count:
            stats["calculation_status"] = "partial_intensity_coverage"
        else:
            stats["calculation_status"] = "unusable_missing_intensity"
        out.setdefault(origin, {})[destination] = stats
    return out


def _pair_representative_intensity(
    subroutes: list[VoyageSubroute],
    *,
    audit_voyage_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Return the transport-work-weighted mean for every eligible OD voyage."""
    resolved: list[tuple[float, float, VoyageSubroute]] = []
    for subroute in subroutes:
        intensity = _float_or_none(
            subroute.intensity_provenance.get("intensity_g_per_tnm")
        )
        if intensity is None or intensity <= 0.0:
            continue
        resolved.append((float(intensity), subroute.transport_work_tnm, subroute))

    positive_weight = [item for item in resolved if item[1] > 0.0]
    zero_weight = [item for item in resolved if item[1] <= 0.0]
    effective_source_counts: Counter[str] = Counter()
    representative: float | None = None
    method = PAIR_INTENSITY_METHOD
    source = PAIR_INTENSITY_SOURCE
    total_weight = sum(item[1] for item in positive_weight)
    values = [item[0] for item in resolved]

    if positive_weight:
        weighted_mean = sum(
            intensity * weight for intensity, weight, _ in positive_weight
        ) / total_weight
        representative = weighted_mean
        effective_source_counts.update(
            str(subroute.intensity_provenance.get("intensity_source") or "unavailable")
            for _, _, subroute in positive_weight
        )
    elif resolved:
        representative = statistics.fmean(values)
        weighted_mean = None
        method = "unweighted_mean_resolved_same_od_voyages_zero_transport_work"
        source = PAIR_INTENSITY_ZERO_WORK_SOURCE
        effective_source_counts.update(
            str(item[2].intensity_provenance.get("intensity_source") or "unavailable")
            for item in resolved
        )
    else:
        weighted_mean = None
        method = "unavailable_no_resolved_same_od_voyage_intensity"
        source = PAIR_INTENSITY_UNAVAILABLE_SOURCE

    audit_ids = audit_voyage_ids or _EMPTY_AUDIT_IDS
    if audit_ids and any(item.voyage_id in audit_ids for item in subroutes):
        origin = subroutes[0].corridor_port_path[0] if subroutes else "unavailable"
        destination = subroutes[0].corridor_port_path[-1] if subroutes else "unavailable"
        _log.debug(
            "maritime_pair_intensity origin=%r destination=%r "
            "candidate_voyage_count=%d resolved_voyage_count=%d "
            "positive_weight_voyage_count=%d total_transport_work_tnm=%.6f "
            "representative_intensity_g_per_tnm=%s "
            "transport_work_weighted_mean_g_per_tnm=%s "
            "unweighted_median_g_per_tnm=%s "
            "effective_source_counts=%s "
            "method=%s source=%s",
            origin,
            destination,
            len(subroutes),
            len(resolved),
            len(positive_weight),
            total_weight,
            representative,
            weighted_mean,
            statistics.median(values) if values else None,
            dict(sorted(effective_source_counts.items())),
            method,
            source,
        )

    return {
        "pair_intensity_g_per_tnm": (
            round(representative, 6) if representative is not None else None
        ),
        "pair_intensity_method": method,
        "pair_intensity_scope": PAIR_INTENSITY_SCOPE,
        "pair_intensity_weight": PAIR_INTENSITY_WEIGHT,
        "pair_intensity_source": source,
        "pair_intensity_candidate_voyage_count": len(subroutes),
        "pair_intensity_resolved_voyage_count": len(resolved),
        "pair_intensity_positive_weight_voyage_count": len(positive_weight),
        "pair_intensity_zero_weight_voyage_count": len(zero_weight),
        "pair_intensity_unresolved_voyage_count": len(subroutes) - len(resolved),
        "pair_intensity_transport_work_tnm": round(total_weight, 3),
        "pair_intensity_source_counts": dict(
            sorted(effective_source_counts.items())
        ),
        "pair_intensity_effective_voyage_count": (
            len(positive_weight) if positive_weight else len(resolved)
        ),
        "pair_intensity_effective_source_counts": dict(
            sorted(effective_source_counts.items())
        ),
        "pair_intensity_unweighted_median_g_per_tnm": (
            round(statistics.median(values), 6) if values else None
        ),
        "pair_intensity_transport_work_weighted_mean_g_per_tnm": (
            round(weighted_mean, 6) if weighted_mean is not None else None
        ),
    }


def _aggregate_corridor_option(
    path: tuple[str, ...],
    subroutes: list[VoyageSubroute],
) -> dict[str, Any]:
    resolved = [item for item in subroutes if item.fuel_consumption_g is not None]
    imo_matched = [
        item
        for item in subroutes
        if item.intensity_provenance.get("intensity_source_level") == "imo"
        and item.fuel_consumption_g is not None
    ]
    fallbacks = [
        item
        for item in resolved
        if bool(item.intensity_provenance.get("is_fallback"))
    ]
    observed_transport_work_tnm = sum(
        item.transport_work_tnm for item in subroutes
    )
    resolved_transport_work_tnm = sum(
        item.transport_work_tnm for item in resolved
    )
    matched_transport_work_tnm = sum(
        item.transport_work_tnm for item in imo_matched
    )
    observed_fuel_g = sum(
        float(item.fuel_consumption_g or 0.0) for item in resolved
    )
    fuel_values = [
        float(item.intensity_provenance["intensity_g_per_tnm"])
        for item in resolved
        if _float_or_none(item.intensity_provenance.get("intensity_g_per_tnm"))
        is not None
    ]
    weighted_mean = (
        observed_fuel_g / resolved_transport_work_tnm
        if resolved_transport_work_tnm > 0
        else None
    )
    intensity_weighting = "observed_transport_work_tnm"
    if weighted_mean is None and fuel_values:
        weighted_mean = sum(fuel_values) / len(fuel_values)
        intensity_weighting = (
            "arithmetic_mean_resolved_voyages_zero_transport_work"
        )
    all_segments = [segment for item in subroutes for segment in item.segments]
    matched_segments = [segment for item in imo_matched for segment in item.segments]
    resolved_segments = [segment for item in resolved for segment in item.segments]
    source_counts = Counter(
        str(item.intensity_provenance.get("intensity_source") or "unavailable")
        for item in subroutes
    )
    distance_source_counts = Counter(
        segment.distance_source for segment in all_segments
    )
    class_fallbacks = [
        item
        for item in fallbacks
        if item.intensity_provenance.get("intensity_source_level") == "vessel_class"
    ]
    type_fallbacks = [
        item
        for item in fallbacks
        if item.intensity_provenance.get("intensity_source_level") == "ship_type"
    ]
    corridor_id = "corridor:" + "->".join(_slugify_port_label(item) for item in path)
    return {
        "corridor_id": corridor_id,
        "corridor_port_path": list(path),
        "corridor_leg_count": len(path) - 1,
        "corridor_sublegs": _aggregate_corridor_sublegs(subroutes),
        "candidate_voyage_ids": sorted({item.voyage_id for item in subroutes}),
        "calculation_status": (
            (
                "complete_zero_transport_work_intensity_mean"
                if resolved_transport_work_tnm <= 0.0
                else "complete"
            )
            if len(resolved) == len(subroutes)
            else (
                "partial_intensity_coverage"
                if resolved
                else "unusable_missing_intensity"
            )
        ),
        "distance_km": round(subroutes[0].distance_km, 3),
        "distance_nm": round(subroutes[0].distance_nm, 3),
        "fuel_g_per_tnm_weighted_mean": (
            round(weighted_mean, 6) if weighted_mean is not None else None
        ),
        "intensity_weighting": intensity_weighting,
        "fuel_g_per_tnm_mean": (
            round(sum(fuel_values) / len(fuel_values), 6) if fuel_values else None
        ),
        "fuel_g_per_tnm_median": (
            round(statistics.median(fuel_values), 6) if fuel_values else None
        ),
        "segment_count": len(all_segments),
        "matched_segment_count": len(matched_segments),
        "resolved_segment_count": len(resolved_segments),
        "haversine_fallback_segment_count": distance_source_counts.get(
            "haversine_fallback", 0
        ),
        "distance_source_counts": dict(sorted(distance_source_counts.items())),
        "voyage_count": len({item.voyage_id for item in subroutes}),
        "matched_voyage_count": len({item.voyage_id for item in imo_matched}),
        "candidate_voyage_count": len(subroutes),
        "candidate_voyage_observation_count": len(subroutes),
        "direct_voyage_count": sum(1 for item in subroutes if item.is_direct),
        "multistop_voyage_count": sum(1 for item in subroutes if not item.is_direct),
        "resolved_voyage_count": len(resolved),
        "imo_intensity_voyage_count": len(imo_matched),
        "class_fallback_voyage_count": len(class_fallbacks),
        "type_fallback_voyage_count": len(type_fallbacks),
        "fallback_voyage_count": len(fallbacks),
        "unresolved_intensity_voyage_count": len(subroutes) - len(resolved),
        "intensity_source_counts": dict(sorted(source_counts.items())),
        "unique_imo_count": len({item.imo for item in subroutes if item.imo}),
        "matched_imo_count": len({item.imo for item in imo_matched if item.imo}),
        "cargo_weight_t_total": round(
            sum(segment.cargo_weight_t for segment in all_segments), 3
        ),
        "cargo_weight_t_matched_total": round(
            sum(segment.cargo_weight_t for segment in matched_segments), 3
        ),
        "tonne_nm_total": round(observed_transport_work_tnm, 3),
        "tonne_nm_matched_total": round(matched_transport_work_tnm, 3),
        "tonne_nm_resolved_total": round(resolved_transport_work_tnm, 3),
        "observed_transport_work_tnm": round(observed_transport_work_tnm, 3),
        "observed_fuel_kg": round(observed_fuel_g / 1000.0, 6),
        "match_rate_segments": (
            round(len(matched_segments) / len(all_segments), 6)
            if all_segments
            else None
        ),
        "match_rate_tonne_nm": (
            round(matched_transport_work_tnm / observed_transport_work_tnm, 6)
            if observed_transport_work_tnm > 0
            else None
        ),
        "intensity_resolution_rate_voyages": (
            round(len(resolved) / len(subroutes), 6) if subroutes else None
        ),
        "intensity_resolution_rate": (
            round(len(resolved) / len(subroutes), 6) if subroutes else None
        ),
    }


def _aggregate_corridor_sublegs(
    subroutes: list[VoyageSubroute],
) -> list[dict[str, Any]]:
    leg_count = len(subroutes[0].segments)
    out: list[dict[str, Any]] = []
    for index in range(leg_count):
        subset = [item.segments[index] for item in subroutes]
        resolved = [item for item in subset if item.fuel_consumption_g is not None]
        resolved_transport_work_tnm = sum(item.tonne_nm for item in resolved)
        resolved_fuel_g = sum(
            float(item.fuel_consumption_g or 0.0) for item in resolved
        )
        intensity_g_per_tnm = (
            resolved_fuel_g / resolved_transport_work_tnm
            if resolved_transport_work_tnm > 0
            else None
        )
        intensity_weighting = "observed_transport_work_tnm"
        if intensity_g_per_tnm is None and resolved:
            resolved_intensities = [
                float(item.fuel_g_per_tnm)
                for item in resolved
                if item.fuel_g_per_tnm is not None and item.fuel_g_per_tnm > 0.0
            ]
            if resolved_intensities:
                intensity_g_per_tnm = sum(resolved_intensities) / len(
                    resolved_intensities
                )
                intensity_weighting = (
                    "arithmetic_mean_resolved_voyages_zero_transport_work"
                )
        source_counts = Counter(item.intensity_source for item in subset)
        distance_source_counts = Counter(item.distance_source for item in subset)
        out.append(
            {
                "corridor_leg_sequence": index,
                "origin_port": subset[0].from_port_name,
                "destination_port": subset[0].to_port_name,
                "distance_km": round(subset[0].distance_km, 3),
                "distance_nm": round(subset[0].distance_nm, 3),
                "distance_source": subset[0].distance_source,
                "distance_source_counts": dict(
                    sorted(distance_source_counts.items())
                ),
                "observed_segment_count": len(subset),
                "resolved_segment_count": len(resolved),
                "average_cargo_onboard_t": round(
                    sum(item.cargo_weight_t for item in subset) / len(subset), 6
                ),
                "observed_transport_work_tnm": round(
                    sum(item.tonne_nm for item in subset), 3
                ),
                "resolved_transport_work_tnm": round(
                    resolved_transport_work_tnm, 3
                ),
                "observed_fuel_kg": round(resolved_fuel_g / 1000.0, 6),
                "intensity_g_per_tnm": (
                    round(intensity_g_per_tnm, 6)
                    if intensity_g_per_tnm is not None
                    else None
                ),
                "fuel_g_per_tnm": (
                    round(intensity_g_per_tnm, 6)
                    if intensity_g_per_tnm is not None
                    else None
                ),
                "intensity_weighting": intensity_weighting,
                "intensity_source_counts": dict(sorted(source_counts.items())),
            }
        )
    return out


def _filter_directional_stats_to_matched(
    directional_stats: dict[str, dict[str, dict[str, Any]]]
) -> dict[str, dict[str, dict[str, Any]]]:
    filtered: dict[str, dict[str, dict[str, Any]]] = {}
    for origin, destinations in directional_stats.items():
        kept = {
            destination: stats
            for destination, stats in destinations.items()
            if _int_or_zero(stats.get("resolved_voyage_count")) > 0
            and _float_or_none(stats.get("fuel_g_per_tnm_weighted_mean")) is not None
        }
        if kept:
            filtered[origin] = kept
    return filtered


def _prune_matrix_to_possible_pairs(
    payload: dict[str, Any],
    directional_stats: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    matrix = payload.get("matrix") if isinstance(payload.get("matrix"), dict) else {}
    ports = payload.get("ports") if isinstance(payload.get("ports"), list) else []

    undirected_pairs = {
        tuple(sorted((origin, destination)))
        for origin, destinations in directional_stats.items()
        for destination in destinations
        if origin and destination and origin != destination
    }
    participating_ports = {name for pair in undirected_pairs for name in pair}

    ordered_port_names: list[str] = []
    filtered_ports: list[dict[str, Any]] = []
    for port in ports:
        if not isinstance(port, dict):
            continue
        name = str(port.get("name") or "").strip()
        if not name or name not in participating_ports:
            continue
        ordered_port_names.append(name)
        filtered_ports.append(port)

    if not ordered_port_names:
        payload["matrix"] = {}
        payload["ports"] = []
        return {
            "participating_ports": 0,
            "possible_pairs_undirected": 0,
            "possible_pairs_directed": 0,
            "matrix_rows": 0,
        }

    filtered_matrix: dict[str, dict[str, float]] = {}
    for origin in ordered_port_names:
        row_out: dict[str, float] = {}
        for destination in ordered_port_names:
            if origin == destination:
                continue
            if tuple(sorted((origin, destination))) not in undirected_pairs:
                continue
            distance = _matrix_distance_km(matrix, origin, destination)
            if distance is None or distance <= 0:
                continue
            row_out[destination] = distance
        filtered_matrix[origin] = row_out

    payload["ports"] = filtered_ports
    payload["matrix"] = filtered_matrix
    return {
        "participating_ports": len(ordered_port_names),
        "possible_pairs_undirected": len(undirected_pairs),
        "possible_pairs_directed": sum(len(row) for row in filtered_matrix.values()),
        "matrix_rows": len(filtered_matrix),
        "pair_policy": "observed_same_voyage_corridor_in_either_direction",
    }


def _resolve_matrix_port_name(row: dict[str, str], port_lookup: dict[str, str]) -> str | None:
    port_name = _text_or_none(row.get("port_name"))
    if port_name:
        direct = port_lookup.get(_norm(port_name))
        if direct:
            return direct
        slug = _norm(_slugify_port_label(port_name))
        direct = port_lookup.get(slug)
        if direct:
            return direct

    atracacao_name = _text_or_none(row.get("atracacao_port_name"))
    if atracacao_name:
        direct = port_lookup.get(_norm(atracacao_name))
        if direct:
            return direct
        slug = _norm(_slugify_port_label(atracacao_name))
        direct = port_lookup.get(slug)
        if direct:
            return direct

    for code_field in ("port_code", "port_key"):
        code = _text_or_none(row.get(code_field))
        if not code:
            continue
        direct = port_lookup.get(_norm(f"porto-{code.lower()}"))
        if direct:
            return direct

    return None


def _matrix_distance_km(matrix: dict[str, Any], from_port: str, to_port: str) -> float | None:
    row = matrix.get(from_port)
    if isinstance(row, dict):
        direct = _float_or_none(row.get(to_port))
        if direct is not None:
            return direct

    row = matrix.get(to_port)
    if isinstance(row, dict):
        reverse = _float_or_none(row.get(from_port))
        if reverse is not None:
            return reverse
    return None


def _slugify_port_label(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    cleaned = []
    for ch in text:
        cleaned.append(ch if ch.isalnum() else "-")
    parts = [part for part in "".join(cleaned).split("-") if part]
    return "-".join(parts)


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _text_or_none(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _float_or_zero(value: Any) -> float:
    parsed = _float_or_none(value)
    return 0.0 if parsed is None else parsed


def _int_or_zero(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0
