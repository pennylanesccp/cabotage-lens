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

_INTENSITY_SOURCE_LABELS = {
    "antaq_mrv_same_od_transport_work_weighted_mean": (
        "ANTAQ + EU MRV same-OD transport-work-weighted mean"
    ),
    "antaq_mrv_same_od_unweighted_mean_zero_transport_work": (
        "ANTAQ + EU MRV same-OD unweighted mean (all transport work zero)"
    ),
    "eu_mrv_imo_outlier_replaced_by_vessel_class": (
        "EU MRV IMO outlier replaced by vessel-class estimate"
    ),
    "eu_mrv_imo_outlier_replaced_by_ship_type": (
        "EU MRV IMO outlier replaced by ship-type estimate"
    ),
    "eu_mrv_imo_latest": "EU MRV latest record by IMO",
    "mrv_imo": "EU MRV match by IMO",
    "imo": "IMO-specific intensity",
    "eu_mrv_vessel_class_mean": "EU MRV vessel-class mean",
    "eu_mrv_vessel_class_trimmed_mean_1pct": (
        "EU MRV vessel-class 1% trimmed mean"
    ),
    "eu_mrv_vessel_class_median": "EU MRV vessel-class median",
    "mrv_vessel_class_mean": "EU MRV vessel-class mean",
    "vessel_class": "Vessel-class fallback",
    "class_fallback": "Vessel-class fallback",
    "eu_mrv_ship_type_mean": "EU MRV ship-type mean",
    "eu_mrv_ship_type_trimmed_mean_1pct": (
        "EU MRV ship-type 1% trimmed mean"
    ),
    "eu_mrv_ship_type_median": "EU MRV ship-type median",
    "mrv_ship_type_mean": "EU MRV ship-type mean",
    "ship_type": "Ship-type fallback",
    "type_fallback": "Ship-type fallback",
    "unavailable": "Unavailable",
    "unresolved": "Unresolved",
}

_DISTANCE_SOURCE_LABELS = {
    "sea_matrix": "Sea matrix",
    "matrix": "Sea matrix",
    "haversine_fallback": "Haversine fallback",
    "unavailable": "Unavailable",
}


