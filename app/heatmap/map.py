from __future__ import annotations

from html import escape
from typing import Any, Iterable, List

import pydeck as pdk
import streamlit as st

from app.heatmap.config import (
    HEATMAP_BRAZIL_CENTER_LAT,
    HEATMAP_BRAZIL_CENTER_LON,
    HEATMAP_BRAZIL_ZOOM,
    HEATMAP_COLOR_MID,
    HEATMAP_COLOR_NEGATIVE,
    HEATMAP_COLOR_POSITIVE,
    HEATMAP_MAP_STYLE,
)
from app.heatmap.types import HeatmapDataset, HeatmapPoint



def _interpolate(start: Iterable[int], end: Iterable[int], ratio: float) -> List[int]:
    ratio = max(0.0, min(1.0, float(ratio)))
    start_values = list(start)
    end_values = list(end)
    return [int(round(s + ((e - s) * ratio))) for s, e in zip(start_values, end_values)]



def _normalized_value(value: float, scale: float) -> float:
    if scale <= 0.0:
        return 0.0
    return max(-1.0, min(1.0, float(value) / float(scale)))



def _color_for_value(value: float, scale: float) -> List[int]:
    normalized = _normalized_value(value, scale)
    if normalized >= 0.0:
        return _interpolate(HEATMAP_COLOR_MID, HEATMAP_COLOR_POSITIVE, normalized)
    return _interpolate(HEATMAP_COLOR_MID, HEATMAP_COLOR_NEGATIVE, abs(normalized))



def _radius_for_value(value: float, scale: float) -> float:
    normalized = abs(_normalized_value(value, scale))
    return 28_000.0 + (normalized * 80_000.0)



def _format_timestamp(value: Any) -> str:
    if value is None:
        return "Unknown"
    text = str(value).strip()
    if "T" in text:
        text = text.replace("T", " ")
    if "+" in text:
        text = text.split("+", 1)[0].strip()
    return text or "Unknown"



def _tooltip_html(point: HeatmapPoint) -> str:
    return (
        f"<div style='font-family: sans-serif; min-width: 260px;'>"
        f"<div style='font-weight: 700; margin-bottom: 4px;'>{escape(point.destiny_name)}</div>"
        f"<div>Road cost: R$ {point.road_cost_r:,.2f}</div>"
        f"<div>Multimodal cost: R$ {point.multimodal_cost_r:,.2f}</div>"
        f"<div>Cost advantage: R$ {point.cost_delta_r:,.2f}</div>"
        f"<div>Road emissions: {point.road_emissions_kg:,.1f} kg CO2e</div>"
        f"<div>Multimodal emissions: {point.multimodal_emissions_kg:,.1f} kg CO2e</div>"
        f"<div>Emissions advantage: {point.emissions_delta_kg:,.1f} kg CO2e</div>"
        f"<div>Nearest destination port: {escape(point.port_destiny_name or 'n/a')}</div>"
        f"<div>Last updated: {escape(_format_timestamp(point.updated_timestamp))}</div>"
        f"</div>"
    )



def _point_rows(dataset: HeatmapDataset, metric: str) -> List[dict[str, Any]]:
    scale = dataset.max_abs_cost_delta if metric == "cost" else dataset.max_abs_emissions_delta
    rows: List[dict[str, Any]] = []
    for point in dataset.points:
        value = point.cost_delta_r if metric == "cost" else point.emissions_delta_kg
        rows.append(
            {
                "lat": point.destiny_lat,
                "lon": point.destiny_lon,
                "value": value,
                "fill_color": _color_for_value(value, scale),
                "radius": _radius_for_value(value, scale),
                "tooltip_html": _tooltip_html(point),
            }
        )
    return rows



def _legend_text(metric: str) -> tuple[str, str, str, str]:
    if metric == "cost":
        return (
            "Cost view",
            "Green: multimodal is cheaper",
            "Yellow: near cost parity",
            "Red: road is cheaper",
        )
    return (
        "Emissions view",
        "Green: multimodal emits less",
        "Yellow: near emissions parity",
        "Red: road emits less",
    )



def render_legend(metric: str) -> None:
    title, green_text, mid_text, red_text = _legend_text(metric)
    gradient = f"linear-gradient(90deg, rgb{HEATMAP_COLOR_NEGATIVE}, rgb{HEATMAP_COLOR_MID}, rgb{HEATMAP_COLOR_POSITIVE})"
    st.markdown(
        f"""
        <div style='padding: 0.9rem 1rem; border: 1px solid rgba(16, 24, 40, 0.12); border-radius: 14px; background: rgba(255, 255, 255, 0.9); margin-bottom: 0.9rem;'>
            <div style='font-weight: 700; margin-bottom: 0.5rem;'>{escape(title)}</div>
            <div style='height: 12px; border-radius: 999px; background: {gradient}; margin-bottom: 0.55rem;'></div>
            <div style='font-size: 0.92rem; line-height: 1.5;'>
                <div>{escape(green_text)}</div>
                <div>{escape(mid_text)}</div>
                <div>{escape(red_text)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_heatmap_map(dataset: HeatmapDataset, metric: str) -> None:
    rows = _point_rows(dataset, metric)
    deck = pdk.Deck(
        map_style=HEATMAP_MAP_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=HEATMAP_BRAZIL_CENTER_LAT,
            longitude=HEATMAP_BRAZIL_CENTER_LON,
            zoom=HEATMAP_BRAZIL_ZOOM,
            pitch=0,
            bearing=0,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=rows,
                get_position="[lon, lat]",
                get_fill_color="fill_color",
                get_radius="radius",
                pickable=True,
                stroked=True,
                get_line_color=[28, 28, 28, 140],
                line_width_min_pixels=1,
                opacity=0.8,
            )
        ],
        tooltip={
            "html": "{tooltip_html}",
            "style": {
                "backgroundColor": "rgba(12, 16, 23, 0.92)",
                "color": "white",
                "fontSize": "13px",
            },
        },
    )
    st.pydeck_chart(deck, use_container_width=True)
