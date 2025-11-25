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
  2. Load fixed offshore waypoints from TXT.
  3. Sort them into a single linear sequence ("Coastal Highway").
  4. Routing A->B finds the slice of points between A and B in this sequence.
"""

import json
import math
from pathlib import Path
from typing import List, Tuple, Any

from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────────

# "The Corner" of Brazil (approx Natal/Touros).
CORNER_LAT = -5.2

# Default paths (relative to repo root when running as module)
_DEFAULT_PORTS_PATH = Path("data/processed/cabotage_data/ports_br.json")
_DEFAULT_WAYPOINTS_PATH = Path("data/raw/plot/fixed_waypoints.txt")

# Global cache for the sorted waypoints
_COASTAL_PATH: List[Tuple[float, float]] = []


# ────────────────────────────────────────────────────────────────────────────────
# Sorting Logic
# ────────────────────────────────────────────────────────────────────────────────

def _get_coastal_score(lat: float, lon: float) -> float:
    """
    Assign a 'score' representing linear distance along the coast from South to North-West.
    """
    if lat < CORNER_LAT:
        # ZONE 1: East Coast (South -> North)
        # Score increases as Latitude increases (moves North toward 0).
        return lat + 40.0
    else:
        # ZONE 2: North Coast (Natal -> Amazon)
        # Score increases as Longitude decreases (moves West toward -60).
        return 40.0 + abs(lon)


def _load_waypoints_from_file(path: Path) -> List[Tuple[float, float]]:
    """Parse 'lat, lon' lines from text file."""
    points = []
    if not path.exists():
        # Try stepping up one level if running from subfolder
        alt = Path("..") / path
        if alt.exists():
            path = alt
        else:
            _log.warning(f"Waypoints file not found at {path}")
            return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    try:
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                        points.append((lat, lon))
                    except ValueError:
                        continue
    except Exception as e:
        _log.error(f"Failed to load waypoints from {path}: {e}")
        
    return points


def _load_ports_from_json(path: Path) -> List[Tuple[float, float]]:
    """Extract lat/lon from ports JSON."""
    points = []
    if not path.exists():
        # Try stepping up
        alt = Path("..") / path
        if alt.exists():
            path = alt
        else:
            # Fallback check for repo root structure
            alt2 = Path("data/processed/cabotage_data/ports_br.json")
            if alt2.exists():
                path = alt2
            else:
                _log.warning(f"Ports file not found at {path}")
                return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            ports = json.load(f)
            for p in ports:
                points.append((float(p["lat"]), float(p["lon"])))
    except Exception as e:
        _log.error(f"Failed to load ports from {path}: {e}")
        
    return points


def _load_combined_path() -> List[Tuple[float, float]]:
    """
    Load ports + fixed waypoints and sort them into a single line.
    """
    points = []
    
    # 1. Load Ports (Real locations)
    points.extend(_load_ports_from_json(_DEFAULT_PORTS_PATH))
    
    # 2. Load Fixed Waypoints (Virtual offshore points)
    points.extend(_load_waypoints_from_file(_DEFAULT_WAYPOINTS_PATH))
    
    if not points:
        _log.error("No coastal points loaded! Sea routes will be straight lines.")
        return []
        
    # 3. Sort everything by "Coastal Score"
    # This merges the lists into one continuous geographic sequence
    points.sort(key=lambda p: _get_coastal_score(p[0], p[1]))
    
    return points


def _ensure_path():
    """Singleton loader."""
    global _COASTAL_PATH
    if not _COASTAL_PATH:
        _COASTAL_PATH = _load_combined_path()
    return _COASTAL_PATH


# ────────────────────────────────────────────────────────────────────────────────
# Routing Logic
# ────────────────────────────────────────────────────────────────────────────────

def _dist_sq(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def _find_nearest_idx(lat, lon, points):
    """Find index of the closest point on the highway."""
    if not points:
        return -1
        
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
    if not highway:
        return [start_coords, end_coords]
    
    # Snap inputs to the nearest points on our sorted line
    idx_start = _find_nearest_idx(start_coords[0], start_coords[1], highway)
    idx_end = _find_nearest_idx(end_coords[0], end_coords[1], highway)
    
    path = [start_coords]
    
    if idx_start != -1 and idx_end != -1 and idx_start != idx_end:
        step = 1 if idx_end > idx_start else -1
        
        # Traverse the highway
        current = idx_start
        
        # Include start anchor if it's not the start itself (it rarely is)
        if highway[current] != start_coords:
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
    from modules.infra.log_manager import init_logging
    init_logging(level="DEBUG")
    
    print("--- Dynamic Route Renderer Test ---")
    path = _load_combined_path()
    print(f"Loaded {len(path)} total waypoints (Ports + Virtual).")
    
    if path:
        print(f"First (South): {path[0]}")
        print(f"Last (North/West): {path[-1]}")
            
    # Test: Santos -> Manaus
    route = get_visual_sea_path((-23.95, -46.32), (-3.1, -60.0))
    print(f"\nRoute Santos->Manaus has {len(route)} points.")