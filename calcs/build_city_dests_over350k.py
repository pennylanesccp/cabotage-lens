#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build `city_dests_over350k.txt` from the tracked IBGE municipalities CSV.

Usage:
    python calcs/build_city_dests_over350k.py

The script is intentionally thin and reuses the parsing/filtering helpers from
`calcs/build_city_dests_over50k.py`. It filters for municipalities with
population strictly greater than 350,000 and writes `Cidade, UF` lines sorted
by UF and city name.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calcs.build_city_dests_over50k import build_list, write_dests

INPUT_CSV = ROOT / "data" / "raw" / "destinies" / "Lista_Municipios_com_IBGE_Brasil_Versao_CSV.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "destinies" / "city_dests_over350k.txt"
MIN_POPULATION = 350_001


def main() -> int:
    if not INPUT_CSV.exists():
        print(f"Error: input file not found at '{INPUT_CSV}'")
        return 1

    print(f"Reading from: {INPUT_CSV}")
    print(f"Filtering for: population > 350,000 (min_pop = {MIN_POPULATION})")

    items = build_list(
        csv_path=INPUT_CSV,
        ufs=None,
        min_pop=MIN_POPULATION,
        order="alpha",
        limit=None,
    )
    write_dests(items, OUTPUT_FILE)

    print(f"\nSuccessfully wrote {len(items)} lines to -> {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
