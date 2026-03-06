from __future__ import annotations

from html import escape
from typing import Any, Mapping

import streamlit as st

from app.main.cards.metrics import multimodal_total_distance
from app.main.utils.formatters import fmt_currency_brl_compact, fmt_distance_km_compact, fmt_emissions_compact


def _metric_row(label: str, value: str) -> str:
    return (
        "<div class='summary-card__row'>"
        f"<span class='summary-card__label'>{escape(label)}</span>"
        f"<strong class='summary-card__value'>{escape(value)}</strong>"
        "</div>"
    )


def _route_card(title: str, accent: str, metrics: list[tuple[str, str]]) -> str:
    rows = "".join(_metric_row(label=label, value=value) for label, value in metrics)
    return (
        f"<article class='summary-card' data-accent='{escape(accent)}'>"
        "<p class='summary-card__eyebrow'>Scenario</p>"
        f"<h3>{escape(title)}</h3>"
        f"<div class='summary-card__metrics'>{rows}</div>"
        "</article>"
    )


def _value_or_placeholder(results: Mapping[str, Any] | None, value: str) -> str:
    return value if results else "-"


def render_summary_cards(results: Mapping[str, Any] | None) -> None:
    road = (results or {}).get("road_only", {})
    multimodal = (results or {}).get("multimodal", {})

    multimodal_metrics = [
        ("Total cost", _value_or_placeholder(results, fmt_currency_brl_compact(multimodal.get("total_cost")))),
        ("Total emissions", _value_or_placeholder(results, fmt_emissions_compact(multimodal.get("total_co2e")))),
        ("Distance", _value_or_placeholder(results, fmt_distance_km_compact(multimodal_total_distance(results or {})))),
    ]
    road_metrics = [
        ("Total cost", _value_or_placeholder(results, fmt_currency_brl_compact(road.get("cost")))),
        ("Total emissions", _value_or_placeholder(results, fmt_emissions_compact(road.get("co2e")))),
        ("Distance", _value_or_placeholder(results, fmt_distance_km_compact(road.get("distance_km")))),
    ]

    cards_html = (
        "<section class='summary-groups'>"
        + _route_card("Multimodal", "multimodal", multimodal_metrics)
        + _route_card("Road Only", "road", road_metrics)
        + "</section>"
    )
    st.markdown(cards_html, unsafe_allow_html=True)
