from __future__ import annotations

from app.main.utils.constants import MAP_STYLES, ROOT

HEATMAP_PAGE_TITLE = "Brazil Modal Advantage Heatmap"
HEATMAP_PAGE_ICON = ":triangular_flag_on_post:"
HEATMAP_DEFAULT_METRIC = "cost"
HEATMAP_METRICS = ("cost", "emissions")
HEATMAP_DESTINATIONS_PATH = ROOT / "data" / "processed" / "destinies" / "city_dests_over50k.txt"
HEATMAP_DESTINATION_SET_ID = HEATMAP_DESTINATIONS_PATH.name
HEATMAP_DESTINATION_LABEL = "Cities with population over 50k"
HEATMAP_BRAZIL_CENTER_LAT = -14.2350
HEATMAP_BRAZIL_CENTER_LON = -51.9253
HEATMAP_BRAZIL_ZOOM = 3.4
HEATMAP_MAP_STYLE = MAP_STYLES["Voyager"]
HEATMAP_COLOR_NEGATIVE = (188, 55, 45)
HEATMAP_COLOR_MID = (243, 210, 102)
HEATMAP_COLOR_POSITIVE = (34, 139, 84)
