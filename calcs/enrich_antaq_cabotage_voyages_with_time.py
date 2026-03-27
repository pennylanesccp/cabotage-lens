#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "cabotage_data"
DEFAULT_INPUT_JSON = (
    REPO_ROOT / "data" / "processed" / "cabotage_data" / "antaq_cabotage_observed_voyages.json"
)


def _parse_decimal(value: str | None) -> float:
    raw = (value or "").strip()
    if not raw:
        return 0.0

    normalized = raw.replace(" ", "")
    normalized = "".join(ch for ch in normalized if ch in "0123456789,.-+")
    normalized = normalized.replace(",", ".")
    if not normalized:
        return 0.0

    try:
        return float(normalized)
    except ValueError:
        return 0.0


def _parse_iso_datetime(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    return datetime.fromisoformat(raw)


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def _empty_time_block() -> dict[str, Any]:
    return {
        "observed_span_hours": None,
        "wait_for_berth_hours": 0.0,
        "wait_for_operation_start_hours": 0.0,
        "operation_hours": 0.0,
        "wait_for_departure_hours": 0.0,
        "berth_time_hours": 0.0,
        "port_stay_hours": 0.0,
        "source_row_count": 0,
        "missing_call_count": 0,
    }


def _load_time_rows(years: list[str]) -> tuple[dict[str, dict[str, float]], int]:
    by_call_id: dict[str, dict[str, float]] = {}
    row_count = 0

    for year in years:
        path = RAW_DIR / f"{year}TemposAtracacao.txt"
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                row_count += 1
                call_id = (row.get("IDAtracacao") or "").strip()
                if not call_id:
                    continue

                by_call_id[call_id] = {
                    "wait_for_berth_hours": _parse_decimal(row.get("TEsperaAtracacao")),
                    "wait_for_operation_start_hours": _parse_decimal(row.get("TEsperaInicioOp")),
                    "operation_hours": _parse_decimal(row.get("TOperacao")),
                    "wait_for_departure_hours": _parse_decimal(row.get("TEsperaDesatracacao")),
                    "berth_time_hours": _parse_decimal(row.get("TAtracado")),
                    "port_stay_hours": _parse_decimal(row.get("TEstadia")),
                }

    return by_call_id, row_count


def _build_time_block(stop: dict[str, Any], time_by_call_id: dict[str, dict[str, float]]) -> tuple[dict[str, Any], int, int]:
    block = _empty_time_block()
    matched = 0
    missing = 0

    first_at = _parse_iso_datetime(stop.get("first_atracacao_at"))
    last_at = _parse_iso_datetime(stop.get("last_atracacao_at"))
    if first_at is not None and last_at is not None:
        block["observed_span_hours"] = _round((last_at - first_at).total_seconds() / 3600.0)

    for call_id in stop.get("call_ids", []) or []:
        row = time_by_call_id.get(str(call_id).strip())
        if row is None:
            missing += 1
            continue

        matched += 1
        block["wait_for_berth_hours"] += row["wait_for_berth_hours"]
        block["wait_for_operation_start_hours"] += row["wait_for_operation_start_hours"]
        block["operation_hours"] += row["operation_hours"]
        block["wait_for_departure_hours"] += row["wait_for_departure_hours"]
        block["berth_time_hours"] += row["berth_time_hours"]
        block["port_stay_hours"] += row["port_stay_hours"]

    for key in (
        "wait_for_berth_hours",
        "wait_for_operation_start_hours",
        "operation_hours",
        "wait_for_departure_hours",
        "berth_time_hours",
        "port_stay_hours",
    ):
        block[key] = _round(block[key]) or 0.0

    block["source_row_count"] = matched
    block["missing_call_count"] = missing
    return block, matched, missing


def _normalize_years(payload: dict[str, Any], args: argparse.Namespace) -> list[str]:
    if args.years:
        return [str(year).strip() for year in args.years if str(year).strip()]

    years = [str(year).strip() for year in payload.get("years", []) if str(year).strip()]
    if years:
        return years

    raise ValueError("Could not determine years. Provide --years explicitly.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich ANTAQ observed voyage JSON with per-stop time-at-port metrics."
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=DEFAULT_INPUT_JSON,
        help=f"Input voyages JSON. Default: {DEFAULT_INPUT_JSON}",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional output JSON path. Defaults to overwriting --input-json.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        help="Optional years for TemposAtracacao lookup. Defaults to years listed in the input JSON.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    input_path = args.input_json
    output_path = args.output_json or input_path

    payload = json.loads(input_path.read_text(encoding="utf-8-sig"))
    years = _normalize_years(payload, args)
    time_by_call_id, time_row_count = _load_time_rows(years)

    total_call_ids = 0
    matched_call_ids = 0
    missing_call_ids = 0
    unique_call_ids_seen: set[str] = set()

    for voyage in payload.get("voyages", []):
        stops = voyage.get("stops", []) or []
        for stop in stops:
            time_block, matched, missing = _build_time_block(stop, time_by_call_id)
            stop["time"] = time_block
            call_ids = [str(call_id).strip() for call_id in (stop.get("call_ids", []) or []) if str(call_id).strip()]
            total_call_ids += len(call_ids)
            matched_call_ids += matched
            missing_call_ids += missing
            unique_call_ids_seen.update(call_ids)

        voyage["origin_time"] = deepcopy(stops[0]["time"]) if stops else _empty_time_block()
        voyage["destination_time"] = deepcopy(stops[-1]["time"]) if stops else _empty_time_block()
        voyage["intermediate_stops"] = [deepcopy(stop) for stop in stops[1:-1]]
        voyage["intermediate_stop_count"] = len(voyage["intermediate_stops"])

    source_files = payload.setdefault("source_files", {})
    source_files["tempos_atracacao"] = [f"data/raw/cabotage_data/{year}TemposAtracacao.txt" for year in years]

    stats = payload.setdefault("stats", {})
    stats["tempos_atracacao_rows"] = int(time_row_count)
    stats["joined_calls_with_time_metrics"] = int(sum(1 for call_id in unique_call_ids_seen if call_id in time_by_call_id))
    stats["joined_calls_without_time_metrics"] = int(sum(1 for call_id in unique_call_ids_seen if call_id not in time_by_call_id))
    stats["voyage_stop_call_id_occurrences_with_time_metrics"] = int(matched_call_ids)
    stats["voyage_stop_call_id_occurrences_without_time_metrics"] = int(missing_call_ids)

    payload["time_enriched_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Years used: {', '.join(years)}")
    print(f"Voyages updated: {len(payload.get('voyages', []))}")
    print(f"Call IDs with time metrics: {matched_call_ids}")
    print(f"Call IDs without time metrics: {missing_call_ids}")
    print(f"Output JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
