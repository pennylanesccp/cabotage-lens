from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from app.main.details.provenance import (
    basis_label,
    clean_text,
    extract_port_ops_payload,
    port_ops_has_unavailable,
    port_ops_source_level,
    source_level_label,
    warnings_summary,
)
from app.main.utils.formatters import (
    fmt_currency_brl,
    fmt_distance_km,
    fmt_emissions_kg,
    format_significant,
    safe_float,
)


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
                "Cost estimate": fmt_currency_brl(road.get("cost")),
                "TTW CO2e": fmt_emissions_kg(road.get("co2e")),
            },
            {
                "Route": "Multimodal (Road + Cabotage)",
                "Distance": fmt_distance_km(mm_distance),
                "Cost estimate": fmt_currency_brl(mm.get("total_cost")),
                "TTW CO2e": fmt_emissions_kg(mm.get("total_co2e")),
            },
        ]
    )


def _legs_table(results: Mapping[str, Any]) -> pd.DataFrame:
    mm = results.get("multimodal", {})
    first = mm.get("first_mile", {})
    last = mm.get("last_mile", {})
    sea = mm.get("sea", {})
    maritime = _maritime_component_breakdown(results)
    port_ops_payload = extract_port_ops_payload(sea) if isinstance(sea, Mapping) else {}
    port_ops_unavailable = bool(
        port_ops_source_level(sea) == "unavailable"
        or (
            port_ops_has_unavailable(sea)
            and safe_float(sea.get("port_ops_fuel_kg")) == 0.0
            and safe_float(sea.get("port_ops_co2e")) == 0.0
        )
    )
    port_ops_partial = bool(
        port_ops_has_unavailable(sea)
        and not port_ops_unavailable
        and port_ops_payload.get("missing_value_policy")
    )

    def _component_value(value: Any, formatter: Any, *, unavailable: bool = False, partial: bool = False) -> str:
        if unavailable:
            return "Unavailable"
        text = formatter(value)
        return f"{text} (partial)" if partial else text

    rows = [
        {
            "Leg": "Road to port (pre-carriage)",
            "Distance": fmt_distance_km(first.get("distance_km")),
            "Cost estimate": fmt_currency_brl(first.get("cost")),
            "TTW CO2e": fmt_emissions_kg(first.get("co2e")),
            "Data source": "-",
        },
        {
            "Leg": "Sea leg (cabotage)",
            "Distance": fmt_distance_km(sea.get("distance_km")),
            "Cost estimate": fmt_currency_brl(maritime.get("sailing_cost_brl")),
            "TTW CO2e": fmt_emissions_kg(maritime.get("sailing_co2e_kg")),
            "Data source": clean_text(sea.get("fuel_g_per_tnm_source")) or "-",
        },
        {
            "Leg": "Port ops",
            "Distance": "-",
            "Cost estimate": _component_value(
                maritime.get("port_ops_cost_brl"),
                fmt_currency_brl,
                unavailable=port_ops_unavailable,
                partial=port_ops_partial,
            ),
            "TTW CO2e": _component_value(
                maritime.get("port_ops_co2e_kg"),
                fmt_emissions_kg,
                unavailable=port_ops_unavailable,
                partial=port_ops_partial,
            ),
            "Data source": source_level_label(port_ops_source_level(sea)) or "-",
        },
    ]

    hoteling_requested = bool(sea.get("hoteling_requested"))
    hoteling_included = bool(sea.get("hoteling_included")) or safe_float(sea.get("hoteling_fuel_kg")) > 0
    hoteling_exclusion = clean_text(sea.get("hoteling_exclusion_reason"))
    if hoteling_requested or hoteling_included or hoteling_exclusion:
        if hoteling_included:
            hoteling_cost = fmt_currency_brl(maritime.get("hoteling_cost_brl"))
            hoteling_co2e = fmt_emissions_kg(maritime.get("hoteling_co2e_kg"))
            hoteling_source = source_level_label(sea.get("hoteling_source_level")) or "-"
        elif hoteling_exclusion == "zero_activity":
            hoteling_cost = fmt_currency_brl(0.0)
            hoteling_co2e = fmt_emissions_kg(0.0)
            hoteling_source = basis_label(hoteling_exclusion) or "-"
        elif hoteling_exclusion == "hoteling_rate_unavailable":
            hoteling_cost = "Unavailable"
            hoteling_co2e = "Unavailable"
            hoteling_source = basis_label(hoteling_exclusion) or "-"
        else:
            hoteling_cost = "Excluded"
            hoteling_co2e = "Excluded"
            hoteling_source = basis_label(hoteling_exclusion) or "-"
        rows.append(
            {
                "Leg": "Hoteling",
                "Distance": "-",
                "Cost estimate": hoteling_cost,
                "TTW CO2e": hoteling_co2e,
                "Data source": hoteling_source,
            }
        )

    rows.append(
        {
            "Leg": "Road from port (on-carriage)",
            "Distance": fmt_distance_km(last.get("distance_km")),
            "Cost estimate": fmt_currency_brl(last.get("cost")),
            "TTW CO2e": fmt_emissions_kg(last.get("co2e")),
            "Data source": "-",
        }
    )

    return pd.DataFrame(rows)


def _port_call_breakdown_table(results: Mapping[str, Any]) -> pd.DataFrame:
    sea = results.get("multimodal", {}).get("sea", {})
    port_ops = sea.get("port_ops", {}) if isinstance(sea, Mapping) else {}
    calls = port_ops.get("port_call_breakdown") if isinstance(port_ops, Mapping) else None
    if not isinstance(calls, list) or not calls:
        return pd.DataFrame()

    def _format_optional_kg(value: Any) -> str:
        if value is None:
            return "Unavailable"
        return f"{format_significant(value)} kg"

    def _format_optional_co2e(value: Any) -> str:
        if value is None:
            return "Unavailable"
        return fmt_emissions_kg(value)

    rows: list[dict[str, str]] = []
    for index, call in enumerate(calls, start=1):
        if not isinstance(call, Mapping):
            continue
        basis = clean_text(call.get("basis"))
        if not basis:
            fuel_resolution = call.get("fuel_resolution")
            if isinstance(fuel_resolution, Mapping):
                basis = clean_text(fuel_resolution.get("basis"))
        note = warnings_summary([call.get("warning")], limit=1) or basis_label(basis) or "-"
        rows.append(
            {
                "Port call": clean_text(call.get("port_name")) or f"Port call {index}",
                "Activity": format_significant(call.get("activity_value")),
                "Activity unit": clean_text(call.get("activity_unit")) or "-",
                "Fuel": _format_optional_kg(call.get("fuel_kg")),
                "CO2e": _format_optional_co2e(call.get("co2e_kg")),
                "Source": source_level_label(call.get("source_level")) or "-",
                "Basis / note": note,
            }
        )
    return pd.DataFrame(rows)


def render_breakdown(results: Mapping[str, Any]) -> None:
    st.caption(
        "Emissions are operational TTW CO2e estimates from the current fuel-factor boundary. "
        "Cost values are model estimates/proxies, not complete commercial freight quotes."
    )
    st.markdown("**Total summary**")
    st.dataframe(_summary_table(results), hide_index=True, width="stretch")
    st.markdown("**Multimodal leg breakdown**")
    st.dataframe(_legs_table(results), hide_index=True, width="stretch")
    port_call_table = _port_call_breakdown_table(results)
    if not port_call_table.empty:
        st.markdown("**Port-call provenance**")
        st.dataframe(port_call_table, hide_index=True, width="stretch")
