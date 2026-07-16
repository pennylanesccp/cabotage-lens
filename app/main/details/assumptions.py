from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from app.main.details.provenance import (
    basis_label,
    clean_text,
    port_ops_calculation_basis,
    port_ops_denominator_unit,
    port_ops_equipment_source_counts,
    port_ops_has_unavailable,
    port_ops_missing_value_policy,
    port_ops_observed_record_count,
    port_ops_source_counts,
    port_ops_source_level,
    port_ops_totals_complete,
    port_ops_warnings,
    source_counts_summary,
    source_level_label,
    warnings_summary,
)
from app.main.utils.formatters import safe_float
from modules.multimodal.distance_provenance import maritime_distance_source_type

_SOURCE_TYPE_LABELS = {
    "seamatrix": "SeaMatrix distance",
    "haversine_fallback": "Fallback estimate",
    "manual_override": "Manual override",
    "external_reference": "External reference",
}

_CORRIDOR_SELECTION_LABELS = {
    "direct_first_then_shortest_distance_km": (
        "Direct observed corridor first; otherwise shortest observed distance (km)"
    ),
    "direct_first_then_shortest_distance": (
        "Direct observed corridor first; otherwise shortest observed distance"
    ),
    "shortest_distance_km": "Shortest observed maritime distance (km)",
    "shortest_distance": "Shortest observed maritime distance",
}

_INTENSITY_SOURCE_LABELS = {
    "eu_mrv_imo_latest": "EU MRV latest record by IMO",
    "mrv_imo": "EU MRV match by IMO",
    "imo": "IMO-specific intensity",
    "eu_mrv_vessel_class_mean": "EU MRV vessel-class mean",
    "mrv_vessel_class_mean": "EU MRV vessel-class mean",
    "vessel_class": "Vessel-class fallback",
    "class_fallback": "Vessel-class fallback",
    "eu_mrv_ship_type_mean": "EU MRV ship-type mean",
    "mrv_ship_type_mean": "EU MRV ship-type mean",
    "ship_type": "Ship-type fallback",
    "type_fallback": "Ship-type fallback",
    "unavailable": "Unavailable",
    "unresolved": "Unresolved",
}

_DISTANCE_SOURCE_LABELS = {
    "sea_matrix": "Sea-matrix distance",
    "matrix": "Sea-matrix distance",
    "haversine_fallback": "Coordinate haversine fallback",
    "unavailable": "Unavailable",
}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(
    primary: Mapping[str, Any],
    primary_keys: tuple[str, ...],
    secondary: Mapping[str, Any],
    secondary_keys: tuple[str, ...] = (),
) -> Any:
    for source, keys in ((primary, primary_keys), (secondary, secondary_keys)):
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _count_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _readable_code(value: Any, labels: Mapping[str, str]) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return labels.get(text, text.replace("_", " ").strip().capitalize())


def _corridor_path_text(value: Any) -> str | None:
    if not isinstance(value, (list, tuple)):
        return None
    ports = [str(item).strip() for item in value if str(item or "").strip()]
    return " → ".join(ports) if len(ports) >= 2 else None


def _intensity_source_counts_text(value: Any) -> str | None:
    if not isinstance(value, Mapping) or not value:
        return None

    ordered_keys = (
        "eu_mrv_imo_latest",
        "mrv_imo",
        "imo",
        "eu_mrv_vessel_class_mean",
        "mrv_vessel_class_mean",
        "vessel_class",
        "class_fallback",
        "eu_mrv_ship_type_mean",
        "mrv_ship_type_mean",
        "ship_type",
        "type_fallback",
        "unavailable",
        "unresolved",
    )
    keys = [key for key in ordered_keys if key in value]
    keys.extend(str(key) for key in value if str(key) not in keys)

    parts: list[str] = []
    for key in keys:
        count = _count_or_none(value.get(key))
        if count is None or count <= 0:
            continue
        label = _readable_code(key, _INTENSITY_SOURCE_LABELS)
        if label:
            parts.append(f"{label}: {count}")
    return "; ".join(parts) or None


