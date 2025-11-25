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
CORNER_LAT = -5.2

# Default path assumption (relative to repo root when running as module)
_DEFAULT_PORTS_PATH = Path("data/processed/cabotage_data/ports_br.json")

# Critical "turning points" to force the route shape around land masses.
# These are inserted into the sorted sequence based on their geography.
# Format: (lat, lon, label)
_FIXED_WAYPOINTS = [
]

# Global cache for the sorted waypoints
_COASTAL_PATH: List[Tuple[float, float]] = []


# ────────────────────────────────────────────────────────────────────────────────
# Sorting Logic
# ────────────────────────────────────────────────────────────────────────────────

def _get_coastal_score(lat: float, lon: float) -> float:
    """
    Assign a 'score' representing linear distance along the coast from South to North-West.
    
    Sequence: South -> North (East Coast) -> West (North Coast/Amazon).
    """
    # The "Corner" is roughly at Latitude -5.2 (Touros, RN)
    if lat < CORNER_LAT:
        # ZONE 1: East Coast (South -> North)
        # Score increases as Latitude increases (moves North toward 0).
        # Range: -34 (South) to -5.2 (Natal)
        # Score: 0 to ~29
        return lat + 40.0
    else:
        # ZONE 2: North Coast (Natal -> Amazon)
        # Score increases as Longitude decreases (moves West toward -60).
        # We start adding from the max score of Zone 1 (~35).
        # Lon -34 (Natal) -> Lon -60 (Manaus).
        # We use abs(lon) to make it positive and additive.
        return 40.0 + abs(lon)


def _load_waypoints(json_path: Path = _DEFAULT_PORTS_PATH) -> List[Tuple[float, float]]:
    """
    Load ports + fixed waypoints and sort them into a single line.
    """
    # Robust path resolution
    if not json_path.exists():
        alt = Path("data/processed/cabotage_data/ports_br.json")
        if alt.exists():
            json_path = alt
        else:
            alt2 = Path("../data/processed/cabotage_data/ports_br.json")
            if alt2.exists():
                json_path = alt2
    
    points = []
    
    # 1. Add Ports from JSON
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            ports = json.load(f)
            for p in ports:
                points.append( (float(p["lat"]), float(p["lon"])) )
    
    # 2. Add Fixed Waypoints (Virtual Turnpoints)
    for lat, lon, _ in _FIXED_WAYPOINTS:
        points.append((lat, lon))
        
    # 3. Sort everything by "Coastal Score"
    # This interleaves the ports and virtual waypoints into one valid sequence
    points.sort(key=lambda p: _get_coastal_score(p[0], p[1]))
    
    return points


def _ensure_path():
    """Singleton loader."""
    global _COASTAL_PATH
    if not _COASTAL_PATH:
        _COASTAL_PATH = _load_waypoints()
    return _COASTAL_PATH


# ────────────────────────────────────────────────────────────────────────────────
# Routing Logic
# ────────────────────────────────────────────────────────────────────────────────

def _dist_sq(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def _find_nearest_idx(lat, lon, points):
    """Find index of the closest point on the highway."""
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
    highway = _ensure_path()
    
    # Snap inputs to the nearest points on our sorted line
    idx_start = _find_nearest_idx(start_coords[0], start_coords[1], highway)
    idx_end = _find_nearest_idx(end_coords[0], end_coords[1], highway)
    
    path = [start_coords]
    
    if idx_start != -1 and idx_end != -1 and idx_start != idx_end:
        step = 1 if idx_end > idx_start else -1
        
        # Traverse the highway from [nearest start] to [nearest end]
        current = idx_start
        
        # Include the start anchor immediately to pull the line to the coast
        if current != idx_start:
             path.append(highway[current])
             
        while current != idx_end:
            path.append(highway[current])
            current += step
        
        # Add the final highway point
        path.append(highway[idx_end])
        
    path.append(end_coords)
    return path

# Smoke test
if __name__ == "__main__":
    print("--- Dynamic Route Renderer Test ---")
    path = _load_waypoints()
    print(f"Loaded {len(path)} total waypoints (Ports + Virtual).")
    
    print("\nSorted Sequence Sample:")
    for p in path:
        # Simple visualization of the sort
        if p[0] < -20: print(f"  South: {p}")
        elif p[0] < -5: print(f"  East:  {p}")
        else:           print(f"  North: {p}")
            
    # Test: Santos -> Manaus
    route = get_visual_sea_path((-23.95, -46.32), (-3.1, -60.0))
    print(f"\nRoute Santos->Manaus has {len(route)} points.")