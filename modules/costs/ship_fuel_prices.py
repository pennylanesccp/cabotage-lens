# modules/costs/ship_fuel_prices.py
# -*- coding: utf-8 -*-
"""
Ship fuel prices (Santos, Brazil) from Ship & Bunker
====================================================

Scrapes https://shipandbunker.com/prices/br-brazil and extracts the
bunker prices for the port of **Santos**.

Also provides `get_bunker_price()` to read the last scraped VLSFO price (BRL/mt).
"""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Dict, Any, Optional, List

import requests
from currency_converter import CurrencyConverter

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

SHIPANDBUNKER_BR_URL = "https://shipandbunker.com/prices/br-brazil"
SANTOS_LABEL = "Santos"

# Path to the persistence file
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_OUTPUT_TXT = os.path.join(
      _REPO_ROOT
    , "data"
    , "processed"
    , "maritime_fuel"
    , "santos_bunker_brl.txt"
)

__all__ = [
      "SHIPANDBUNKER_BR_URL"
    , "fetch_santos_prices"
    , "apply_fx_brl"
    , "write_prices_txt"
    , "get_bunker_price"  # <--- New Export
]


# ────────────────────────────────────────────────────────────────────────────────
# Price Reader (for Evaluator)
# ────────────────────────────────────────────────────────────────────────────────

