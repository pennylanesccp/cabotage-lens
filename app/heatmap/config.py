from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.main.utils.constants import MAP_STYLES, ROOT

HEATMAP_PAGE_TITLE = "Heatmap"
HEATMAP_PAGE_ICON = "📍"
HEATMAP_DEFAULT_METRIC = "cost"
HEATMAP_METRICS = ("cost", "emissions")
HEATMAP_DESTINATIONS_DIR = ROOT / "data" / "processed" / "destinies"
HEATMAP_DEFAULT_DESTINATION_SET_ID = "city_dests_over50k.txt"
HEATMAP_DESTINATIONS_PATH = HEATMAP_DESTINATIONS_DIR / HEATMAP_DEFAULT_DESTINATION_SET_ID
HEATMAP_DESTINATION_SET_ID = HEATMAP_DESTINATIONS_PATH.name
HEATMAP_DESTINATION_LABEL = "Cities with population over 50k"
HEATMAP_BRAZIL_BOUNDARY_PATH = ROOT / "data" / "processed" / "geo" / "brazil_boundary_simplified.geojson"
HEATMAP_BRAZIL_CENTER_LAT = -14.2350
HEATMAP_BRAZIL_CENTER_LON = -51.9253
HEATMAP_BRAZIL_ZOOM = 3.7
HEATMAP_3D_PITCH = 67
HEATMAP_3D_BEARING = 34
HEATMAP_MAP_STYLE = MAP_STYLES["Voyager"]
HEATMAP_COLOR_NEGATIVE = (203, 96, 48)
HEATMAP_COLOR_MID = (236, 214, 118)
HEATMAP_COLOR_POSITIVE = (106, 156, 67)
HEATMAP_SURFACE_ALPHA = 210
HEATMAP_SURFACE_CELL_SIZE_DEGREES = 0.65
HEATMAP_SURFACE_COLOR_QUANTILE = 0.88
HEATMAP_SURFACE_ELEVATION_QUANTILE = 0.58
HEATMAP_SURFACE_MAX_ELEVATION_M = 310_000.0
HEATMAP_SURFACE_ELEVATION_FLOOR_RATIO = 0.01
HEATMAP_SURFACE_ELEVATION_GAMMA = 0.42
HEATMAP_POINT_OVERLAY_RADIUS_M = 22_000.0


@lru_cache(maxsize=1)
def list_heatmap_destination_sets() -> tuple[str, ...]:
    if not HEATMAP_DESTINATIONS_DIR.exists():
        return (HEATMAP_DESTINATION_SET_ID,)

    options = sorted(
        path.name
        for path in HEATMAP_DESTINATIONS_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".txt"
    )
    if HEATMAP_DESTINATION_SET_ID not in options:
        options.insert(0, HEATMAP_DESTINATION_SET_ID)
    return tuple(options)


def resolve_heatmap_destination_path(destination_set_id: str | None) -> Path:
    candidate = str(destination_set_id or HEATMAP_DESTINATION_SET_ID).strip() or HEATMAP_DESTINATION_SET_ID
    path = (HEATMAP_DESTINATIONS_DIR / candidate).resolve()
    expected_root = HEATMAP_DESTINATIONS_DIR.resolve()
    if path.parent != expected_root or not path.is_file():
        raise FileNotFoundError(f"Destination file not found under {expected_root}: {candidate}")
    return path


def heatmap_destination_label(destination_set_id: str | None) -> str:
    candidate = str(destination_set_id or HEATMAP_DESTINATION_SET_ID).strip() or HEATMAP_DESTINATION_SET_ID
    if candidate == HEATMAP_DESTINATION_SET_ID:
        return HEATMAP_DESTINATION_LABEL
    return candidate
