from __future__ import annotations

from html import escape
from typing import Any, Mapping

import streamlit as st

from app.main.cards.metrics import multimodal_total_distance
from app.main.utils.formatters import fmt_currency_brl_rounded, fmt_distance_km_rounded, fmt_emissions_compact


def _metric_cell(title: str, value: str) -> str:
    return (
        "<div class='summary-panel__metric'>"
        f"<p class='summary-panel__label'>{escape(title)}</p>"
        f"<p class='summary-panel__value'>{escape(value)}</p>"
        "</div>"
    )


def _scenario_panel(
    *,
    title: str,
    accent: str,
    metrics: list[tuple[str, str]],
) -> str:
    return (
        f"<article class='summary-panel' data-accent='{escape(accent)}'>"
        "<header class='summary-panel__header'>"
        f"<p class='summary-panel__eyebrow'>{escape(title)}</p>"
        "</header>"
        "<div class='summary-panel__metrics'>"
        + "".join(_metric_cell(metric_title, metric_value) for metric_title, metric_value in metrics)
        + "</div>"
        "</article>"
    )


def _value_or_placeholder(results: Mapping[str, Any] | None, value: str) -> str:
    return value if results else "-"


def render_summary_cards(results: Mapping[str, Any] | None) -> None:
    road = (results or {}).get("road_only", {})
    multimodal = (results or {}).get("multimodal", {})

    multimodal_metrics = [
        ("Fuel cost", _value_or_placeholder(results, fmt_currency_brl_rounded(multimodal.get("total_cost")))),
        ("Emissions", _value_or_placeholder(results, fmt_emissions_compact(multimodal.get("total_co2e")))),
        ("Distance", _value_or_placeholder(results, fmt_distance_km_rounded(multimodal_total_distance(results or {})))),
    ]
    road_metrics = [
        ("Fuel cost", _value_or_placeholder(results, fmt_currency_brl_rounded(road.get("cost")))),
        ("Emissions", _value_or_placeholder(results, fmt_emissions_compact(road.get("co2e")))),
        ("Distance", _value_or_placeholder(results, fmt_distance_km_rounded(road.get("distance_km")))),
    ]

    cards_html = (
        "<section class='summary-panels'>"
        + _scenario_panel(
            title="Multimodal",
            accent="multimodal",
            metrics=multimodal_metrics,
        )
        + _scenario_panel(
            title="Road Only",
            accent="road",
            metrics=road_metrics,
        )
        + "</section>"
    )
    st.markdown(cards_html, unsafe_allow_html=True)