def get_bunker_price(default_price_brl_mt: float = 3500.0) -> float:
    """
    Get the latest VLSFO price in BRL/mt from the local text file.
    If file is missing or empty, returns the default.
    """
    if not os.path.exists(DEFAULT_OUTPUT_TXT):
        _log.warning(f"Bunker price file not found: {DEFAULT_OUTPUT_TXT}. Using default: R$ {default_price_brl_mt:.2f}")
        return default_price_brl_mt

    try:
        with open(DEFAULT_OUTPUT_TXT, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if not lines:
            return default_price_brl_mt

        # Format: date_iso \t label \t vlsfo_brl \t mgo_brl \t fx
        last_line = lines[-1].strip()
        parts = last_line.split("\t")
        
        if len(parts) >= 3:
            price = float(parts[2])
            _log.info(f"Loaded Bunker Price (VLSFO): R$ {price:.2f}/mt (Date: {parts[0]})")
            return price
            
    except Exception as e:
        _log.error(f"Failed to read bunker price: {e}")

    return default_price_brl_mt


# ────────────────────────────────────────────────────────────────────────────────
# HTML parsing helpers (regex-based, no external deps)
# ────────────────────────────────────────────────────────────────────────────────

_SANTOS_TR_RE = re.compile(
      r"<tr[^>]*>\s*"
      r"<th[^>]*>\s*<a[^>]*>\s*Santos\s*</a>\s*</th>"
      r"(?P<body>.*?)"
      r"</tr>"
    , flags=re.IGNORECASE | re.DOTALL
)

_PRICE_CELL_RE = re.compile(
      r'<td[^>]*class="price[^"]*"[^>]*>.*?'
      r'<span[^>]*title="(?P<price>\d+(?:\.\d+)?)"[^>]*>'
    , flags=re.IGNORECASE | re.DOTALL
)

_DATE_CELL_RE = re.compile(
      r'<td[^>]*class="date[^"]*"[^>]*>\s*([^<]+)\s*</td>'
    , flags=re.IGNORECASE | re.DOTALL
)


def _extract_santos_row(html: str) -> str | None:
    """
    Return the full <tr>...</tr> HTML for the Santos row, or None if not found.
    """
    m = _SANTOS_TR_RE.search(html)
    if not m:
        return None
    return m.group(0)


def _parse_prices_from_row(row_html: str) -> Dict[str, Any]:
    """
    Given the Santos <tr> HTML, extract VLSFO and MGO prices (USD/mt)
    and the date label.
    """
    prices = [
        float(m.group("price"))
        for m in _PRICE_CELL_RE.finditer(row_html)
    ]

    if len(prices) < 2:
        raise ValueError(
            f"Expected at least two price cells for Santos, found {len(prices)}. "
            "Row HTML snippet: "
            f"{row_html[:300]!r}..."
        )

    vlsfo_price = prices[0]
    mgo_price = prices[1]

    date_match = _DATE_CELL_RE.search(row_html)
    date_label = date_match.group(1).strip() if date_match else None

    _log.debug(
        "Parsed Santos row → VLSFO=%.2f USD/mt, MGO=%.2f USD/mt, date=%s",
        vlsfo_price,
        mgo_price,
        date_label,
    )

    return {
          "port": SANTOS_LABEL
        , "vlsfo_usd_per_mt": vlsfo_price
        , "mgo_usd_per_mt": mgo_price
        , "date_label": date_label
        , "source_url": SHIPANDBUNKER_BR_URL
        , "row_html_preview": row_html[:200]
    }


# ────────────────────────────────────────────────────────────────────────────────
# Public scraper (USD)
# ────────────────────────────────────────────────────────────────────────────────

def fetch_santos_prices(
    *,
    session: Optional[requests.Session] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Fetch current Santos bunker prices (VLSFO and MGO) from Ship & Bunker.
    """
    sess = session or requests.Session()
    headers = {
          "User-Agent": "carbon-footprint-tf1/1.0 (academic, non-commercial)"
    }

    _log.info("Fetching Santos bunker prices from %s", SHIPANDBUNKER_BR_URL)

    try:
        resp = sess.get(SHIPANDBUNKER_BR_URL, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        _log.error("HTTP error when fetching Ship & Bunker page: %s", e)
        raise RuntimeError("Failed to fetch Ship & Bunker Brazil prices page.") from e

    html = resp.text
    row_html = _extract_santos_row(html)

    if not row_html:
        _log.error(
            "Could not locate Santos <tr> row in Ship & Bunker HTML. "
            "First 400 chars of page: %r",
            html[:400],
        )
        raise RuntimeError("Failed to parse Santos row from Ship & Bunker page.")

    prices = _parse_prices_from_row(row_html)

    _log.info(
        "Santos bunker prices (USD): VLSFO=%.2f USD/mt, MGO=%.2f USD/mt (date=%s)",
        prices["vlsfo_usd_per_mt"],
        prices["mgo_usd_per_mt"],
        prices["date_label"],
    )
    return prices


# ────────────────────────────────────────────────────────────────────────────────
# FX conversion helpers (USD → BRL)
# ────────────────────────────────────────────────────────────────────────────────

def apply_fx_brl(
    prices: Dict[str, Any],
    *,
    converter: Optional[CurrencyConverter] = None,
) -> Dict[str, Any]:
    """
    Take a prices dict in USD from `fetch_santos_prices` and enrich it with
    BRL/mt values using the `CurrencyConverter` package.
    """
    if "vlsfo_usd_per_mt" not in prices or "mgo_usd_per_mt" not in prices:
        raise ValueError(
            "apply_fx_brl expects keys 'vlsfo_usd_per_mt' and 'mgo_usd_per_mt' "
            f"but received keys={list(prices.keys())}"
        )

    c = converter or CurrencyConverter()

    # FX for 1 USD → BRL (ECB reference rate)
    fx_brl_per_usd = float(c.convert(1.0, "USD", "BRL"))
    _log.info(
        "FX rate used for conversion: 1 USD = %.6f BRL",
        fx_brl_per_usd,
    )

    vlsfo_usd = float(prices["vlsfo_usd_per_mt"])
    mgo_usd = float(prices["mgo_usd_per_mt"])

    vlsfo_brl = vlsfo_usd * fx_brl_per_usd
    mgo_brl = mgo_usd * fx_brl_per_usd

    _log.info(
        "Converted prices to BRL: "
        "VLSFO=%.2f USD/mt → %.2f BRL/mt; "
        "MGO=%.2f USD/mt → %.2f BRL/mt",
        vlsfo_usd,
        vlsfo_brl,
        mgo_usd,
        mgo_brl,
    )

    run_date_iso = date.today().isoformat()

    enriched = {
          **prices
        , "fx_brl_per_usd": fx_brl_per_usd
        , "vlsfo_brl_per_mt": vlsfo_brl
        , "mgo_brl_per_mt": mgo_brl
        , "run_date_iso": run_date_iso
    }

    return enriched


# ────────────────────────────────────────────────────────────────────────────────
# Simple TXT writer (BRL prices)
# ────────────────────────────────────────────────────────────────────────────────

def write_prices_txt(
    prices_brl: Dict[str, Any],
    *,
    output_path: str = DEFAULT_OUTPUT_TXT,
    append: bool = True,
) -> str:
    """
    Append (or overwrite) a simple text line with BRL prices.
    """
    required_keys = [
          "run_date_iso"
        , "date_label"
        , "vlsfo_brl_per_mt"
        , "mgo_brl_per_mt"
        , "fx_brl_per_usd"
    ]
    missing = [k for k in required_keys if k not in prices_brl]
    if missing:
        raise ValueError(
            f"write_prices_txt missing keys {missing} in prices_brl payload."
        )

    run_date_iso = str(prices_brl["run_date_iso"])
    date_label = str(prices_brl.get("date_label") or "")
    vlsfo_brl = float(prices_brl["vlsfo_brl_per_mt"])
    mgo_brl = float(prices_brl["mgo_brl_per_mt"])
    fx_brl_per_usd = float(prices_brl["fx_brl_per_usd"])

    # Ensure directory exists
    abs_path = os.path.abspath(output_path)
    out_dir = os.path.dirname(abs_path)
    os.makedirs(out_dir, exist_ok=True)

    mode = "a" if append else "w"
    line = (
          f"{run_date_iso}\t"
          f"{date_label}\t"
          f"{vlsfo_brl:.2f}\t"
          f"{mgo_brl:.2f}\t"
          f"{fx_brl_per_usd:.6f}\n"
    )

    _log.info(
        "Writing BRL prices to TXT file: path=%s, mode=%s, line=%r",
        abs_path,
        mode,
        line.strip(),
    )

    with open(abs_path, mode, encoding="utf-8") as f:
        f.write(line)

    return abs_path


# ────────────────────────────────────────────────────────────────────────────────
# CLI / smoke test
# ────────────────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI smoke test.
    """
    import argparse
    import json

    from modules.infra.log_manager import init_logging

    parser = argparse.ArgumentParser(
        description="Fetch Santos bunker prices (VLSFO & MGO)."
    )
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output-txt", default=DEFAULT_OUTPUT_TXT)
    parser.add_argument("--no-write", action="store_true")

    args = parser.parse_args(argv)

    init_logging(level=args.log_level, force=True, write_output=False)

    # 1) Fetch USD prices
    prices_usd = fetch_santos_prices(timeout=args.timeout)

    # 2) Convert to BRL
    prices_brl = apply_fx_brl(prices_usd)

    # 3) Optionally write TXT snapshot
    if not args.no_write:
        path = write_prices_txt(prices_brl, output_path=args.output_txt, append=True)
        prices_brl["output_txt_path"] = path

    print(json.dumps(prices_brl, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())