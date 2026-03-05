from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

import pydeck as pdk
import streamlit.components.v1 as components

from app.main.cards.summary import render_cards_overlay
from app.main.map.ports import build_port_and_endpoint_points
from app.main.map.routes import build_route_rows
from app.main.styles import MAP_OVERLAY_CSS
from app.main.utils.constants import MAP_STYLES
from app.main.utils.formatters import clean_place_label, safe_float


def safe_latlon(point: Mapping[str, Any]) -> Tuple[float, float]:
    return float(point["lat"]), float(point["lon"])


def map_points(geo: Mapping[str, Any]) -> list[Tuple[float, float]]:
    origin = safe_latlon(geo["origin"])
    destiny = safe_latlon(geo["destiny"])

    po = geo["port_origin"]
    pd = geo["port_destiny"]
    po_coords = safe_latlon(po["gate"]) if po.get("gate") else safe_latlon(po)
    pd_coords = safe_latlon(pd["gate"]) if pd.get("gate") else safe_latlon(pd)

    return [origin, destiny, po_coords, pd_coords]


def zoom_from_span(lat_span: float, lon_span: float) -> float:
    span = max(lat_span, lon_span)
    if span < 0.05:
        return 11.5
    if span < 0.2:
        return 10.0
    if span < 0.8:
        return 8.5
    if span < 2.0:
        return 7.2
    if span < 5.0:
        return 6.0
    if span < 10.0:
        return 5.2
    if span < 20.0:
        return 4.5
    return 3.8


def fit_view(points: list[Tuple[float, float]]) -> tuple[float, float, float]:
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    center_lat = (lat_min + lat_max) / 2.0
    center_lon = (lon_min + lon_max) / 2.0
    zoom = zoom_from_span(lat_max - lat_min, lon_max - lon_min)
    return center_lat, center_lon, zoom


def maritime_component_breakdown(results: Mapping[str, Any]) -> Dict[str, float]:
    sea = results.get("multimodal", {}).get("sea", {})
    inputs = results.get("inputs", {})

    bunker_price = safe_float(inputs.get("bunker_price"))
    marine_ef = safe_float(inputs.get("marine_ef_kg_per_kg"))

    sailing_fuel_kg = safe_float(sea.get("fuel_kg_sailing"))
    hoteling_fuel_kg = safe_float(sea.get("hoteling_fuel_kg"))

    return {
        "sailing_cost_brl": (sailing_fuel_kg / 1000.0) * bunker_price,
        "sailing_co2e_kg": sailing_fuel_kg * marine_ef,
        "hoteling_cost_brl": (hoteling_fuel_kg / 1000.0) * bunker_price,
        "hoteling_co2e_kg": hoteling_fuel_kg * marine_ef,
        "port_ops_cost_brl": safe_float(sea.get("port_ops_cost")),
        "port_ops_co2e_kg": safe_float(sea.get("port_ops_co2e")),
    }


def build_map_deck(geo: Mapping[str, Any], results: Mapping[str, Any] | None, state: Mapping[str, Any]) -> pdk.Deck:
    results = results or {}

    origin = safe_latlon(geo["origin"])
    destiny = safe_latlon(geo["destiny"])

    po = geo["port_origin"]
    pd = geo["port_destiny"]
    po_coords = safe_latlon(po["gate"]) if po.get("gate") else safe_latlon(po)
    pd_coords = safe_latlon(pd["gate"]) if pd.get("gate") else safe_latlon(pd)

    maritime = maritime_component_breakdown(results)

    origin_name = clean_place_label(geo.get("origin", {}).get("label")) or clean_place_label(state.get("origin"))
    destiny_name = clean_place_label(geo.get("destiny", {}).get("label")) or clean_place_label(state.get("destiny"))
    port_origin_name = clean_place_label(po.get("name"))
    port_destiny_name = clean_place_label(pd.get("name"))

    route_rows = build_route_rows(
        geo=geo,
        results=results,
        state=state,
        origin=origin,
        destiny=destiny,
        po_coords=po_coords,
        pd_coords=pd_coords,
        port_origin_name=port_origin_name,
        port_destiny_name=port_destiny_name,
        maritime=maritime,
    )

    zoom = float(state.get("map_zoom", 4.8))
    radius_base = max(1200.0, 9000.0 - (zoom * 550.0))

    point_rows = build_port_and_endpoint_points(
        origin=origin,
        destiny=destiny,
        po_coords=po_coords,
        pd_coords=pd_coords,
        origin_name=origin_name,
        destiny_name=destiny_name,
        port_origin_name=port_origin_name,
        port_destiny_name=port_destiny_name,
        maritime=maritime,
        radius_base=radius_base,
        show_ports=bool(state.get("map_show_ports", True)),
    )

    layers: list[pdk.Layer] = []

    if route_rows:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=route_rows,
                get_path="path",
                get_color="hitbox_color",
                get_width="hitbox_width",
                width_min_pixels=12,
                pickable=True,
            )
        )
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=route_rows,
                get_path="path",
                get_color="color",
                get_width="width",
                width_min_pixels=3,
                pickable=True,
            )
        )

    if bool(state.get("map_show_labels", True)) and route_rows:
        layers.append(
            pdk.Layer(
                "TextLayer",
                data=route_rows,
                get_position="label_position",
                get_text="label",
                get_size=11,
                get_color=[245, 247, 250, 250],
                get_text_anchor="middle",
                get_alignment_baseline="center",
                pickable=False,
            )
        )

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=point_rows,
            get_position="position",
            get_color=[255, 255, 255, 4],
            get_radius="radius",
            radius_min_pixels=16,
            radius_max_pixels=30,
            pickable=True,
        )
    )

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=point_rows,
            get_position="position",
            get_color="color",
            get_radius="radius",
            radius_min_pixels=5,
            radius_max_pixels=18,
            pickable=True,
        )
    )

    if bool(state.get("map_show_labels", True)):
        layers.append(
            pdk.Layer(
                "TextLayer",
                data=point_rows,
                get_position="position",
                get_text="kind",
                get_size=13,
                get_color=[248, 250, 252, 245],
                get_text_anchor="middle",
                get_alignment_baseline="bottom",
                pickable=False,
            )
        )

    return pdk.Deck(
        map_style=MAP_STYLES[str(state.get("map_style", "Voyager"))],
        initial_view_state=pdk.ViewState(
            latitude=float(state.get("map_center_lat", -15.0)),
            longitude=float(state.get("map_center_lon", -50.0)),
            zoom=float(state.get("map_zoom", 4.8)),
            pitch=float(state.get("map_pitch", 30)),
            bearing=float(state.get("map_bearing", 5)),
        ),
        layers=layers,
        tooltip={"text": "{tooltip}"},
    )


def render_map(geo: Mapping[str, Any], results: Mapping[str, Any] | None, state: Mapping[str, Any]) -> None:
    map_height = 560
    deck = build_map_deck(geo, results=results, state=state)

    deck_html = deck.to_html(
        as_string=True,
        notebook_display=False,
        iframe_width="100%",
        iframe_height=map_height,
    )

    overlay_html = render_cards_overlay(results)

    if "</head>" in deck_html:
        deck_html = deck_html.replace("</head>", MAP_OVERLAY_CSS + "</head>", 1)
    else:
        deck_html = MAP_OVERLAY_CSS + deck_html

    if "<body>" in deck_html:
        deck_html = deck_html.replace("<body>", f"<body><div id='overlay-root'>{overlay_html}</div>", 1)
    else:
        deck_html = f"<div id='overlay-root'>{overlay_html}</div>" + deck_html

    components.html(deck_html, height=map_height, scrolling=False)
