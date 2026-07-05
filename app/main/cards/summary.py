from __future__ import annotations

from html import escape
from typing import Any, Mapping

import streamlit as st

from app.main.cards.metrics import multimodal_total_distance
from app.main.utils.formatters import (
    fmt_currency_brl_rounded,
    fmt_distance_km_rounded,
    fmt_emissions_compact,
    safe_float,
)


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
    subhead: str,
    accent: str,
    metrics: list[tuple[str, str]],
) -> str:
    return (
        f"<article class='summary-panel' data-accent='{escape(accent)}'>"
        "<header class='summary-panel__header'>"
        f"<p class='summary-panel__eyebrow'>{escape(title)}</p>"
        f"<p class='summary-panel__subhead'>{escape(subhead)}</p>"
        "</header>"
        "<div class='summary-panel__metrics'>"
        + "".join(_metric_cell(metric_title, metric_value) for metric_title, metric_value in metrics)
        + "</div>"
        "</article>"
    )


def _value_or_placeholder(results: Mapping[str, Any] | None, value: str) -> str:
    return value if results else "-"


def _insight_card(label: str, value: str, note: str) -> str:
    return (
        "<article class='insight-card'>"
        f"<p class='insight-card__label'>{escape(label)}</p>"
        f"<p class='insight-card__value'>{escape(value)}</p>"
        f"<p class='insight-card__note'>{escape(note)}</p>"
        "</article>"
    )


def _delta_statement(
    *,
    results: Mapping[str, Any] | None,
    delta: Any,
    formatter: Any,
    metric_label: str,
) -> tuple[str, str]:
    if not results:
        return "Awaiting analysis", f"{metric_label} comparison appears after a completed route run."

    numeric_delta = safe_float(delta)
    formatted = formatter(abs(numeric_delta))
    if numeric_delta < 0:
        return f"Multimodal lower by {formatted}", "Difference is multimodal minus direct-road reference."
    if numeric_delta > 0:
        return f"Road lower by {formatted}", "Difference is multimodal minus direct-road reference."
    return "No modelled difference", "Values are equal at the displayed precision."


def _render_section_heading(results: Mapping[str, Any] | None) -> None:
    if results:
        body = "Read the headline cost and operational TTW CO2e comparison before inspecting route legs and provenance."
    else:
        body = "Run a scenario from the sidebar to populate costs, operational TTW CO2e, routes, and data-quality notes."
    st.markdown(
        f"""
        <div class='section-heading'>
            <p class='section-heading__kicker'>Route comparison</p>
            <h2>Scenario summary</h2>
            <p>{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_cards(results: Mapping[str, Any] | None) -> None:
    road = (results or {}).get("road_only", {})
    multimodal = (results or {}).get("multimodal", {})
    comparison = (results or {}).get("comparison", {})

    multimodal_metrics = [
        ("Cost estimate", _value_or_placeholder(results, fmt_currency_brl_rounded(multimodal.get("total_cost")))),
        ("TTW CO2e", _value_or_placeholder(results, fmt_emissions_compact(multimodal.get("total_co2e")))),
        ("Distance", _value_or_placeholder(results, fmt_distance_km_rounded(multimodal_total_distance(results or {})))),
    ]
    road_metrics = [
        ("Cost estimate", _value_or_placeholder(results, fmt_currency_brl_rounded(road.get("cost")))),
        ("TTW CO2e", _value_or_placeholder(results, fmt_emissions_compact(road.get("co2e")))),
        ("Distance", _value_or_placeholder(results, fmt_distance_km_rounded(road.get("distance_km")))),
    ]

    cost_value, cost_note = _delta_statement(
        results=results,
        delta=comparison.get("delta_cost"),
        formatter=fmt_currency_brl_rounded,
        metric_label="Cost",
    )
    emissions_value, emissions_note = _delta_statement(
        results=results,
        delta=comparison.get("delta_co2e"),
        formatter=fmt_emissions_compact,
        metric_label="Emissions",
    )

    _render_section_heading(results)
    st.markdown(
        "<section class='insight-strip'>"
        + _insight_card("Cost difference", cost_value, cost_note)
        + _insight_card("Emissions difference", emissions_value, emissions_note)
        + "</section>",
        unsafe_allow_html=True,
    )

    cards_html = (
        "<section class='summary-panels'>"
        + _scenario_panel(
            title="Multimodal",
            subhead="Road access legs plus cabotage sea leg.",
            accent="multimodal",
            metrics=multimodal_metrics,
        )
        + _scenario_panel(
            title="Road only",
            subhead="Direct-road reference for the same cargo.",
            accent="road",
            metrics=road_metrics,
        )
        + "</section>"
    )
    st.markdown(cards_html, unsafe_allow_html=True)
