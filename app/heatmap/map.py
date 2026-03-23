from __future__ import annotations

from html import escape
from typing import Any, List

import pydeck as pdk
import streamlit as st

from app.heatmap.config import (
    HEATMAP_3D_BEARING,
    HEATMAP_3D_PITCH,
    HEATMAP_BRAZIL_CENTER_LAT,
    HEATMAP_BRAZIL_CENTER_LON,
    HEATMAP_BRAZIL_ZOOM,
    HEATMAP_COLOR_MID,
    HEATMAP_COLOR_NEGATIVE,
    HEATMAP_COLOR_POSITIVE,
    HEATMAP_MAP_STYLE,
    HEATMAP_POINT_OVERLAY_RADIUS_M,
)
from app.heatmap.surface import build_surface
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapSurface, HeatmapSurfaceCell

_HEATMAP_MAP_CSS = """
<style>
    div[data-testid="stDeckGlJsonChart"] {
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 22px;
        overflow: hidden;
        background: rgba(248, 250, 252, 0.92);
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
    }
    div[data-testid="stDeckGlJsonChart"] * {
        outline: none !important;
    }
    .heatmap-legend-card {
        padding: 0.95rem 1rem;
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        margin-bottom: 0.9rem;
    }
    .heatmap-legend-card__title {
        color: #0f172a;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .heatmap-legend-card__gradient {
        height: 12px;
        border-radius: 999px;
        margin-bottom: 0.6rem;
        border: 1px solid rgba(148, 163, 184, 0.18);
    }
    .heatmap-legend-card__body {
        font-size: 0.92rem;
        line-height: 1.5;
    }
    .heatmap-legend-card__semantic {
        color: #0f172a;
    }
    .heatmap-legend-card__helper {
        color: #334155;
    }
    .heatmap-legend-card__scale {
        color: #0f172a;
        font-weight: 600;
    }
</style>
"""


def _format_timestamp(value: Any) -> str:
    if value is None:
        return "Unknown"
    text = str(value).strip()
    if "T" in text:
        text = text.replace("T", " ")
    if "+" in text:
        text = text.split("+", 1)[0].strip()
    return text or "Unknown"


def _format_signed_currency(value: float) -> str:
    return f"R$ {value:,.2f}"


def _format_signed_emissions(value: float) -> str:
    return f"{value:,.1f} kg CO2e"


def _reference_city_label(name: str, uf: str | None) -> str:
    if not name:
        return "Unavailable"
    return f"{name}, {uf}" if uf else name


def _surface_tooltip_html(cell: HeatmapSurfaceCell, metric: str) -> str:
    reference_label = _reference_city_label(cell.nearest_destiny_name, cell.nearest_destiny_uf)
    if metric == "cost":
        percentage_label = "Interpolated cost advantage"
        absolute_label = "Interpolated signed absolute advantage"
        absolute_value = _format_signed_currency(cell.absolute_value)
    else:
        percentage_label = "Interpolated emissions advantage"
        absolute_label = "Interpolated signed absolute advantage"
        absolute_value = _format_signed_emissions(cell.absolute_value)

    return (
        f"<div style='font-family: sans-serif; min-width: 260px;'>"
        f"<div style='font-weight: 700; margin-bottom: 4px;'>Brazil surface cell</div>"
        f"<div>{escape(percentage_label)}: {cell.percentage_value:,.2f}%</div>"
        f"<div>{escape(absolute_label)}: {escape(absolute_value)}</div>"
        f"<div>Reference city: {escape(reference_label)}</div>"
        f"<div>Reference distance: {cell.nearest_distance_km:,.1f} km</div>"
        f"</div>"
    )


def _point_tooltip_html(point: HeatmapPoint) -> str:
    return (
        f"<div style='font-family: sans-serif; min-width: 260px;'>"
        f"<div style='font-weight: 700; margin-bottom: 4px;'>{escape(point.destiny_name)}</div>"
        f"<div>Road cost: R$ {point.road_cost_r:,.2f}</div>"
        f"<div>Multimodal cost: R$ {point.multimodal_cost_r:,.2f}</div>"
        f"<div>Cost advantage: {_format_signed_currency(point.cost_delta_r)}</div>"
        f"<div>Cost advantage (%): {_safe_percentage(point.cost_savings_pct, point.cost_delta_r, point.road_cost_r):,.2f}%</div>"
        f"<div>Road emissions: {point.road_emissions_kg:,.1f} kg CO2e</div>"
        f"<div>Multimodal emissions: {point.multimodal_emissions_kg:,.1f} kg CO2e</div>"
        f"<div>Emissions advantage: {_format_signed_emissions(point.emissions_delta_kg)}</div>"
        f"<div>Emissions advantage (%): {_safe_percentage(point.emissions_savings_pct, point.emissions_delta_kg, point.road_emissions_kg):,.2f}%</div>"
        f"<div>Nearest destination port: {escape(point.port_destiny_name or 'n/a')}</div>"
        f"<div>Last updated: {escape(_format_timestamp(point.updated_timestamp))}</div>"
        f"</div>"
    )


