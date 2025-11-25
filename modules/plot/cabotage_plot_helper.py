# modules/plot/cabotage_plot_helper.py
# -*- coding: utf-8 -*-

"""
Cabotage Route Renderer (Dynamic).
==================================

Generates visual path coordinates for sea legs that follow the Brazilian coast.
Instead of a straight line, it routes through an ordered sequence of known ports,
creating a realistic "arc" effect.
"""

import json
import math
from pathlib import Path
from typing import List, Tuple, Any

# ────────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────────

# Default path assumption (relative to repo root when running as module)
_DEFAULT_PORTS_PATH = Path("data/processed/cabotage_data/ports_br.json")

# Critical "turning points" to force the route shape
# These are inserted into the sequence to ensure the line bends around land masses
# Format: (lat, lon, label)
_FIXED_WAYPOINTS = [
    (-34.0, -52.0, "Offshore South"),        # Start of line (South)
    (-5.0, -34.8, "Corner (Natal)"),         # The "Hump" of Brazil
    (0.5, -47.5, "Amazon Mouth"),            # Entry to Amazon River
]

# Global cache for the sorted waypoints
_COASTAL_PATH: List[Tuple[float, float]] = []


# ────────────────────────────────────────────────────────────────────────────────
# Sorting Logic
# ────────────────────────────────────────────────────────────────────────────────

def _get_coastal_score(lat: float, lon: float) -> float:
    """
    Assign a 'score' representing distance along the coast from South to North-West.
    
    Zone 1: East Coast (South -> Natal). Driven by Latitude.
            Lat ranges -34 to -5. Score 0 to ~30.
            
    Zone 2: North Coast (Natal -> Amazon). Driven by Longitude.
            Lon ranges -35 to -60. Score ~30 to ~60.
    """
    # The "Corner" is approx Lat -5.0
    if lat < -5.0:
        # Zone 1: Score is based on how far North we are (Lat + 35)
        # -34 -> 1, -23 -> 12, -5 -> 30
        return lat + 40.0
    else:
        # Zone 2: Score is based on how far West we are.
        # We start adding from the max score of Zone 1 (~35)
        # Lon -35 -> +0, Lon -60 -> +25
        # Score = 35 + (start_lon - current_lon)
        # Actually, just use abs(lon) added to base.
        return 40.0 + abs(lon)


def _load_waypoints(json_path: Path = _DEFAULT_PORTS_PATH) -> List[Tuple[float, float]]:
    """
    Load ports + fixed waypoints and sort them into a single line.
    """
    # Try to find the file
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
    
    # 2. Add Fixed Waypoints (to ensure curves exist even without ports there)
    for lat, lon, _ in _FIXED_WAYPOINTS:
        points.append((lat, lon))
        
    # 3. Sort everything by "Coastal Score"
    # This creates a single ordered list: South -> North -> West
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
    
    # Find where our Start and End ports fit onto the highway
    idx_start = _find_nearest_idx(start_coords[0], start_coords[1], highway)
    idx_end = _find_nearest_idx(end_coords[0], end_coords[1], highway)
    
    path = [start_coords]
    
    if idx_start != -1 and idx_end != -1 and idx_start != idx_end:
        step = 1 if idx_end > idx_start else -1
        
        # Traverse highway
        # If going South->North (start < end), we iterate forward
        # If going North->South (start > end), we iterate backward
        
        current = idx_start
        while current != idx_end:
            # Don't add the start/end ports themselves again if they are close
            # But do add the intermediate points
            if current != idx_start:
                path.append(highway[current])
            current += step
            
        # Add the last highway point before the destination
        if idx_end != idx_start:
             path.append(highway[idx_end])

    path.append(end_coords)
    return path

# Smoke test
if __name__ == "__main__":
    print("--- Route Renderer Test ---")
    path = _load_waypoints()
    print(f"Loaded {len(path)} coastal points.")
    print("Sample (First 3):", path[:3])
    print("Sample (Last 3):", path[-3:])
    
    # Test: Santos -> Manaus
    # Santos ~ -23.9, -46.3
    # Manaus ~ -3.1, -60.0
    route = get_visual_sea_path((-23.95, -46.32), (-3.1, -60.0))
    print(f"Route Santos->Manaus has {len(route)} points.")