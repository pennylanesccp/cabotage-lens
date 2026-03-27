from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from modules.infra.db.core import DBConnection, table_exists
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

PARSER_VERSION = "antaq_voyage_tables_v1"
DEFAULT_VOYAGES_JSON_PATH = Path("data/processed/cabotage_data/antaq_cabotage_observed_voyages.json")
DEFAULT_OUTPUT_DIR = Path("data/processed/cabotage_data/tabular")

_CARGO_FIELDS: tuple[str, ...] = (
    "loaded_teu",
    "unloaded_teu",
    "moved_teu",
    "net_teu",
    "loaded_weight_t",
    "unloaded_weight_t",
    "moved_weight_t",
    "net_weight_t",
)
_TIME_FIELDS: tuple[str, ...] = (
    "observed_span_hours",
    "wait_for_berth_hours",
    "wait_for_operation_start_hours",
    "operation_hours",
    "wait_for_departure_hours",
    "berth_time_hours",
    "port_stay_hours",
    "source_row_count",
    "missing_call_count",
)

VOYAGE_COLUMNS: tuple[str, ...] = (
    "voyage_id",
    "imo",
    "started_at",
    "ended_at",
    "duration_hours",
    "closed_loop",
    "closed_by",
    "origin_port_code",
    "origin_port_name",
    "destination_port_code",
    "destination_port_name",
    "stop_count",
    "intermediate_stop_count",
    "call_count_total",
    "loaded_teu_total",
    "unloaded_teu_total",
    "moved_teu_total",
    "net_teu_total",
    "loaded_weight_t_total",
    "unloaded_weight_t_total",
    "moved_weight_t_total",
    "net_weight_t_total",
    "source_generated_at",
    "time_enriched_at",
    "source_years_json",
    "source_files_json",
    "filters_json",
    "segmentation_json",
    "stats_json",
    "source_file",
    "parser_version",
    "ingestion_timestamp",
)

STOP_COLUMNS: tuple[str, ...] = (
    "voyage_id",
    "sequence",
    "stop_type",
    "port_key",
    "port_code",
    "port_name",
    "atracacao_port_name",
    "municipality",
    "state",
    "first_atracacao_at",
    "last_atracacao_at",
    "call_count",
    "loaded_teu",
    "unloaded_teu",
    "moved_teu",
    "net_teu",
    "loaded_weight_t",
    "unloaded_weight_t",
    "moved_weight_t",
    "net_weight_t",
    "observed_span_hours",
    "wait_for_berth_hours",
    "wait_for_operation_start_hours",
    "operation_hours",
    "wait_for_departure_hours",
    "berth_time_hours",
    "port_stay_hours",
    "source_row_count",
    "missing_call_count",
    "source_file",
    "parser_version",
    "ingestion_timestamp",
)

STOP_CALL_COLUMNS: tuple[str, ...] = (
    "voyage_id",
    "stop_sequence",
    "call_order",
    "call_id",
    "source_file",
    "parser_version",
    "ingestion_timestamp",
)

RAW_COLUMNS: tuple[str, ...] = (
    "voyage_id",
    "imo",
    "source_generated_at",
    "time_enriched_at",
    "source_file",
    "parser_version",
    "ingestion_timestamp",
    "raw_payload",
)


@dataclass(frozen=True)
class NormalizedVoyageTables:
    voyages: list[dict[str, Any]]
    stops: list[dict[str, Any]]
    stop_calls: list[dict[str, Any]]
    raw_rows: list[dict[str, Any]]
    source_path: Path
    parser_version: str


def load_observed_voyages_payload(path: Path | str = DEFAULT_VOYAGES_JSON_PATH) -> tuple[Path, dict[str, Any]]:
    resolved = Path(path).resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Observed voyages payload must be a JSON object: {resolved}")
    return resolved, payload


