#!/usr/bin/env python3
# calcs/build_distance_matrix.py
# -*- coding: utf-8 -*-

"""
Port-to-port sea-distance matrix (km, using Geografos.com.br)
=============================================================

Builds a symmetric matrix of sea distances between all Brazilian cabotage ports
defined in ``data/processed/cabotage_data/ports_br.json``.

Coordinates
-----------
For each port we choose coordinates in this order of preference:

  1) Gate coordinates, if available:
       - p["gate_lat"] / p["gate_lon"], or
       - p["gate"]["lat"] / p["gate"]["lon"]
  2) Fallback: p["lat"] / p["lon"]

Primary distance source
-----------------------
For each unordered port pair (A, B) we try to fetch the official sailing
distance from:

    https://www.geografos.com.br/viagem-maritima-entre-portos-brasil/

The URL pattern used by that site is, for example:

    distancia-entre-porto-santos-e-porto-aracaju.php

i.e.::

    distancia-entre-{slug_A}-e-{slug_B}.php

where each ``slug`` is a normalised lower-case form of the port name like
``porto-santos``, ``porto-angra-dos-reis`` etc.

The script derives a best-effort slug from the port name, but if your
``ports_br.json`` already contains a field ``"geografos_slug"`` for a given
port, that value is used instead.

If the HTML page is found, we parse the ``<strong>Distância: ... Km ...</strong>``
element and extract the distance in kilometres.

Fallback
--------
If either:

  * both URL orders (A–B and B–A) fail, or
  * we cannot parse the distance from the page,

then we fall back to a geometric approximation:

    Haversine great-circle distance × COASTLINE_FACTOR

Output
------
Saves a JSON file at:

    data/processed/cabotage_data/sea_matrix.json

with structure:

    {
      "unit": "km",
      "method": "geografos_maritime_distance_v1",
      "coastline_factor": 1.18,
      "note": "Off-diagonal entries are sea distances (km) between port centroids/gates; symmetric.",
      "matrix": {
        "Port A": {"Port A": 0.0, "Port B": 123.4, ...},
        "Port B": {...},
        ...
      }
    }

(You can uncomment the CSV export if you also want a tabular file.)

Dependencies
------------
This script requires the ``requests`` and ``beautifulsoup4`` packages::

    pip install requests beautifulsoup4
"""

from __future__ import annotations

import itertools as it
import json
import math
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ───────────────────────────── debug flag ────────────────────────────────
DEBUG = os.getenv("SEA_MATRIX_DEBUG", "0") == "1"
SLEEP_SECONDS = float(os.getenv("SEA_MATRIX_SLEEP", "0.0"))  # polite rate limiting


def _debug(msg: str) -> None:
    if DEBUG:
        print(msg)


# ───────────────────────────── repo root helper ──────────────────────────
def _repo_root() -> str:
    """
    Try to locate the repository root by walking upwards until we find a
    ``modules`` directory. If that fails, fall back to ``$PROJECT_ROOT``.
    """
    cand = os.getcwd()
    for _ in range(8):
        if os.path.isdir(os.path.join(cand, "modules")):
            return cand
        cand = os.path.dirname(cand)

    env = os.getenv("PROJECT_ROOT")
    if env and os.path.isdir(os.path.join(env, "modules")):
        return env

    raise SystemExit("❌ Could not locate repo root (no 'modules' dir found).")


ROOT = _repo_root()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.ports.ports_index import load_ports  # noqa: E402  (after sys.path tweak)


# ───────────────────────────── ports loader ──────────────────────────────
PORTS_PATH = os.path.join(
      ROOT
    , "data"
    , "processed"
    , "cabotage_data"
    , "ports_br.json"
)

ports: List[Dict[str, Any]] = load_ports(PORTS_PATH)


def _resolve_port_coords(port: Dict[str, Any]) -> Tuple[float, float]:
    """
    Return (lat, lon) for a port, preferring gate coordinates if available.

    Priority:
      1) port["gate_lat"], port["gate_lon"]
      2) port["gate"]["lat"], port["gate"]["lon"]
      3) port["lat"], port["lon"]

    Raises ValueError if nothing usable is found.
    """
    # 1) Flat gate_lat / gate_lon keys
    gate_lat = port.get("gate_lat")
    gate_lon = port.get("gate_lon")
    if gate_lat is not None and gate_lon is not None:
        return float(gate_lat), float(gate_lon)

    # 2) Nested gate dict
    gate = port.get("gate")
    if isinstance(gate, dict):
        g_lat = gate.get("lat")
        g_lon = gate.get("lon")
        if g_lat is not None and g_lon is not None:
            return float(g_lat), float(g_lon)

    # 3) Fallback to generic lat / lon
    lat = port.get("lat")
    lon = port.get("lon")
    if lat is not None and lon is not None:
        return float(lat), float(lon)

    raise ValueError(f"No usable coordinates for port: {port!r}")


