#!/usr/bin/env python3
# calcs/build_distance_matrix.py
# -*- coding: utf-8 -*-

"""
Port-to-port sea-distance matrix (km, using searoute)
=====================================================

Builds a symmetric matrix of sea distances between all Brazilian cabotage ports
defined in ``data/cabotage_data/ports_br.json``.

Distances are computed with the `searoute` Python package (shortest sea route
over a maritime network). If `searoute` fails for any pair, we fall back to a
Haversine great-circle distance multiplied by a coastline factor.

Output
------
Saves a JSON file at:

    data/cabotage_data/sea_matrix.json

with structure:

    {
      "unit": "km",
      "method": "searoute_py_<version>",
      "coastline_factor": 1.18,
      "note": "Off-diagonal entries are sea distances (km) between port centroids; symmetric.",
      "matrix": {
        "Port A": {"Port A": 0.0, "Port B": 123.4, ...},
        "Port B": {...},
        ...
      }
    }

(You can uncomment the CSV export if you also want a tabular file.)
"""

from __future__ import annotations

import itertools as it
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

# ───────────────────────────── dependencies ──────────────────────────────
import searoute as sr

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

from modules.ports.ports_index import load_ports


# ───────────────────────────── ports loader ──────────────────────────────
PORTS_PATH = os.path.join(ROOT, "data", "processed", "cabotage_data", "ports_br.json")
ports: List[Dict[str, Any]] = load_ports(PORTS_PATH)

# Stable list of (label, lat, lon)
port_list: List[Tuple[str, float, float]] = [
      (p["name"], float(p["lat"]), float(p["lon"]))
    for p in ports
]

# ───────────────────────────── utilities ──────────────────────────────────
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


def _fallback_distance_km(
    a_lat: float
    , a_lon: float
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Approximate sea distance as Haversine × coastline factor.

    This is only used if `searoute` fails for some reason (e.g. weird coords).
    """
    hv = haversine_km(a_lat, a_lon, b_lat, b_lon)
    return hv * COASTLINE_FACTOR


def _route_properties(route: Any) -> Dict[str, Any]:
    """
    Normalise access to the `properties` of the object returned by `searoute`.

    Depending on the version, `searoute` may return either:
      • a geojson.Feature-like object with `.properties` attribute, or
      • a plain `dict` with a `"properties"` key.

    This helper handles both.
    """
    props = getattr(route, "properties", None)
    # print(route)
    if props is not None:
        return props
    return route["properties"]  # type: ignore[index]


def fetch_distance_km(
    a_name: str
    , a_lat: float
    , a_lon: float
    , b_name: str
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Compute sea distance (km) between two ports using `searoute`.

    If `searoute` raises, fall back to Haversine×coastline_factor.
    """
    # searoute expects [lon, lat]
    origin = [a_lon, a_lat]
    destination = [b_lon, b_lat]

    try:
        # units="km" → distance in kilometres in `properties["length"]`
        route = sr.searoute(origin, destination, units="km")
        props = _route_properties(route)
        length = float(props["length"])
        return length

    except Exception as exc:  # pragma: no cover  (safety net)
        print(
            f"⚠️  searoute failed for '{a_name}' → '{b_name}': {exc!r}\n"
            f"   Falling back to Haversine×coastline_factor={COASTLINE_FACTOR}."
        )
        return _fallback_distance_km(a_lat, a_lon, b_lat, b_lon)


# ───────────────────────────── build matrix ───────────────────────────────
def build_matrix() -> pd.DataFrame:
    """
    Build a symmetric DataFrame of sea distances (km) between all ports.
    """
    names = [name for (name, _, _) in port_list]
    N = len(names)
    matrix_km = pd.DataFrame(0.0, index=names, columns=names, dtype=float)

    # Fill the diagonal explicitly for clarity
    for name in names:
        matrix_km.at[name, name] = 0.0

    total_pairs = math.comb(N, 2) if N >= 2 else 0
    done = 0

    print(f"▶ Building sea-distance matrix for {N} ports ({total_pairs} pairs)...")

    # combinations() → each unordered pair once (no need for manual cache)
    for (na, la, loa), (nb, lb, lob) in it.combinations(port_list, 2):
        print(na, la, loa, nb, lb, lob)
        done += 1
        dist_km = fetch_distance_km(na, la, loa, nb, lb, lob)
        matrix_km.at[na, nb] = dist_km
        matrix_km.at[nb, na] = dist_km

        if done % 10 == 0 or done == total_pairs:
            print(f"  • processed {done}/{total_pairs} pairs", flush=True)

    print("✔ Matrix build complete.")
    return matrix_km


# ───────────────────────────── persist outputs ────────────────────────────
def main() -> None:
    matrix_km = build_matrix()

    outdir = Path(ROOT) / "data" / "processed" / "cabotage_data"
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "sea_matrix.csv"
    json_path = outdir / "sea_matrix.json"

    # Uncomment if you want the CSV as well
    # matrix_km.to_csv(csv_path, float_format="%.3f", encoding="utf-8")

    searoute_version = getattr(sr, "__version__", None)
    method = (
          "searoute_py"
        + (f"_{searoute_version}" if searoute_version else "")
    )

    names = list(matrix_km.index)

    payload: Dict[str, Any] = {
          "unit": "km"
        , "method": method
        , "coastline_factor": COASTLINE_FACTOR
        , "note": (
            "Off-diagonal entries are sea distances (km) between port "
            "centroids; symmetric. Distances computed with `searoute`; "
            "Haversine×coastline_factor used only as a fallback."
        )
        , "matrix": {
              r: {c: float(matrix_km.at[r, c]) for c in names}
              for r in names
          }
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # print(f"✓ Saved {csv_path}")
    print(f"✅ Saved {json_path}")


if __name__ == "__main__":
    main()
