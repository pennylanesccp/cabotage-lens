#!/usr/bin/env python3
# calcs/build_distance_matrix.py
# -*- coding: utf-8 -*-

"""
Port-to-port sea-distance matrix (km, Geografos + searoute fallback, with aliases)
==================================================================================

Builds a symmetric matrix of sea distances between all Brazilian cabotage ports
defined in ``data/processed/cabotage_data/ports_br.json``.

Distance source priority
------------------------
Para cada par NÃO ordenado de portos (A, B):

  1) Tenta Geografos com TODAS as combinações possíveis de slugs:

       • slugs de A (nome principal + aliases) × slugs de B (nome principal + aliases)
       • para cada par (slug_a, slug_b), tenta as duas URLs:

           https://www.geografos.com.br/viagem-maritima-entre-portos-brasil/
               distancia-entre-{slug_a}-e-{slug_b}.php

           https://www.geografos.com.br/viagem-maritima-entre-portos-brasil/
               distancia-entre-{slug_b}-e-{slug_a}.php

     Até encontrar uma página que contenha algo como:

         "Distância: 198 Km ou 107 Milhas Náuticas"

     Usamos esse valor de km como distância marítima.

  2) Se todas as combinações de slugs falharem (erro HTTP, timeout, parse error, etc.),
     caímos para o `searoute`:

         route = searoute.searoute([lon_a, lat_a], [lon_b, lat_b], units="km")
         km = route.properties["length"]

  3) Se até o searoute falhar, a função levanta uma exceção.

Coordinates
-----------
Para coordenadas, preferência:

  1) Coordenadas de gate, se existirem:
       - p["gate_lat"] / p["gate_lon"], ou
       - p["gate"]["lat"] / p["gate"]["lon"]
  2) Caso contrário: p["lat"] / p["lon"]

Aliases
-------
Este script suporta aliases no JSON de portos. Para cada porto, consideramos:

  • p["geografos_slug"]          → string única ou lista de slugs explícitos.
  • p["aliases"], p["alias"],
    p["aka"], p["geografos_aliases"]
      → podem ser string única ou lista de nomes alternativos.

Para cada alias que for um NOME (não slug), geramos o slug com a mesma função que
usamos para o nome principal (lowercase, sem acento, etc.).

Output
------
Salva um JSON em:

    data/processed/cabotage_data/sea_matrix.json

no formato:

    {
      "unit": "km",
      "method": "geografos_plus_searoute_v2_aliases",
      "note": "Off-diagonal entries are sea distances (km) between ports; symmetric.",
      "ports": [
        {
          "name": "...",
          "slug": "...",
          "slug_candidates": ["...", "..."],
          "lat": ...,
          "lon": ...
        },
        ...
      ],
      "matrix": {
        "Port A": {"Port A": 0.0, "Port B": 123.4, ...},
        "Port B": {"Port A": 123.4, "Port B": 0.0, ...},
        ...
      }
    }

Env-tunable knobs
-----------------
• SEA_MATRIX_DEBUG = "1" → debug verbose no stdout.
• GEOGRAFOS_TIMEOUT = segundos (default: 12.0).
• SEA_MATRIX_SLEEP = segundos de sleep entre chamadas HTTP bem-sucedidas (default: 0.0).

Requirements
------------
pip install:

    requests
    beautifulsoup4
    pandas
    searoute
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
import searoute as sr


# ───────────────────────────── debug flag ────────────────────────────────
DEBUG = os.getenv("SEA_MATRIX_DEBUG", "0") == "1"


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

ports_raw: List[Dict[str, Any]] = load_ports(PORTS_PATH)


def _resolve_port_coords(port: Dict[str, Any]) -> Tuple[float, float]:
    """
    Return (lat, lon) for a port, preferring gate coordinates if available.

    Priority:
      1) port["gate_lat"], port["gate_lon"]
      2) port["gate"]["lat"], port["gate"]["lon"]
      3) port["lat"], port["lon"]

    Raises ValueError if nothing usable is found.
    """
    gate_lat = port.get("gate_lat")
    gate_lon = port.get("gate_lon")
    if gate_lat is not None and gate_lon is not None:
        return float(gate_lat), float(gate_lon)

    gate = port.get("gate")
    if isinstance(gate, dict):
        g_lat = gate.get("lat")
        g_lon = gate.get("lon")
        if g_lat is not None and g_lon is not None:
            return float(g_lat), float(g_lon)

    lat = port.get("lat")
    lon = port.get("lon")
    if lat is not None and lon is not None:
        return float(lat), float(lon)

    raise ValueError(f"No usable coordinates for port: {port!r}")


def _strip_accents(text: str) -> str:
    """
    Remove accents/diacritics from a Unicode string.
    """
    norm = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def _default_geografos_slug(name: str) -> str:
    """
    Derive a Geografos-style slug from a human-readable port name.

    Example:
      "Porto de Santos"                 → "porto-santos"
      "Porto do Rio de Janeiro"         → "porto-rio-de-janeiro"
      "Porto de São Francisco do Sul"   → "porto-sao-francisco-do-sul"

    Logic:
      1) Lowercase + accent stripping.
      2) Strip Portuguese articles/prepositions that Geografos often omits
         from between "porto" and the city name ("de", "do", "da", "dos", "das").
      3) Ensure a canonical "porto <rest>" base string.
      4) Replace spaces/underscores with hyphens, drop other punctuation.
    """
    if not name:
        return ""

    txt = _strip_accents(name).lower().strip()

    prefixes = [
          "porto de "
        , "porto do "
        , "porto da "
        , "porto dos "
        , "porto das "
        , "porto "
    ]

    rest = None
    for pref in prefixes:
        if txt.startswith(pref):
            rest = txt[len(pref):].strip()
            break

    if rest is None:
        base = txt
    else:
        base = f"porto {rest}"

    chars: List[str] = []
    for ch in base:
        if ch.isalnum():
            chars.append(ch)
        elif ch in (" ", "-", "_"):
            chars.append("-")

    slug = "".join(chars)
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug


def _ensure_list_str(value: Any) -> List[str]:
    """
    Normalize a value to a list[str].

    • None              → []
    • "foo"             → ["foo"]
    • ["foo", "bar"]    → ["foo", "bar"]
    • other types       → []
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
        return out
    return []