# ───────────────────────────── name → slug helper ────────────────────────
_STOPWORDS_AFTER_PORT = {"de", "da", "do", "das", "dos"}


def _strip_accents(text: str) -> str:
    """
    Remove accents/diacritics and keep only ASCII characters.
    """
    norm = unicodedata.normalize("NFKD", text)
    return norm.encode("ascii", "ignore").decode("ascii")


def _normalise_port_name_for_slug(name: str) -> str:
    """
    Convert a human port name to the slug pattern used by Geografos.

    Examples (intended behaviour):
      "Porto de Santos"         → "porto-santos"
      "Porto de Rio Grande - RS"→ "porto-rio-grande"
      "Porto Angra dos Reis"    → "porto-angra-dos-reis"
      "Porto do Itaqui"         → "porto-itaqui"
    """
    # Lower-case, strip accents and trim whitespace
    txt = _strip_accents(name).lower().strip()

    # Remove trailing state code like " - rj" if present
    # (simple heuristic: drop " - XX" at the end)
    if " -" in txt:
        # E.g. "porto angra dos reis - rj" → "porto angra dos reis"
        txt = txt.rsplit(" -", 1)[0].strip()

    # Replace any non-alphanumeric characters (except spaces) with spaces
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    # Collapse multiple spaces
    txt = re.sub(r"\s+", " ", txt)

    tokens = txt.split()
    if not tokens:
        raise ValueError(f"Cannot derive slug from empty port name: {name!r}")

    # Expect first token to be "porto" in your data, but be defensive
    if tokens[0] == "porto" and len(tokens) >= 3 and tokens[1] in _STOPWORDS_AFTER_PORT:
        # "porto de santos" → "porto-santos"
        # "porto do itaqui" → "porto-itaqui"
        slug_tokens = ["porto"] + tokens[2:]
    else:
        # "porto angra dos reis" → "porto-angra-dos-reis"
        slug_tokens = tokens

    return "-".join(slug_tokens)


# Build a stable list of ports with derived slugs and coordinates
port_records: List[Dict[str, Any]] = []
for p in ports:
    name = p.get("name") or p.get("label") or "UNKNOWN_PORT"
    slug = p.get("geografos_slug") or _normalise_port_name_for_slug(name)
    lat, lon = _resolve_port_coords(p)
    port_records.append(
        {
              "name": name
            , "slug": slug
            , "lat": float(lat)
            , "lon": float(lon)
        }
    )