def _distance_source_counts_text(value: Any) -> str | None:
    if not isinstance(value, Mapping) or not value:
        return None
    parts: list[str] = []
    for key in ("sea_matrix", "matrix", "haversine_fallback", "unavailable"):
        count = _count_or_none(value.get(key))
        if count is None or count <= 0:
            continue
        label = _DISTANCE_SOURCE_LABELS.get(key, key.replace("_", " ").capitalize())
        parts.append(f"{label}: {count}")
    return "; ".join(parts) or None


def _maritime_route_rows(results: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    inputs = results.get("inputs", {})
    sea = results.get("multimodal", {}).get("sea", {})
    if not isinstance(inputs, Mapping):
        inputs = {}
    if not isinstance(sea, Mapping):
        sea = {}

    route_observation_mode = _clean_text(
        _first_value(
            sea,
            ("route_observation_mode",),
            inputs,
            ("sea_route_observation_mode",),
        )
    )
    if route_observation_mode != "observed_voyage_corridors":
        return []

    rows: list[tuple[str, str, str]] = []
    path = _corridor_path_text(
        _first_value(
            sea,
            ("route_corridor_port_path", "corridor_port_path", "selected_corridor_port_path"),
            inputs,
            ("sea_route_corridor_port_path",),
        )
    )
    corridor_id = _clean_text(
        _first_value(
            sea,
            ("selected_corridor_id",),
            inputs,
            ("sea_route_selected_corridor_id",),
        )
    )
    if path:
        selected_value = path
        if corridor_id:
            selected_value = f"{selected_value}; record: {corridor_id}"
        rows.append(
            (
                "Selected observed corridor",
                "Observed ANTAQ port sequence selected for the maritime calculation.",
                selected_value,
            )
        )

    criterion = _readable_code(
        _first_value(
            sea,
            ("selection_criterion", "route_selection_criterion", "corridor_selection_criterion"),
            inputs,
            ("sea_route_selection_criterion",),
        ),
        _CORRIDOR_SELECTION_LABELS,
    )
    if criterion:
        rows.append(
            (
                "Corridor selection criterion",
                "Rule used to choose among the observed direct and multistop voyage corridors.",
                criterion,
            )
        )

    route_count_fields = (
        (
            "observed corridors",
            ("corridor_count", "route_corridor_count", "observed_corridor_count"),
            ("sea_route_corridor_count",),
        ),
        (
            "candidate voyages",
            (
                "candidate_voyage_observation_count",
                "candidate_voyage_count",
                "route_candidate_voyage_count",
            ),
            (
                "sea_route_candidate_voyage_observation_count",
                "sea_route_candidate_voyage_count",
            ),
        ),
        (
            "route voyages",
            ("route_voyage_count", "voyage_count"),
            ("sea_route_voyage_count",),
        ),
        (
            "direct voyages",
            ("direct_voyage_count", "route_direct_voyage_count"),
            ("sea_route_direct_voyage_count",),
        ),
        (
            "multistop voyages",
            ("multistop_voyage_count", "route_multistop_voyage_count"),
            ("sea_route_multistop_voyage_count",),
        ),
    )
    coverage_parts: list[str] = []
    for label, sea_keys, input_keys in route_count_fields:
        count = _count_or_none(_first_value(sea, sea_keys, inputs, input_keys))
        if count is not None:
            coverage_parts.append(f"{label}: {count}")
    if coverage_parts:
        rows.append(
            (
                "Observed maritime coverage",
                "Number of observed corridors and ANTAQ voyages considered without combining unrelated voyages.",
                "; ".join(coverage_parts),
            )
        )

    intensity_count_fields = (
        (
            "resolved voyages",
            ("resolved_voyage_count", "route_resolved_voyage_count"),
            ("sea_route_resolved_voyage_count",),
        ),
        (
            "IMO-specific intensity",
            ("imo_intensity_voyage_count", "route_imo_intensity_voyage_count"),
            ("sea_route_imo_intensity_voyage_count",),
        ),
        (
            "vessel-class fallback",
            ("class_fallback_voyage_count", "route_class_fallback_voyage_count"),
            ("sea_route_class_fallback_voyage_count",),
        ),
        (
            "ship-type fallback",
            ("type_fallback_voyage_count", "route_type_fallback_voyage_count"),
            ("sea_route_type_fallback_voyage_count",),
        ),
        (
            "unresolved intensity",
            ("unresolved_intensity_voyage_count", "route_unresolved_intensity_voyage_count"),
            ("sea_route_unresolved_intensity_voyage_count",),
        ),
    )
    intensity_parts: list[str] = []
    for label, sea_keys, input_keys in intensity_count_fields:
        count = _count_or_none(_first_value(sea, sea_keys, inputs, input_keys))
        if count is not None:
            intensity_parts.append(f"{label}: {count}")
    if intensity_parts:
        rows.append(
            (
                "Maritime intensity coverage",
                "Voyage coverage by exact EU MRV IMO match, type/class mean fallback, or unresolved intensity.",
                "; ".join(intensity_parts),
            )
        )

    source_counts = _first_value(
        sea,
        ("intensity_source_counts", "route_intensity_source_counts"),
        inputs,
        ("sea_route_intensity_source_counts",),
    )
    source_counts_text = _intensity_source_counts_text(source_counts)
    if source_counts_text:
        rows.append(
            (
                "Maritime intensity sources",
                "Count of candidate voyages across all evaluated corridors by the intensity source actually used.",
                source_counts_text,
            )
        )

    selected_distance_counts = _first_value(
        sea,
        ("selected_corridor_distance_source_counts",),
        inputs,
        ("sea_route_selected_corridor_distance_source_counts",),
    )
    selected_distance_counts_text = _distance_source_counts_text(
        selected_distance_counts
    )
    if selected_distance_counts_text:
        rows.append(
            (
                "Selected-corridor distance sources",
                "Distance provenance for the sublegs used in the maritime result.",
                selected_distance_counts_text,
            )
        )

    return rows


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


def _port_ops_rows(results: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    sea = results.get("multimodal", {}).get("sea", {})
    if not isinstance(sea, Mapping):
        return []

    rows: list[tuple[str, str, str]] = []
    source_level = source_level_label(port_ops_source_level(sea))
    if source_level:
        rows.append(
            (
                "Port ops data source",
                "Provenance level for port-operation fuel and emissions in this route.",
                source_level,
            )
        )

    counts_text = source_counts_summary(port_ops_source_counts(sea))
    equipment_counts_text = source_counts_summary(port_ops_equipment_source_counts(sea))
    observed_count = port_ops_observed_record_count(sea)
    coverage_parts = []
    if counts_text:
        coverage_parts.append(f"port calls: {counts_text}")
    if equipment_counts_text:
        coverage_parts.append(f"equipment factors: {equipment_counts_text}")
    if observed_count is not None:
        coverage_parts.append(f"observed records available: {observed_count}")
    if coverage_parts:
        rows.append(
            (
                "Port ops coverage",
                "Coverage of observed, estimated, documented-default, and unavailable port-operation values.",
                "; ".join(coverage_parts),
            )
        )

    complete = port_ops_totals_complete(sea)
    policy = port_ops_missing_value_policy(sea)
    completeness_parts = []
    if complete is not None:
        completeness_parts.append("complete" if complete else "incomplete")
    if port_ops_has_unavailable(sea):
        completeness_parts.append("unavailable components are flagged")
    if policy:
        completeness_parts.append(policy.replace("_", " "))
    if completeness_parts:
        rows.append(
            (
                "Port ops completeness",
                "Whether numeric port-operation totals include all represented components.",
                "; ".join(completeness_parts),
            )
        )

    basis = basis_label(port_ops_calculation_basis(sea))
    denominator_unit = port_ops_denominator_unit(sea)
    basis_parts = []
    if basis:
        basis_parts.append(basis)
    if denominator_unit:
        basis_parts.append(f"fallback denominator: {denominator_unit}")
    if basis_parts:
        rows.append(
            (
                "Port ops fallback basis",
                "Basis used when port-specific observed data are incomplete or absent.",
                "; ".join(basis_parts),
            )
        )

    warnings_text = warnings_summary(port_ops_warnings(sea))
    if warnings_text:
        rows.append(
            (
                "Port ops warning",
                "Fallback or unavailable-data warning retained from the calculation layer.",
                warnings_text,
            )
        )

    return rows


def _hoteling_rows(results: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    inputs = results.get("inputs", {})
    sea = results.get("multimodal", {}).get("sea", {})
    if not isinstance(inputs, Mapping):
        inputs = {}
    if not isinstance(sea, Mapping):
        sea = {}

    rows: list[tuple[str, str, str]] = []
    source_level = source_level_label(sea.get("hoteling_source_level") or inputs.get("hoteling_source_level"))
    if source_level:
        rows.append(
            (
                "Hoteling data source",
                "Provenance level for berth-side hoteling fuel and emissions.",
                source_level,
            )
        )

    basis = basis_label(sea.get("hoteling_basis") or inputs.get("hoteling_basis"))
    if basis:
        rows.append(
            (
                "Hoteling basis",
                "Basis used to resolve hoteling fuel and emissions for this route.",
                basis,
            )
        )

    warning = clean_text(sea.get("hoteling_warning") or inputs.get("hoteling_warning"))
    if warning:
        rows.append(
            (
                "Hoteling warning",
                "Fallback warning retained from the hoteling resolver.",
                warning,
            )
        )

    exclusion = clean_text(inputs.get("hoteling_exclusion_reason") or sea.get("hoteling_exclusion_reason"))
    if exclusion:
        rows.append(
            (
                "Hoteling exclusion reason",
                "Reason hoteling was not added as a separate component, when applicable.",
                basis_label(exclusion) or exclusion,
            )
        )

    return rows


def _assumptions_table(results: Mapping[str, Any], payload: Mapping[str, Any]) -> pd.DataFrame:
    inputs = results.get("inputs", {})
    hoteling_reason = str(inputs.get("hoteling_exclusion_reason") or "").strip()
    hoteling_requested = bool(inputs.get("hoteling_requested"))
    hoteling_included = bool(inputs.get("hoteling_included") or inputs.get("include_hoteling"))
    if hoteling_included:
        hoteling_value = "included"
    elif hoteling_reason == "included_in_transport_work_intensity":
        hoteling_value = "skipped (already covered by MRV transport-work intensity)"
    elif hoteling_reason == "zero_activity":
        hoteling_value = "zero activity"
    elif hoteling_reason == "hoteling_rate_unavailable":
        hoteling_value = "unavailable (not included without defensible data)"
    elif hoteling_requested:
        hoteling_value = "requested but not included"
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
        *_maritime_route_rows(results),
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
        *_port_ops_rows(results),
        (
            "Hoteling",
            "Whether berth-side auxiliary fuel use and emissions are included while the vessel is in port.",
            hoteling_value,
        ),
        *_hoteling_rows(results),
    ]
    return pd.DataFrame(rows, columns=["Parameter", "Description", "Value"])


def render_assumptions(results: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    st.caption(
        "This table preserves the calculation boundary, selected model parameters, and any fallback or unavailable-data basis "
        "that affects interpretation."
    )
    st.dataframe(_assumptions_table(results=results, payload=payload), hide_index=True, width="stretch")
