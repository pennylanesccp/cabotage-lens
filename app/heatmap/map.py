from __future__ import annotations

from html import escape
from typing import Any, List

import pydeck as pdk
import streamlit as st

from app.components.deck import render_deck_chart
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
    HEATMAP_MAP_HEIGHT,
    HEATMAP_POINT_OVERLAY_RADIUS_M,
    HEATMAP_SURFACE_SIDE_WALL_ALPHA,
    HEATMAP_SURFACE_SIDE_WALL_NEUTRAL,
    HEATMAP_SURFACE_SIDE_WALL_TINT_RATIO,
    HEATMAP_SURFACE_TOP_CAP_LIFT_M,
    HEATMAP_SURFACE_ZERO_PLANE_ELEVATION_M,
)
from app.heatmap.surface import build_surface
from app.heatmap.types import HeatmapDataset, HeatmapPoint, HeatmapSurface, HeatmapSurfaceCell

_HEATMAP_MAP_CSS = """
<style>
    .heatmap-legend-card {
        padding: 0.7rem 0.9rem;
        border: 1px solid rgba(255, 255, 255, 0.0);
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.92));
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        margin-bottom: 0.65rem;
    }
    .heatmap-legend-card__title {
        color: #0f172a;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .heatmap-legend-card__gradient {
        height: 14px;
        border-radius: 999px;
        margin-bottom: 0.45rem;
        border: 1px solid rgba(148, 163, 184, 0.12);
    }
    .heatmap-legend-card__body {
        font-size: 0.86rem;
        line-height: 1.4;
    }
    .heatmap-legend-card__semantic {
        color: #0f172a;
        font-weight: 600;
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
        percentage_label = "Cost advantage"
        absolute_label = "Cost difference"
        absolute_value = _format_signed_currency(cell.absolute_value)
    else:
        percentage_label = "Emissions advantage"
        absolute_label = "Emissions difference"
        absolute_value = _format_signed_emissions(cell.absolute_value)

    return (
        f"<div style='font-family: sans-serif; min-width: 220px;'>"
        f"<div style='font-weight: 700; margin-bottom: 4px;'>Surface cell</div>"
        f"<div>{escape(percentage_label)}: {cell.percentage_value:,.2f}%</div>"
        f"<div>{escape(absolute_label)}: {escape(absolute_value)}</div>"
        f"<div>Reference city: {escape(reference_label)}</div>"
        f"</div>"
    )


def _point_tooltip_html(point: HeatmapPoint) -> str:
    return (
        f"<div style='font-family: sans-serif; min-width: 240px;'>"
        f"<div style='font-weight: 700; margin-bottom: 4px;'>{escape(point.destiny_name)}</div>"
        f"<div>Road cost: R$ {point.road_cost_r:,.2f}</div>"
        f"<div>Multimodal cost: R$ {point.multimodal_cost_r:,.2f}</div>"
        f"<div>Cost difference: {_format_signed_currency(point.cost_delta_r)}</div>"
        f"<div>Cost advantage (%): {_safe_percentage(point.cost_savings_pct, point.cost_delta_r, point.road_cost_r):,.2f}%</div>"
        f"<div>Road emissions: {point.road_emissions_kg:,.1f} kg CO2e</div>"
        f"<div>Multimodal emissions: {point.multimodal_emissions_kg:,.1f} kg CO2e</div>"
        f"<div>Emissions difference: {_format_signed_emissions(point.emissions_delta_kg)}</div>"
        f"<div>Emissions advantage (%): {_safe_percentage(point.emissions_savings_pct, point.emissions_delta_kg, point.road_emissions_kg):,.2f}%</div>"
        f"<div>Nearest destination port: {escape(point.port_destiny_name or 'n/a')}</div>"
        f"</div>"
    )


def _safe_percentage(raw_value: float | None, absolute_value: float, baseline: float) -> float:
    if raw_value is not None:
        return float(raw_value)
    if not baseline:
        return 0.0
    return (float(absolute_value) / float(baseline)) * 100.0


def _muted_side_fill_color(fill_color: tuple[int, int, int, int]) -> list[int]:
    tint_ratio = min(max(float(HEATMAP_SURFACE_SIDE_WALL_TINT_RATIO), 0.0), 1.0)
    rgb = [
        int(round((float(channel) * tint_ratio) + (float(neutral) * (1.0 - tint_ratio))))
        for channel, neutral in zip(fill_color[:3], HEATMAP_SURFACE_SIDE_WALL_NEUTRAL)
    ]
    return [*rgb, int(HEATMAP_SURFACE_SIDE_WALL_ALPHA)]


def _surface_body_rows(surface: HeatmapSurface, metric: str) -> List[dict[str, Any]]:
    zero_plane = float(HEATMAP_SURFACE_ZERO_PLANE_ELEVATION_M)
    return [
        {
            "polygon": [[lon, lat, zero_plane] for lon, lat in cell.polygon],
            "fill_color": _muted_side_fill_color(cell.fill_color),
            "elevation": float(cell.elevation_m),
            "tooltip_html": _surface_tooltip_html(cell, metric),
        }
        for cell in surface.cells
    ]


def _surface_cap_rows(surface: HeatmapSurface, metric: str) -> List[dict[str, Any]]:
    cap_lift = float(HEATMAP_SURFACE_TOP_CAP_LIFT_M)
    zero_plane = float(HEATMAP_SURFACE_ZERO_PLANE_ELEVATION_M)
    return [
        {
            "polygon": [[lon, lat, zero_plane + float(cell.elevation_m) + cap_lift] for lon, lat in cell.polygon],
            "fill_color": list(cell.fill_color),
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


def _legend_labels(metric: str, surface: HeatmapSurface) -> tuple[str, list[str], list[str]]:
    if metric == "cost":
        title = "3D cost surface"
        height_line = "Height shows signed cost difference around a zero plane, with road-favoring cells below it and multimodal-favoring cells above it."
    else:
        title = "3D emissions surface"
        height_line = "Height shows signed emissions difference around a zero plane, with road-favoring cells below it and multimodal-favoring cells above it."

    semantic_lines = [
        "Orange-red favors road, golden sand marks parity, green favors multimodal.",
    ]
    helper_lines = [
        "Color lives on the raised top surface and shows relative advantage across the interpolated terrain.",
        height_line,
    ]
    return title, semantic_lines, helper_lines


def render_legend(metric: str, surface: HeatmapSurface) -> None:
    _inject_heatmap_map_css()
    title, semantic_lines, helper_lines = _legend_labels(metric, surface)
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
    body_rows = _surface_body_rows(surface, metric)
    cap_rows = _surface_cap_rows(surface, metric)

    layers: list[pdk.Layer] = [
        pdk.Layer(
            "PolygonLayer",
            data=body_rows,
            get_polygon="polygon",
            get_fill_color="fill_color",
            get_elevation="elevation",
            pickable=True,
            extruded=True,
            stroked=False,
            filled=True,
            wireframe=False,
            elevation_scale=1.0,
            opacity=0.92,
        ),
        pdk.Layer(
            "PolygonLayer",
            data=cap_rows,
            get_polygon="polygon",
            get_fill_color="fill_color",
            pickable=True,
            extruded=False,
            stroked=False,
            filled=True,
            wireframe=False,
            opacity=0.98,
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
                radius_max_pixels=5,
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
    render_deck_chart(deck, height=HEATMAP_MAP_HEIGHT, require_ctrl_for_wheel_zoom=True)
    return surface