def _first_available(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _format_optional_measure(value: Any, unit: str) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return "Unavailable"
    try:
        float(value)
    except (TypeError, ValueError):
        text = clean_text(value)
        return text or "Unavailable"
    return f"{format_significant(value)} {unit}"


def _intensity_source_label(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return _INTENSITY_SOURCE_LABELS.get(
        text,
        text.replace("_", " ").strip().capitalize(),
    )


def _intensity_source_counts_text(value: Any) -> str | None:
    if not isinstance(value, Mapping) or not value:
        return None

    preferred_order = tuple(_INTENSITY_SOURCE_LABELS)
    keys = [key for key in preferred_order if key in value]
    keys.extend(str(key) for key in value if str(key) not in keys)
    parts: list[str] = []
    for key in keys:
        raw_count = value.get(key)
        if isinstance(raw_count, bool):
            continue
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        label = _intensity_source_label(key)
        if label:
            parts.append(f"{label}: {count}")
    return "; ".join(parts) or None


def _distance_source_label(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return "Unavailable"
    return _DISTANCE_SOURCE_LABELS.get(
        text,
        text.replace("_", " ").strip().capitalize(),
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
            "Data source": _intensity_source_label(
                sea.get("fuel_g_per_tnm_source")
            )
            or "-",
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


def _selected_corridor_sublegs_table(results: Mapping[str, Any]) -> pd.DataFrame:
    sea = results.get("multimodal", {}).get("sea", {})
    if not isinstance(sea, Mapping):
        return pd.DataFrame()

    raw_sublegs = _first_available(
        sea,
        "selected_corridor_sublegs",
        "selected_corridor_legs",
    )
    if not isinstance(raw_sublegs, (list, tuple)) or not raw_sublegs:
        return pd.DataFrame()

    rows: list[dict[str, str]] = []
    for raw_subleg in raw_sublegs:
        if not isinstance(raw_subleg, Mapping):
            continue

        distance_nm = _first_available(raw_subleg, "distance_nm")
        distance_km = _first_available(raw_subleg, "distance_km")
        if distance_nm is not None:
            distance = _format_optional_measure(distance_nm, "nm")
        else:
            distance = _format_optional_measure(distance_km, "km")

        applied_source = _intensity_source_label(
            _first_available(
                raw_subleg,
                "scenario_intensity_source",
                "pair_intensity_source",
                "intensity_source",
                "fuel_g_per_tnm_source",
            )
        )
        observed_source = _intensity_source_label(
            _first_available(
                raw_subleg,
                "observed_corridor_intensity_source",
                "intensity_source",
                "fuel_g_per_tnm_source",
                "intensity_source_level",
            )
        )
        source_counts = _intensity_source_counts_text(
            raw_subleg.get("intensity_source_counts")
        )
        observed_source = observed_source or source_counts

        rows.append(
            {
                "From port": clean_text(
                    _first_available(raw_subleg, "origin_port", "from_port_name")
                )
                or "-",
                "To port": clean_text(
                    _first_available(raw_subleg, "destination_port", "to_port_name")
                )
                or "-",
                "Distance": distance,
                "Distance source": _distance_source_label(
                    raw_subleg.get("distance_source")
                ),
                "ANTAQ cargo aboard": _format_optional_measure(
                    _first_available(
                        raw_subleg,
                        "observed_cargo_t",
                        "average_cargo_t",
                        "cargo_weight_t",
                    ),
                    "t",
                ),
                "Applied OD intensity": _format_optional_measure(
                    _first_available(
                        raw_subleg,
                        "applied_pair_intensity_g_per_tnm",
                        "scenario_fuel_g_per_tnm",
                        "fuel_g_per_tnm",
                        "weighted_fuel_intensity_g_per_tnm",
                    ),
                    "g/(t·nm)",
                ),
                "Selected-corridor observed intensity": _format_optional_measure(
                    _first_available(
                        raw_subleg,
                        "observed_corridor_fuel_g_per_tnm",
                    ),
                    "g/(t·nm)",
                ),
                "Applied intensity basis": applied_source or "Unavailable",
                "Observed intensity basis": observed_source or "Unavailable",
                "Observed fuel": _format_optional_measure(
                    _first_available(
                        raw_subleg,
                        "observed_fuel_kg",
                        "observed_fuel_kg_total",
                    ),
                    "kg",
                ),
                "Scenario-attributed fuel": _format_optional_measure(
                    _first_available(
                        raw_subleg,
                        "scenario_fuel_kg",
                        "attributed_vlsfo_fuel_kg",
                    ),
                    "kg",
                ),
            }
        )

    return pd.DataFrame(rows)


def render_breakdown(results: Mapping[str, Any]) -> None:
    st.caption(
        "Emissions are operational TTW CO2e estimates from the current fuel-factor boundary. "
        "Cost values are model estimates/proxies, not complete commercial freight quotes."
    )
    st.markdown("**Route totals**")
    st.caption("Direct-road and multimodal totals are shown on the same cost, distance, and TTW CO2e basis.")
    st.dataframe(_summary_table(results), hide_index=True, width="stretch")
    st.markdown("**Multimodal component breakdown**")
    st.caption("Port operations and hoteling remain visible as separate components when requested or resolved.")
    st.dataframe(_legs_table(results), hide_index=True, width="stretch")
    sublegs_table = _selected_corridor_sublegs_table(results)
    if not sublegs_table.empty:
        st.markdown("**Selected maritime path sublegs**")
        st.caption(
            "The selected corridor supplies path and distance. ANTAQ cargo aboard, observed "
            "intensity, and observed fuel remain diagnostics; scenario fuel applies the robust "
            "same-OD intensity to each selected subleg distance."
        )
        st.dataframe(sublegs_table, hide_index=True, width="stretch")
    port_call_table = _port_call_breakdown_table(results)
    if not port_call_table.empty:
        st.markdown("**Port-call provenance**")
        st.caption("Unavailable or partial port-call values are retained in the table instead of being hidden.")
        st.dataframe(port_call_table, hide_index=True, width="stretch")
