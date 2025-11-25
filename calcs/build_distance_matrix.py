#!/usr/bin/env python3
# calcs/build_distance_matrix.py
# -*- coding: utf-8 -*-

"""
Port-to-port sea-distance matrix (km, using external maritime routing API)
=========================================================================

Builds a symmetric matrix of sea distances between all Brazilian cabotage ports
defined in ``data/processed/cabotage_data/ports_br.json``.

Routing backend
---------------
Distances are obtained from an **external maritime routing API** (HTTP),
configured via environment variables:

  • SEA_MATRIX_API_BASE  → base URL (default: "https://api.distance.tools")
  • SEA_MATRIX_API_KEY   → API key / token (required)

The code assumes an endpoint similar to:

    POST {SEA_MATRIX_API_BASE}/api/v2/distance/route/maritime

with a JSON payload like:

    {
      "route": [
        {"lat": <origin_lat>, "lon": <origin_lon>},
        {"lat": <dest_lat>,   "lon": <dest_lon>}
      ]
    }

and a response containing a "distance" object with a "kilometers" field:

    {
      "distance": {
        "kilometers": 1234.56,
        ...
      },
      ...
    }

⚠ IMPORTANT
-----------
You *must* adjust:

  • ``_MARITIME_PATH``
  • the JSON payload in ``_api_distance_km``
  • the parsing logic of the API response

to match the provider you actually choose (SeaRoutes, NavAPI, distance.tools, ...).
The rest of the script (matrix building, ports loading, fallback, JSON schema)
is independent of the specific provider.

Coordinates
-----------
For each port we choose coordinates in this order of preference:

  1) Gate coordinates, if available:
       - p["gate_lat"] / p["gate_lon"], or
       - p["gate"]["lat"] / p["gate"]["lon"]
  2) Fallback: p["lat"] / p["lon"]

If the routing API fails for some pair (network error, bad response, etc.),
we fall back to a Haversine great-circle distance multiplied by a coastline factor
to approximate coastal routing.

Output
------
Saves a JSON file at:

    data/processed/cabotage_data/sea_matrix.json

with structure:

    {
      "unit": "km",
      "method": "sea_matrix_api_<provider>_<version>",
      "coastline_factor": 1.18,
      "note": "Off-diagonal entries are sea distances (km) between port centroids/gates; symmetric.",
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
import requests


# ───────────────────────────── debug flag ────────────────────────────────
DEBUG = os.getenv("SEA_MATRIX_DEBUG", "0") == "1"


def _debug(msg: str) -> None:
    if DEBUG:
        print(msg)


# ──────────────────────────── HTTP config ────────────────────────────────
_API_BASE_DEFAULT = "https://api.distance.tools"
_MARITIME_PATH = "/api/v2/distance/route/maritime"  # ← adjust to your provider


def _get_api_base() -> str:
    base = os.getenv("SEA_MATRIX_API_BASE", _API_BASE_DEFAULT).rstrip("/")
    return base


def _get_api_key() -> str:
    key = os.getenv("SEA_MATRIX_API_KEY")
    if not key:
        raise SystemExit(
            "❌ SEA_MATRIX_API_KEY not set. Please export your maritime routing "
            "API key, e.g.:\n"
            "   export SEA_MATRIX_API_KEY='your-key-here'"
        )
    return key


_SESSION = requests.Session()


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


# Stable list of (label, lat, lon), using gate coords when present
port_list: List[Tuple[str, float, float]] = []
for p in ports:
    name = p.get("name") or p.get("label") or "UNKNOWN_PORT"
    lat, lon = _resolve_port_coords(p)
    port_list.append((name, lat, lon))


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


def _fallback_distance_km(
    a_lat: float
    , a_lon: float
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Approximate sea distance as Haversine × coastline factor.

    This is only used if the maritime routing API fails for some reason
    (e.g. network issues, invalid response).
    """
    hv = haversine_km(a_lat, a_lon, b_lat, b_lon)
    return hv * COASTLINE_FACTOR


# Cache to avoid recomputing distances for identical coord pairs
_route_cache: Dict[Tuple[float, float, float, float], float] = {}


