# calcs/cabotage_plot_helper.py
# -*- coding: utf-8 -*-

"""
Cabotage Route Renderer.
========================

Provides heuristic paths for visualizing sea routes along the Brazilian coast.
Instead of straight lines, it returns a sequence of waypoints that follow the
general coastline curvature, making maps look realistic.

Logic:
  - Uses a simplified ordered list of coastal "anchor points" (Lat/Lon).
  - When routing from A to B, it snaps A and B to the nearest anchors,
    then fills the gaps with the intermediate anchors.
"""

import math

# ────────────────────────────────────────────────────────────────────────────────
# Coastal Waypoints (Ordered South -> North -> West)
# ────────────────────────────────────────────────────────────────────────────────
# These approximate the curve of the Brazilian coast.
_COASTAL_WAYPOINTS = [
    (-32.17, -52.05), # Rio Grande
    (-28.23, -48.65), # Imbituba
    (-26.92, -48.63), # Itajaí/Navegantes
    (-25.50, -48.50), # Paranaguá
    (-24.10, -46.10), # Santos (Offshore)
    (-23.00, -43.00), # Rio (Offshore)
    (-20.30, -40.20), # Vitória
    (-18.00, -38.50), # Abrolhos Bank (Correction for Bahia curve)
    (-13.00, -38.30), # Salvador
    (-10.00, -36.00), # Maceió / Sergipe offshore
    (-8.00,  -34.50), # Recife (The "Hump")
    (-5.50,  -35.00), # Natal (Corner)
    (-3.70,  -38.40), # Fortaleza
    (-2.50,  -44.20), # São Luís
    (-0.50,  -47.50), # Salinópolis (Amazon Mouth entry)
    (0.00,   -50.00), # Amazon Delta
    (-1.45,  -52.50), # Amazon River (Almeirim)
    (-2.20,  -54.00), # Santarém
    (-3.10,  -60.00), # Manaus
]

def _dist_sq(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2

def _find_nearest_idx(lat, lon):
    """Find index of the closest waypoint to the given point."""
    best_idx = -1
    best_dist = float('inf')
    
    for i, (w_lat, w_lon) in enumerate(_COASTAL_WAYPOINTS):
        d = _dist_sq((lat, lon), (w_lat, w_lon))
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx

def get_visual_sea_path(start_coords, end_coords):
    """
    Returns a list of [lat, lon] tuples including start, intermediates, and end.
    
    Parameters
    ----------
    start_coords : tuple (lat, lon)
    end_coords : tuple (lat, lon)
    """
    lat1, lon1 = start_coords
    lat2, lon2 = end_coords
    
    idx1 = _find_nearest_idx(lat1, lon1)
    idx2 = _find_nearest_idx(lat2, lon2)
    
    path = [start_coords]
    
    if idx1 != -1 and idx2 != -1 and idx1 != idx2:
        # Determine direction
        step = 1 if idx2 > idx1 else -1
        
        # Add intermediate waypoints (inclusive of the "nearest" anchors to guide the curve)
        # We range from idx1 to idx2
        current = idx1
        while current != idx2:
            current += step
            path.append(_COASTAL_WAYPOINTS[current])
            
    path.append(end_coords)
    return path