def _build_port_list() -> List[Dict[str, Any]]:
    """
    Return a stable list of port dicts:

        {
          "name": "...",
          "slug": "...",             # primary slug
          "slug_candidates": [...],  # primary + aliases
          "lat": ...,
          "lon": ...
        }

    using gate coordinates when present and allowing manual 'geografos_slug'
    overrides and aliases from the JSON.

    Alias logic:
      • Alias names that do NOT start with "Porto " (case/accents ignored)
        are first wrapped as "Porto de {alias}" before slugification.
    """
    port_list: List[Dict[str, Any]] = []

    alias_fields = [
          "aliases"
        , "alias"
        , "aka"
        , "geografos_aliases"
    ]

    for p in ports_raw:
        name = p.get("name") or p.get("label") or "UNKNOWN_PORT"
        lat, lon = _resolve_port_coords(p)

        # 1) Primary slug override from JSON, if present
        geog_slug_raw = p.get("geografos_slug")
        geog_slugs_explicit = _ensure_list_str(geog_slug_raw)

        if geog_slugs_explicit:
            primary_slug = geog_slugs_explicit[0]
        else:
            primary_slug = _default_geografos_slug(name)

        # 2) Alias names (to be slugified, forcing "Porto de " when missing)
        alias_names: List[str] = []
        for field in alias_fields:
            alias_names.extend(_ensure_list_str(p.get(field)))

        alias_slugs: List[str] = []
        for alias_name in alias_names:
            alias_name = alias_name.strip()
            if not alias_name:
                continue

            # Normalize to check if it already starts with "porto "
            base_no_acc = _strip_accents(alias_name).lower().strip()
            if not base_no_acc.startswith("porto "):
                # If alias is just "Angra dos Reis", treat it as "Porto de Angra dos Reis"
                alias_full = f"Porto de {alias_name}"
            else:
                alias_full = alias_name

            alias_slugs.append(_default_geografos_slug(alias_full))

        # 3) Explicit alias slugs (if geog_slugs_explicit has more than one,
        #    or if geografos_aliases already contained slug-like strings).
        slug_candidates_raw: List[str] = [
              primary_slug
            , *geog_slugs_explicit
            , *alias_slugs
        ]

        # 4) Deduplicate while preserving order and dropping empty strings
        seen: set[str] = set()
        slug_candidates: List[str] = []
        for s in slug_candidates_raw:
            s_norm = s.strip()
            if not s_norm:
                continue
            if s_norm in seen:
                continue
            seen.add(s_norm)
            slug_candidates.append(s_norm)

        port_dict = {
              "name": name
            , "slug": primary_slug
            , "slug_candidates": slug_candidates
            , "lat": float(lat)
            , "lon": float(lon)
        }

        port_list.append(port_dict)

        _debug(
            f"[PORT] {name!r} → primary_slug={primary_slug!r}, "
            f"candidates={slug_candidates!r}, coords=({lat}, {lon})"
        )

    return port_list


