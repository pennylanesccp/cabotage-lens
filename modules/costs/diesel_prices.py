# modules/costs/diesel_prices.py
# -*- coding: utf-8 -*-
"""
Diesel price helpers (UF-based).

Main entry point:
- get_average_price(uf_o, uf_d, default_price_r_per_l=6.0, csv_path=None)
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from modules.infra.log_manager import get_logger
from modules.infra.data_assets import resolve_data_asset_path

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIESEL_PRICES_CSV: Path = (
    _REPO_ROOT / "data" / "processed" / "road_data" / "latest_diesel_prices.csv"
)

_STATE_TO_UF = {
    "ACRE": "AC",
    "ALAGOAS": "AL",
    "AMAPA": "AP",
    "AMAZONAS": "AM",
    "BAHIA": "BA",
    "CEARA": "CE",
    "DISTRITO FEDERAL": "DF",
    "ESPIRITO SANTO": "ES",
    "GOIAS": "GO",
    "MARANHAO": "MA",
    "MATO GROSSO": "MT",
    "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG",
    "PARA": "PA",
    "PARAIBA": "PB",
    "PARANA": "PR",
    "PERNAMBUCO": "PE",
    "PIAUI": "PI",
    "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS",
    "RONDONIA": "RO",
    "RORAIMA": "RR",
    "SANTA CATARINA": "SC",
    "SAO PAULO": "SP",
    "SERGIPE": "SE",
    "TOCANTINS": "TO",
}


@dataclass(frozen=True)
class DieselPriceLookup:
    """Prepared UF->price lookup reusable across many evaluations in one run."""

    source_csv: str
    default_price_r_per_l: float
    uf_to_price: Dict[str, float]
    row_count: int


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_uf(value: Optional[str]) -> str:
    """Normalize UF inputs from code or full state names to two-letter code."""
    if not value:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    # Common geocode labels include the UF as the final comma-separated token.
    if "," in raw:
        tail = raw.split(",")[-1].strip()
        if len(tail) == 2 and tail.isalpha():
            return tail.upper()

    direct = raw.upper()
    if len(direct) == 2 and direct.isalpha():
        return direct

    normalized = _strip_accents(raw).upper().replace("-", " ")
    normalized = " ".join(normalized.split())

    if len(normalized) == 2 and normalized.isalpha():
        return normalized
    if normalized in _STATE_TO_UF:
        return _STATE_TO_UF[normalized]

    return ""


@lru_cache(maxsize=16)
def _load_latest_diesel_price_cached(path_str: str, mtime_ns: int) -> pd.DataFrame:
    # mtime_ns is part of the cache key to auto-bust cache when file is updated.
    _ = mtime_ns
    path = Path(path_str)
    df_raw = pd.read_csv(path)

    cols_map = {str(c).lower().strip(): c for c in df_raw.columns}
    uf_col = cols_map.get("uf") or cols_map.get("state") or "UF"
    price_col = (
        cols_map.get("price_brl_l")
        or cols_map.get("price")
        or cols_map.get("diesel_price_brl_l")
        or cols_map.get("price_brl")
        or "price_brl_l"
    )

    df = pd.DataFrame(
        {
            "UF": df_raw[uf_col].astype(str).map(normalize_uf),
            "price_brl_l": pd.to_numeric(df_raw[price_col], errors="coerce"),
        }
    ).dropna(subset=["price_brl_l"])

    df = df[df["UF"].str.len() == 2].reset_index(drop=True)
    return df


def load_latest_diesel_price(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Load normalized diesel prices with a small in-process cache."""
    requested_path = Path(csv_path) if csv_path is not None else DEFAULT_DIESEL_PRICES_CSV
    path = resolve_data_asset_path(requested_path).resolve()

    if not path.is_file():
        _log.warning(
            "load_latest_diesel_price: CSV not found at '%s'. Returning empty DataFrame.",
            path,
        )
        return pd.DataFrame(columns=["UF", "price_brl_l"])

    mtime_ns = path.stat().st_mtime_ns
    df = _load_latest_diesel_price_cached(str(path), mtime_ns).copy()

    _log.info("load_latest_diesel_price: loaded %d rows from '%s'.", len(df), path)
    return df


def avg_price_for_ufs(
    uf_o: str,
    uf_d: str,
    table: pd.DataFrame,
    *,
    source_csv: str | Path | None = None,
) -> Tuple[float, Dict[str, Any]]:
    """Average diesel price for origin/destiny UFs with fallback logic."""
    source_csv_str = str(source_csv) if source_csv is not None else str(DEFAULT_DIESEL_PRICES_CSV)

    uf_o_norm = normalize_uf(uf_o)
    uf_d_norm = normalize_uf(uf_d)

    if table.empty:
        uf_to_price: Dict[str, float] = {}
    else:
        uf_to_price = {
            str(k): float(v)
            for k, v in zip(table["UF"].tolist(), table["price_brl_l"].tolist())
            if isinstance(k, str) and k
        }

    p_o = uf_to_price.get(uf_o_norm)
    p_d = uf_to_price.get(uf_d_norm)

    fallback_used = False
    if p_o is None and p_d is not None:
        p_o, fallback_used = p_d, True
    if p_d is None and p_o is not None:
        p_d, fallback_used = p_o, True

    if p_o is None and p_d is None:
        avg = 0.0
        fallback_used = True
    else:
        avg = (float(p_o) + float(p_d)) / 2.0

    ctx: Dict[str, Any] = {
        "uf_origin": uf_o_norm or None,
        "uf_destiny": uf_d_norm or None,
        "price_origin": None if p_o is None else float(p_o),
        "price_destiny": None if p_d is None else float(p_d),
        "source_csv": source_csv_str,
        "fallback_used": bool(fallback_used),
    }

    _log.info(
        "avg_price_for_ufs: uf_o=%s uf_d=%s price_o=%s price_d=%s avg=%.4f fallback_used=%s",
        uf_o_norm,
        uf_d_norm,
        ctx["price_origin"],
        ctx["price_destiny"],
        avg,
        fallback_used,
    )
    return float(avg), ctx


