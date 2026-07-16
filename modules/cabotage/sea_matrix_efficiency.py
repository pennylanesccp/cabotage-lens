from __future__ import annotations

import csv
import json
import math
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
PARSER_VERSION = "sea_matrix_efficiency_v2"
_KM_PER_NAUTICAL_MILE = 1.852
DEPLOYMENT_REQUIRED_ROUTE = ("Porto de Santos", "Porto de Manaus")
ROUTE_OBSERVATION_MODE = "observed_voyage_corridors"
CORRIDOR_SELECTION_CRITERION = "direct_first_then_shortest_distance_km"
FALLBACK_TRIM_FRACTION_EACH_TAIL = 0.01
FALLBACK_OUTLIER_RULE = "symmetric_trim_1pct_each_tail_floor_count"


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
    )
    directional_stats = _aggregate_subroute_stats(subroutes)
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
        "generated_at": datetime.now(UTC).isoformat(),
        "source": (
            "ANTAQ observed same-voyage corridors + EU MRV latest IMO intensity with "
            "robust vessel-class and ship-type fallbacks"
        ),
        "route_observation_mode": ROUTE_OBSERVATION_MODE,
        "corridor_selection_criterion": CORRIDOR_SELECTION_CRITERION,
        "weighting": "tonne_nm",
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
            "eu_mrv_vessel_class_trimmed_mean_1pct_or_median",
            "eu_mrv_ship_type_trimmed_mean_1pct_or_median",
            "eu_mrv_ship_type_robust_default_container_ship",
            "unavailable",
        ],
        "fallback_outlier_policy": {
            "exact_imo_values": "preserved_without_trimming",
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
        required_positive_fields = (
            "segment_count",
            "resolved_segment_count",
            "resolved_voyage_count",
            "intensity_resolution_rate",
        )
        coverage_label = "resolved-intensity"
    else:
        required_positive_fields = (
            "segment_count",
            "matched_segment_count",
            "unique_imo_count",
            "matched_imo_count",
            "match_rate_segments",
            "match_rate_tonne_nm",
        )
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
        "fuel_g_per_tnm_weighted_mean": stats.get("fuel_g_per_tnm_weighted_mean"),
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

    return {
        "by_imo": by_imo,
        "ship_metadata": ship_metadata,
        "ship_type_fallbacks": ship_type_fallbacks,
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
        canonical_port = _resolve_matrix_port_name(row, port_lookup)
        item["_resolved_matrix_port_name"] = canonical_port
        if (
            collapsed
            and canonical_port is not None
            and collapsed[-1].get("_resolved_matrix_port_name") == canonical_port
        ):
            for field in ("net_weight_t", "net_teu"):
                collapsed[-1][field] = _float_or_zero(collapsed[-1].get(field)) + (
                    _float_or_zero(item.get(field))
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
            "one_observation_per_voyage_and_ordered_port_pair_using_"
            "direct_first_then_shortest_distance_km"
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
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str, tuple[str, ...]], list[VoyageSubroute]] = {}
    for subroute in subroutes:
        key = (
            subroute.corridor_port_path[0],
            subroute.corridor_port_path[-1],
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
                0 if int(item["corridor_leg_count"]) == 1 else 1,
                float(item["distance_km"]),
                int(item["corridor_leg_count"]),
                str(item["corridor_id"]),
            ),
        )
        usable_options = [
            item
            for item in ordered_options
            if _float_or_none(item.get("fuel_g_per_tnm_weighted_mean")) is not None
            and float(item["fuel_g_per_tnm_weighted_mean"]) > 0.0
        ]
        direct_options = [
            item for item in usable_options if int(item["corridor_leg_count"]) == 1
        ]
        selectable = direct_options or usable_options or ordered_options
        selected = min(
            selectable,
            key=lambda item: (
                float(item["distance_km"]),
                int(item["corridor_leg_count"]),
                str(item["corridor_id"]),
            ),
        )
        # Keep the selected aggregate at pair level without serializing its leg
        # audit twice. Runtime-facing leg data is copied explicitly to
        # ``selected_corridor_sublegs``; option summaries retain every observed
        # path and the voyage IDs that contributed to it.
        stats = {
            key: value
            for key, value in selected.items()
            if key not in {"corridor_sublegs", "candidate_voyage_ids"}
        }
        stats["route_observation_mode"] = ROUTE_OBSERVATION_MODE
        stats["selection_criterion"] = CORRIDOR_SELECTION_CRITERION
        stats["selected_corridor_id"] = selected["corridor_id"]
        stats["corridor_port_path"] = list(selected["corridor_port_path"])
        stats["corridor_leg_count"] = int(selected["corridor_leg_count"])
        stats["selected_corridor_sublegs"] = list(selected["corridor_sublegs"])
        stats["selected_corridor_distance_source_counts"] = dict(
            selected.get("distance_source_counts") or {}
        )
        stats["corridor_count"] = len(ordered_options)
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
        stats["selected_corridor_candidate_voyage_count"] = int(
            selected["candidate_voyage_count"]
        )
        stats["selected_corridor_candidate_voyage_ids"] = list(
            selected.get("candidate_voyage_ids") or []
        )

        count_fields = (
            "candidate_voyage_count",
            "candidate_voyage_observation_count",
            "direct_voyage_count",
            "multistop_voyage_count",
            "resolved_voyage_count",
            "imo_intensity_voyage_count",
            "class_fallback_voyage_count",
            "type_fallback_voyage_count",
            "fallback_voyage_count",
            "unresolved_intensity_voyage_count",
            "haversine_fallback_segment_count",
        )
        for field in count_fields:
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
        stats["candidate_observed_transport_work_tnm"] = round(
            sum(float(item.get("observed_transport_work_tnm") or 0.0) for item in ordered_options),
            3,
        )
        stats["candidate_observed_fuel_kg"] = round(
            sum(float(item.get("observed_fuel_kg") or 0.0) for item in ordered_options),
            6,
        )
        out.setdefault(origin, {})[destination] = stats
    return out


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
