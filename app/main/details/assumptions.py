from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from app.main.utils.formatters import safe_float


def _assumptions_table(results: Mapping[str, Any], payload: Mapping[str, Any]) -> pd.DataFrame:
    inputs = results.get("inputs", {})
    rows = [
        ("Truck preset", str(payload.get("truck_key") or "n/a")),
        ("Vessel class", str(inputs.get("vessel_class") or payload.get("vessel_class") or "n/a")),
        ("Diesel price source", str(inputs.get("diesel_price_source") or "n/a")),
        ("Marine fuel type", str(inputs.get("marine_fuel_type") or "n/a")),
        ("Marine EF", f"{safe_float(inputs.get('marine_ef_kg_per_kg')):.4f} kg CO2e/kg"),
        ("Allocation mode", str(inputs.get("allocation_mode_used") or payload.get("allocation_mode") or "auto")),
        ("TEU load factor", f"{safe_float(inputs.get('allocation_load_factor')):.2f}"),
        ("Port ops scenario", str(payload.get("port_ops_scenario") or "n/a")),
        ("Hoteling", "enabled" if payload.get("include_hoteling") else "disabled"),
    ]
    return pd.DataFrame(rows, columns=["Parameter", "Value"])


def render_assumptions(results: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    st.dataframe(_assumptions_table(results=results, payload=payload), hide_index=True, width="stretch")