def _safe_percentage(raw_value: float | None, absolute_value: float, baseline: float) -> float:
    if raw_value is not None:
        return float(raw_value)
    if not baseline:
        return 0.0
    return (float(absolute_value) / float(baseline)) * 100.0


def _surface_rows(surface: HeatmapSurface, metric: str) -> List[dict[str, Any]]:
    return [
        {
            "polygon": [[lon, lat] for lon, lat in cell.polygon],
            "fill_color": list(cell.fill_color),
            "elevation": float(cell.elevation_m),
            "tooltip_html": _surface_tooltip_html(cell, metric),
        }
        for cell in surface.cells
    ]


def _point_rows(dataset: HeatmapDataset) -> List[dict[str, Any]]:
    return [
        {
            "position": [float(point.destiny_lon), float(point.destiny_lat)],
            "radius": float(HEATMAP_POINT_OVERLAY_RADIUS_M),
            "fill_color": [19, 31, 45, 170],
            "line_color": [255, 255, 255, 220],
            "tooltip_html": _point_tooltip_html(point),
        }
        for point in dataset.points
    ]


def _inject_heatmap_map_css() -> None:
    st.markdown(_HEATMAP_MAP_CSS, unsafe_allow_html=True)


def _legend_labels(metric: str, surface: HeatmapSurface) -> tuple[str, list[str], list[str], list[str]]:
    if metric == "cost":
        title = "3D cost surface"
        scale_text = f"Color scale: robust +/- {surface.color_scale:,.1f}% cost advantage"
        elevation_text = f"Height scale: robust +/- {_format_signed_currency(surface.elevation_scale)}"
    else:
        title = "3D emissions surface"
        scale_text = f"Color scale: robust +/- {surface.color_scale:,.1f}% emissions advantage"
        elevation_text = f"Height scale: robust +/- {_format_signed_emissions(surface.elevation_scale)}"

    semantic_lines = [
        "Green: multimodal is better",
        "Yellow: near parity",
        "Red: road is better",
    ]
    helper_lines = [
        "Color encodes relative advantage (%) across the interpolated surface.",
        "Surface coverage is limited to the convex hull of available destination cities.",
        "Height encodes signed absolute advantage: lower terrain favors road, higher terrain favors multimodal.",
    ]
    scale_lines = [scale_text, elevation_text]
    return title, semantic_lines, helper_lines, scale_lines


def render_legend(metric: str, surface: HeatmapSurface) -> None:
    _inject_heatmap_map_css()
    title, semantic_lines, helper_lines, scale_lines = _legend_labels(metric, surface)
    gradient = (
        f"linear-gradient(90deg, rgb{HEATMAP_COLOR_NEGATIVE}, "
        f"rgb{HEATMAP_COLOR_MID}, rgb{HEATMAP_COLOR_POSITIVE})"
    )
    st.markdown(
        f"""
        <section class='heatmap-legend-card'>
            <div class='heatmap-legend-card__title'>{escape(title)}</div>
            <div class='heatmap-legend-card__gradient' style='background: {gradient};'></div>
            <div class='heatmap-legend-card__body'>
                {''.join(f"<div class='heatmap-legend-card__semantic'>{escape(line)}</div>" for line in semantic_lines)}
                {''.join(f"<div class='heatmap-legend-card__helper'>{escape(line)}</div>" for line in helper_lines)}
                {''.join(f"<div class='heatmap-legend-card__scale'>{escape(line)}</div>" for line in scale_lines)}
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_heatmap_map(
    dataset: HeatmapDataset,
    metric: str,
    *,
    show_points: bool = False,
    surface: HeatmapSurface | None = None,
) -> HeatmapSurface:
    _inject_heatmap_map_css()
    surface = surface or build_surface(dataset, metric)
    surface_rows = _surface_rows(surface, metric)

    layers: list[pdk.Layer] = [
        pdk.Layer(
            "PolygonLayer",
            data=surface_rows,
            get_polygon="polygon",
            get_fill_color="fill_color",
            get_elevation="elevation",
            pickable=True,
            extruded=True,
            stroked=False,
            filled=True,
            wireframe=False,
            opacity=0.9,
        ),
    ]

    if show_points:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=_point_rows(dataset),
                get_position="position",
                get_fill_color="fill_color",
                get_line_color="line_color",
                get_radius="radius",
                radius_min_pixels=2,
                radius_max_pixels=6,
                stroked=True,
                line_width_min_pixels=1,
                pickable=True,
            )
        )

    deck = pdk.Deck(
        map_style=HEATMAP_MAP_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=HEATMAP_BRAZIL_CENTER_LAT,
            longitude=HEATMAP_BRAZIL_CENTER_LON,
            zoom=HEATMAP_BRAZIL_ZOOM,
            pitch=HEATMAP_3D_PITCH,
            bearing=HEATMAP_3D_BEARING,
        ),
        layers=layers,
        tooltip={
            "html": "{tooltip_html}",
            "style": {
                "backgroundColor": "rgba(12, 16, 23, 0.92)",
                "color": "white",
                "fontSize": "13px",
            },
        },
    )
    st.pydeck_chart(deck, width="stretch")
    return surface
