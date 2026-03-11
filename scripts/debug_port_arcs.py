from __future__ import annotations

import argparse
from pathlib import Path

import pydeck as pdk

from app.main.map.routing.geometry_utils import dedupe_latlon_path, haversine_km
from app.main.map.routing.marine_master_route import load_master_route_ports
from app.main.map.routing.marine_waypoints import normalize_port_name, point_names_to_latlon, resolve_port_approach_point_names
from app.main.map.routing.water_validation import load_reference_water_lane
from modules.infra.log_manager import init_logging
from modules.plot.port_arc_geometry import build_port_arc_debug_payload

DEFAULT_PORTS = (
    "Porto de Santos",
    "Porto de Fortaleza",
    "Porto de Vila do Conde",
    "Porto de Manaus",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render corridor-based maritime port-arc diagnostics.")
    parser.add_argument("--port", dest="ports", action="append", help="Canonical port name to render. Can be repeated.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logs/port_arc_debug.html"),
        help="HTML output path for the debug map.",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _port_lookup() -> dict[str, tuple[str, tuple[float, float]]]:
    lookup: dict[str, tuple[str, tuple[float, float]]] = {}
    for port in load_master_route_ports():
        lookup[normalize_port_name(port.name)] = (port.name, (float(port.latlon[0]), float(port.latlon[1])))
    return lookup


def _nearest_index(target_latlon: tuple[float, float], points: list[tuple[float, float]]) -> int:
    best_index = 0
    best_distance = float("inf")
    for index, point in enumerate(points):
        distance = haversine_km(target_latlon[0], target_latlon[1], point[0], point[1])
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index


def _local_corridor_for_port(port_name: str, port_latlon: tuple[float, float]) -> list[tuple[float, float]]:
    approach_points = point_names_to_latlon(resolve_port_approach_point_names(port_name))
    anchor = approach_points[-1] if approach_points else port_latlon
    lane = load_reference_water_lane()
    lane_index = _nearest_index(anchor, lane)
    start = max(0, lane_index - 2)
    end = min(len(lane), lane_index + 3)
    return dedupe_latlon_path(approach_points + lane[start:end])


def _path_row(name: str, path_latlon: list[tuple[float, float]], color: list[int], width: int) -> dict[str, object]:
    return {
        "name": name,
        "path": [[float(lon), float(lat)] for lat, lon in path_latlon],
        "color": color,
        "width": width,
    }


def _point_row(name: str, latlon: tuple[float, float], color: list[int], radius: int) -> dict[str, object]:
    return {
        "name": name,
        "position": [float(latlon[1]), float(latlon[0])],
        "color": color,
        "radius": radius,
    }


def main() -> None:
    args = _parse_args()
    init_logging(level=str(args.log_level), force=True, write_output=False)

    port_names = tuple(args.ports or DEFAULT_PORTS)
    lookup = _port_lookup()
    peer_ports = tuple(latlon for _, latlon in lookup.values())

    path_rows: list[dict[str, object]] = []
    point_rows: list[dict[str, object]] = []

    for requested_name in port_names:
        key = normalize_port_name(requested_name)
        resolved = lookup.get(key)
        if resolved is None:
            raise KeyError(f"Port not found in master route catalog: {requested_name}")

        canonical_name, port_latlon = resolved
        corridor = _local_corridor_for_port(canonical_name, port_latlon)
        payload = build_port_arc_debug_payload(
            name=canonical_name,
            port_latlon=port_latlon,
            corridor_latlon=corridor,
            peer_port_latlons=peer_ports,
        )

        path_rows.append(_path_row(f"{canonical_name} corridor", list(payload.corridor_path_latlon), [52, 152, 219, 180], 5))
        path_rows.append(_path_row(f"{canonical_name} nearest segment", list(payload.nearest_segment_latlon), [231, 76, 60, 220], 8))
        path_rows.append(_path_row(f"{canonical_name} water vector", list(payload.water_vector_latlon), [46, 204, 113, 220], 4))
        path_rows.append(_path_row(f"{canonical_name} arc", list(payload.arc_points_latlon), [241, 196, 15, 240], 7))

        point_rows.append(_point_row(f"{canonical_name} port", payload.port_latlon, [192, 57, 43, 245], 14000))
        point_rows.append(_point_row(f"{canonical_name} center", payload.center_latlon, [39, 174, 96, 230], 11000))
        point_rows.append(_point_row(f"{canonical_name} anchor", payload.corridor_anchor_latlon, [52, 73, 94, 220], 10000))
        point_rows.append(_point_row(f"{canonical_name} midpoint", payload.midpoint_latlon, [142, 68, 173, 230], 11500))

    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=-11.0, longitude=-50.0, zoom=3.6, pitch=0, bearing=0),
        layers=[
            pdk.Layer(
                "PathLayer",
                data=path_rows,
                get_path="path",
                get_color="color",
                get_width="width",
                width_min_pixels=2,
                pickable=True,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=point_rows,
                get_position="position",
                get_fill_color="color",
                get_radius="radius",
                pickable=True,
                opacity=0.9,
            ),
            pdk.Layer(
                "TextLayer",
                data=point_rows,
                get_position="position",
                get_text="name",
                get_size=13,
                get_color=[255, 255, 255, 240],
                get_text_anchor="start",
                get_alignment_baseline="center",
            ),
        ],
        tooltip={"text": "{name}"},
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        deck.to_html(as_string=True, notebook_display=False, iframe_width="100%", iframe_height=860),
        encoding="utf-8",
    )
    print(f"Wrote port-arc debug map to {output_path}")


if __name__ == "__main__":
    main()
