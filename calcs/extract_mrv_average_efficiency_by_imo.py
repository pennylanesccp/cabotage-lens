#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calcs.mrv_container_efficiency import (
    _coerce_numeric,
    _find_column,
    _normalize_text,
)


MRV_RAW_DIR = REPO_ROOT / "data" / "raw" / "cabotage_data"
MRV_FILE_GLOB = "*EU MRV Publication of information.xlsx"
DEFAULT_ANTAQ_JSON = (
    REPO_ROOT / "data" / "processed" / "cabotage_data" / "antaq_cabotage_observed_voyages.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "data" / "processed" / "cabotage_data" / "mrv_average_efficiency_by_imo.json"
)


@dataclass(frozen=True)
class LookupColumns:
    imo_number: str
    ship_name: str | None
    ship_type: str
    reporting_period: str | None
    fuel_per_transport_work_dwt: str | None
    fuel_per_transport_work_mass: str | None


def _resolve_lookup_columns(df: pd.DataFrame) -> LookupColumns:
    cols = [str(c) for c in df.columns]

    imo_number = _find_column(cols, include=["imo", "number"])
    ship_name = _find_column(cols, include=["name"], exclude=["verifier", "company"])
    ship_type = _find_column(cols, include=["ship", "type"])
    reporting_period = _find_column(cols, include=["reporting", "period"])
    fuel_per_transport_work_dwt = _find_column(
        cols,
        include=["fuel", "consumption", "per", "transport", "work", "dwt"],
        exclude=["laden"],
    )
    fuel_per_transport_work_mass = _find_column(
        cols,
        include=["fuel", "consumption", "per", "transport", "work", "mass"],
        exclude=["laden"],
    )

    missing: list[str] = []
    if imo_number is None:
        missing.append("IMO Number")
    if ship_type is None:
        missing.append("Ship type")
    if fuel_per_transport_work_dwt is None and fuel_per_transport_work_mass is None:
        missing.append("Fuel consumption per transport work [dwt or mass]")

    if missing:
        raise ValueError(f"Required columns not found: {', '.join(missing)}")

    return LookupColumns(
        imo_number=imo_number,
        ship_name=ship_name,
        ship_type=ship_type,
        reporting_period=reporting_period,
        fuel_per_transport_work_dwt=fuel_per_transport_work_dwt,
        fuel_per_transport_work_mass=fuel_per_transport_work_mass,
    )


def _load_mrv_efficiency_rows(path: Path) -> pd.DataFrame:
    workbook = pd.ExcelFile(path)
    rows: list[pd.DataFrame] = []

    for sheet_name in workbook.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet_name, header=2, dtype=object)
        columns = _resolve_lookup_columns(df)

        out = pd.DataFrame(index=df.index)
        out["source_file"] = path.name
        out["source_sheet"] = sheet_name
        out["imo"] = df[columns.imo_number].astype(str).str.strip()
        out["ship_name"] = (
            df[columns.ship_name].astype(str).str.strip() if columns.ship_name is not None else ""
        )
        out["ship_type"] = df[columns.ship_type].astype(str).str.strip()
        out["reporting_period"] = (
            _coerce_numeric(df[columns.reporting_period])
            if columns.reporting_period is not None
            else pd.Series([pd.NA] * len(out), index=out.index, dtype="Float64")
        )
        out["fuel_per_transport_work_dwt_g_per_tonne_nm"] = (
            _coerce_numeric(df[columns.fuel_per_transport_work_dwt])
            if columns.fuel_per_transport_work_dwt is not None
            else pd.Series([pd.NA] * len(out), index=out.index, dtype="Float64")
        )
        out["fuel_per_transport_work_mass_g_per_tonne_nm"] = (
            _coerce_numeric(df[columns.fuel_per_transport_work_mass])
            if columns.fuel_per_transport_work_mass is not None
            else pd.Series([pd.NA] * len(out), index=out.index, dtype="Float64")
        )

        out["fuel_per_transport_work_g_per_tonne_nm"] = out[
            "fuel_per_transport_work_dwt_g_per_tonne_nm"
        ].where(out["fuel_per_transport_work_dwt_g_per_tonne_nm"] > 0)
        out["fuel_per_transport_work_source"] = pd.Series(
            [""] * len(out), index=out.index, dtype="string"
        )
        out.loc[
            out["fuel_per_transport_work_g_per_tonne_nm"].notna(),
            "fuel_per_transport_work_source",
        ] = "dwt"

        fallback_mass = out["fuel_per_transport_work_g_per_tonne_nm"].isna() & (
            out["fuel_per_transport_work_mass_g_per_tonne_nm"] > 0
        )
        out.loc[
            fallback_mass,
            "fuel_per_transport_work_g_per_tonne_nm",
        ] = out.loc[fallback_mass, "fuel_per_transport_work_mass_g_per_tonne_nm"]
        out.loc[fallback_mass, "fuel_per_transport_work_source"] = "mass_fallback"

        rows.append(out)

    if not rows:
        return pd.DataFrame(
            columns=[
                "imo",
                "ship_name",
                "ship_type",
                "reporting_period",
                "fuel_per_transport_work_dwt_g_per_tonne_nm",
                "fuel_per_transport_work_mass_g_per_tonne_nm",
                "fuel_per_transport_work_g_per_tonne_nm",
                "fuel_per_transport_work_source",
                "source_file",
                "source_sheet",
            ]
        )

    merged = pd.concat(rows, ignore_index=True)
    merged["imo"] = merged["imo"].astype(str).str.strip()
    merged = merged[merged["imo"].str.fullmatch(r"\d+")]
    return merged


def _discover_mrv_workbooks() -> list[Path]:
    return sorted(MRV_RAW_DIR.glob(MRV_FILE_GLOB))


