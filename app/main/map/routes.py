from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from modules.plot.sea_lane_brazil import BRAZIL_COASTAL_SEA_WAYPOINTS, build_sea_lane_path
from modules.plot.sea_path_pretty import build_pretty_sea_path

from app.main.map.labels import extract_leg_path
from app.main.utils.formatters import path_midpoint, route_metric_label


def build_route_rows(
    *,
    geo: Mapping[str, Any],
    results: Mapping[str, Any],
    state: Mapping[str, Any],
    origin: Tuple[float, float],
    destiny: Tuple[float, float],
    po_coords: Tuple[float, float],
    pd_coords: Tuple[float, float],
    port_origin_name: str,
    port_destiny_name: str,
    maritime: Mapping[str, float],
) -> List[Dict[str, Any]]:
    road = results.get("road_only", {})
    mm = results.get("multimodal", {})
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})

    direct_path = extract_leg_path(dict(geo.get("road_direct", {})), origin, destiny)
    first_path = extract_leg_path(dict(geo.get("first_mile", {})), origin, po_coords)
    last_path = extract_leg_path(dict(geo.get("last_mile", {})), pd_coords, destiny)

    sea_path_style = str(state.get("map_sea_path_style", "Coastal lane (default)"))
    if sea_path_style == "Coastal lane (default)":
        sea_path = build_sea_lane_path(
            origin_latlon=po_coords,
            dest_latlon=pd_coords,
            waypoints=BRAZIL_COASTAL_SEA_WAYPOINTS,
            n_points=int(state.get("map_sea_n_points", 200)),
            smooth_window=int(state.get("map_sea_smooth_window", 7)),
        )
    else:
        sea_path = build_pretty_sea_path(
            origin_lat=po_coords[0],
            origin_lon=po_coords[1],
            dest_lat=pd_coords[0],
            dest_lon=pd_coords[1],
            n_points=int(state.get("map_sea_n_points", 200)),
            curvature=float(state.get("map_sea_curvature", 0.25)),
            smooth_window=int(state.get("map_sea_smooth_window", 7)),
        )

    route_rows: list[dict[str, Any]] = []

    if bool(state.get("map_show_direct", True)):
        route_rows.append(
            {
                "route_name": "Road",
                "path": direct_path,
                "color": [220, 72, 62, 215],
                "width": 5,
                "tooltip": route_metric_label(
                    "Road",
                    road.get("distance_km"),
                    road.get("cost"),
                    road.get("co2e"),
                ),
            }
        )

    if bool(state.get("map_show_first_last", True)) and origin != po_coords:
        route_rows.append(
            {
                "route_name": "Road (pre-carriage)",
                "path": first_path,
                "color": [155, 89, 182, 220],
                "width": 5,
                "tooltip": route_metric_label(
                    "Road (pre-carriage)",
                    first.get("distance_km"),
                    first.get("cost"),
                    first.get("co2e"),
                ),
            }
        )

    if bool(state.get("map_show_sea", True)):
        route_rows.append(
            {
                "route_name": f"Sea (cabotage): {port_origin_name} -> {port_destiny_name}",
                "path": sea_path,
                "color": [41, 128, 185, 230],
                "width": 6,
                "tooltip": route_metric_label(
                    f"Sea (cabotage): {port_origin_name} -> {port_destiny_name}",
                    sea.get("distance_km"),
                    maritime.get("sailing_cost_brl"),
                    maritime.get("sailing_co2e_kg"),
                ),
            }
        )

    if bool(state.get("map_show_first_last", True)) and pd_coords != destiny:
        route_rows.append(
            {
                "route_name": "Road (on-carriage)",
                "path": last_path,
                "color": [155, 89, 182, 220],
                "width": 5,
                "tooltip": route_metric_label(
                    "Road (on-carriage)",
                    last.get("distance_km"),
                    last.get("cost"),
                    last.get("co2e"),
                ),
            }
        )

    for row in route_rows:
        row["label_position"] = path_midpoint(row.get("path") or [])
        row["label"] = row["tooltip"]
        row["hitbox_color"] = [255, 255, 255, 4]
        row["hitbox_width"] = 18

    return route_rows
