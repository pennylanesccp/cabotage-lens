from __future__ import annotations

from html import escape
from typing import Any, Mapping

import streamlit as st

from app.main.cards.metrics import multimodal_total_distance
from app.main.utils.formatters import fmt_currency_brl_rounded, fmt_distance_km_rounded, fmt_emissions_compact


def _metric_card(title: str, scenario: str, accent: str, value: str) -> str:
    return (
        f"<article class='summary-card' data-accent='{escape(accent)}'>"
        f"<p class='summary-card__eyebrow'>{escape(scenario)}</p>"
        f"<h3>{escape(title)}</h3>"
        f"<p class='summary-card__value'>{escape(value)}</p>"
        "</article>"
    )


def _value_or_placeholder(results: Mapping[str, Any] | None, value: str) -> str:
    return value if results else "-"


def render_summary_cards(results: Mapping[str, Any] | None) -> None:
    road = (results or {}).get("road_only", {})
    multimodal = (results or {}).get("multimodal", {})

    cards_html = (
        "<section class='summary-groups'>"
        + _metric_card(
            title="Fuel cost",
            scenario="Multimodal",
            accent="multimodal",
            value=_value_or_placeholder(results, fmt_currency_brl_rounded(multimodal.get("total_cost"))),
        )
        + _metric_card(
            title="Emissions",
            scenario="Multimodal",
            accent="multimodal",
            value=_value_or_placeholder(results, fmt_emissions_compact(multimodal.get("total_co2e"))),
        )
        + _metric_card(
            title="Distance",
            scenario="Multimodal",
            accent="multimodal",
            value=_value_or_placeholder(results, fmt_distance_km_rounded(multimodal_total_distance(results or {}))),
        )
        + _metric_card(
            title="Fuel cost",
            scenario="Road Only",
            accent="road",
            value=_value_or_placeholder(results, fmt_currency_brl_rounded(road.get("cost"))),
        )
        + _metric_card(
            title="Emissions",
            scenario="Road Only",
            accent="road",
            value=_value_or_placeholder(results, fmt_emissions_compact(road.get("co2e"))),
        )
        + _metric_card(
            title="Distance",
            scenario="Road Only",
            accent="road",
            value=_value_or_placeholder(results, fmt_distance_km_rounded(road.get("distance_km"))),
        )
        + "</section>"
    )
    st.markdown(cards_html, unsafe_allow_html=True)