ports: List[Dict[str, Any]] = _build_port_list()


# ───────────────────────────── searoute helper ───────────────────────────
def _route_properties(route: Any) -> Dict[str, Any]:
    """
    Normalise access to the `properties` of the object returned by `searoute`.

    Depending on the version, `searoute` may return either:
      • a geojson.Feature-like object with `.properties` attribute, or
      • a plain `dict` with a `"properties"` key.
    """
    props = getattr(route, "properties", None)
    if props is not None:
        return props
    return route["properties"]  # type: ignore[index]


def _searoute_distance_km(
    a_name: str
    , a_lat: float
    , a_lon: float
    , b_name: str
    , b_lat: float
    , b_lon: float
) -> float:
    """
    Compute sea distance (km) between two ports using `searoute`.

    Raises if searoute fails.
    """
    origin = [a_lon, a_lat]
    destination = [b_lon, b_lat]

    route = sr.searoute(origin, destination, units="km")
    props = _route_properties(route)
    length = float(props["length"])

    _debug(
        f"[searoute] {a_name} ↔ {b_name}: {length:.1f} km "
        "(fallback after Geografos failure)"
    )
    return length


# ───────────────────────────── Geografos helpers ─────────────────────────
BASE_URL = (
    "https://www.geografos.com.br"
    "/viagem-maritima-entre-portos-brasil"
)

REQUEST_HEADERS = {
      "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    , "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    )
    , "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
    , "Connection": "keep-alive"
}

REQUEST_TIMEOUT = float(os.getenv("GEOGRAFOS_TIMEOUT", "2.0"))
SLEEP_SECONDS = float(os.getenv("SEA_MATRIX_SLEEP", "0.0"))