def _cache_key(
    a_lat: float
    , a_lon: float
    , b_lat: float
    , b_lon: float
) -> Tuple[float, float, float, float]:
    """
    Build a symmetric cache key based on coordinates.
    We round a bit for stability but keep decent precision.
    """
    a = (round(a_lat, 7), round(a_lon, 7))
    b = (round(b_lat, 7), round(b_lon, 7))
    return tuple(sorted((a, b)))  # type: ignore[return-value]


# ───────────────────────────── API caller ────────────────────────────────
def _api_distance_km(
    a_lat: float
    , a_lon: float
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Call the external maritime routing API and return distance in km.

    This function is deliberately written to be easy to tweak for a specific
    provider. Adjust:

      • URL (base + path)
      • headers / auth
      • payload structure
      • response parsing

    to match your chosen API.
    """
    base = _get_api_base()
    key = _get_api_key()
    url = f"{base}{_MARITIME_PATH}"

    # Example payload for a distance.tools-like API:
    payload: Dict[str, Any] = {
          "route": [
              {
                  "lat": a_lat
                , "lon": a_lon
              }
            , {
                  "lat": b_lat
                , "lon": b_lon
              }
          ]
    }

    headers = {
          "Authorization": f"Bearer {key}"
        , "Content-Type": "application/json"
        , "Accept": "application/json"
    }

    _debug(f"[HTTP] POST {url} payload={payload}")

    resp = _SESSION.post(
          url
        , headers=headers
        , json=payload
        , timeout=60
    )

    if not resp.ok:
        raise RuntimeError(
            f"HTTP {resp.status_code} from maritime API: {resp.text[:200]}"
        )

    data = resp.json()

    # Example parsing: adjust to your provider
    try:
        distance_km = float(data["distance"]["kilometers"])
    except Exception as exc:
        raise RuntimeError(
            f"Unexpected maritime API response structure: {data!r}"
        ) from exc

    _debug(f"[API] distance = {distance_km:.3f} km")
    return distance_km


def fetch_distance_km(
    a_name: str
    , a_lat: float
    , a_lon: float
    , b_name: str
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Compute sea distance (km) between two ports using an external
    maritime routing API.

    If the API call fails for any reason, fall back to Haversine×coastline_factor.

    We also cache by coordinates so identical coord pairs across different
    labels don't hit the API repeatedly.
    """
    key = _cache_key(a_lat, a_lon, b_lat, b_lon)
    if key in _route_cache:
        return _route_cache[key]

    try:
        length = _api_distance_km(a_lat, a_lon, b_lat, b_lon)
        _route_cache[key] = length
        _debug(
            f"[sea-api] {a_name} → {b_name}: "
            f"{length:.1f} km (cached under {key})"
        )
        return length

    except Exception as exc:  # pragma: no cover  (safety net)
        _debug(
            f"⚠️  maritime API failed for '{a_name}' → '{b_name}': {exc!r}; "
            f"falling back to Haversine×{COASTLINE_FACTOR}"
        )
        length = _fallback_distance_km(a_lat, a_lon, b_lat, b_lon)
        _route_cache[key] = length
        return length


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

    for (na, la, loa), (nb, lb, lob) in it.combinations(port_list, 2):
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

    # csv_path = outdir / "sea_matrix.csv"
    json_path = outdir / "sea_matrix.json"

    # Uncomment if you want the CSV as well
    # matrix_km.to_csv(csv_path, float_format="%.3f", encoding="utf-8")

    # You can later customise `method` to reflect your provider + version
    provider = os.getenv("SEA_MATRIX_PROVIDER", "external_maritime_api")
    api_version = os.getenv("SEA_MATRIX_API_VERSION", "v1")
    method = f"{provider}_{api_version}"

    names = list(matrix_km.index)

    payload: Dict[str, Any] = {
          "unit": "km"
        , "method": method
        , "coastline_factor": COASTLINE_FACTOR
        , "note": (
            "Off-diagonal entries are sea distances (km) between port "
            "centroids/gates; symmetric. Distances computed with an external "
            "maritime routing API; Haversine×coastline_factor used only as a "
            "fallback."
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
