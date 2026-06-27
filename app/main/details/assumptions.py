from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from app.main.utils.formatters import safe_float
from modules.multimodal.distance_provenance import maritime_distance_source_type

_SOURCE_TYPE_LABELS = {
    "seamatrix": "SeaMatrix distance",
    "haversine_fallback": "Fallback estimate",
    "manual_override": "Manual override",
    "external_reference": "External reference",
}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _maritime_source_rows(results: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    sea = results.get("multimodal", {}).get("sea", {})
    if not isinstance(sea, Mapping):
        return []

    provenance = sea.get("distance_provenance")
    if not isinstance(provenance, Mapping):
        provenance = {}

    source = _clean_text(provenance.get("source") or sea.get("distance_source"))
    raw_source_type = _clean_text(provenance.get("source_type"))
    source_type = None
    if source or raw_source_type:
        normalized = maritime_distance_source_type(source, source_type=raw_source_type)
        source_type = None if normalized == "unknown" else normalized

    if not source and not source_type:
        return []

    label = _SOURCE_TYPE_LABELS.get(source_type or "", "Maritime distance source")
    if source_type and source:
        value = f"{label} ({source_type}): {source}"
    elif source_type:
        value = f"{label} ({source_type})"
    else:
        value = source or "n/a"

    rows = [
        (
            "Maritime distance source",
            "Source used for the sea-leg distance. Distance source affects route confidence, not the emission factor itself.",
            value,
        )
    ]

    caution_by_type = {
        "haversine_fallback": "Fallback estimate; treat route confidence as lower until checked against corridor evidence.",
        "manual_override": "Manual override; review documented provenance before route-level conclusions.",
        "external_reference": "External reference; confirm it matches the selected ports and corridor boundary.",
    }
    caution = caution_by_type.get(source_type or "")
    if caution:
        rows.append(
            (
                "Maritime distance note",
                "Short caution for distance sources that affect route-confidence interpretation.",
                caution,
            )
        )

    return rows


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
        *_maritime_source_rows(results),
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
