from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.main.utils.constants import MAP_STYLES, ROOT
from modules.infra.data_assets import build_data_assets_client, load_data_assets_settings, resolve_data_asset_path

HEATMAP_PAGE_TITLE = "Heatmap"
HEATMAP_PAGE_ICON = "🗺️"
HEATMAP_DEFAULT_METRIC = "cost"
HEATMAP_METRICS = ("cost", "emissions")
HEATMAP_DESTINATIONS_DIR = ROOT / "data" / "processed" / "destinies"
HEATMAP_DEFAULT_DESTINATION_SET_ID = "city_dests_over50k.txt"
HEATMAP_DESTINATIONS_PATH = HEATMAP_DESTINATIONS_DIR / HEATMAP_DEFAULT_DESTINATION_SET_ID
HEATMAP_DESTINATION_SET_ID = HEATMAP_DESTINATIONS_PATH.name
HEATMAP_DESTINATION_LABELS = {
    "city_dests.txt": "All tracked cities",
    "city_dests_borders.txt": "Border and remote cities",
    "city_dests_over350k.txt": "Cities with population over 350k",
    "city_dests_over50k.txt": "Cities with population over 50k",
}
HEATMAP_BRAZIL_BOUNDARY_PATH = ROOT / "data" / "processed" / "geo" / "brazil_boundary_simplified.geojson"
HEATMAP_BRAZIL_CENTER_LAT = -14.2350
HEATMAP_BRAZIL_CENTER_LON = -51.9253
HEATMAP_BRAZIL_ZOOM = 3.6
HEATMAP_3D_PITCH = 71
HEATMAP_3D_BEARING = 40
HEATMAP_MAP_HEIGHT = 620
HEATMAP_MAP_STYLE = MAP_STYLES["Voyager"]
HEATMAP_COLOR_NEGATIVE = (201, 36, 54)
HEATMAP_COLOR_MID = (233, 198, 84)
HEATMAP_COLOR_POSITIVE = (28, 143, 77)
HEATMAP_SURFACE_ALPHA = 210
HEATMAP_SURFACE_SIDE_WALL_NEUTRAL = (224, 219, 208)
HEATMAP_SURFACE_SIDE_WALL_TINT_RATIO = 0.18
HEATMAP_SURFACE_SIDE_WALL_ALPHA = 0
HEATMAP_SURFACE_TOP_CAP_LIFT_M = 0.0
HEATMAP_SURFACE_ZERO_PLANE_ELEVATION_M = 14_000.0
HEATMAP_SURFACE_CELL_SIZE_DEGREES = 0.5
HEATMAP_SURFACE_COLOR_QUANTILE = 0.88
HEATMAP_SURFACE_ELEVATION_QUANTILE = 0.5
HEATMAP_SURFACE_MAX_ELEVATION_M = 12_000.0
HEATMAP_SURFACE_ELEVATION_FLOOR_RATIO = 0.0
HEATMAP_SURFACE_ELEVATION_GAMMA = 1.2
HEATMAP_SURFACE_ELEVATION_BOOST = 0.85
HEATMAP_SURFACE_INTERPOLATION_RADIUS_QUANTILE = 0.85
HEATMAP_SURFACE_INTERPOLATION_RADIUS_FACTOR = 2.25
HEATMAP_SURFACE_INTERPOLATION_RADIUS_MIN_KM = 180.0
HEATMAP_SURFACE_INTERPOLATION_RADIUS_MAX_KM = 650.0
HEATMAP_POINT_OVERLAY_RADIUS_M = 22_000.0


def _normalize_destination_set_id(destination_set_id: str | None) -> str:
    candidate = str(destination_set_id or HEATMAP_DESTINATION_SET_ID).strip() or HEATMAP_DESTINATION_SET_ID
    candidate_path = Path(candidate)
    if candidate_path.name != candidate or candidate_path.suffix.lower() != ".txt":
        raise FileNotFoundError(f"Destination set must be a .txt filename under {HEATMAP_DESTINATIONS_DIR}: {candidate}")
    return candidate


def _remote_destination_set_names() -> tuple[str, ...]:
    settings = load_data_assets_settings()
    if settings is None:
        return ()

    try:
        client = build_data_assets_client(settings)
        items = client.list_objects(
            bucket=settings.data_bucket,
            prefix="data/processed/destinies",
        )
    except Exception:
        return ()

    names = sorted(
        {
            str(item.get("name") or "").strip()
            for item in items
            if str(item.get("name") or "").strip().lower().endswith(".txt")
        }
    )
    return tuple(names)


@lru_cache(maxsize=1)
def list_heatmap_destination_sets() -> tuple[str, ...]:
    options: set[str] = set()

    if HEATMAP_DESTINATIONS_DIR.exists():
        options.update(
            path.name
            for path in HEATMAP_DESTINATIONS_DIR.iterdir()
            if path.is_file() and path.suffix.lower() == ".txt"
        )

    options.update(_remote_destination_set_names())
    ordered = sorted(options)
    if HEATMAP_DESTINATION_SET_ID in ordered:
        ordered.remove(HEATMAP_DESTINATION_SET_ID)
    ordered.insert(0, HEATMAP_DESTINATION_SET_ID)
    return tuple(ordered)


def resolve_heatmap_destination_path(destination_set_id: str | None) -> Path:
    candidate = _normalize_destination_set_id(destination_set_id)
    path = resolve_data_asset_path(HEATMAP_DESTINATIONS_DIR / candidate)
    if not path.is_file():
        raise FileNotFoundError(f"Destination file not found under {HEATMAP_DESTINATIONS_DIR}: {candidate}")
    return path


def heatmap_destination_label(destination_set_id: str | None) -> str:
    candidate = _normalize_destination_set_id(destination_set_id)
    fallback = Path(candidate).stem.replace("_", " ").strip().title()
    return str(HEATMAP_DESTINATION_LABELS.get(candidate) or fallback or candidate)
