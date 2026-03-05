from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from app.main.utils.formatters import fmt_currency_brl, fmt_distance_km, fmt_emissions_kg, safe_float


def _maritime_component_breakdown(results: Mapping[str, Any]) -> dict[str, float]:
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


def _summary_table(results: Mapping[str, Any]) -> pd.DataFrame:
    road = results.get("road_only", {})
    mm = results.get("multimodal", {})

    mm_distance = (
        safe_float(mm.get("first_mile", {}).get("distance_km"))
        + safe_float(mm.get("sea", {}).get("distance_km"))
        + safe_float(mm.get("last_mile", {}).get("distance_km"))
    )

    return pd.DataFrame(
        [
            {
                "Route": "Road",
                "Distance": fmt_distance_km(road.get("distance_km")),
                "Cost": fmt_currency_brl(road.get("cost")),
                "Emissions": fmt_emissions_kg(road.get("co2e")),
            },
            {
                "Route": "Multimodal (Road + Cabotage)",
                "Distance": fmt_distance_km(mm_distance),
                "Cost": fmt_currency_brl(mm.get("total_cost")),
                "Emissions": fmt_emissions_kg(mm.get("total_co2e")),
            },
        ]
    )


def _legs_table(results: Mapping[str, Any]) -> pd.DataFrame:
    mm = results.get("multimodal", {})
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})
    maritime = _maritime_component_breakdown(results)

    return pd.DataFrame(
        [
            {
                "Leg": "Road to port (pre-carriage)",
                "Distance": fmt_distance_km(first.get("distance_km")),
                "Cost": fmt_currency_brl(first.get("cost")),
                "Emissions": fmt_emissions_kg(first.get("co2e")),
            },
            {
                "Leg": "Sea leg (cabotage)",
                "Distance": fmt_distance_km(sea.get("distance_km")),
                "Cost": fmt_currency_brl(maritime.get("sailing_cost_brl")),
                "Emissions": fmt_emissions_kg(maritime.get("sailing_co2e_kg")),
            },
            {
                "Leg": "Port ops",
                "Distance": "-",
                "Cost": fmt_currency_brl(maritime.get("port_ops_cost_brl")),
                "Emissions": fmt_emissions_kg(maritime.get("port_ops_co2e_kg")),
            },
            {
                "Leg": "Hoteling",
                "Distance": "-",
                "Cost": fmt_currency_brl(maritime.get("hoteling_cost_brl")),
                "Emissions": fmt_emissions_kg(maritime.get("hoteling_co2e_kg")),
            },
            {
                "Leg": "Road from port (on-carriage)",
                "Distance": fmt_distance_km(last.get("distance_km")),
                "Cost": fmt_currency_brl(last.get("cost")),
                "Emissions": fmt_emissions_kg(last.get("co2e")),
            },
        ]
    )


def render_breakdown(results: Mapping[str, Any]) -> None:
    st.markdown("**Total summary**")
    st.dataframe(_summary_table(results), hide_index=True, use_container_width=True)
    st.markdown("**Multimodal leg breakdown**")
    st.dataframe(_legs_table(results), hide_index=True, use_container_width=True)

