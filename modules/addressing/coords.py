# modules/addressing/coords.py
# -*- coding: utf-8 -*-

"""
Coordinate Utilities.
=====================

Helpers for parsing, validating, and normalizing geographic coordinates
from various input formats (strings, ORS/Pelias JSON responses).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Path Bootstrap (for direct execution)
if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

# Standard Pelican/ORS layers usually considered "valid" for an address search
_ALLOWED_LAYERS_DEFAULT = {
    "address", "street", "venue", "postalcode", "postcode",
    "neighbourhood", "locality", "localadmin", "borough", "municipality"
}

# Brazil Centroid Approximate Bounds (to reject generic "Brazil" matches)
# Approx Lat: -10 to -15, Lon: -50 to -55 depending on the provider's "center"
# We use a specific point often returned by ORS for "Brazil": ~(-14.2, -51.9)
# But the provided logic was: abs(lat + 10.0) < 0.5 ...
# We will implement a configurable rejection logic.

# ────────────────────────────────────────────────────────────────────────────────
# Parsing Logic
# ────────────────────────────────────────────────────────────────────────────────

def parse_lat_lon_string(text: Any) -> Optional[Tuple[float, float]]:
    """
    Try to extract a (lat, lon) tuple from a string.
    
    Accepts: "-23.5, -46.6" or " -23.5 , -46.6 "
    Returns: (lat, lon) as floats, or None if invalid.
    """
    if not isinstance(text, str):
        return None

    # Regex: start, optional whitespace, number, comma, number, optional whitespace, end
    # Captures floats like -23.5, 10, +5.2
    pattern = r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$"
    match = re.match(pattern, text.strip())
    
    if not match:
        return None

    try:
        lat = float(match.group(1))
        lon = float(match.group(2))

        # Basic sanity check for WGS84
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            _log.warning(f"Parsed coords out of bounds: {lat}, {lon}")
            return None

        return lat, lon
    except ValueError:
        return None


def reject_brazil_centroid(lat: float, lon: float) -> bool:
    """
    Check if a point is suspiciously close to the geometric center of Brazil.
    ORS often returns this when it can't find a specific address in Brazil.
    """
    # Heuristic: Brazil center is roughly -14.2350, -51.9253
    # The previous logic was: abs(lat + 10.0) < 0.5 (near -10) and abs(lon + 55.0) < 0.5 (near -55)
    # We will accept the provided logic but log it.
    
    # Check for the "generic" Brazil centroid often used by Geocoders
    # (Specific implementation depends on what ORS returns for 'Brazil')
    if abs(lat - (-14.235)) < 1.0 and abs(lon - (-51.925)) < 1.0:
        return True
        
    # Keep legacy check if it was tuned for specific data
    if abs(lat + 10.0) < 0.5 and abs(lon + 55.0) < 0.5:
        return True
        
    return False


# ────────────────────────────────────────────────────────────────────────────────
# Normalization Logic
# ────────────────────────────────────────────────────────────────────────────────

def normalize_hit(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Flatten an ORS/Pelias result feature into a simple dict.
    
    Input (GeoJSON Feature):
        { "geometry": {"coordinates": [lon, lat]}, "properties": {"label": "..."} }
    
    OR Input (Flat Dict):
        { "lat": -23.5, "lon": -46.6, "label": "..." }

    Returns:
        { "lat": float, "lon": float, "label": str, "layer": str }
        OR None if invalid.
    """
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    # 1. Extract metadata
    props = raw.get("properties") or {}
    label = raw.get("label") or raw.get("name") or props.get("label") or props.get("name")
    layer = raw.get("layer") or props.get("layer") or "unknown"

    # 2. Extract coordinates (Priority: Top-level > Geometry)
    if "lat" in raw and "lon" in raw:
        # Flat format
        try:
            lat = float(raw["lat"])
            lon = float(raw["lon"])
        except (ValueError, TypeError):
            pass
    else:
        # GeoJSON format
        geom = raw.get("geometry") or {}
        coords = geom.get("coordinates") # [lon, lat]
        if coords and len(coords) >= 2:
            try:
                lon = float(coords[0])
                lat = float(coords[1])
            except (ValueError, TypeError):
                pass

    if lat is None or lon is None:
        return None

    return {
        "lat": lat, 
        "lon": lon, 
        "label": str(label), 
        "layer": str(layer).lower()
    }


def filter_hits(
    hits: Any,
    allowed_layers: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Process a list of raw geocoder results.
    
    1. Normalizes formats.
    2. Filters out 'country' level matches (too generic).
    3. Filters out centroids.
    4. Filters by allowed layers.
    """
    allowed = set(allowed_layers) if allowed_layers else _ALLOWED_LAYERS_DEFAULT
    
    # Normalize input container
    raw_list = []
    if isinstance(hits, list):
        raw_list = hits
    elif isinstance(hits, dict):
        # Handle ORS response wrapper {"features": [...]}
        raw_list = hits.get("features") or [hits]
    
    valid_hits = []

    for item in raw_list:
        # Handle potential double-encoded JSON strings
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                continue

        if not isinstance(item, dict):
            continue

        norm = normalize_hit(item)
        if not norm:
            continue

        lat, lon = norm["lat"], norm["lon"]
        layer = norm["layer"]

        # -- Filters --
        if layer == "country":
            _log.debug(f"Rejecting country match: {norm['label']}")
            continue
            
        if reject_brazil_centroid(lat, lon):
            _log.debug(f"Rejecting centroid match: {lat}, {lon}")
            continue
            
        if allowed and layer and layer not in allowed:
            _log.debug(f"Rejecting layer '{layer}': {norm['label']}")
            continue

        valid_hits.append(norm)

    return valid_hits


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging
    init_logging(level="DEBUG")
    
    print("--- Coords Smoke Test ---")
    
    # 1. Test Parsing
    s = " -23.5505 , -46.6333 "
    parsed = parse_lat_lon_string(s)
    print(f"Parsed '{s}': {parsed}")
    assert parsed == (-23.5505, -46.6333)

    # 2. Test Normalization (GeoJSON)
    geojson_feat = {
        "geometry": {"coordinates": [-46.6, -23.5]},
        "properties": {"label": "Test Point", "layer": "venue"}
    }
    norm = normalize_hit(geojson_feat)
    print(f"Normalized GeoJSON: {norm}")
    assert norm["lat"] == -23.5
    
    # 3. Test Filtering
    bad_hits = [
        {"lat": -14.235, "lon": -51.925, "layer": "country"}, # Brazil centroid
        {"lat": 0, "lon": 0, "layer": "ocean"}               # Wrong layer
    ]
    filtered = filter_hits(bad_hits + [geojson_feat])
    print(f"Filtered count: {len(filtered)} (expected 1)")
    assert len(filtered) == 1

    print("--- Done ---")