def materialize_voyage_tables(
    payload: dict[str, Any],
    *,
    source_path: Path,
    ingestion_time: datetime | None = None,
    parser_version: str = PARSER_VERSION,
) -> NormalizedVoyageTables:
    generated_at = _text_or_none(payload.get("generated_at"))
    time_enriched_at = _text_or_none(payload.get("time_enriched_at"))
    source_years = payload.get("years") if isinstance(payload.get("years"), list) else []
    source_files = payload.get("source_files") if isinstance(payload.get("source_files"), list) else []
    filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
    segmentation = payload.get("segmentation") if isinstance(payload.get("segmentation"), dict) else {}
    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    voyages_payload = payload.get("voyages") if isinstance(payload.get("voyages"), list) else []
    ingestion_timestamp = (ingestion_time or datetime.now(UTC)).isoformat()
    source_file = str(source_path)

    voyages_rows: list[dict[str, Any]] = []
    stops_rows: list[dict[str, Any]] = []
    stop_call_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []

    source_years_json = _json_text(source_years)
    source_files_json = _json_text(source_files)
    filters_json = _json_text(filters)
    segmentation_json = _json_text(segmentation)
    stats_json = _json_text(stats)

    for voyage in voyages_payload:
        if not isinstance(voyage, dict):
            continue

        voyage_id = str(voyage.get("voyage_id") or "").strip()
        if not voyage_id:
            continue

        stops = voyage.get("stops") if isinstance(voyage.get("stops"), list) else []
        totals = _sum_cargo_metrics(stops)
        call_count_total = sum(_int_or_zero(stop.get("call_count")) for stop in stops if isinstance(stop, dict))

        voyages_rows.append(
            {
                "voyage_id": voyage_id,
                "imo": _text_or_none(voyage.get("imo")),
                "started_at": _text_or_none(voyage.get("started_at")),
                "ended_at": _text_or_none(voyage.get("ended_at")),
                "duration_hours": _duration_hours(voyage.get("started_at"), voyage.get("ended_at")),
                "closed_loop": bool(voyage.get("closed_loop", False)),
                "closed_by": _text_or_none(voyage.get("closed_by")),
                "origin_port_code": _text_or_none(voyage.get("origin_port_code")),
                "origin_port_name": _text_or_none(voyage.get("origin_port_name")),
                "destination_port_code": _text_or_none(voyage.get("destination_port_code")),
                "destination_port_name": _text_or_none(voyage.get("destination_port_name")),
                "stop_count": _int_or_zero(voyage.get("stop_count") or len(stops)),
                "intermediate_stop_count": _int_or_zero(voyage.get("intermediate_stop_count")),
                "call_count_total": call_count_total,
                "loaded_teu_total": totals["loaded_teu"],
                "unloaded_teu_total": totals["unloaded_teu"],
                "moved_teu_total": totals["moved_teu"],
                "net_teu_total": totals["net_teu"],
                "loaded_weight_t_total": totals["loaded_weight_t"],
                "unloaded_weight_t_total": totals["unloaded_weight_t"],
                "moved_weight_t_total": totals["moved_weight_t"],
                "net_weight_t_total": totals["net_weight_t"],
                "source_generated_at": generated_at,
                "time_enriched_at": time_enriched_at,
                "source_years_json": source_years_json,
                "source_files_json": source_files_json,
                "filters_json": filters_json,
                "segmentation_json": segmentation_json,
                "stats_json": stats_json,
                "source_file": source_file,
                "parser_version": parser_version,
                "ingestion_timestamp": ingestion_timestamp,
            }
        )

        raw_rows.append(
            {
                "voyage_id": voyage_id,
                "imo": _text_or_none(voyage.get("imo")),
                "source_generated_at": generated_at,
                "time_enriched_at": time_enriched_at,
                "source_file": source_file,
                "parser_version": parser_version,
                "ingestion_timestamp": ingestion_timestamp,
                "raw_payload": voyage,
            }
        )

        last_sequence = len(stops) - 1
        for stop in stops:
            if not isinstance(stop, dict):
                continue

            sequence = _int_or_zero(stop.get("sequence"))
            stop_type = "intermediate"
            if sequence == 0:
                stop_type = "origin"
            elif sequence == last_sequence:
                stop_type = "destination"

            cargo = stop.get("cargo") if isinstance(stop.get("cargo"), dict) else {}
            time_block = stop.get("time") if isinstance(stop.get("time"), dict) else {}

            stops_rows.append(
                {
                    "voyage_id": voyage_id,
                    "sequence": sequence,
                    "stop_type": stop_type,
                    "port_key": _text_or_none(stop.get("port_key")),
                    "port_code": _text_or_none(stop.get("port_code")),
                    "port_name": _text_or_none(stop.get("port_name")),
                    "atracacao_port_name": _text_or_none(stop.get("atracacao_port_name")),
                    "municipality": _text_or_none(stop.get("municipality")),
                    "state": _text_or_none(stop.get("state")),
                    "first_atracacao_at": _text_or_none(stop.get("first_atracacao_at")),
                    "last_atracacao_at": _text_or_none(stop.get("last_atracacao_at")),
                    "call_count": _int_or_zero(stop.get("call_count")),
                    "loaded_teu": _float_or_zero(cargo.get("loaded_teu")),
                    "unloaded_teu": _float_or_zero(cargo.get("unloaded_teu")),
                    "moved_teu": _float_or_zero(cargo.get("moved_teu")),
                    "net_teu": _float_or_zero(cargo.get("net_teu")),
                    "loaded_weight_t": _float_or_zero(cargo.get("loaded_weight_t")),
                    "unloaded_weight_t": _float_or_zero(cargo.get("unloaded_weight_t")),
                    "moved_weight_t": _float_or_zero(cargo.get("moved_weight_t")),
                    "net_weight_t": _float_or_zero(cargo.get("net_weight_t")),
                    "observed_span_hours": _float_or_none(time_block.get("observed_span_hours")),
                    "wait_for_berth_hours": _float_or_none(time_block.get("wait_for_berth_hours")),
                    "wait_for_operation_start_hours": _float_or_none(time_block.get("wait_for_operation_start_hours")),
                    "operation_hours": _float_or_none(time_block.get("operation_hours")),
                    "wait_for_departure_hours": _float_or_none(time_block.get("wait_for_departure_hours")),
                    "berth_time_hours": _float_or_none(time_block.get("berth_time_hours")),
                    "port_stay_hours": _float_or_none(time_block.get("port_stay_hours")),
                    "source_row_count": _int_or_zero(time_block.get("source_row_count")),
                    "missing_call_count": _int_or_zero(time_block.get("missing_call_count")),
                    "source_file": source_file,
                    "parser_version": parser_version,
                    "ingestion_timestamp": ingestion_timestamp,
                }
            )

            call_ids = stop.get("call_ids") if isinstance(stop.get("call_ids"), list) else []
            for call_order, call_id in enumerate(call_ids, start=1):
                stop_call_rows.append(
                    {
                        "voyage_id": voyage_id,
                        "stop_sequence": sequence,
                        "call_order": call_order,
                        "call_id": str(call_id),
                        "source_file": source_file,
                        "parser_version": parser_version,
                        "ingestion_timestamp": ingestion_timestamp,
                    }
                )

    return NormalizedVoyageTables(
        voyages=voyages_rows,
        stops=stops_rows,
        stop_calls=stop_call_rows,
        raw_rows=raw_rows,
        source_path=source_path,
        parser_version=parser_version,
    )


