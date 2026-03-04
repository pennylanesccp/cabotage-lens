#!/usr/bin/env python3
# calcs/port_ops_params_builder.py
# -*- coding: utf-8 -*-

"""
Build moves-based port operations parameters from local references.

Outputs:
- data/processed/cabotage_data/port_ops_params_santos.json

Reference scope is intentionally restricted to files in `references/`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_XLSX = REPO_ROOT / "references" / "Dados Relatorio 2.xlsx"
OUTPUT_JSON = REPO_ROOT / "data" / "processed" / "cabotage_data" / "port_ops_params_santos.json"

# From references/hybrid_rtg_diesel_battery_energy_management_2021.pdf:
# - 40.6% reduction in operation cost and CO2 emissions (case study result)
# - 27% result reported in simulation discussion
HYBRID_REDUCTION_P10 = 0.406
HYBRID_REDUCTION_P90 = 0.270


def _normalize(text: Any) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _as_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(out):
        return None
    return out


def _extract_consumption_and_moves(xlsx: Path, sheet_name: str) -> tuple[float, float]:
    """
    Extract per-container fuel consumption and movement multiplier from a sheet.

    Expected pattern (in any column offset):
    - 'Consumo' -> numeric value -> unit containing 'cont'
    - 'Movimentos' -> numeric value
    """
    df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)

    consumption_l_per_container: float | None = None
    moves_per_container: float | None = None

    for _, row in df.iterrows():
        cells = list(row.tolist())
        for idx, cell in enumerate(cells):
            key = _normalize(cell)
            if key not in {"consumo", "movimentos"}:
                continue

            value = _as_float(cells[idx + 1] if idx + 1 < len(cells) else None)
            unit = _normalize(cells[idx + 2] if idx + 2 < len(cells) else "")

            if key == "consumo" and value is not None and "cont" in unit:
                consumption_l_per_container = value
            elif key == "movimentos" and value is not None:
                moves_per_container = value

    if consumption_l_per_container is None or moves_per_container is None or moves_per_container <= 0:
        raise ValueError(f"Could not extract consumption/moves from sheet: {sheet_name}")

    return float(consumption_l_per_container), float(moves_per_container)


def _extract_default_moves_per_call(xlsx: Path, sheet_name: str = "RTG Base C1") -> tuple[float, float, float]:
    """
    Derive default quay moves-per-call distribution from the 'Transporte Semanal' matrix.
    """
    df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
    start_idx: int | None = None
    label_col: int | None = None

    for idx, row in df.iterrows():
        cells = list(row.tolist())
        for col, cell in enumerate(cells):
            if _normalize(cell) == "transporte semanal":
                start_idx = idx + 1
                label_col = col
                break
        if start_idx is not None:
            break

    if start_idx is None or label_col is None:
        raise ValueError("Could not locate 'Transporte Semanal' block for moves default extraction.")

    values: list[float] = []
    for idx in range(start_idx, len(df)):
        label = _normalize(df.iloc[idx, label_col] if label_col < df.shape[1] else "")
        if label.startswith("total destino"):
            break

        for col in range(label_col + 1, df.shape[1]):
            value = _as_float(df.iloc[idx, col])
            if value is not None and value > 0:
                values.append(float(value))

    if not values:
        raise ValueError("No non-zero transport values found for default port moves derivation.")

    series = pd.Series(values, dtype="float64")
    return (
        float(series.quantile(0.10)),
        float(series.median()),
        float(series.quantile(0.90)),
    )


def _stats_from_values(v1: float, v2: float) -> dict[str, float]:
    low = min(v1, v2)
    high = max(v1, v2)
    med = (low + high) / 2.0
    return {"p10": float(low), "median": float(med), "p90": float(high)}


def build_payload() -> dict[str, Any]:
    rtg_base_l_per_container, rtg_moves = _extract_consumption_and_moves(REFERENCE_XLSX, "RTG Base C1")
    rtg_alt_l_per_container, _ = _extract_consumption_and_moves(REFERENCE_XLSX, "RTG C2")

    tt_base_l_per_container, tt_moves = _extract_consumption_and_moves(REFERENCE_XLSX, "TT Base C1")
    tt_alt_l_per_container, _ = _extract_consumption_and_moves(REFERENCE_XLSX, "TT C2")

    default_moves_p10, default_moves_median, default_moves_p90 = _extract_default_moves_per_call(REFERENCE_XLSX)

    rtg_base_l_per_move = rtg_base_l_per_container / rtg_moves
    rtg_alt_l_per_move = rtg_alt_l_per_container / rtg_moves

    tt_base_l_per_move = tt_base_l_per_container / tt_moves
    tt_alt_l_per_move = tt_alt_l_per_container / tt_moves

    # Partially electrified proxy represented by lower diesel-per-move factors
    # from hybrid DG+battery RTG evidence in the provided reference paper.
    rtg_hybrid_l_per_move_p10 = rtg_base_l_per_move * (1.0 - HYBRID_REDUCTION_P10)
    rtg_hybrid_l_per_move_p90 = rtg_base_l_per_move * (1.0 - HYBRID_REDUCTION_P90)
    rtg_hybrid_l_per_move_median = (rtg_hybrid_l_per_move_p10 + rtg_hybrid_l_per_move_p90) / 2.0

    return {
        "version": "1.0.0",
        "scope": "santos_port_ops_moves_based",
        "references": [
            "references/Dados Relatorio 2.xlsx",
            "references/rtg_crane_energy_usage_analysis_2017.pdf",
            "references/hybrid_rtg_diesel_battery_energy_management_2021.pdf",
            "references/ship_hoteling_loading_unloading_emissions_se_asia_2022.pdf",
            "references/brazilian_cabotage_decarbonization_pathways_fuels_2024.pdf",
        ],
        "defaults": {
            "default_port_calls": 2,
            "t_per_teu_default": 14.0,
            "default_port_moves_per_call": {
                "p10": default_moves_p10,
                "median": default_moves_median,
                "p90": default_moves_p90,
                "source": "Dados Relatorio 2.xlsx :: RTG Base C1 :: Transporte Semanal non-zero cells",
            },
            "diesel_density_kg_per_l": 0.85,
            "diesel_fuel_type": "diesel",
            "electricity_kg_co2e_per_kwh": 0.0,
            "electricity_price_brl_per_kwh": 0.0,
        },
        "scenarios": {
            "santos_diesel_heavy": {
                "description": "Diesel-heavy terminal operations based on Santos workbook baselines.",
                "equipment": {
                    "sts_quay": {
                        "moves_per_container": 1.0,
                        "diesel_l_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "No explicit STS per-move fuel factor identified in provided references.",
                        },
                        "electricity_kwh_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "No explicit STS electric factor identified in provided references.",
                        },
                    },
                    "rtg_yard": {
                        "moves_per_container": rtg_moves,
                        "diesel_l_per_move": {
                            **_stats_from_values(rtg_base_l_per_move, rtg_alt_l_per_move),
                            "source": "Dados Relatorio 2.xlsx :: RTG Base C1 / RTG C2",
                        },
                        "electricity_kwh_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "RTG scenarios in workbook are fuel-based (diesel/HVO).",
                        },
                    },
                    "terminal_truck": {
                        "moves_per_container": tt_moves,
                        "diesel_l_per_move": {
                            **_stats_from_values(tt_base_l_per_move, tt_alt_l_per_move),
                            "source": "Dados Relatorio 2.xlsx :: TT Base C1 / TT C2",
                        },
                        "electricity_kwh_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "No electric terminal-truck factor identified in provided references.",
                        },
                    },
                },
            },
            "santos_partially_electrified": {
                "description": "RTG diesel-per-move reduction proxy from hybrid DG+battery RTG literature.",
                "equipment": {
                    "sts_quay": {
                        "moves_per_container": 1.0,
                        "diesel_l_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "No explicit STS per-move fuel factor identified in provided references.",
                        },
                        "electricity_kwh_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "No explicit STS electric factor identified in provided references.",
                        },
                    },
                    "rtg_yard": {
                        "moves_per_container": rtg_moves,
                        "diesel_l_per_move": {
                            "p10": rtg_hybrid_l_per_move_p10,
                            "median": rtg_hybrid_l_per_move_median,
                            "p90": rtg_hybrid_l_per_move_p90,
                            "source": (
                                "hybrid_rtg_diesel_battery_energy_management_2021.pdf "
                                "(27% and 40.6% reduction evidence) applied to RTG Base C1 diesel baseline"
                            ),
                        },
                        "electricity_kwh_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "Hybrid RTG paper support is used as diesel reduction proxy only.",
                        },
                    },
                    "terminal_truck": {
                        "moves_per_container": tt_moves,
                        "diesel_l_per_move": {
                            **_stats_from_values(tt_base_l_per_move, tt_alt_l_per_move),
                            "source": "Dados Relatorio 2.xlsx :: TT Base C1 / TT C2",
                        },
                        "electricity_kwh_per_move": {
                            "p10": 0.0,
                            "median": 0.0,
                            "p90": 0.0,
                            "source": "No electric terminal-truck factor identified in provided references.",
                        },
                    },
                },
            },
        },
    }


def main() -> int:
    if not REFERENCE_XLSX.exists():
        raise FileNotFoundError(f"Missing reference workbook: {REFERENCE_XLSX}")

    payload = build_payload()

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    defaults = payload["defaults"]["default_port_moves_per_call"]
    print(f"Saved: {OUTPUT_JSON}")
    print(
        "Default port moves per call (from reference matrix): "
        f"p10={defaults['p10']:.3f}, median={defaults['median']:.3f}, p90={defaults['p90']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