def _load_requested_imos(args: argparse.Namespace) -> list[str]:
    requested: set[str] = {imo.strip() for imo in (args.imo or []) if str(imo).strip()}

    if args.imo_file is not None:
        for line in args.imo_file.read_text(encoding="utf-8-sig").splitlines():
            imo = line.strip()
            if imo:
                requested.add(imo)

    if args.from_antaq_json is not None:
        payload = json.loads(args.from_antaq_json.read_text(encoding="utf-8-sig"))
        for voyage in payload.get("voyages", []):
            imo = str(voyage.get("imo", "")).strip()
            if imo:
                requested.add(imo)

    if not requested:
        raise ValueError("Provide at least one IMO via --imo, --imo-file, or --from-antaq-json.")

    return sorted(requested)


def _first_non_empty(values: pd.Series) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _record_from_row(row: pd.Series) -> dict[str, Any]:
    reporting_period = row.get("reporting_period")
    fuel_per_transport_work = row.get("fuel_per_transport_work_g_per_tonne_nm")
    fuel_per_transport_work_dwt = row.get("fuel_per_transport_work_dwt_g_per_tonne_nm")
    fuel_per_transport_work_mass = row.get("fuel_per_transport_work_mass_g_per_tonne_nm")
    fuel_per_transport_work_source = str(row.get("fuel_per_transport_work_source", "") or "").strip()

    return {
        "reporting_period": int(reporting_period) if pd.notna(reporting_period) else None,
        "average_fuel_consumption_per_transport_work_g_per_tonne_nmile": (
            float(fuel_per_transport_work) if pd.notna(fuel_per_transport_work) else None
        ),
        "average_fuel_consumption_per_transport_work_dwt_g_per_tonne_nmile": (
            float(fuel_per_transport_work_dwt) if pd.notna(fuel_per_transport_work_dwt) else None
        ),
        "average_fuel_consumption_per_transport_work_mass_g_per_tonne_nmile": (
            float(fuel_per_transport_work_mass) if pd.notna(fuel_per_transport_work_mass) else None
        ),
        "fuel_consumption_per_transport_work_source": fuel_per_transport_work_source or None,
        "source_file": str(row.get("source_file", "") or "").strip(),
        "source_sheet": str(row.get("source_sheet", "") or "").strip(),
    }


def _build_ship_payload(filtered: pd.DataFrame) -> list[dict[str, Any]]:
    ships: list[dict[str, Any]] = []

    if filtered.empty:
        return ships

    for imo, subset in filtered.groupby("imo", sort=True):
        subset = subset.sort_values(
            by=["reporting_period", "source_file", "source_sheet"],
            ascending=[False, True, True],
            na_position="last",
        )
        ships.append(
            {
                "imo": str(imo).strip(),
                "ship_name": _first_non_empty(subset["ship_name"]),
                "ship_type": _first_non_empty(subset["ship_type"]),
                "records": [_record_from_row(row) for _, row in subset.iterrows()],
            }
        )

    return ships


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract MRV annual average fuel per transport work rows for one or more IMOs."
        )
    )
    parser.add_argument(
        "--imo",
        action="append",
        default=[],
        help="IMO number to lookup. Repeat the flag for multiple IMOs.",
    )
    parser.add_argument(
        "--imo-file",
        type=Path,
        help="Optional text file with one IMO per line.",
    )
    parser.add_argument(
        "--from-antaq-json",
        type=Path,
        help=(
            "Optional ANTAQ voyages JSON to import unique IMOs from, for example "
            f"{DEFAULT_ANTAQ_JSON}."
        ),
    )
    parser.add_argument(
        "--container-only",
        action="store_true",
        help="Keep only MRV rows where Ship type == 'Container ship'.",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Keep only the latest reporting period per IMO.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Output JSON path. Default: {DEFAULT_OUTPUT_JSON}",
    )
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    requested_imos = _load_requested_imos(args)

    mrv_files = _discover_mrv_workbooks()
    if not mrv_files:
        raise FileNotFoundError(
            f"No MRV workbooks found in {MRV_RAW_DIR} matching {MRV_FILE_GLOB}."
        )

    frames = [_load_mrv_efficiency_rows(path) for path in mrv_files]
    df = pd.concat(frames, ignore_index=True)

    if args.container_only:
        ship_type_norm = df["ship_type"].apply(_normalize_text)
        df = df[ship_type_norm.eq("container ship")].copy()

    filtered = df[df["imo"].isin(requested_imos)].copy()
    filtered = filtered[filtered["fuel_per_transport_work_g_per_tonne_nm"].notna()].copy()

    if args.latest_only and not filtered.empty:
        filtered = filtered.sort_values(
            by=["imo", "reporting_period", "source_file", "source_sheet"],
            ascending=[True, False, True, True],
            na_position="last",
        )
        filtered = filtered.drop_duplicates(subset=["imo"], keep="first")

    filtered = filtered.sort_values(
        by=["imo", "reporting_period", "source_file", "source_sheet"],
        ascending=[True, True, True, True],
        na_position="last",
    )

    matched_imos = sorted(filtered["imo"].dropna().astype(str).unique().tolist())
    unmatched_imos = [imo for imo in requested_imos if imo not in matched_imos]

    payload = {
        "source_files": [str(path) for path in mrv_files],
        "requested_imos": requested_imos,
        "matched_imos": matched_imos,
        "unmatched_imos": unmatched_imos,
        "match_count": int(len(matched_imos)),
        "record_count": int(filtered.shape[0]),
        "ships": _build_ship_payload(filtered),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Requested IMOs: {len(requested_imos)}")
    print(f"Matched IMOs: {len(matched_imos)}")
    print(f"Records written: {filtered.shape[0]}")
    print(f"Output JSON: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