def _build_geografos_urls(slug_a: str, slug_b: str) -> List[str]:
    """
    Return the two possible URL permutations for a slug pair (A, B).

    Geografos uses URLs like:

      /distancia-entre-{slug_a}-e-{slug_b}.php
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

    strong_tags = soup.find_all("strong")
    for tag in strong_tags:
        txt = tag.get_text(strip=True)
        if "Distância:" not in txt:
            continue

        # Example: "Distância: 198 Km ou 107 Milhas Náuticas"
        m = re.search(r"Distância:\s*([\d.,]+)\s*Km", txt)
        if not m:
            continue

        raw = m.group(1)
        cleaned = raw.replace(".", "").replace(",", ".")
        return float(cleaned)

    raise RuntimeError("Could not find distance pattern in Geografos HTML")


# Cache for Geografos distances (by unordered slug pair)
_geografos_cache: Dict[Tuple[str, str], float] = {}


def _geografos_distance_km(
    slugs_a: List[str]
    , slugs_b: List[str]
) -> float:
    """
    Try to fetch distance (km) from Geografos for an unordered pair of
    slug candidate lists.

    For each (slug_a, slug_b) combination:

      1) Check the cache for the unordered pair.
      2) Try both URL permutations (A-B, B-A).

    If one succeeds, cache the result and return it.
    If all fail, raises RuntimeError.
    """
    last_error: Exception | None = None

    # Normalize candidates: drop empties
    cand_a = [s for s in slugs_a if s]
    cand_b = [s for s in slugs_b if s]

    for slug_a in cand_a:
        for slug_b in cand_b:
            key = tuple(sorted((slug_a, slug_b)))
            if key in _geografos_cache:
                return _geografos_cache[key]

            for url in _build_geografos_urls(slug_a, slug_b):
                try:
                    resp = requests.get(
                          url
                        , headers=REQUEST_HEADERS
                        , timeout=REQUEST_TIMEOUT
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"HTTP {resp.status_code} for {url}")

                    km = _parse_km_from_html(resp.text)
                    _geografos_cache[key] = km

                    _debug(
                        f"[Geografos] {slug_a} ↔ {slug_b}: "
                        f"{km:.1f} km @ {url}"
                    )

                    if SLEEP_SECONDS > 0:
                        time.sleep(SLEEP_SECONDS)

                    return km

                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    _debug(
                        f"[Geografos] Failed for {slug_a} ↔ {slug_b} "
                        f"via {url!r}: {exc!r}"
                    )
                    continue

    raise RuntimeError(
        "Geografos distance not available for slug candidates "
        f"{cand_a!r} ↔ {cand_b!r} (last error: {last_error!r})"
    )


# ───────────────────────────── distance dispatcher ───────────────────────
_distance_cache: Dict[Tuple[float, float, float, float], float] = {}


def fetch_distance_km(
    a: Dict[str, Any]
    , b: Dict[str, Any]
) -> float:
    """
    Compute sea distance (km) between two port dicts (with name, slug, lat, lon).

    Priority:
      1) Geografos (all slug candidate combinations, both URL permutations).
      2) searoute (using gate/centroid coordinates).

    No Haversine / coastline factor. Raises if both fail.
    """
    a_name = a["name"]
    b_name = b["name"]
    a_lat = a["lat"]
    a_lon = a["lon"]
    b_lat = b["lat"]
    b_lon = b["lon"]
    slugs_a = a.get("slug_candidates", [a.get("slug", "")])
    slugs_b = b.get("slug_candidates", [b.get("slug", "")])

    # Coordinate-based symmetric cache for searoute fallback
    coord_key = tuple(
        sorted(
            [
                (round(a_lat, 6), round(a_lon, 6)),
                (round(b_lat, 6), round(b_lon, 6)),
            ]
        )
    )  # type: ignore[assignment]

    # 1) Try Geografos with aliases
    try:
        km = _geografos_distance_km(slugs_a, slugs_b)
        _debug(
            f"[DIST] {a_name} ↔ {b_name}: {km:.1f} km (Geografos, with aliases)"
        )
        return km

    except Exception as exc_geo:  # noqa: BLE001
        _debug(
            f"⚠️  Geografos distance not available for "
            f"'{a_name}' ↔ '{b_name}' "
            f"(last error: {exc_geo!r}); falling back to searoute."
        )

    # 2) Fallback: searoute
    if coord_key in _distance_cache:
        return _distance_cache[coord_key]

    km = _searoute_distance_km(
          a_name
        , a_lat
        , a_lon
        , b_name
        , b_lat
        , b_lon
    )
    _distance_cache[coord_key] = km
    return km


# ───────────────────────────── build matrix ───────────────────────────────
def build_matrix() -> pd.DataFrame:
    """
    Build a symmetric DataFrame of sea distances (km) between all ports.
    """
    names = [p["name"] for p in ports]
    N = len(names)
    matrix_km = pd.DataFrame(0.0, index=names, columns=names, dtype=float)

    for name in names:
        matrix_km.at[name, name] = 0.0

    total_pairs = math.comb(N, 2) if N >= 2 else 0
    done = 0

    print(f"▶ Building sea-distance matrix for {N} ports ({total_pairs} pairs)...")

    for a_port, b_port in it.combinations(ports, 2):
        done += 1
        dist_km = fetch_distance_km(a_port, b_port)
        a_name = a_port["name"]
        b_name = b_port["name"]

        matrix_km.at[a_name, b_name] = dist_km
        matrix_km.at[b_name, a_name] = dist_km

        if done % 10 == 0 or done == total_pairs:
            print(f"  • processed {done}/{total_pairs} pairs", flush=True)

    print("✔ Matrix build complete.")
    return matrix_km


# ───────────────────────────── persist outputs ────────────────────────────
def main() -> None:
    matrix_km = build_matrix()

    outdir = Path(ROOT) / "data" / "processed" / "cabotage_data"
    outdir.mkdir(parents=True, exist_ok=True)

    json_path = outdir / "sea_matrix.json"

    # Dict matrix: {name: {name: distance}}
    matrix_dict: Dict[str, Dict[str, float]] = {
        row_name: {
            col_name: float(matrix_km.at[row_name, col_name])
            for col_name in matrix_km.columns
        }
        for row_name in matrix_km.index
    }

    meta = {
          "unit": "km"
        , "method": "geografos_plus_searoute_v2_aliases"
        , "note": (
            "Off-diagonal entries are sea distances (km) between port "
            "centroids/gates, using Geografos (with aliases) when available "
            "and searoute otherwise; symmetric."
        )
        , "ports": ports
        , "matrix": matrix_dict
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"✔ Saved JSON matrix to {json_path}")


if __name__ == "__main__":
    main()
