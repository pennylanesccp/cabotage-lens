from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "cabotage_data"
PORTS_PATH = ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"
DEFAULT_OUTPUT = (
    ROOT / "data" / "processed" / "cabotage_data" / "antaq_top_destinations_by_origin.csv"
)
MAIN_CARGA_PATTERN = re.compile(r"^(?P<year>\d{4})Carga\.txt$")


@dataclass
class FlowStats:
    shipments: int = 0
    teu: float = 0.0
    weight_t: float = 0.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize ANTAQ containerized cabotage flows by origin port and rank "
            "the top destination ports."
        )
    )
    parser.add_argument(
        "--years",
        nargs="*",
        help="Years to include (example: 2025 2026). Defaults to all available main Carga files.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=2,
        help="How many top destinations to expose per origin. Default: 2.",
    )
    parser.add_argument(
        "--rank-by",
        choices=("weight_t", "teu", "shipments"),
        default="weight_t",
        help="Metric used to rank destination ports. Default: weight_t.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV output path. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def parse_decimal(raw: str) -> float:
    value = (raw or "").strip()
    if not value:
        return 0.0
    return float(value.replace(",", "."))


def normalize_port_key(value: str) -> str:
    return (value or "").strip().upper()


def discover_carga_files(raw_dir: Path, years: Iterable[str] | None) -> list[Path]:
    available: dict[str, Path] = {}
    for path in raw_dir.iterdir():
        match = MAIN_CARGA_PATTERN.match(path.name)
        if match:
            available[match.group("year")] = path

    if years:
        missing = [year for year in years if year not in available]
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise FileNotFoundError(f"Missing ANTAQ Carga files for year(s): {missing_list}")
        selected_years = sorted(set(years))
    else:
        selected_years = sorted(available)

    return [available[year] for year in selected_years]


def build_port_name_map(ports_path: Path) -> dict[str, str]:
    if not ports_path.exists():
        return {}

    alias_map: dict[str, str] = {}
    ports = json.loads(ports_path.read_text(encoding="utf-8"))
    for port in ports:
        port_name = str(port.get("name", "")).strip()
        aliases = {
            port_name,
            str(port.get("city", "")).strip(),
            *[str(alias).strip() for alias in port.get("aliases", [])],
        }
        for alias in aliases:
            key = normalize_port_key(alias)
            if key and key not in alias_map:
                alias_map[key] = port_name or alias
    return alias_map


def is_containerized_cabotage(row: dict[str, str]) -> bool:
    if (row.get("Tipo Navegação", "") or "").strip().lower() != "cabotagem":
        return False

    teu = parse_decimal(row.get("TEU", ""))
    if teu > 0:
        return True

    natureza = (row.get("Natureza da Carga", "") or "").lower()
    acondicionamento = (row.get("Carga Geral Acondicionamento", "") or "").lower()
    return "conteiner" in natureza or "conteiner" in acondicionamento


def resolve_port_name(code: str, alias_map: dict[str, str]) -> str:
    normalized = normalize_port_key(code)
    return alias_map.get(normalized, normalized or code)


def build_summary(
    carga_files: list[Path],
    alias_map: dict[str, str],
    top_n: int,
    rank_by: str,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    origin_totals: dict[str, FlowStats] = defaultdict(FlowStats)
    origin_dest_totals: dict[tuple[str, str], FlowStats] = defaultdict(FlowStats)

    processed_rows = 0
    kept_rows = 0

    for carga_file in carga_files:
        with carga_file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            for row in reader:
                processed_rows += 1
                if not is_containerized_cabotage(row):
                    continue

                origin = normalize_port_key(row.get("Origem", ""))
                destination = normalize_port_key(row.get("Destino", ""))
                if not origin or not destination:
                    continue

                teu = parse_decimal(row.get("TEU", ""))
                weight_t = parse_decimal(row.get("VLPesoCargaBruta", ""))

                kept_rows += 1

                origin_stats = origin_totals[origin]
                origin_stats.shipments += 1
                origin_stats.teu += teu
                origin_stats.weight_t += weight_t

                flow_stats = origin_dest_totals[(origin, destination)]
                flow_stats.shipments += 1
                flow_stats.teu += teu
                flow_stats.weight_t += weight_t

    destinations_by_origin: dict[str, list[tuple[str, FlowStats]]] = defaultdict(list)
    for (origin, destination), stats in origin_dest_totals.items():
        destinations_by_origin[origin].append((destination, stats))

    rows: list[dict[str, object]] = []
    for origin, total_stats in sorted(
        origin_totals.items(),
        key=lambda item: (-item[1].weight_t, -item[1].teu, item[0]),
    ):
        row: dict[str, object] = {
            "origin_port_code": origin,
            "origin_port_name": resolve_port_name(origin, alias_map),
            "total_departure_shipments": total_stats.shipments,
            "total_departure_teu": round(total_stats.teu, 3),
            "total_departure_weight_t": round(total_stats.weight_t, 3),
        }

        ranked_destinations = sorted(
            destinations_by_origin[origin],
            key=lambda item: (
                -getattr(item[1], rank_by),
                -item[1].weight_t,
                -item[1].teu,
                -item[1].shipments,
                item[0],
            ),
        )

        for index in range(top_n):
            prefix = f"top_dest_{index + 1}"
            if index < len(ranked_destinations):
                destination, stats = ranked_destinations[index]
                row[f"{prefix}_code"] = destination
                row[f"{prefix}_name"] = resolve_port_name(destination, alias_map)
                row[f"{prefix}_shipments"] = stats.shipments
                row[f"{prefix}_teu"] = round(stats.teu, 3)
                row[f"{prefix}_weight_t"] = round(stats.weight_t, 3)
                row[f"{prefix}_teu_share_pct"] = round(
                    100.0 * stats.teu / total_stats.teu if total_stats.teu else 0.0,
                    2,
                )
                row[f"{prefix}_weight_share_pct"] = round(
                    100.0 * stats.weight_t / total_stats.weight_t if total_stats.weight_t else 0.0,
                    2,
                )
            else:
                row[f"{prefix}_code"] = ""
                row[f"{prefix}_name"] = ""
                row[f"{prefix}_shipments"] = 0
                row[f"{prefix}_teu"] = 0.0
                row[f"{prefix}_weight_t"] = 0.0
                row[f"{prefix}_teu_share_pct"] = 0.0
                row[f"{prefix}_weight_share_pct"] = 0.0

        rows.append(row)

    summary = {
        "processed_rows": processed_rows,
        "kept_containerized_cabotage_rows": kept_rows,
        "origin_ports": len(origin_totals),
        "origin_destination_pairs": len(origin_dest_totals),
    }
    return rows, summary


def write_csv(rows: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    years = args.years or None
    carga_files = discover_carga_files(RAW_DIR, years)
    alias_map = build_port_name_map(PORTS_PATH)
    rows, summary = build_summary(
        carga_files=carga_files,
        alias_map=alias_map,
        top_n=args.top_n,
        rank_by=args.rank_by,
    )
    write_csv(rows, args.output)

    year_labels = ", ".join(path.stem[:4] for path in carga_files)
    print(f"Processed ANTAQ years: {year_labels}")
    print(f"Processed rows: {summary['processed_rows']}")
    print(f"Kept containerized cabotage rows: {summary['kept_containerized_cabotage_rows']}")
    print(f"Origin ports: {summary['origin_ports']}")
    print(f"Origin/destination pairs: {summary['origin_destination_pairs']}")
    print(f"Wrote CSV: {args.output}")


if __name__ == "__main__":
    main()
