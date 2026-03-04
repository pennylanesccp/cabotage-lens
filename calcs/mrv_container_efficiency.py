#!/usr/bin/env python3
# calcs/mrv_container_efficiency.py
# -*- coding: utf-8 -*-

"""
Build container-vessel fuel intensity classes from EU MRV publication workbooks.

This script is a one-time preprocessing step. Runtime services must consume only:

    data/processed/container_ship_efficiency_classes.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

NM_TO_KM = 1.852

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_FILES: tuple[Path, ...] = (
    REPO_ROOT / "data" / "raw" / "cabotage_data" / "2021-v216-06022026-EU MRV Publication of information.xlsx",
    REPO_ROOT / "data" / "raw" / "cabotage_data" / "2022-v241-06022026-EU MRV Publication of information.xlsx",
    REPO_ROOT / "data" / "raw" / "cabotage_data" / "2023-v85-08022026-EU MRV Publication of information.xlsx",
    REPO_ROOT / "data" / "raw" / "cabotage_data" / "2024-v184-03032026-EU MRV Publication of information.xlsx",
)

OUTPUT_JSON = REPO_ROOT / "data" / "processed" / "container_ship_efficiency_classes.json"

CLASS_BINS = (
    ("container_small", float("-inf"), 20000.0),
    ("container_feeder", 20000.0, 40000.0),
    ("container_large", 40000.0, float("inf")),
)


@dataclass(frozen=True)
class CanonicalColumns:
    ship_type: str
    deadweight: str | None
    fuel_per_nm: str
    co2_per_nm: str
    technical_efficiency: str | None


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.lower()
    text = text.replace("₂", "2").replace("₄", "4").replace("₀", "0")
    text = text.replace("·", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _find_column(columns: list[str], *, include: list[str], exclude: list[str] | None = None) -> str | None:
    exclude = exclude or []
    normalized = {col: _normalize_text(col) for col in columns}
    for col, norm in normalized.items():
        if all(token in norm for token in include) and all(token not in norm for token in exclude):
            return col
    return None


def _coerce_numeric(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    text = text.str.replace(r"(?i)^division by zero!?$", "", regex=True)
    text = text.str.replace(" ", "", regex=False)
    text = text.str.replace(",", ".", regex=False)
    text = text.str.replace(r"[^0-9.+-]", "", regex=True)
    return pd.to_numeric(text, errors="coerce")


def _parse_tech_efficiency_g_per_t_nm(value: Any) -> float | None:
    """
    Parse numeric gCO2/t.nm from strings like "EIV (29.43 gCO₂/t·nm)".

    This fallback is used only when no deadweight column exists in the workbook.
    """
    text = str(value or "")
    match = re.search(r"([-+]?\d+(?:[.,]\d+)?)\s*g", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _resolve_columns(df: pd.DataFrame) -> CanonicalColumns:
    cols = [str(c) for c in df.columns]

    ship_type = _find_column(cols, include=["ship", "type"])
    fuel_per_nm = _find_column(
        cols,
        include=["fuel", "consumption", "per", "distance", "kg", "n", "mile"],
        exclude=["laden"],
    )
    co2_per_nm = _find_column(
        cols,
        include=["co2", "emissions", "per", "distance", "kg", "n", "mile"],
        exclude=["laden", "co2eq"],
    )
    deadweight = _find_column(cols, include=["deadweight"])
    technical_efficiency = _find_column(cols, include=["technical", "efficiency"])

    missing: list[str] = []
    if ship_type is None:
        missing.append("Ship type")
    if fuel_per_nm is None:
        missing.append("Fuel consumption per distance [kg / n mile]")
    if co2_per_nm is None:
        missing.append("CO2 emissions per distance [kg CO2 / n mile]")

    if missing:
        raise ValueError(f"Required columns not found: {', '.join(missing)}")

    return CanonicalColumns(
        ship_type=ship_type,
        deadweight=deadweight,
        fuel_per_nm=fuel_per_nm,
        co2_per_nm=co2_per_nm,
        technical_efficiency=technical_efficiency,
    )


def _classify_deadweight(deadweight_t: float) -> str:
    for label, lower, upper in CLASS_BINS:
        if lower <= deadweight_t < upper:
            return label
    return "container_large"


def _stats(series: pd.Series) -> dict[str, float | int | None]:
    clean = series.dropna()
    if clean.empty:
        return {
            "mean": None,
            "median": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "min": None,
            "max": None,
            "count": 0,
        }

    return {
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p10": float(clean.quantile(0.10)),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "p90": float(clean.quantile(0.90)),
        "min": float(clean.min()),
        "max": float(clean.max()),
        "count": int(clean.shape[0]),
    }


def _load_mrv_rows(path: Path) -> pd.DataFrame:
    workbook = pd.ExcelFile(path)
    rows: list[pd.DataFrame] = []

    for sheet_name in workbook.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet_name, header=2, dtype=object)
        columns = _resolve_columns(df)

        out = pd.DataFrame(index=df.index)
        out["source_file"] = path.name
        out["source_sheet"] = sheet_name

        out["ship_type"] = df[columns.ship_type].astype(str).str.strip()
        out["fuel_per_nm"] = _coerce_numeric(df[columns.fuel_per_nm])
        out["co2_per_nm"] = _coerce_numeric(df[columns.co2_per_nm])

        if columns.deadweight is not None:
            out["deadweight"] = _coerce_numeric(df[columns.deadweight])
            out["deadweight_source"] = "dataset_column"
        else:
            out["deadweight"] = pd.Series([float("nan")] * len(out), dtype="float64")
            out["deadweight_source"] = "missing"

        if columns.technical_efficiency is not None:
            out["tech_eff_g_per_t_nm"] = df[columns.technical_efficiency].apply(_parse_tech_efficiency_g_per_t_nm)
        else:
            out["tech_eff_g_per_t_nm"] = pd.Series([float("nan")] * len(out), dtype="float64")

        # Deadweight fallback when no explicit deadweight column is available:
        # deadweight[t] ≈ (co2_per_nm[kg/nm] * 1000[g/kg]) / technical_efficiency[g/(t*nm)]
        missing_deadweight = out["deadweight"].isna() | (out["deadweight"] <= 0)
        can_derive = out["tech_eff_g_per_t_nm"].notna() & (out["tech_eff_g_per_t_nm"] > 0) & (out["co2_per_nm"] > 0)
        derived = (out["co2_per_nm"] * 1000.0) / out["tech_eff_g_per_t_nm"]
        out.loc[missing_deadweight & can_derive, "deadweight"] = derived[missing_deadweight & can_derive]
        out.loc[missing_deadweight & can_derive, "deadweight_source"] = "derived_from_technical_efficiency"

        rows.append(out)

    if not rows:
        return pd.DataFrame(columns=["ship_type", "fuel_per_nm", "co2_per_nm", "deadweight", "deadweight_source"])
    return pd.concat(rows, ignore_index=True)


def _aggregate_by_class(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for class_name, _, _ in CLASS_BINS:
        subset = df[df["vessel_class"] == class_name]
        payload[class_name] = {
            "fuel_per_nm": _stats(subset["fuel_per_nm"]),
            "fuel_per_km": _stats(subset["fuel_per_km"]),
            "co2_per_nm": _stats(subset["co2_per_nm"]),
            "sample_size": int(subset.shape[0]),
        }
    return payload


def main() -> int:
    missing_files = [str(path) for path in RAW_FILES if not path.exists()]
    if missing_files:
        print("Missing MRV workbooks:")
        for item in missing_files:
            print(f"  - {item}")
        return 1

    print("Loading MRV workbooks...")
    frames = [_load_mrv_rows(path) for path in RAW_FILES]
    df = pd.concat(frames, ignore_index=True)
    print(f"Loaded rows: {len(df):,}")

    ship_type_norm = df["ship_type"].apply(_normalize_text)
    container_df = df[ship_type_norm.eq("container ship")].copy()
    print(f"Container ship rows before cleaning: {len(container_df):,}")

    removed_invalid_fuel = int((container_df["fuel_per_nm"] <= 0).sum() + container_df["fuel_per_nm"].isna().sum())
    removed_invalid_dwt = int((container_df["deadweight"] <= 0).sum() + container_df["deadweight"].isna().sum())

    container_df = container_df[container_df["fuel_per_nm"] > 0]
    container_df = container_df[container_df["deadweight"] > 0]

    container_df["fuel_per_km"] = container_df["fuel_per_nm"] / NM_TO_KM
    container_df["vessel_class"] = container_df["deadweight"].apply(_classify_deadweight)

    print(f"Rows removed (fuel_per_nm <= 0 or NaN): {removed_invalid_fuel:,}")
    print(f"Rows removed (deadweight <= 0 or NaN): {removed_invalid_dwt:,}")
    print(f"Container ship rows after cleaning: {len(container_df):,}")

    deadweight_sources = container_df["deadweight_source"].value_counts(dropna=False).to_dict()
    print(f"Deadweight source counts: {deadweight_sources}")

    class_payload = _aggregate_by_class(container_df)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(class_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved class efficiency artifact: {OUTPUT_JSON}")
    for class_name, stats in class_payload.items():
        print(
            f"  - {class_name}: n={stats['sample_size']} "
            f"median_fuel_per_nm={stats['fuel_per_nm']['median']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())



