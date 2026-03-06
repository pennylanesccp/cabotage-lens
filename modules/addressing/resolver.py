# modules/addressing/resolver.py
# -*- coding: utf-8 -*-

"""
Address Resolver.
=================

Converts diverse inputs (CEP, Lat/Lon string, Address text) into
resolved GeoPoint objects using OpenRouteService.
"""

from __future__ import annotations

import re
from typing import Any, Optional, TYPE_CHECKING

from modules.core.models import GeoPoint
from modules.addressing.coords import parse_lat_lon_string
from modules.addressing.text import ascii_place_text

# Use TYPE_CHECKING to avoid circular imports if strictly typing,
# but here we just import the client class for annotation.
if TYPE_CHECKING:
    from modules.road.ors import ORSClient
    from logging import Logger

# ────────────────────────────────────────────────────────────────────────────────
# Logic
# ────────────────────────────────────────────────────────────────────────────────

def resolve_point(
      value: Any
    , ors: ORSClient
    , log: Optional[Logger] = None
) -> Optional[GeoPoint]:
    """
    Resolve a raw input value into a GeoPoint.

    Strategies:
    1. If value is already a dict/GeoPoint with lat/lon -> return it.
    2. If value looks like "lat, lon" -> parse it.
    3. If value looks like a CEP -> structured geocode.
    4. Else -> free text geocode.
    """
    # 1. Pass-through (Already resolved)
    if hasattr(value, "lat") and hasattr(value, "lon"):
        return GeoPoint(
            lat=float(value.lat), 
            lon=float(value.lon), 
            uf=getattr(value, "uf", None), 
            label=ascii_place_text(getattr(value, "label", "Point"))
        )
    
    if isinstance(value, dict):
        lat = value.get("lat") or value.get("latitude")
        lon = value.get("lon") or value.get("longitude")
        if lat is not None and lon is not None:
            return GeoPoint(
                lat=float(lat), 
                lon=float(lon), 
                uf=value.get("uf"), # Can be None
                label=ascii_place_text(value.get("label", "Point"))
            )

    # 2. Coordinate String ("-23.5, -46.6")
    val_str = str(value).strip()
    coords = parse_lat_lon_string(val_str)
    if coords:
        return GeoPoint(
            lat=coords[0], 
            lon=coords[1], 
            uf=None, 
            label=ascii_place_text(val_str)
        )

    # 3. CEP (Postal Code) - regex check for 8 digits
    if re.match(r"^\d{5}-?\d{3}$", val_str):
        if log: log.debug(f"Resolving CEP: {val_str}")
        
        try:
            # New API returns List[Dict]
            features = ors.geocode_structured(postalcode=val_str, country="BR", size=1)
            if features:
                f = features[0]
                c = f["geometry"]["coordinates"] # [lon, lat]
                props = f.get("properties", {})
                
                # Try to extract state/region for UF
                uf = props.get("region_a") or props.get("region")
                label = ascii_place_text(props.get("label") or f"CEP {val_str}")
                
                return GeoPoint(lat=c[1], lon=c[0], uf=uf, label=label)
        except Exception as e:
            if log: log.warning(f"CEP geocode failed for {val_str}: {e}")

    # 4. Free Text
    try:
        if log: log.debug(f"Resolving text: {val_str}")
        features = ors.geocode_text(val_str, size=1)
        if features:
            f = features[0]
            c = f["geometry"]["coordinates"]
            props = f.get("properties", {})
            
            uf = props.get("region_a") or props.get("region")
            label = ascii_place_text(props.get("label") or val_str)
            
            return GeoPoint(lat=c[1], lon=c[0], uf=uf, label=label)
    except Exception as e:
        if log: log.warning(f"Text geocode failed for {val_str}: {e}")

    return None


def resolve_point_null_safe(
      value: Any
    , ors: ORSClient
    , log: Optional[Logger] = None
) -> Optional[GeoPoint]:
    """Wrapper that catches all exceptions and returns None on failure."""
    try:
        return resolve_point(value, ors, log)
    except Exception as e:
        if log: log.error(f"Fatal error resolving '{value}': {e}")
        return None
