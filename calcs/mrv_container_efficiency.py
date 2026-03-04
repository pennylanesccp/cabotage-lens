#!/usr/bin/env python3
# calcs/mrv_container_efficiency.py
# -*- coding: utf-8 -*-

"""
Build container vessel-class artifacts from EU MRV publication workbooks.

This script is a one-time preprocessing step. Runtime services must consume:

- data/processed/container_ship_efficiency_classes.json
- data/processed/container_ship_fuel_rate_sea_by_class.json
- data/processed/container_ship_hoteling_rate_by_class.json
"""

from __future__ import annotations

import argparse
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

OUTPUT_CLASS_EFFICIENCY_JSON = REPO_ROOT / "data" / "processed" / "container_ship_efficiency_classes.json"
OUTPUT_SEA_RATE_JSON = REPO_ROOT / "data" / "processed" / "container_ship_fuel_rate_sea_by_class.json"
OUTPUT_HOTELING_RATE_JSON = REPO_ROOT / "data" / "processed" / "container_ship_hoteling_rate_by_class.json"

CLASS_BINS = (
    ("container_small", float("-inf"), 20000.0),
    ("container_feeder", 20000.0, 40000.0),
    ("container_large", 40000.0, float("inf")),
)

# EMEP/EEA 2023 ratios and load factors used for first-order hoteling derivation.
CRUISE_ME_LOAD = 0.80
CRUISE_AE_LOAD = 0.30
HOTELING_AE_LOAD = 0.40
DEFAULT_AUX_MAIN_RATIO = 0.25


@dataclass(frozen=True)
class CanonicalColumns:
    ship_type: str
    deadweight: str | None
    fuel_per_nm: str
    co2_per_nm: str
    technical_efficiency: str | None
    total_fuel_t: str | None
    time_at_sea_h: str | None
    fuel_rate_sea_t_per_h: str | None


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.lower()
    text = text.replace("\u2082", "2").replace("\u2084", "4").replace("\u2080", "0")
    text = text.replace("\u00b7", " ")
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
    Parse numeric gCO2/t.nm from strings like "EIV (29.43 gCO2/t.nm)".

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

    total_fuel_t = _find_column(
        cols,
        include=["total", "fuel", "consumption"],
        exclude=["benefitting", "laden", "cargo", "heating", "dynamic", "positioning"],
    )
    annual_time_at_sea = _find_column(cols, include=["annual", "time", "spent", "at", "sea"])
    generic_time_at_sea = _find_column(
        cols,
        include=["time", "spent", "at", "sea", "hours"],
        exclude=["through", "ice", "total", "co2", "co2eq", "ch4", "n2o"],
    )
    time_at_sea_h = annual_time_at_sea or generic_time_at_sea

    fuel_rate_sea_t_per_h = _find_column(
        cols,
        include=["fuel", "consumption", "per", "time", "spent", "at", "sea"],
        exclude=["co2", "co2eq"],
    )

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
        total_fuel_t=total_fuel_t,
        time_at_sea_h=time_at_sea_h,
        fuel_rate_sea_t_per_h=fuel_rate_sea_t_per_h,
    )


def _classify_deadweight(deadweight_t: float) -> str:
    for label, lower, upper in CLASS_BINS:
        if lower <= deadweight_t < upper:
            return label
    return "container_large"


def _stats_full(series: pd.Series) -> dict[str, float | int | None]:
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


