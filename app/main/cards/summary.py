from __future__ import annotations

from html import escape
from typing import Any, Mapping

from app.main.cards.metrics import best_option, multimodal_total_distance
from app.main.utils.formatters import fmt_currency_brl, fmt_distance_km, fmt_emissions_kg, safe_float


def render_cards_overlay(results: Mapping[str, Any] | None) -> str:
    if not results:
        return (
            "<div class='map-overlay-cards'>"
            "<article class='overlay-card overlay-note'>"
            "<h4>Run analysis</h4>"
            "<p>Map overlays appear here with route totals.</p>"
            "</article>"
            "</div>"
        )

    road = results.get("road_only", {})
    mm = results.get("multimodal", {})
    comp = results.get("comparison", {})

    road_cost = safe_float(road.get("cost"))
    mm_cost = safe_float(mm.get("total_cost"))
    road_co2e = safe_float(road.get("co2e"))
    mm_co2e = safe_float(mm.get("total_co2e"))

    return f"""
<div class='map-overlay-cards'>
  <article class='overlay-card'>
    <h4>Road</h4>
    <p>{fmt_distance_km(road.get('distance_km'))}</p>
    <p>{fmt_currency_brl(road_cost)}</p>
    <p>{fmt_emissions_kg(road_co2e)}</p>
  </article>
  <article class='overlay-card'>
    <h4>Multimodal (Road + Cabotage)</h4>
    <p>{fmt_distance_km(multimodal_total_distance(results))}</p>
    <p>{fmt_currency_brl(mm_cost)}</p>
    <p>{fmt_emissions_kg(mm_co2e)}</p>
  </article>
  <article class='overlay-card overlay-highlight'>
    <h4>Best option: {escape(best_option(results))}</h4>
    <p>Delta cost: {fmt_currency_brl(comp.get('delta_cost'))}</p>
    <p>Delta emissions: {fmt_emissions_kg(comp.get('delta_co2e'))}</p>
  </article>
</div>
"""