def write_tables_to_disk(
    tables: NormalizedVoyageTables,
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    include_raw_jsonl: bool = False,
) -> dict[str, str]:
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    voyages_path = target_dir / "antaq_voyages.csv"
    stops_path = target_dir / "antaq_voyage_stops.csv"
    stop_calls_path = target_dir / "antaq_voyage_stop_calls.csv"
    raw_path = target_dir / "antaq_voyages_raw.jsonl"

    _write_csv(voyages_path, VOYAGE_COLUMNS, tables.voyages)
    _write_csv(stops_path, STOP_COLUMNS, tables.stops)
    _write_csv(stop_calls_path, STOP_CALL_COLUMNS, tables.stop_calls)
    if include_raw_jsonl:
        _write_jsonl(raw_path, tables.raw_rows)

    outputs = {
        "voyages_csv": str(voyages_path),
        "stops_csv": str(stops_path),
        "stop_calls_csv": str(stop_calls_path),
    }
    if include_raw_jsonl:
        outputs["raw_jsonl"] = str(raw_path)
    return outputs


def upsert_tables_to_db(conn: DBConnection, tables: NormalizedVoyageTables) -> dict[str, int]:
    required_tables = (
        "antaq_voyages",
        "antaq_voyage_stops",
        "antaq_voyage_stop_calls",
        "antaq_voyages_raw",
    )
    missing = [name for name in required_tables if not table_exists(conn, name)]
    if missing:
        raise RuntimeError(
            "Missing ANTAQ voyage tables in the target database. Apply the Supabase migration first: "
            + ", ".join(missing)
        )

    voyage_rows = [
        (
            row["voyage_id"],
            row["imo"],
            row["started_at"],
            row["ended_at"],
            row["duration_hours"],
            row["closed_loop"],
            row["closed_by"],
            row["origin_port_code"],
            row["origin_port_name"],
            row["destination_port_code"],
            row["destination_port_name"],
            row["stop_count"],
            row["intermediate_stop_count"],
            row["call_count_total"],
            row["loaded_teu_total"],
            row["unloaded_teu_total"],
            row["moved_teu_total"],
            row["net_teu_total"],
            row["loaded_weight_t_total"],
            row["unloaded_weight_t_total"],
            row["moved_weight_t_total"],
            row["net_weight_t_total"],
            row["source_generated_at"],
            row["time_enriched_at"],
            row["source_years_json"],
            row["source_files_json"],
            row["filters_json"],
            row["segmentation_json"],
            row["stats_json"],
            row["source_file"],
            row["parser_version"],
            row["ingestion_timestamp"],
        )
        for row in tables.voyages
    ]
    _executemany_chunked(conn, _VOYAGES_UPSERT_SQL, voyage_rows)

    stop_rows = [
        (
            row["voyage_id"],
            row["sequence"],
            row["stop_type"],
            row["port_key"],
            row["port_code"],
            row["port_name"],
            row["atracacao_port_name"],
            row["municipality"],
            row["state"],
            row["first_atracacao_at"],
            row["last_atracacao_at"],
            row["call_count"],
            row["loaded_teu"],
            row["unloaded_teu"],
            row["moved_teu"],
            row["net_teu"],
            row["loaded_weight_t"],
            row["unloaded_weight_t"],
            row["moved_weight_t"],
            row["net_weight_t"],
            row["observed_span_hours"],
            row["wait_for_berth_hours"],
            row["wait_for_operation_start_hours"],
            row["operation_hours"],
            row["wait_for_departure_hours"],
            row["berth_time_hours"],
            row["port_stay_hours"],
            row["source_row_count"],
            row["missing_call_count"],
            row["source_file"],
            row["parser_version"],
            row["ingestion_timestamp"],
        )
        for row in tables.stops
    ]
    _executemany_chunked(conn, _STOPS_UPSERT_SQL, stop_rows)

    stop_call_rows = [
        (
            row["voyage_id"],
            row["stop_sequence"],
            row["call_order"],
            row["call_id"],
            row["source_file"],
            row["parser_version"],
            row["ingestion_timestamp"],
        )
        for row in tables.stop_calls
    ]
    _executemany_chunked(conn, _STOP_CALLS_UPSERT_SQL, stop_call_rows)

    raw_rows = [
        (
            row["voyage_id"],
            row["imo"],
            row["source_generated_at"],
            row["time_enriched_at"],
            row["source_file"],
            row["parser_version"],
            row["ingestion_timestamp"],
            _json_text(row["raw_payload"]),
        )
        for row in tables.raw_rows
    ]
    _executemany_chunked(conn, _RAW_UPSERT_SQL, raw_rows)

    return {
        "voyages_upserted": len(voyage_rows),
        "stops_upserted": len(stop_rows),
        "stop_calls_upserted": len(stop_call_rows),
        "raw_rows_upserted": len(raw_rows),
    }


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = dict(row)
            payload["raw_payload"] = row.get("raw_payload")
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _sum_cargo_metrics(stops: Iterable[dict[str, Any]]) -> dict[str, float]:
    totals = {field: 0.0 for field in _CARGO_FIELDS}
    for stop in stops:
        cargo = stop.get("cargo") if isinstance(stop.get("cargo"), dict) else {}
        for field in _CARGO_FIELDS:
            totals[field] += _float_or_zero(cargo.get(field))
    return totals


