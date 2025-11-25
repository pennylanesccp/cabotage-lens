# modules/plot/cabotage_plot_helper.py
# -*- coding: utf-8 -*-

"""
Cabotage Route Renderer (Dynamic).
==================================

Generates visual path coordinates for sea legs that follow the Brazilian coast.
Instead of a straight line, it routes through an ordered sequence of known ports,
creating a realistic "arc" effect.

Logic:
  1. Load all ports from JSON.
  2. Sort them into a single linear sequence ("Coastal Highway"):
     - South of Natal (~-5.5 lat): Ordered South -> North (increasing Lat).
     - North of Natal: Ordered East -> West (decreasing Lon).
  3. Routing A->B finds the slice of ports between A and B in this sequence.
"""

import json
import math
from pathlib import Path
from typing import List, Tuple, Any

# ────────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────────

# "The Corner" of Brazil (approx Natal/Touros).
# Divides the North coast (Amazon) from the East/South coast.
CORNER_LAT = -5.5

# Default path assumption (relative to repo root when running as module)
_DEFAULT_PORTS_PATH = Path("data/processed/cabotage_data/ports_br.json")

# Global cache for the sorted waypoints
_COASTAL_WAYPOINTS: List[Tuple[float, float]] = []


# ────────────────────────────────────────────────────────────────────────────────
# Sorting Logic
# ────────────────────────────────────────────────────────────────────────────────

def _get_sort_key(port: dict) -> float:
    """
    Assign a sorting score to a port to linearize the Brazilian coast.
    
    Sequence:
    1. South (-33) -> North (-5.5): Score based on Latitude (0 to ~28).
    2. North (-5.5) -> West (-60): Score based on Longitude (starts higher to append).
    """
    lat = float(port["lat"])
    lon = float(port["lon"])
    
    # Shift coords to be positive-ish for easier mental math, though not strictly needed
    
    if lat < CORNER_LAT:
        # SEGMENT 1: Southern/Eastern Coast (Rio Grande -> Natal)
        # Order: South to North.
        # Score = Latitude itself (e.g. -32 is "smaller/earlier" than -20)
        # We normalize it to be the first segment.
        return lat
    else:
        # SEGMENT 2: Northern Coast (Natal -> Manaus)
        # Order: East to West.
        # Natal is approx -35 lon, Manaus is -60 lon.
        # We want Natal to be "after" the southern coast, and Manaus last.
        # So we sort by -Longitude (or similar).
        
        # Let's map Longitude (-35 to -60) to a Score > 0 (Lat is < 0).
        # Lon -35 -> Score 35
        # Lon -60 -> Score 60
        # This puts East (Natal) before West (Manaus).
        return 1000.0 + abs(lon)


def _load_waypoints(json_path: Path = _DEFAULT_PORTS_PATH) -> List[Tuple[float, float]]:
    """
    Load ports from JSON and return them as a sorted list of (lat, lon) tuples.
    """
    # Try to find the file. If running from 'apps/', root is up one level.
    if not json_path.exists():
        # Fallback check: are we in repo root?
        alt = Path("data/processed/cabotage_data/ports_br.json")
        if alt.exists():
            json_path = alt
        else:
            # Fallback check: are we in 'apps/'?
            alt2 = Path("../data/processed/cabotage_data/ports_br.json")
            if alt2.exists():
                json_path = alt2
    
    if not json_path.exists():
        # Hard fallback if file completely missing (prevents crash in GUI)
        return [
            (-32.03, -52.09), # Rio Grande
            (-23.95, -46.32), # Santos
            (-22.90, -43.16), # Rio
            (-12.96, -38.51), # Salvador
            (-8.06,  -34.87), # Recife
            (-3.71,  -38.47), # Fortaleza
            (-1.44,  -48.50), # Belém
            (-3.15,  -60.00), # Manaus
        ]

    with open(json_path, "r", encoding="utf-8") as f:
        ports = json.load(f)

    # Sort by our custom coastal logic
    sorted_ports = sorted(ports, key=_get_sort_key)
    
    # Extract coordinates
    waypoints = [(float(p["lat"]), float(p["lon"])) for p in sorted_ports]
    
    return waypoints


def _ensure_waypoints():
    """Singleton loader."""
    global _COASTAL_WAYPOINTS
    if not _COASTAL_WAYPOINTS:
        _COASTAL_WAYPOINTS = _load_waypoints()
    return _COASTAL_WAYPOINTS


# ────────────────────────────────────────────────────────────────────────────────
# Routing Logic
# ────────────────────────────────────────────────────────────────────────────────

def _dist_sq(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def _find_nearest_idx(lat, lon, points):
    best_i = -1
    best_d = float("inf")
    for i, p in enumerate(points):
        d = _dist_sq((lat, lon), p)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i

def get_visual_sea_path(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> List[Tuple[float, float]]:
    """
    Return a list of coordinates representing the sea path.
    Snaps start/end to the "Coastal Highway" and fills the gap.
    """
    highway = _ensure_waypoints()
    
    idx_start = _find_nearest_idx(start_coords[0], start_coords[1], highway)
    idx_end = _find_nearest_idx(end_coords[0], end_coords[1], highway)
    
    path = [start_coords]
    
    # If valid indices found and they are distinct
    if idx_start != -1 and idx_end != -1 and idx_start != idx_end:
        step = 1 if idx_end > idx_start else -1
        
        # Traverse the highway from nearest start to nearest end
        # We include idx_start to "pull" the route to the coast immediately
        # We do NOT include idx_end here because we append exact end_coords last
        
        current = idx_start
        while current != idx_end:
            path.append(highway[current])
            current += step
        
        # Add the final highway point (nearest to dest)
        path.append(highway[idx_end])
        
    path.append(end_coords)
    return path