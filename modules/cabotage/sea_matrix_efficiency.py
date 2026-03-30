from __future__ import annotations

import csv
import json
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from modules.infra.data_assets import resolve_data_asset_path
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

DEFAULT_SEA_MATRIX_PATH = Path("data/sea_matrix.json")
DEFAULT_VOYAGES_CSV_PATH = Path("data/processed/cabotage_data/tabular/antaq_voyages.csv")
DEFAULT_STOPS_CSV_PATH = Path("data/processed/cabotage_data/tabular/antaq_voyage_stops.csv")
DEFAULT_MRV_JSON_PATH = Path("data/processed/cabotage_data/mrv_average_efficiency_by_imo.json")
PARSER_VERSION = "sea_matrix_efficiency_v1"
_KM_PER_NAUTICAL_MILE = 1.852


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
    tonne_nm: float
    fuel_g_per_tnm: float | None


def enrich_sea_matrix_with_efficiency(
    *,
    sea_matrix_path: Path | str = DEFAULT_SEA_MATRIX_PATH,
    voyages_csv_path: Path | str = DEFAULT_VOYAGES_CSV_PATH,
    stops_csv_path: Path | str = DEFAULT_STOPS_CSV_PATH,
    mrv_json_path: Path | str = DEFAULT_MRV_JSON_PATH,
    possible_pairs_only: bool = True,
    matched_pairs_only: bool = True,
    prefer_local_voyage_inputs: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sea_matrix_resolved = resolve_data_asset_path(sea_matrix_path)
    mrv_resolved = resolve_data_asset_path(mrv_json_path)
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
    imo_efficiency = _load_latest_imo_efficiency(mrv_resolved)

    voyage_imo = {
        str(row.get("voyage_id") or "").strip(): str(row.get("imo") or "").strip()
        for row in voyages
        if str(row.get("voyage_id") or "").strip()
    }
    port_lookup = _build_port_lookup(payload)
    matrix = payload.get("matrix") or {}

    segments, segment_meta = _build_segments(
        stops=stops,
        voyage_imo=voyage_imo,
        imo_efficiency=imo_efficiency,
        port_lookup=port_lookup,
        matrix=matrix,
    )
    directional_stats = _aggregate_segment_stats(segments)
    if matched_pairs_only:
        directional_stats = _filter_directional_stats_to_matched(directional_stats)
    possible_pairs_meta = None
    if possible_pairs_only:
        possible_pairs_meta = _prune_matrix_to_possible_pairs(
            payload,
            segments,
            matched_pairs_only=matched_pairs_only,
        )

    payload["voyage_fuel_g_per_tnm_directional"] = directional_stats
    payload["voyage_fuel_g_per_tnm_directional_meta"] = {
        "parser_version": PARSER_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "ANTAQ voyage stop pairs + latest positive MRV fuel per transport work by IMO",
        "weighting": "tonne_nm",
        "segment_cargo_rule": "cumulative net cargo after each stop, applied to the following leg",
        "possible_pairs_only": bool(possible_pairs_only),
        "matched_pairs_only": bool(matched_pairs_only),
        "inputs": {
            "sea_matrix_path": str(Path(sea_matrix_resolved)),
            "voyages_csv_path": str(Path(voyages_resolved)),
            "stops_csv_path": str(Path(stops_resolved)),
            "mrv_json_path": str(Path(mrv_resolved)),
        },
        "segment_summary": segment_meta,
        "possible_pairs_summary": possible_pairs_meta,
    }

    summary = {
        "directional_pairs": sum(len(v) for v in directional_stats.values()),
        "segments_contributing": sum(
            stats.get("matched_segment_count", 0)
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
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _load_csv_rows(path: Path | str) -> list[dict[str, str]]:
    resolved = Path(path)
    with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_latest_imo_efficiency(path: Path | str) -> dict[str, float]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    ships = payload.get("ships") if isinstance(payload, dict) else None
    if not isinstance(ships, list):
        raise ValueError(f"Invalid MRV efficiency payload: {path}")

    latest: dict[str, float] = {}
    for ship in ships:
        if not isinstance(ship, dict):
            continue
        imo = str(ship.get("imo") or "").strip()
        records = ship.get("records") if isinstance(ship.get("records"), list) else []
        selected = None
        for record in records:
            if not isinstance(record, dict):
                continue
            value = _float_or_none(record.get("average_fuel_consumption_per_transport_work_g_per_tonne_nmile"))
            if value is None or value <= 0:
                continue
            reporting_period = _int_or_zero(record.get("reporting_period"))
            selected = (reporting_period, value)
            break
        if imo and selected is not None:
            latest[imo] = selected[1]
    return latest


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


def _build_segments(
    *,
    stops: list[dict[str, str]],
    voyage_imo: dict[str, str],
    imo_efficiency: dict[str, float],
    port_lookup: dict[str, str],
    matrix: dict[str, Any],
) -> tuple[list[VoyageSegment], dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in stops:
        voyage_id = str(row.get("voyage_id") or "").strip()
        if not voyage_id:
            continue
        grouped.setdefault(voyage_id, []).append(row)

    segments: list[VoyageSegment] = []
    total_candidate_segments = 0
    positive_cargo_segments = 0
    mapped_segments = 0
    matched_segments = 0
    skipped_unmapped_ports = 0
    skipped_missing_distance = 0
    skipped_nonpositive_cargo = 0

    for voyage_id, rows in grouped.items():
        rows.sort(key=lambda row: _int_or_zero(row.get("sequence")))
        imo = voyage_imo.get(voyage_id, "")
        fuel_g_per_tnm = imo_efficiency.get(imo)
        cumulative_weight_t = 0.0
        cumulative_teu = 0.0

        for idx in range(len(rows) - 1):
            current = rows[idx]
            nxt = rows[idx + 1]
            total_candidate_segments += 1

            cumulative_weight_t += _float_or_zero(current.get("net_weight_t"))
            cumulative_teu += _float_or_zero(current.get("net_teu"))
            cargo_weight_t = max(cumulative_weight_t, 0.0)
            cargo_teu = max(cumulative_teu, 0.0)
            if cargo_weight_t <= 0:
                skipped_nonpositive_cargo += 1
                continue
            positive_cargo_segments += 1

            from_port = _resolve_matrix_port_name(current, port_lookup)
            to_port = _resolve_matrix_port_name(nxt, port_lookup)
            if from_port is None or to_port is None:
                skipped_unmapped_ports += 1
                continue

            distance_km = _matrix_distance_km(matrix, from_port, to_port)
            if distance_km is None or distance_km <= 0:
                skipped_missing_distance += 1
                continue

            mapped_segments += 1
            distance_nm = distance_km / _KM_PER_NAUTICAL_MILE
            tonne_nm = cargo_weight_t * distance_nm
            if fuel_g_per_tnm is not None and fuel_g_per_tnm > 0:
                matched_segments += 1

            segments.append(
                VoyageSegment(
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
                    tonne_nm=tonne_nm,
                    fuel_g_per_tnm=fuel_g_per_tnm,
                )
            )

    meta = {
        "candidate_segments": total_candidate_segments,
        "positive_cargo_segments": positive_cargo_segments,
        "mapped_segments": mapped_segments,
        "matched_segments": matched_segments,
        "skipped_nonpositive_cargo_segments": skipped_nonpositive_cargo,
        "skipped_unmapped_port_segments": skipped_unmapped_ports,
        "skipped_missing_distance_segments": skipped_missing_distance,
        "imo_match_rate_on_mapped_segments": (
            round(matched_segments / mapped_segments, 6) if mapped_segments else None
        ),
    }
    return segments, meta


def _aggregate_segment_stats(segments: list[VoyageSegment]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[VoyageSegment]] = {}
    for segment in segments:
        grouped.setdefault((segment.from_port_name, segment.to_port_name), []).append(segment)

    out: dict[str, dict[str, dict[str, Any]]] = {}
    for (from_port, to_port), subset in sorted(grouped.items()):
        matched = [segment for segment in subset if isinstance(segment.fuel_g_per_tnm, (int, float))]
        fuel_values = [float(segment.fuel_g_per_tnm) for segment in matched if segment.fuel_g_per_tnm is not None]
        weighted_mean = None
        tonne_nm_matched_total = sum(segment.tonne_nm for segment in matched)
        if matched and tonne_nm_matched_total > 0:
            weighted_mean = sum(float(segment.fuel_g_per_tnm) * segment.tonne_nm for segment in matched if segment.fuel_g_per_tnm is not None) / tonne_nm_matched_total

        cargo_weight_t_total = sum(segment.cargo_weight_t for segment in subset)
        cargo_weight_t_matched_total = sum(segment.cargo_weight_t for segment in matched)
        tonne_nm_total = sum(segment.tonne_nm for segment in subset)
        distance_km = subset[0].distance_km if subset else None
        distance_nm = subset[0].distance_nm if subset else None

        stats = {
            "distance_km": round(distance_km, 3) if distance_km is not None else None,
            "distance_nm": round(distance_nm, 3) if distance_nm is not None else None,
            "fuel_g_per_tnm_weighted_mean": (round(weighted_mean, 6) if weighted_mean is not None else None),
            "fuel_g_per_tnm_mean": (round(sum(fuel_values) / len(fuel_values), 6) if fuel_values else None),
            "fuel_g_per_tnm_median": (round(statistics.median(fuel_values), 6) if fuel_values else None),
            "segment_count": len(subset),
            "matched_segment_count": len(matched),
            "voyage_count": len({segment.voyage_id for segment in subset}),
            "matched_voyage_count": len({segment.voyage_id for segment in matched}),
            "unique_imo_count": len({segment.imo for segment in subset if segment.imo}),
            "matched_imo_count": len({segment.imo for segment in matched if segment.imo}),
            "cargo_weight_t_total": round(cargo_weight_t_total, 3),
            "cargo_weight_t_matched_total": round(cargo_weight_t_matched_total, 3),
            "tonne_nm_total": round(tonne_nm_total, 3),
            "tonne_nm_matched_total": round(tonne_nm_matched_total, 3),
            "match_rate_segments": (round(len(matched) / len(subset), 6) if subset else None),
            "match_rate_tonne_nm": (
                round(tonne_nm_matched_total / tonne_nm_total, 6)
                if tonne_nm_total > 0
                else None
            ),
        }
        out.setdefault(from_port, {})[to_port] = stats

    return out


def _filter_directional_stats_to_matched(
    directional_stats: dict[str, dict[str, dict[str, Any]]]
) -> dict[str, dict[str, dict[str, Any]]]:
    filtered: dict[str, dict[str, dict[str, Any]]] = {}
    for origin, destinations in directional_stats.items():
        kept = {
            destination: stats
            for destination, stats in destinations.items()
            if _int_or_zero(stats.get("matched_segment_count")) > 0
            and _float_or_none(stats.get("fuel_g_per_tnm_weighted_mean")) is not None
        }
        if kept:
            filtered[origin] = kept
    return filtered


def _prune_matrix_to_possible_pairs(
    payload: dict[str, Any],
    segments: list[VoyageSegment],
    *,
    matched_pairs_only: bool,
) -> dict[str, Any]:
    matrix = payload.get("matrix") if isinstance(payload.get("matrix"), dict) else {}
    ports = payload.get("ports") if isinstance(payload.get("ports"), list) else []

    eligible_segments = [
        segment
        for segment in segments
        if (not matched_pairs_only) or (segment.fuel_g_per_tnm is not None and segment.fuel_g_per_tnm > 0)
    ]
    undirected_pairs = {
        tuple(sorted((segment.from_port_name, segment.to_port_name)))
        for segment in eligible_segments
        if segment.from_port_name and segment.to_port_name and segment.from_port_name != segment.to_port_name
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
        "pair_policy": (
            "observed_segment_with_mrv_match_in_either_direction"
            if matched_pairs_only
            else "observed_segment_in_either_direction"
        ),
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