def _stats_p10_p90(series: pd.Series) -> dict[str, float | None]:
    clean = series.dropna()
    if clean.empty:
        return {
            "median": None,
            "p10": None,
            "p90": None,
        }

    return {
        "median": float(clean.median()),
        "p10": float(clean.quantile(0.10)),
        "p90": float(clean.quantile(0.90)),
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
            out["deadweight"] = pd.Series([float("nan")] * len(out), dtype="float64", index=out.index)
            out["deadweight_source"] = "missing"

        if columns.technical_efficiency is not None:
            out["tech_eff_g_per_t_nm"] = df[columns.technical_efficiency].apply(_parse_tech_efficiency_g_per_t_nm)
        else:
            out["tech_eff_g_per_t_nm"] = pd.Series([float("nan")] * len(out), dtype="float64", index=out.index)

        # Deadweight fallback when no explicit deadweight column is available:
        # deadweight[t] ~= (co2_per_nm[kg/nm] * 1000[g/kg]) / technical_efficiency[g/(t*nm)]
        missing_deadweight = out["deadweight"].isna() | (out["deadweight"] <= 0)
        can_derive = out["tech_eff_g_per_t_nm"].notna() & (out["tech_eff_g_per_t_nm"] > 0) & (out["co2_per_nm"] > 0)
        derived_deadweight = (out["co2_per_nm"] * 1000.0) / out["tech_eff_g_per_t_nm"]
        out.loc[missing_deadweight & can_derive, "deadweight"] = derived_deadweight[missing_deadweight & can_derive]
        out.loc[missing_deadweight & can_derive, "deadweight_source"] = "derived_from_technical_efficiency"

        total_fuel_t = (
            _coerce_numeric(df[columns.total_fuel_t])
            if columns.total_fuel_t is not None
            else pd.Series([float("nan")] * len(out), dtype="float64", index=out.index)
        )
        time_at_sea_h = (
            _coerce_numeric(df[columns.time_at_sea_h])
            if columns.time_at_sea_h is not None
            else pd.Series([float("nan")] * len(out), dtype="float64", index=out.index)
        )
        direct_rate_tph = (
            _coerce_numeric(df[columns.fuel_rate_sea_t_per_h])
            if columns.fuel_rate_sea_t_per_h is not None
            else pd.Series([float("nan")] * len(out), dtype="float64", index=out.index)
        )

        derived_rate_tph = total_fuel_t / time_at_sea_h
        derived_rate_tph = derived_rate_tph.where((total_fuel_t > 0) & (time_at_sea_h > 0))

        out["fuel_rate_sea_t_per_h"] = direct_rate_tph.where(direct_rate_tph > 0, derived_rate_tph)
        direct_valid = direct_rate_tph > 0
        derived_valid = derived_rate_tph > 0
        out["fuel_rate_sea_source"] = "missing"
        out.loc[direct_valid, "fuel_rate_sea_source"] = "direct_mrv_column"
        out.loc[(~direct_valid) & derived_valid, "fuel_rate_sea_source"] = "derived_total_fuel_div_time"

        rows.append(out)

    if not rows:
        return pd.DataFrame(
            columns=[
                "ship_type",
                "fuel_per_nm",
                "co2_per_nm",
                "deadweight",
                "deadweight_source",
                "fuel_rate_sea_t_per_h",
                "fuel_rate_sea_source",
            ]
        )
    return pd.concat(rows, ignore_index=True)


def _aggregate_efficiency_by_class(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for class_name, _, _ in CLASS_BINS:
        subset = df[df["vessel_class"] == class_name]
        payload[class_name] = {
            "fuel_per_nm": _stats_full(subset["fuel_per_nm"]),
            "fuel_per_km": _stats_full(subset["fuel_per_km"]),
            "co2_per_nm": _stats_full(subset["co2_per_nm"]),
            "sample_size": int(subset.shape[0]),
        }
    return payload


def _aggregate_sea_rate_by_class(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for class_name, _, _ in CLASS_BINS:
        subset = df[df["vessel_class"] == class_name]
        payload[class_name] = {
            "fuel_rate_sea_t_per_h": _stats_p10_p90(subset["fuel_rate_sea_t_per_h"]),
            "sample_size": int(subset.shape[0]),
        }
    return payload


def _aggregate_hoteling_rate_by_class(df: pd.DataFrame, aux_main_ratio: float) -> dict[str, dict[str, Any]]:
    frac_cruise = CRUISE_ME_LOAD + (CRUISE_AE_LOAD * aux_main_ratio)
    frac_hot = HOTELING_AE_LOAD * aux_main_ratio
    ratio_used = frac_hot / frac_cruise if frac_cruise > 0 else 0.0

    payload: dict[str, dict[str, Any]] = {}
    for class_name, _, _ in CLASS_BINS:
        subset = df[df["vessel_class"] == class_name]
        hoteling_rate_tph = subset["fuel_rate_sea_t_per_h"] * ratio_used
        payload[class_name] = {
            "fuel_rate_hoteling_t_per_h": _stats_p10_p90(hoteling_rate_tph),
            "ratio_used": float(ratio_used),
            "aux_main_ratio": float(aux_main_ratio),
            "sample_size": int(subset.shape[0]),
        }
    return payload


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build container-class MRV efficiency + sea-rate + hoteling-rate artifacts"
    )
    parser.add_argument(
        "--aux-main-ratio",
        type=float,
        default=DEFAULT_AUX_MAIN_RATIO,
        help="Aux/Main nominal power ratio used for hoteling derivation (e.g., 0.25 or 0.27)",
    )
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    aux_main_ratio = float(args.aux_main_ratio)
    if aux_main_ratio <= 0:
        raise ValueError("--aux-main-ratio must be > 0")

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

    class_df = container_df[container_df["deadweight"] > 0].copy()
    class_df["vessel_class"] = class_df["deadweight"].apply(_classify_deadweight)

    efficiency_df = class_df[class_df["fuel_per_nm"] > 0].copy()
    efficiency_df["fuel_per_km"] = efficiency_df["fuel_per_nm"] / NM_TO_KM

    sea_rate_df = class_df[class_df["fuel_rate_sea_t_per_h"] > 0].copy()

    print(f"Rows removed (fuel_per_nm <= 0 or NaN): {removed_invalid_fuel:,}")
    print(f"Rows removed (deadweight <= 0 or NaN): {removed_invalid_dwt:,}")
    print(f"Container rows used for class efficiency: {len(efficiency_df):,}")
    print(f"Container rows used for sea-rate stats: {len(sea_rate_df):,}")

    deadweight_sources = efficiency_df["deadweight_source"].value_counts(dropna=False).to_dict()
    sea_rate_sources = sea_rate_df["fuel_rate_sea_source"].value_counts(dropna=False).to_dict()
    print(f"Deadweight source counts: {deadweight_sources}")
    print(f"Sea fuel-rate source counts: {sea_rate_sources}")

    class_efficiency_payload = _aggregate_efficiency_by_class(efficiency_df)
    sea_rate_payload = _aggregate_sea_rate_by_class(sea_rate_df)
    hoteling_payload = _aggregate_hoteling_rate_by_class(sea_rate_df, aux_main_ratio=aux_main_ratio)

    OUTPUT_CLASS_EFFICIENCY_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CLASS_EFFICIENCY_JSON.write_text(
        json.dumps(class_efficiency_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    OUTPUT_SEA_RATE_JSON.write_text(json.dumps(sea_rate_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_HOTELING_RATE_JSON.write_text(json.dumps(hoteling_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    frac_cruise = CRUISE_ME_LOAD + (CRUISE_AE_LOAD * aux_main_ratio)
    frac_hot = HOTELING_AE_LOAD * aux_main_ratio
    ratio_used = frac_hot / frac_cruise if frac_cruise > 0 else 0.0

    print(f"Saved class efficiency artifact: {OUTPUT_CLASS_EFFICIENCY_JSON}")
    print(f"Saved sea-rate artifact: {OUTPUT_SEA_RATE_JSON}")
    print(f"Saved hoteling-rate artifact: {OUTPUT_HOTELING_RATE_JSON}")
    print(
        "Hoteling derivation ratio: "
        f"r={aux_main_ratio:.4f}, frac_cruise={frac_cruise:.6f}, frac_hot={frac_hot:.6f}, ratio={ratio_used:.6f}"
    )

    for class_name, stats in class_efficiency_payload.items():
        print(
            f"  - {class_name}: n={stats['sample_size']} "
            f"median_fuel_per_nm={stats['fuel_per_nm']['median']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

