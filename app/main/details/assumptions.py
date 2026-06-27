from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from app.main.utils.formatters import safe_float


def _assumptions_table(results: Mapping[str, Any], payload: Mapping[str, Any]) -> pd.DataFrame:
    inputs = results.get("inputs", {})
    hoteling_reason = str(inputs.get("hoteling_exclusion_reason") or "").strip()
    if bool(inputs.get("include_hoteling")):
        hoteling_value = "enabled"
    elif hoteling_reason == "included_in_transport_work_intensity":
        hoteling_value = "skipped (already covered by MRV transport-work intensity)"
    else:
        hoteling_value = "disabled"

    rows = [
        (
            "Truck preset",
            "Road vehicle configuration used for the road-only route and the road legs in multimodal routing.",
            str(payload.get("truck_key") or "n/a"),
        ),
        (
            "Vessel class",
            "Container vessel class used to select maritime fuel intensity, fallback hoteling, and other sea-leg factors.",
            str(inputs.get("vessel_class") or payload.get("vessel_class") or "n/a"),
        ),
        (
            "Diesel price source",
            "Source table used to value truck diesel consumption in BRL.",
            str(inputs.get("diesel_price_source") or "n/a"),
        ),
        (
            "Marine fuel type",
            "Fuel assumption applied to cabotage fuel-cost and emissions calculations.",
            str(inputs.get("marine_fuel_type") or "n/a"),
        ),
        (
            "Marine EF",
            "Operational TTW emission factor applied per kilogram of marine fuel burned.",
            f"{safe_float(inputs.get('marine_ef_kg_per_kg')):.4f} kg CO2e/kg",
        ),
        (
            "Emissions boundary",
            "Displayed emissions use the current operational TTW CO2e boundary unless an explicit override says otherwise.",
            "TTW CO2e",
        ),
        (
            "Cost boundary",
            "Displayed cost values are model estimates/proxies, not complete commercial freight rates.",
            "operational estimate",
        ),
        (
            "Allocation mode",
            "Method used to allocate vessel totals to the cargo share represented by this scenario.",
            str(inputs.get("allocation_mode_used") or payload.get("allocation_mode") or "auto"),
        ),
        (
            "TEU load factor",
            "Utilization factor applied when converting vessel capacity into effective carried container load.",
            f"{safe_float(inputs.get('allocation_load_factor')):.2f}",
        ),
        (
            "Port ops scenario",
            "Parameter set used for port handling time, cost, fuel, and emissions assumptions.",
            str(payload.get("port_ops_scenario") or "n/a"),
        ),
        (
            "Hoteling",
            "Whether berth-side auxiliary fuel use and emissions are included while the vessel is in port.",
            hoteling_value,
        ),
    ]
    return pd.DataFrame(rows, columns=["Parameter", "Description", "Value"])


def render_assumptions(results: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    st.dataframe(_assumptions_table(results=results, payload=payload), hide_index=True, width="stretch")
