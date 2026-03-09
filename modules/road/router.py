#!/usr/bin/env python3
# modules/road/router.py
# -*- coding: utf-8 -*-

"""
Road Router Service & CLI.
==========================

Serves as the "Mother Module" for road legs.
- CLI: Precomputes routes from command line.
- Library: Exposes `get_or_create_leg` for other modules to fetch/calculate routes.
- Facade: Re-exports ORSClient/ORSConfig for convenience.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

# Path Bootstrap (for CLI usage)
if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import init_logging, get_logger
from modules.infra.database_manager import (
      db_session
    , ensure_main_table
    , get_run
    , upsert_run
    , delete_key
    , DEFAULT_DB_PATH
    , DEFAULT_TABLE
)
from modules.road.ors import ORSConfig, RateLimited, NoRoute, ORSClient
from modules.addressing.resolver import resolve_point_null_safe
from modules.addressing.text import ascii_place_text
from modules.infra.db.road_cache import normalize_profile, profile_is_hgv

_log = get_logger(__name__)

# --- Public API Exports ---
__all__ = [
    "get_or_create_leg",
    "ORSClient",
    "ORSConfig",
    "RateLimited",
    "NoRoute"
]


# ────────────────────────────────────────────────────────────────────────────────
# Public Service API
# ────────────────────────────────────────────────────────────────────────────────

def get_or_create_leg(
      ors: ORSClient
    , origin: Any
    , destiny: Any
    , *
    , profile: str = "driving-hgv"
    , fallback_to_car: bool = True
    , overwrite: bool = False
    , db_path: Path | str = DEFAULT_DB_PATH
    , table_name: str = DEFAULT_TABLE
) -> Dict[str, Any]:
    """
    The "One Stop Shop" for road legs.
    
    1. Checks DB for cached leg (unless overwrite=True).
    2. If missing, calls ORS API (with fallback strategy).
    3. Saves result to DB.
    4. Returns standardized dictionary with leg info.

    Parameters
    ----------
    ors : ORSClient
        Configured ORS client instance.
    origin, destiny : Any
        Can be strings ("Sao Paulo") or dicts ({"lat": -23.5, "lon": -46.6, "label": "..."}).
        Using dicts with explicit coords is preferred to avoid re-geocoding.
    """
    
    # 1. Normalize Inputs
    # We need string labels for DB lookups
    def _extract_label(val: Any) -> str:
        if isinstance(val, dict):
            return ascii_place_text(val.get("label") or val.get("input") or "Unknown")
        return ascii_place_text(val)

    origin_label = _extract_label(origin)
    destiny_label = _extract_label(destiny)
    requested_profile = normalize_profile(profile)

    # 2. Check Cache
    with db_session(db_path) as conn:
        ensure_main_table(conn, table_name=table_name)
        
        if overwrite:
            deleted = delete_key(
                conn,
                origin=origin_label,
                destiny=destiny_label,
                profile_requested=requested_profile,
                table_name=table_name,
            )
            _log.info(
                "Road cache overwrite: %s -> %s requested_profile=%s deleted=%d",
                origin_label,
                destiny_label,
                requested_profile,
                deleted,
            )
        else:
            row = get_run(
                conn,
                origin=origin_label,
                destiny=destiny_label,
                profile_requested=requested_profile,
                table_name=table_name,
            )
            if row and row.get("distance_km") is not None:
                _log.info(
                    "Road cache hit: %s -> %s requested_profile=%s used_profile=%s distance_km=%.3f",
                    origin_label,
                    destiny_label,
                    requested_profile,
                    row.get("profile_used") or requested_profile,
                    float(row["distance_km"]),
                )
                return {
                    "origin_name": row["origin"],
                    "destiny_name": row["destiny"],
                    "distance_km": row["distance_km"],
                    "is_hgv": row["is_hgv"],
                    "profile_requested": row["profile_requested"],
                    "profile_used": row.get("profile_used") or requested_profile,
                    "cached": True,
                    "source": "cache",
                }

    # 3. Calculate Route (API)
    _log.info(
        "Road cache miss: %s -> %s requested_profile=%s",
        origin_label,
        destiny_label,
        requested_profile,
    )
    
    try:
        prof_used, dist_km = _calculate_route(ors, origin, destiny, requested_profile, fallback_to_car)
    except RateLimited:
        _log.critical("ORS Rate Limit Reached during leg calculation.")
        raise

    # Determine is_hgv flag
    is_hgv: Optional[bool] = None
    if dist_km is not None and prof_used:
        is_hgv = profile_is_hgv(prof_used)

    # 4. Persist to DB
    # We need coordinates for the DB. If inputs were dicts, use them. 
    # If strings, we rely on what ORS returned or resolved.
    # For simplicity here, we try to extract from input or leave None (DB allows NULL).
    def _get_coord(obj: Any, key: str) -> Optional[float]:
        if isinstance(obj, dict):
            return float(obj[key]) if obj.get(key) is not None else None
        return None

    if dist_km is not None:
        with db_session(db_path) as conn:
            upsert_run(
                conn,
                origin=origin_label,
                origin_lat=_get_coord(origin, "lat"),
                origin_lon=_get_coord(origin, "lon"),
                destiny=destiny_label,
                destiny_lat=_get_coord(destiny, "lat"),
                destiny_lon=_get_coord(destiny, "lon"),
                distance_km=dist_km,
                profile_requested=requested_profile,
                profile_used=prof_used,
                is_hgv=is_hgv,
                table_name=table_name,
            )
        _log.info(
            "Road distance cached: %s -> %s requested_profile=%s used_profile=%s distance_km=%.3f",
            origin_label,
            destiny_label,
            requested_profile,
            prof_used,
            float(dist_km),
        )
    else:
        _log.warning(
            "Routing returned no distance and will not be cached: %s -> %s requested_profile=%s",
            origin_label,
            destiny_label,
            requested_profile,
        )

    return {
        "origin_name": origin_label,
        "destiny_name": destiny_label,
        "distance_km": dist_km,
        "is_hgv": is_hgv,
        "profile_requested": requested_profile,
        "profile_used": prof_used,
        "cached": False,
        "source": "api",
    }


# ────────────────────────────────────────────────────────────────────────────────
# Internal Logic
# ────────────────────────────────────────────────────────────────────────────────

def _calculate_route(
      ors: ORSClient
    , origin: Any
    , destiny: Any
    , primary_profile: str
    , fallback: bool
) -> Tuple[Optional[str], Optional[float]]:
    """Try primary profile, fallback if needed. Returns (profile, km)."""
    profiles = [primary_profile]
    if fallback and primary_profile != "driving-car":
        profiles.append("driving-car")

    last_exc = None

    for prof in profiles:
        try:
            res = ors.route_road(origin, destiny, profile=prof)
            m = res.get("distance_m")
            km = m / 1000.0 if m is not None else None
            return prof, km
        except (NoRoute, Exception) as e:
            _log.debug(f"Route failed for {prof}: {e}")
            last_exc = e
            # If quota exceeded, bubble up immediately
            if "quota" in str(e).lower(): 
                raise RateLimited(str(e)) from e

    _log.warning(f"All profiles failed for leg. Last error: {last_exc}")
    return (profiles[-1] if profiles else None), None


# ────────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ────────────────────────────────────────────────────────────────────────────────

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Road Router CLI")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destiny", required=True)
    parser.add_argument("--ors-profile", default="driving-hgv")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    
    args = parser.parse_args(argv)
    init_logging(level=args.log_level)

    ors = ORSClient() # Config loaded from env/defaults

    # Resolve points first if they look like addresses, 
    # so we can pass clean objects to the logic
    # (The logic handles raw strings too, but resolving here gives us better control)
    p_origin = resolve_point_null_safe(args.origin, ors, _log) or args.origin
    p_destiny = resolve_point_null_safe(args.destiny, ors, _log) or args.destiny

    # For CLI, we want to pass dicts if resolved, to populate lat/lon in DB
    def _prep(p: Any, raw: str) -> Any:
        if hasattr(p, "lat"): # GeoPoint
            return {"lat": p.lat, "lon": p.lon, "label": p.label}
        return {"label": raw} # Fallback

    result = get_or_create_leg(
        ors, 
        origin=_prep(p_origin, args.origin),
        destiny=_prep(p_destiny, args.destiny),
        profile=args.ors_profile,
        overwrite=args.overwrite,
        db_path=args.db_path
    )

    if args.pretty:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))

    return 0

if __name__ == "__main__":
    # If no args are passed, run a smoke test automatically
    if len(sys.argv) == 1:
        print("--- Road Router Smoke Test (Auto-Mode) ---")
        test_argv = [
              "--origin", "Av. Paulista, 1578, São Paulo"
            , "--destiny", "Porto de Santos"
            , "--pretty"
            , "--log-level", "DEBUG"
        ]
        sys.exit(main(test_argv))
    
    sys.exit(main())