def build_price_lookup(
    *,
    default_price_r_per_l: float = 6.0,
    csv_path: str | Path | None = None,
) -> DieselPriceLookup:
    """Load the diesel table once and prepare a reusable UF lookup map."""
    requested_path = Path(csv_path) if csv_path is not None else DEFAULT_DIESEL_PRICES_CSV
    source_csv = str(resolve_data_asset_path(requested_path).resolve())
    table = load_latest_diesel_price(csv_path=csv_path)
    uf_to_price: Dict[str, float] = {}
    if not table.empty:
        uf_to_price = {
            str(k): float(v)
            for k, v in zip(table["UF"].tolist(), table["price_brl_l"].tolist())
            if isinstance(k, str) and k
        }

    return DieselPriceLookup(
        source_csv=source_csv,
        default_price_r_per_l=float(default_price_r_per_l),
        uf_to_price=uf_to_price,
        row_count=len(uf_to_price),
    )


def get_average_price_from_lookup(
    uf_o: str,
    uf_d: str,
    lookup: DieselPriceLookup,
) -> Dict[str, Any]:
    """Resolve diesel price metadata from a prepared lookup without reloading the CSV."""
    uf_o_norm = normalize_uf(uf_o)
    uf_d_norm = normalize_uf(uf_d)

    if not lookup.uf_to_price or not uf_o_norm or not uf_d_norm:
        price = float(lookup.default_price_r_per_l)
        reason_parts: list[str] = []
        if not lookup.uf_to_price:
            reason_parts.append("empty_or_missing_table")
        if not uf_o_norm:
            reason_parts.append("missing_uf_origin")
        if not uf_d_norm:
            reason_parts.append("missing_uf_destiny")
        reason = ",".join(reason_parts) or "unknown"

        _log.warning(
            "get_average_price_from_lookup: fallback to default. uf_o=%r uf_d=%r default=%.4f reason=%s",
            uf_o_norm,
            uf_d_norm,
            price,
            reason,
        )
        return {
            "price_r_per_l": price,
            "source": "default_price_param",
            "uf_origin": uf_o_norm or None,
            "uf_destiny": uf_d_norm or None,
            "fallback_used": True,
            "csv_path": lookup.source_csv,
            "fallback_reason": reason,
        }

    p_o = lookup.uf_to_price.get(uf_o_norm)
    p_d = lookup.uf_to_price.get(uf_d_norm)

    fallback_used = False
    if p_o is None and p_d is not None:
        p_o, fallback_used = p_d, True
    if p_d is None and p_o is not None:
        p_d, fallback_used = p_o, True

    if p_o is None and p_d is None:
        avg = float(lookup.default_price_r_per_l)
        fallback_used = True
        source = "default_price_param"
    else:
        avg = (float(p_o) + float(p_d)) / 2.0
        source = "latest_diesel_prices_csv"

    return {
        "price_r_per_l": float(avg),
        "source": source,
        "uf_origin": uf_o_norm or None,
        "uf_destiny": uf_d_norm or None,
        "price_origin": None if p_o is None else float(p_o),
        "price_destiny": None if p_d is None else float(p_d),
        "source_csv": lookup.source_csv,
        "csv_path": lookup.source_csv,
        "fallback_used": bool(fallback_used),
    }


def get_average_price(
    uf_o: str,
    uf_d: str,
    *,
    default_price_r_per_l: float = 6.0,
    csv_path: str | Path | None = None,
) -> Dict[str, Any]:
    """UF-based adapter used by road fuel services and evaluators."""
    lookup = build_price_lookup(
        default_price_r_per_l=default_price_r_per_l,
        csv_path=csv_path,
    )
    meta = get_average_price_from_lookup(uf_o, uf_d, lookup)

    _log.debug(
        "get_average_price: uf_o=%s uf_d=%s avg_price=%.4f R$/L",
        meta.get("uf_origin"),
        meta.get("uf_destiny"),
        float(meta.get("price_r_per_l") or 0.0),
    )
    return meta


def main(argv: list[str] | None = None) -> int:
    """CLI smoke test for diesel price helpers."""
    import argparse
    import json

    from modules.infra.log_manager import init_logging

    parser = argparse.ArgumentParser(
        description="Load diesel CSV and compute average price between two UFs."
    )
    parser.add_argument("--uf-origin", dest="uf_origin", default="SP", help="Origin UF code (default: SP).")
    parser.add_argument("--uf-destiny", dest="uf_destiny", default="RJ", help="Destiny UF code (default: RJ).")
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_DIESEL_PRICES_CSV),
        help=f"Diesel prices CSV path (default: {DEFAULT_DIESEL_PRICES_CSV}).",
    )
    parser.add_argument(
        "--default-price",
        type=float,
        default=6.0,
        help="Default fallback price (R$/L) when UF/table is unavailable.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )

    args = parser.parse_args(argv)

    init_logging(level=args.log_level, force_clean=True, archive_to_storage=False)

    payload = get_average_price(
        uf_o=args.uf_origin,
        uf_d=args.uf_destiny,
        default_price_r_per_l=args.default_price,
        csv_path=args.csv_path,
    )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