# ───────────────────────────── utilities ─────────────────────────────────
def haversine_km(
    a_lat: float
    , a_lon: float
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Great-circle distance between two points on Earth (WGS84), in km.
    """
    R = 6371.0088
    ar1 = math.radians(a_lat)
    br1 = math.radians(a_lon)
    ar2 = math.radians(b_lat)
    br2 = math.radians(b_lon)
    da = ar2 - ar1
    db = br2 - br1
    s = (
          math.sin(da / 2) ** 2
        + math.cos(ar1) * math.cos(ar2) * math.sin(db / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(s), math.sqrt(1 - s))


COASTLINE_FACTOR = 1.18  # used only for fallback approximation

BASE_URL = (
    "https://www.geografos.com.br"
    "/viagem-maritima-entre-portos-brasil"
)


def _build_geografos_urls(
    slug_a: str
    , slug_b: str
) -> List[str]:
    """
    Return the two possible URL permutations for a port pair (A, B).

    Geografos appears to use URLs like:

      /distancia-entre-{slug_a}-e-{slug_b}.php

    but some pairs may exist only in one order. We therefore try both.
    """
    path1 = f"distancia-entre-{slug_a}-e-{slug_b}.php"
    path2 = f"distancia-entre-{slug_b}-e-{slug_a}.php"
    return [
          f"{BASE_URL}/{path1}"
        , f"{BASE_URL}/{path2}"
    ]


def _parse_km_from_html(html: str) -> float:
    """
    Given a page HTML from Geografos, extract the distance in km.

    We look for a <strong> element whose text contains 'Distância:'
    and then parse the first number before 'Km'.
    """
    soup = BeautifulSoup(html, "html.parser")

    strong = soup.find("strong", string=re.compile(r"Dist.ncia:", re.IGNORECASE))
    if strong is None:
        # Fallback: search the entire text (more expensive, but robust)
        text = soup.get_text(" ", strip=True)
    else:
        text = strong.get_text(" ", strip=True)

    m = re.search(r"Dist.ncia:\s*([\d\.,]+)\s*Km", text, flags=re.IGNORECASE)
    if not m:
        raise ValueError("Could not find 'Distância: ... Km' pattern in page.")

    raw_num = m.group(1).strip()
    # Portuguese-style numbers: '.' thousands separator, ',' decimal
    # Remove dots, replace comma with dot
    normalised = raw_num.replace(".", "").replace(",", ".")
    return float(normalised)


# Optional cache to avoid recomputing distances for identical slug pairs
_route_cache: Dict[Tuple[str, str], float] = {}


def fetch_distance_km(
    a_name: str
    , a_slug: str
    , a_lat: float
    , a_lon: float
    , b_name: str
    , b_slug: str
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Compute sea distance (km) between two ports.

    First, we try to fetch a "true" maritime distance from Geografos. If
    that fails (network error, HTTP error, pattern not found, etc.), we
    fall back to Haversine×coastline_factor.

    We cache by *slug* pair (unordered) so that repeated calls for the
    same A–B pair do not re-hit the site.
    """
    # Build a symmetric cache key based on slugs
    key = tuple(sorted((a_slug, b_slug)))
    if key in _route_cache:
        return _route_cache[key]

    urls = _build_geografos_urls(a_slug, b_slug)
    last_exc: Exception | None = None

    for url in urls:
        try:
            _debug(f"[HTTP] GET {url}")
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                _debug(f"[HTTP] {url} → status {resp.status_code}")
                last_exc = RuntimeError(
                    f"HTTP {resp.status_code} for {url}"
                )
                continue

            km = _parse_km_from_html(resp.text)
            _route_cache[key] = km
            _debug(f"[OK] {a_name} ↔ {b_name}: {km:.1f} km (from {url})")

            if SLEEP_SECONDS > 0:
                time.sleep(SLEEP_SECONDS)

            return km

        except Exception as exc:
            last_exc = exc
            _debug(f"[WARN] Failed to parse distance from {url}: {exc!r}")

    # If we reach here, both URL permutations failed → fallback
    hv = haversine_km(a_lat, a_lon, b_lat, b_lon)
    approx = hv * COASTLINE_FACTOR
    _route_cache[key] = approx

    msg = (
        f"⚠️  Geografos distance not available for '{a_name}' ↔ '{b_name}' "
        f"(last error: {last_exc!r}); using Haversine×{COASTLINE_FACTOR} "
        f"≈ {approx:.1f} km instead."
    )
    print(msg)
    return approx


# ───────────────────────────── build matrix ───────────────────────────────
def build_matrix() -> pd.DataFrame:
    """
    Build a symmetric DataFrame of sea distances (km) between all ports.
    """
    names = [rec["name"] for rec in port_records]
    N = len(names)
    matrix_km = pd.DataFrame(0.0, index=names, columns=names, dtype=float)

    # Fill the diagonal explicitly for clarity
    for name in names:
        matrix_km.at[name, name] = 0.0

    total_pairs = math.comb(N, 2) if N >= 2 else 0
    done = 0

    print(f"▶ Building sea-distance matrix for {N} ports ({total_pairs} pairs)...")

    for a_rec, b_rec in it.combinations(port_records, 2):
        done += 1
        dist_km = fetch_distance_km(
              a_rec["name"]
            , a_rec["slug"]
            , a_rec["lat"]
            , a_rec["lon"]
            , b_rec["name"]
            , b_rec["slug"]
            , b_rec["lat"]
            , b_rec["lon"]
        )
        matrix_km.at[a_rec["name"], b_rec["name"]] = dist_km
        matrix_km.at[b_rec["name"], a_rec["name"]] = dist_km

        if done % 10 == 0 or done == total_pairs:
            print(f"  • processed {done}/{total_pairs} pairs", flush=True)

    print("✔ Matrix build complete.")
    return matrix_km


# ───────────────────────────── persist outputs ────────────────────────────
def main() -> None:
    matrix_km = build_matrix()

    outdir = Path(ROOT) / "data" / "processed" / "cabotage_data"
    outdir.mkdir(parents=True, exist_ok=True)

    # csv_path = outdir / "sea_matrix.csv"
    json_path = outdir / "sea_matrix.json"

    # Uncomment if you want the CSV as well
    # matrix_km.to_csv(csv_path, float_format="%.3f", encoding="utf-8")

    method = "geografos_maritime_distance_v1"

    names = list(matrix_km.index)

    payload: Dict[str, Any] = {
          "unit": "km"
        , "method": method
        , "coastline_factor": COASTLINE_FACTOR
        , "note": (
            "Off-diagonal entries are sea distances (km) between port "
            "centroids/gates; symmetric. Distances primarily from "
            "Geografos.com.br; Haversine×coastline_factor used only as "
            "a fallback when no page is available or cannot be parsed."
        )
        , "matrix": {
              r: {c: float(matrix_km.at[r, c]) for c in names}
              for r in names
          }
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {json_path}")


if __name__ == "__main__":
    main()
