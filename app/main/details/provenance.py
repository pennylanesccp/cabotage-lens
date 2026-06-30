from __future__ import annotations

from typing import Any, Mapping, Sequence


SOURCE_LEVEL_LABELS = {
    "zero_activity": "Zero activity",
    "observed": "Observed port-specific data",
    "estimated_port_average": "Estimated from weighted average of observed ports",
    "literature_default": "Documented model default",
    "unavailable": "Unavailable / not included without defensible data",
}

_BASIS_LABELS = {
    "documented_moves_based_scenario": "Documented moves-based scenario",
    "observed_port_ops_hierarchy": "Observed/fallback port data hierarchy",
    "weighted_average_observed_ports": "Weighted average of observed ports",
    "port_specific_observed_intensity": "Port-specific observed intensity",
    "mrv_class_rate_scaled_by_emep_ratio": "MRV class rate scaled by EMEP/EEA ratio",
    "vessel_class_hoteling_rate": "Vessel-class hoteling rate",
    "included_in_transport_work_intensity": "Already covered by MRV transport-work intensity",
    "disabled_by_user": "Disabled by user",
    "zero_activity": "Zero activity",
    "hoteling_rate_unavailable": "Hoteling rate unavailable",
    "no_observed_or_documented_default": "No observed or documented default basis",
    "converted_from_resolved_fuel_kg": "CO2e converted from resolved fuel mass",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def source_level_label(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return SOURCE_LEVEL_LABELS.get(text, text.replace("_", " ").title())


def basis_label(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return _BASIS_LABELS.get(text, text.replace("_", " "))


def source_counts_summary(counts: Any) -> str | None:
    if not isinstance(counts, Mapping) or not counts:
        return None

    parts: list[str] = []
    for key in ("zero_activity", "observed", "estimated_port_average", "literature_default", "unavailable"):
        value = counts.get(key)
        if not isinstance(value, (int, float)) or int(value) <= 0:
            continue
        label = source_level_label(key)
        if label:
            parts.append(f"{label}: {int(value)}")
    return "; ".join(parts) or None


def warnings_summary(warnings: Any, *, limit: int = 2) -> str | None:
    if isinstance(warnings, str):
        warnings_list = [warnings]
    elif isinstance(warnings, Sequence):
        warnings_list = [str(item).strip() for item in warnings if str(item or "").strip()]
    else:
        warnings_list = []

    if not warnings_list:
        return None

    shown = warnings_list[:limit]
    suffix = f" (+{len(warnings_list) - limit} more)" if len(warnings_list) > limit else ""
    return "; ".join(shown) + suffix


def extract_port_ops_payload(sea: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = sea.get("port_ops")
    return payload if isinstance(payload, Mapping) else {}


def port_ops_source_level(sea: Mapping[str, Any]) -> str | None:
    payload = extract_port_ops_payload(sea)
    return clean_text(sea.get("port_ops_source_level") or payload.get("source_level"))


def port_ops_source_counts(sea: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = extract_port_ops_payload(sea)
    counts = sea.get("port_ops_source_level_counts") or payload.get("source_level_counts")
    return counts if isinstance(counts, Mapping) else {}


def port_ops_equipment_source_counts(sea: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = extract_port_ops_payload(sea)
    counts = payload.get("equipment_source_level_counts")
    return counts if isinstance(counts, Mapping) else {}


def port_ops_warnings(sea: Mapping[str, Any]) -> list[str]:
    payload = extract_port_ops_payload(sea)
    warnings = sea.get("port_ops_warnings") or payload.get("warnings") or []
    if isinstance(warnings, str):
        return [warnings]
    if isinstance(warnings, Sequence):
        return [str(item).strip() for item in warnings if str(item or "").strip()]
    return []


def port_ops_calculation_basis(sea: Mapping[str, Any]) -> str | None:
    payload = extract_port_ops_payload(sea)
    return clean_text(payload.get("calculation_basis"))


def port_ops_denominator_unit(sea: Mapping[str, Any]) -> str | None:
    payload = extract_port_ops_payload(sea)
    return clean_text(payload.get("fallback_denominator_unit"))


def port_ops_observed_record_count(sea: Mapping[str, Any]) -> int | None:
    payload = extract_port_ops_payload(sea)
    value = payload.get("observed_port_ops_record_count")
    if isinstance(value, (int, float)) and int(value) >= 0:
        return int(value)
    return None


def port_ops_has_unavailable(sea: Mapping[str, Any]) -> bool:
    payload = extract_port_ops_payload(sea)
    return bool(sea.get("port_ops_has_unavailable") or payload.get("has_unavailable_port_ops"))


def port_ops_totals_complete(sea: Mapping[str, Any]) -> bool | None:
    payload = extract_port_ops_payload(sea)
    value = sea.get("port_ops_totals_complete")
    if isinstance(value, bool):
        return value
    payload_value = payload.get("totals_complete")
    return payload_value if isinstance(payload_value, bool) else None


def port_ops_missing_value_policy(sea: Mapping[str, Any]) -> str | None:
    payload = extract_port_ops_payload(sea)
    return clean_text(payload.get("missing_value_policy"))