def _duration_hours(started_at: Any, ended_at: Any) -> float | None:
    started = _parse_timestamp(started_at)
    ended = _parse_timestamp(ended_at)
    if started is None or ended is None:
        return None
    return round((ended - started).total_seconds() / 3600.0, 3)


def _parse_timestamp(value: Any) -> datetime | None:
    text = _text_or_none(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _text_or_none(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _float_or_none(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _float_or_zero(value: Any) -> float:
    parsed = _float_or_none(value)
    return 0.0 if parsed is None else parsed


def _int_or_zero(value: Any) -> int:
    try:
        return 0 if value in (None, "") else int(value)
    except (TypeError, ValueError):
        return 0


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _executemany_chunked(
    conn: DBConnection,
    sql: str,
    rows: Sequence[Sequence[Any]],
    *,
    chunk_size: int = 500,
) -> None:
    if not rows:
        return
    for start in range(0, len(rows), chunk_size):
        conn.executemany(sql, rows[start : start + chunk_size])


_VOYAGES_UPSERT_SQL = """
INSERT INTO antaq_voyages (
      voyage_id
    , imo
    , started_at
    , ended_at
    , duration_hours
    , closed_loop
    , closed_by
    , origin_port_code
    , origin_port_name
    , destination_port_code
    , destination_port_name
    , stop_count
    , intermediate_stop_count
    , call_count_total
    , loaded_teu_total
    , unloaded_teu_total
    , moved_teu_total
    , net_teu_total
    , loaded_weight_t_total
    , unloaded_weight_t_total
    , moved_weight_t_total
    , net_weight_t_total
    , source_generated_at
    , time_enriched_at
    , source_years
    , source_files
    , filters
    , segmentation
    , stats
    , source_file
    , parser_version
    , ingestion_timestamp
) VALUES (
      ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , CAST(? AS jsonb)
    , CAST(? AS jsonb)
    , CAST(? AS jsonb)
    , CAST(? AS jsonb)
    , CAST(? AS jsonb)
    , ?
    , ?
    , ?
)
ON CONFLICT (voyage_id) DO UPDATE SET
      imo = EXCLUDED.imo
    , started_at = EXCLUDED.started_at
    , ended_at = EXCLUDED.ended_at
    , duration_hours = EXCLUDED.duration_hours
    , closed_loop = EXCLUDED.closed_loop
    , closed_by = EXCLUDED.closed_by
    , origin_port_code = EXCLUDED.origin_port_code
    , origin_port_name = EXCLUDED.origin_port_name
    , destination_port_code = EXCLUDED.destination_port_code
    , destination_port_name = EXCLUDED.destination_port_name
    , stop_count = EXCLUDED.stop_count
    , intermediate_stop_count = EXCLUDED.intermediate_stop_count
    , call_count_total = EXCLUDED.call_count_total
    , loaded_teu_total = EXCLUDED.loaded_teu_total
    , unloaded_teu_total = EXCLUDED.unloaded_teu_total
    , moved_teu_total = EXCLUDED.moved_teu_total
    , net_teu_total = EXCLUDED.net_teu_total
    , loaded_weight_t_total = EXCLUDED.loaded_weight_t_total
    , unloaded_weight_t_total = EXCLUDED.unloaded_weight_t_total
    , moved_weight_t_total = EXCLUDED.moved_weight_t_total
    , net_weight_t_total = EXCLUDED.net_weight_t_total
    , source_generated_at = EXCLUDED.source_generated_at
    , time_enriched_at = EXCLUDED.time_enriched_at
    , source_years = EXCLUDED.source_years
    , source_files = EXCLUDED.source_files
    , filters = EXCLUDED.filters
    , segmentation = EXCLUDED.segmentation
    , stats = EXCLUDED.stats
    , source_file = EXCLUDED.source_file
    , parser_version = EXCLUDED.parser_version
    , ingestion_timestamp = EXCLUDED.ingestion_timestamp
    , updated_timestamp = CURRENT_TIMESTAMP
"""

_STOPS_UPSERT_SQL = """
INSERT INTO antaq_voyage_stops (
      voyage_id
    , sequence
    , stop_type
    , port_key
    , port_code
    , port_name
    , atracacao_port_name
    , municipality
    , state
    , first_atracacao_at
    , last_atracacao_at
    , call_count
    , loaded_teu
    , unloaded_teu
    , moved_teu
    , net_teu
    , loaded_weight_t
    , unloaded_weight_t
    , moved_weight_t
    , net_weight_t
    , observed_span_hours
    , wait_for_berth_hours
    , wait_for_operation_start_hours
    , operation_hours
    , wait_for_departure_hours
    , berth_time_hours
    , port_stay_hours
    , source_row_count
    , missing_call_count
    , source_file
    , parser_version
    , ingestion_timestamp
) VALUES (
      ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
)
ON CONFLICT (voyage_id, sequence) DO UPDATE SET
      stop_type = EXCLUDED.stop_type
    , port_key = EXCLUDED.port_key
    , port_code = EXCLUDED.port_code
    , port_name = EXCLUDED.port_name
    , atracacao_port_name = EXCLUDED.atracacao_port_name
    , municipality = EXCLUDED.municipality
    , state = EXCLUDED.state
    , first_atracacao_at = EXCLUDED.first_atracacao_at
    , last_atracacao_at = EXCLUDED.last_atracacao_at
    , call_count = EXCLUDED.call_count
    , loaded_teu = EXCLUDED.loaded_teu
    , unloaded_teu = EXCLUDED.unloaded_teu
    , moved_teu = EXCLUDED.moved_teu
    , net_teu = EXCLUDED.net_teu
    , loaded_weight_t = EXCLUDED.loaded_weight_t
    , unloaded_weight_t = EXCLUDED.unloaded_weight_t
    , moved_weight_t = EXCLUDED.moved_weight_t
    , net_weight_t = EXCLUDED.net_weight_t
    , observed_span_hours = EXCLUDED.observed_span_hours
    , wait_for_berth_hours = EXCLUDED.wait_for_berth_hours
    , wait_for_operation_start_hours = EXCLUDED.wait_for_operation_start_hours
    , operation_hours = EXCLUDED.operation_hours
    , wait_for_departure_hours = EXCLUDED.wait_for_departure_hours
    , berth_time_hours = EXCLUDED.berth_time_hours
    , port_stay_hours = EXCLUDED.port_stay_hours
    , source_row_count = EXCLUDED.source_row_count
    , missing_call_count = EXCLUDED.missing_call_count
    , source_file = EXCLUDED.source_file
    , parser_version = EXCLUDED.parser_version
    , ingestion_timestamp = EXCLUDED.ingestion_timestamp
    , updated_timestamp = CURRENT_TIMESTAMP
"""

_STOP_CALLS_UPSERT_SQL = """
INSERT INTO antaq_voyage_stop_calls (
      voyage_id
    , stop_sequence
    , call_order
    , call_id
    , source_file
    , parser_version
    , ingestion_timestamp
) VALUES (
      ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
)
ON CONFLICT (call_id) DO UPDATE SET
      voyage_id = EXCLUDED.voyage_id
    , stop_sequence = EXCLUDED.stop_sequence
    , call_order = EXCLUDED.call_order
    , source_file = EXCLUDED.source_file
    , parser_version = EXCLUDED.parser_version
    , ingestion_timestamp = EXCLUDED.ingestion_timestamp
    , updated_timestamp = CURRENT_TIMESTAMP
"""

_RAW_UPSERT_SQL = """
INSERT INTO antaq_voyages_raw (
      voyage_id
    , imo
    , source_generated_at
    , time_enriched_at
    , source_file
    , parser_version
    , ingestion_timestamp
    , raw_payload
) VALUES (
      ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , ?
    , CAST(? AS jsonb)
)
ON CONFLICT (voyage_id) DO UPDATE SET
      imo = EXCLUDED.imo
    , source_generated_at = EXCLUDED.source_generated_at
    , time_enriched_at = EXCLUDED.time_enriched_at
    , source_file = EXCLUDED.source_file
    , parser_version = EXCLUDED.parser_version
    , ingestion_timestamp = EXCLUDED.ingestion_timestamp
    , raw_payload = EXCLUDED.raw_payload
    , updated_timestamp = CURRENT_TIMESTAMP
"""
