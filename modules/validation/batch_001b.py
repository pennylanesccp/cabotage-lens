"""Batch 001B validation rerun support.

This module is intentionally file-artifact focused. It does not persist results
to application tables, and it only executes model cases when the caller opts in.
"""

from __future__ import annotations

import csv
import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modules.multimodal.distance_provenance import (
    build_maritime_distance_provenance,
    is_maritime_fallback_source,
    maritime_distance_source_type,
)

NM_TO_KM = 1.852

OUTPUT_FIELDS = [
    "case_id",
    "original_case_id",
    "batch_id",
    "origin",
    "destination",
    "cargo_t",
    "teu",
    "road_only_distance_km",
    "pre_carriage_distance_km",
    "maritime_distance_km",
    "maritime_distance_nm",
    "on_carriage_distance_km",
    "selected_origin_port",
    "selected_destination_port",
    "forced_origin_port",
    "forced_destination_port",
    "origin_port_override",
    "destination_port_override",
    "maritime_distance_override",
    "maritime_distance_source",
    "maritime_distance_provenance",
    "original_maritime_distance_km",
    "original_maritime_distance_source",
    "same_port_flag",
    "cabotage_inappropriate_flag",
    "fallback_flags",
    "road_emissions_kgco2e",
    "multimodal_emissions_kgco2e",
    "road_cost_brl",
    "multimodal_cost_brl",
    "validation_status",
    "sensitivity_required",
    "notes",
]

EXTRA_OUTPUT_FIELDS = [
    "execution_mode",
    "automatic_origin_port",
    "automatic_destination_port",
    "origin_port_override_provenance",
    "destination_port_override_provenance",
    "maritime_distance_unit",
    "maritime_distance_source_type",
    "maritime_distance_notes",
    "maritime_distance_lower_bound_km",
    "maritime_distance_upper_bound_km",
    "original_maritime_distance_source_type",
    "maritime_distance_override_type",
    "maritime_distance_bound_role",
    "output_status",
]

ALL_OUTPUT_FIELDS = [*OUTPUT_FIELDS, *EXTRA_OUTPUT_FIELDS]

RECORD_ONLY_MODES = {"record_only", "excluded", "invalid", "warning_only"}
MODEL_RERUN_MODE = "model_rerun"
PLANNED_MODES = {"planned", "not_run"}


class ValidationConfigError(ValueError):
    """Raised when a Batch 001B config cannot be interpreted safely."""


@dataclass(frozen=True)
class MaritimeDistanceOverride:
    enabled: bool
    distance_km: float | None = None
    distance_nm: float | None = None
    unit: str | None = None
    source: str | None = None
    source_type: str | None = None
    provenance: str | None = None
    notes: str | None = None
    lower_bound_km: float | None = None
    lower_bound_nm: float | None = None
    upper_bound_km: float | None = None
    upper_bound_nm: float | None = None
    scenario_type: str | None = None
    bound_role: str | None = None
    required: bool = False


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().casefold()
    if text in {"1", "true", "yes", "y", "sim"}:
        return True
    if text in {"0", "false", "no", "n", "nao"}:
        return False
    return bool(default)


def _float_or_none(value: Any, *, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationConfigError(f"{field_name} must be numeric when provided.") from exc


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _repair_mojibake(text: str) -> str | None:
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return None
    return repaired if repaired != text else None


def _text_variants(value: Any) -> set[str]:
    text = _clean_text(value)
    if text is None:
        return set()
    variants = {text}
    repaired = _repair_mojibake(text)
    if repaired:
        variants.add(repaired)
    variants.update(_strip_accents(item) for item in list(variants))
    return variants


def _normalized_key(text: str) -> str:
    return " ".join(_strip_accents(text).casefold().split())


def _text_key(value: Any) -> str:
    keys = _normalize_port_index_value(value)
    return keys[0] if keys else ""


def _port_name(port: Mapping[str, Any] | None) -> str | None:
    if not isinstance(port, Mapping):
        return None
    return _clean_text(port.get("name") or port.get("label") or port.get("code"))


def _selected_port_from_case(case: Mapping[str, Any], side: str) -> str | None:
    original = case.get("original_model")
    if not isinstance(original, Mapping):
        original = {}
    key = "selected_origin_port" if side == "origin" else "selected_destination_port"
    return _clean_text(original.get(key) or case.get(key))


def _port_override_spec(case: Mapping[str, Any], side: str) -> Mapping[str, Any] | None:
    overrides = case.get("port_overrides")
    if isinstance(overrides, Mapping):
        raw = overrides.get(side)
        if isinstance(raw, Mapping):
            return raw
        if raw not in (None, ""):
            return {"port": raw}

    legacy_key = "forced_origin_port" if side == "origin" else "forced_destination_port"
    raw_legacy = case.get(legacy_key)
    if isinstance(raw_legacy, Mapping):
        return raw_legacy
    if raw_legacy not in (None, ""):
        return {"port": raw_legacy}
    return None


def _port_override_query(case: Mapping[str, Any], side: str) -> Any:
    spec = _port_override_spec(case, side)
    if spec is None:
        return None
    return spec.get("port") or spec.get("name") or spec.get("code")


def _port_override_provenance(case: Mapping[str, Any], side: str) -> str | None:
    spec = _port_override_spec(case, side)
    if spec is None:
        return None
    return _clean_text(spec.get("provenance") or spec.get("reason") or spec.get("source"))


def _normalize_port_index_value(value: Any) -> list[str]:
    keys = {_normalized_key(item) for item in _text_variants(value)}
    return sorted(key for key in keys if key)


def resolve_port(ports: Sequence[Mapping[str, Any]], query: Any) -> dict[str, Any] | None:
    """Resolve a port by name, alias, code, or an already structured port dict."""
    if query in (None, ""):
        return None

    if isinstance(query, Mapping):
        if query.get("lat") is not None and query.get("lon") is not None:
            return dict(query)
        query = query.get("name") or query.get("code") or query.get("port")

    query_keys = set(_normalize_port_index_value(query))
    if not query_keys:
        return None

    for port in ports:
        candidate_values: list[Any] = [
            port.get("name"),
            port.get("city"),
            port.get("code"),
        ]
        aliases = port.get("aliases")
        if isinstance(aliases, Iterable) and not isinstance(aliases, (str, bytes)):
            candidate_values.extend(aliases)

        candidate_keys: set[str] = set()
        for value in candidate_values:
            candidate_keys.update(_normalize_port_index_value(value))

        if query_keys & candidate_keys:
            return dict(port)

    raise ValidationConfigError(f"Port override could not be resolved from catalog: {query!r}")


def convert_maritime_distance(value: Any, unit: Any) -> tuple[float | None, float | None]:
    """Return maritime distance as (km, nm), preserving explicit unit semantics."""
    distance = _float_or_none(value, field_name="maritime distance value")
    if distance is None:
        return None, None
    if distance < 0:
        raise ValidationConfigError("maritime distance value cannot be negative.")

    unit_text = str(unit or "").strip().casefold()
    if unit_text in {"km", "kilometer", "kilometers", "kilometre", "kilometres"}:
        return float(distance), float(distance) / NM_TO_KM
    if unit_text in {"nm", "nmi", "nautical_mile", "nautical_miles", "nautical mile", "nautical miles"}:
        return float(distance) * NM_TO_KM, float(distance)
    raise ValidationConfigError("maritime distance unit must be 'km' or 'nm'.")


def _convert_optional_maritime_distance(value: Any, unit: Any, *, field_name: str) -> tuple[float | None, float | None]:
    if value in (None, ""):
        return None, None
    try:
        return convert_maritime_distance(value, unit)
    except ValidationConfigError as exc:
        raise ValidationConfigError(f"{field_name}: {exc}") from exc


def _normalize_maritime_bound(
    raw: Mapping[str, Any],
    *,
    generic_key: str,
    km_key: str,
    nm_key: str,
    default_unit: Any,
) -> tuple[float | None, float | None]:
    km = _float_or_none(raw.get(km_key), field_name=km_key)
    nm = _float_or_none(raw.get(nm_key), field_name=nm_key)
    if km is not None and km < 0:
        raise ValidationConfigError(f"{km_key} cannot be negative.")
    if nm is not None and nm < 0:
        raise ValidationConfigError(f"{nm_key} cannot be negative.")
    if km is not None:
        return km, nm if nm is not None else km / NM_TO_KM
    if nm is not None:
        return nm * NM_TO_KM, nm
    return _convert_optional_maritime_distance(
        raw.get(generic_key),
        raw.get("bounds_unit") or raw.get("bound_unit") or default_unit,
        field_name=generic_key,
    )


def normalize_maritime_override(raw: Any) -> MaritimeDistanceOverride:
    if raw in (None, "", False):
        return MaritimeDistanceOverride(enabled=False)
    if not isinstance(raw, Mapping):
        raise ValidationConfigError("maritime_distance_override must be an object when provided.")

    value = raw.get("value")
    required = _as_bool(raw.get("required"), default=False)
    lower_km, lower_nm = _normalize_maritime_bound(
        raw,
        generic_key="lower_bound",
        km_key="lower_bound_km",
        nm_key="lower_bound_nm",
        default_unit=raw.get("unit"),
    )
    upper_km, upper_nm = _normalize_maritime_bound(
        raw,
        generic_key="upper_bound",
        km_key="upper_bound_km",
        nm_key="upper_bound_nm",
        default_unit=raw.get("unit"),
    )
    if lower_km is not None and upper_km is not None and lower_km > upper_km:
        raise ValidationConfigError("maritime_distance_override lower bound cannot exceed upper bound.")

    if value in (None, ""):
        return MaritimeDistanceOverride(
            enabled=True,
            source=_clean_text(raw.get("source")),
            source_type=_clean_text(raw.get("source_type")),
            provenance=_clean_text(raw.get("provenance")),
            notes=_clean_text(raw.get("notes")),
            lower_bound_km=lower_km,
            lower_bound_nm=lower_nm,
            upper_bound_km=upper_km,
            upper_bound_nm=upper_nm,
            scenario_type=_clean_text(raw.get("scenario_type") or raw.get("type")),
            bound_role=_clean_text(raw.get("bound_role")),
            required=required,
        )

    km, nm = convert_maritime_distance(value, raw.get("unit"))
    return MaritimeDistanceOverride(
        enabled=True,
        distance_km=km,
        distance_nm=nm,
        unit=str(raw.get("unit")).strip().lower(),
        source=_clean_text(raw.get("source")) or "validation_override",
        source_type=_clean_text(raw.get("source_type")),
        provenance=_clean_text(raw.get("provenance")),
        notes=_clean_text(raw.get("notes")),
        lower_bound_km=lower_km,
        lower_bound_nm=lower_nm,
        upper_bound_km=upper_km,
        upper_bound_nm=upper_nm,
        scenario_type=_clean_text(raw.get("scenario_type") or raw.get("type")) or "single",
        bound_role=_clean_text(raw.get("bound_role")),
        required=required,
    )


def _case_maritime_override(case: Mapping[str, Any]) -> MaritimeDistanceOverride:
    return normalize_maritime_override(case.get("maritime_distance_override"))


def _sea_leg_distance_provenance(
    sea_leg: Mapping[str, Any],
    *,
    is_override: bool = False,
) -> dict[str, Any]:
    raw = sea_leg.get("distance_provenance")
    if isinstance(raw, Mapping):
        return dict(raw)
    return build_maritime_distance_provenance(
        distance_km=sea_leg.get("distance_km"),
        source=sea_leg.get("source"),
        unit="km",
        is_override=is_override,
    )


def _provenance_value(provenance: Mapping[str, Any] | None, key: str) -> Any:
    if not isinstance(provenance, Mapping):
        return None
    return provenance.get(key)


def apply_maritime_distance_override(
    geometry: Mapping[str, Any],
    override: MaritimeDistanceOverride,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a geometry copy with validation maritime distance applied."""
    updated = deepcopy(dict(geometry))
    sea_leg = dict(updated.get("sea_leg") or {})
    original_provenance = _sea_leg_distance_provenance(sea_leg)
    original = {
        "distance_km": sea_leg.get("distance_km"),
        "source": sea_leg.get("source"),
        "source_type": original_provenance.get("source_type"),
        "distance_provenance": original_provenance,
    }
    if override.enabled and override.distance_km is not None:
        sea_leg["distance_km"] = float(override.distance_km)
        sea_leg["source"] = override.source or "validation_override"
        sea_leg["original_distance_provenance"] = original_provenance
        sea_leg["distance_provenance"] = build_maritime_distance_provenance(
            distance_km=override.distance_km,
            distance_nm=override.distance_nm,
            distance_value=override.distance_nm if override.unit == "nm" else override.distance_km,
            unit=override.unit or "km",
            source=override.source or "validation_override",
            source_type=override.source_type,
            notes=override.notes,
            lower_bound_km=override.lower_bound_km,
            upper_bound_km=override.upper_bound_km,
            is_override=True,
        )
        sea_leg["validation_override"] = {
            "distance_km": override.distance_km,
            "distance_nm": override.distance_nm,
            "source": override.source,
            "source_type": maritime_distance_source_type(
                override.source,
                source_type=override.source_type,
                is_override=True,
            ),
            "provenance": override.provenance,
            "notes": override.notes,
            "lower_bound_km": override.lower_bound_km,
            "lower_bound_nm": override.lower_bound_nm,
            "upper_bound_km": override.upper_bound_km,
            "upper_bound_nm": override.upper_bound_nm,
            "scenario_type": override.scenario_type,
            "bound_role": override.bound_role,
        }
    updated["sea_leg"] = sea_leg
    return updated, original


def load_validation_config(path: Path | str) -> dict[str, Any]:
    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValidationConfigError("Batch 001B config must be a JSON object.")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValidationConfigError("Batch 001B config must contain a cases list.")
    return payload


def _case_execution_mode(case: Mapping[str, Any]) -> str:
    mode = _clean_text(case.get("execution_mode") or case.get("mode"))
    if mode:
        return mode
    status = _clean_text(case.get("validation_status"))
    if status in {"excluded", "invalid", "warning_only"}:
        return "record_only"
    return MODEL_RERUN_MODE


def _model_defaults(config: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    defaults = dict(config.get("model_defaults") or {})
    defaults.update(dict(case.get("model") or {}))
    return defaults


def _case_batch_id(config: Mapping[str, Any], case: Mapping[str, Any]) -> str:
    return str(case.get("batch_id") or config.get("batch_id") or "Batch 001B")


def _case_cargo_t(config: Mapping[str, Any], case: Mapping[str, Any]) -> float | None:
    value = case.get("cargo_t")
    if value is None:
        value = _model_defaults(config, case).get("cargo_t")
    return _float_or_none(value, field_name="cargo_t")


def _case_teu(config: Mapping[str, Any], case: Mapping[str, Any]) -> float | None:
    value = case.get("teu")
    if value is None:
        value = _model_defaults(config, case).get("cargo_teu")
    return _float_or_none(value, field_name="teu")


def _same_port(origin_port: Any, destination_port: Any) -> bool:
    origin_key = _text_key(origin_port)
    destination_key = _text_key(destination_port)
    return bool(origin_key and destination_key and origin_key == destination_key)


def _joined_flags(values: Iterable[Any]) -> str | None:
    flags: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            parts = [value]
        elif isinstance(value, Iterable):
            parts = [str(item) for item in value]
        else:
            parts = [str(value)]
        for part in parts:
            text = part.strip()
            if text and text not in flags:
                flags.append(text)
    return "; ".join(flags) if flags else None


def _fallback_flags(case: Mapping[str, Any], original_source: Any, geometry: Mapping[str, Any] | None) -> str | None:
    values: list[Any] = []
    values.append(case.get("fallback_flags"))
    sea_source = _clean_text(original_source)
    current_source = None
    current_source_type = None
    if isinstance(geometry, Mapping):
        sea_leg = geometry.get("sea_leg") or {}
        if isinstance(sea_leg, Mapping):
            current_source = _clean_text(sea_leg.get("source"))
            current_source_type = _provenance_value(_sea_leg_distance_provenance(sea_leg), "source_type")
    for source, source_type in ((sea_source, None), (current_source, current_source_type)):
        if source and is_maritime_fallback_source(source, source_type=source_type):
            values.append("SeaMatrix haversine fallback")
        elif source and "fallback" in source.casefold():
            values.append(source)
    return _joined_flags(values)


def _empty_row() -> dict[str, Any]:
    return {field: None for field in ALL_OUTPUT_FIELDS}


def _base_row(config: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    row = _empty_row()
    row.update(
        {
            "case_id": _clean_text(case.get("case_id")),
            "original_case_id": _clean_text(case.get("original_case_id")),
            "batch_id": _case_batch_id(config, case),
            "origin": _clean_text(case.get("origin")),
            "destination": _clean_text(case.get("destination")),
            "cargo_t": _case_cargo_t(config, case),
            "teu": _case_teu(config, case),
            "execution_mode": _case_execution_mode(case),
            "validation_status": _clean_text(case.get("validation_status")) or "not_run",
            "sensitivity_required": _as_bool(case.get("sensitivity_required"), default=False),
            "notes": _clean_text(case.get("notes")),
        }
    )
    return row


def _populate_original_model(row: dict[str, Any], case: Mapping[str, Any]) -> None:
    original = case.get("original_model")
    if not isinstance(original, Mapping):
        original = {}
    row["original_maritime_distance_km"] = original.get("maritime_distance_km")
    row["original_maritime_distance_source"] = _clean_text(original.get("maritime_distance_source"))
    row["original_maritime_distance_source_type"] = _clean_text(
        original.get("maritime_distance_source_type")
    ) or maritime_distance_source_type(row["original_maritime_distance_source"])
    row["selected_origin_port"] = row["selected_origin_port"] or _clean_text(original.get("selected_origin_port"))
    row["selected_destination_port"] = row["selected_destination_port"] or _clean_text(
        original.get("selected_destination_port")
    )
    row["road_only_distance_km"] = row["road_only_distance_km"] or original.get("road_only_distance_km")
    row["pre_carriage_distance_km"] = row["pre_carriage_distance_km"] or original.get("pre_carriage_distance_km")
    row["maritime_distance_km"] = row["maritime_distance_km"] or original.get("maritime_distance_km")
    row["maritime_distance_source"] = row["maritime_distance_source"] or row["original_maritime_distance_source"]
    row["maritime_distance_source_type"] = (
        row["maritime_distance_source_type"]
        or _clean_text(original.get("maritime_distance_source_type"))
        or maritime_distance_source_type(row["maritime_distance_source"])
    )
    if row["maritime_distance_km"] not in (None, ""):
        row["maritime_distance_unit"] = row["maritime_distance_unit"] or "km"
    row["on_carriage_distance_km"] = row["on_carriage_distance_km"] or original.get("on_carriage_distance_km")


def _populate_override_fields(row: dict[str, Any], case: Mapping[str, Any], override: MaritimeDistanceOverride) -> None:
    origin_query = _port_override_query(case, "origin")
    destination_query = _port_override_query(case, "destination")
    row["forced_origin_port"] = _clean_text(origin_query)
    row["forced_destination_port"] = _clean_text(destination_query)
    row["origin_port_override"] = bool(origin_query)
    row["destination_port_override"] = bool(destination_query)
    row["origin_port_override_provenance"] = _port_override_provenance(case, "origin")
    row["destination_port_override_provenance"] = _port_override_provenance(case, "destination")

    row["maritime_distance_override"] = bool(override.enabled and override.distance_km is not None)
    row["maritime_distance_override_type"] = override.scenario_type
    row["maritime_distance_bound_role"] = override.bound_role
    row["maritime_distance_notes"] = override.notes
    row["maritime_distance_lower_bound_km"] = override.lower_bound_km
    row["maritime_distance_upper_bound_km"] = override.upper_bound_km
    if override.distance_km is not None:
        row["maritime_distance_km"] = override.distance_km
        row["maritime_distance_nm"] = override.distance_nm
        row["maritime_distance_unit"] = override.unit or "km"
        row["maritime_distance_source"] = override.source
        row["maritime_distance_source_type"] = maritime_distance_source_type(
            override.source,
            source_type=override.source_type,
            is_override=True,
        )
        row["maritime_distance_provenance"] = override.provenance


def _finalize_flags(row: dict[str, Any], case: Mapping[str, Any]) -> None:
    explicit_same_port = case.get("same_port_flag")
    same_port = (
        _as_bool(explicit_same_port)
        if explicit_same_port is not None
        else _same_port(row.get("selected_origin_port"), row.get("selected_destination_port"))
    )
    row["same_port_flag"] = bool(same_port)
    explicit_inappropriate = case.get("cabotage_inappropriate_flag")
    row["cabotage_inappropriate_flag"] = (
        _as_bool(explicit_inappropriate) if explicit_inappropriate is not None else bool(same_port)
    )


def build_planned_row(config: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    override = _case_maritime_override(case)
    row = _base_row(config, case)
    _populate_original_model(row, case)
    _populate_override_fields(row, case, override)
    if row["forced_origin_port"]:
        row["selected_origin_port"] = row["forced_origin_port"]
    if row["forced_destination_port"]:
        row["selected_destination_port"] = row["forced_destination_port"]
    row["fallback_flags"] = _fallback_flags(case, row.get("original_maritime_distance_source"), None)
    _finalize_flags(row, case)
    row["output_status"] = "planned"
    return row


def build_exclusion_row(config: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    row = build_planned_row(config, case)
    row["validation_status"] = _clean_text(case.get("validation_status")) or "excluded"
    row["output_status"] = "record_only"
    return row


def build_result_row(
    config: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    geometry: Mapping[str, Any],
    results: Mapping[str, Any] | None,
    original_sea_leg: Mapping[str, Any] | None,
    automatic_origin_port: Mapping[str, Any] | None = None,
    automatic_destination_port: Mapping[str, Any] | None = None,
    forced_origin_port: Mapping[str, Any] | None = None,
    forced_destination_port: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    override = _case_maritime_override(case)
    row = _base_row(config, case)
    _populate_original_model(row, case)

    road_direct = geometry.get("road_direct") or {}
    first_mile = geometry.get("first_mile") or {}
    sea_leg = geometry.get("sea_leg") or {}
    last_mile = geometry.get("last_mile") or {}
    origin_port = geometry.get("port_origin") or {}
    destination_port = geometry.get("port_destiny") or {}

    row["road_only_distance_km"] = road_direct.get("distance_km")
    row["pre_carriage_distance_km"] = first_mile.get("distance_km")
    row["maritime_distance_km"] = sea_leg.get("distance_km")
    distance_provenance = _sea_leg_distance_provenance(sea_leg)
    if row["maritime_distance_km"] not in (None, ""):
        row["maritime_distance_nm"] = float(row["maritime_distance_km"]) / NM_TO_KM
        row["maritime_distance_unit"] = _provenance_value(distance_provenance, "unit") or "km"
    row["on_carriage_distance_km"] = last_mile.get("distance_km")
    row["selected_origin_port"] = _port_name(origin_port)
    row["selected_destination_port"] = _port_name(destination_port)
    row["automatic_origin_port"] = _port_name(automatic_origin_port)
    row["automatic_destination_port"] = _port_name(automatic_destination_port)
    row["forced_origin_port"] = _port_name(forced_origin_port)
    row["forced_destination_port"] = _port_name(forced_destination_port)
    row["origin_port_override"] = bool(forced_origin_port)
    row["destination_port_override"] = bool(forced_destination_port)
    row["origin_port_override_provenance"] = _port_override_provenance(case, "origin")
    row["destination_port_override_provenance"] = _port_override_provenance(case, "destination")

    row["maritime_distance_override"] = bool(override.enabled and override.distance_km is not None)
    row["maritime_distance_source"] = _provenance_value(distance_provenance, "source") or (
        override.source if row["maritime_distance_override"] else sea_leg.get("source")
    )
    row["maritime_distance_source_type"] = _provenance_value(distance_provenance, "source_type") or (
        maritime_distance_source_type(
            override.source,
            source_type=override.source_type,
            is_override=True,
        )
        if row["maritime_distance_override"]
        else maritime_distance_source_type(sea_leg.get("source"))
    )
    row["maritime_distance_provenance"] = override.provenance
    row["maritime_distance_notes"] = _provenance_value(distance_provenance, "notes") or override.notes
    row["maritime_distance_lower_bound_km"] = _provenance_value(distance_provenance, "lower_bound_km")
    row["maritime_distance_upper_bound_km"] = _provenance_value(distance_provenance, "upper_bound_km")
    row["maritime_distance_override_type"] = override.scenario_type
    row["maritime_distance_bound_role"] = override.bound_role
    if original_sea_leg:
        original_provenance = _sea_leg_distance_provenance(original_sea_leg)
        row["original_maritime_distance_km"] = original_sea_leg.get("distance_km")
        row["original_maritime_distance_source"] = original_sea_leg.get("source")
        row["original_maritime_distance_source_type"] = _provenance_value(
            original_provenance,
            "source_type",
        ) or maritime_distance_source_type(row["original_maritime_distance_source"])
    row["fallback_flags"] = _fallback_flags(case, row.get("original_maritime_distance_source"), geometry)

    if results:
        road = results.get("road_only") or {}
        multimodal = results.get("multimodal") or {}
        row["road_emissions_kgco2e"] = road.get("co2e")
        row["road_cost_brl"] = road.get("cost")
        row["multimodal_emissions_kgco2e"] = multimodal.get("total_co2e")
        row["multimodal_cost_brl"] = multimodal.get("total_cost")

    _finalize_flags(row, case)
    row["output_status"] = "executed"
    row["validation_status"] = _clean_text(case.get("executed_validation_status")) or row["validation_status"]
    return row


def build_rows_without_execution(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in config.get("cases") or []:
        if not isinstance(case, Mapping):
            raise ValidationConfigError("Each Batch 001B case must be an object.")
        mode = _case_execution_mode(case)
        if mode in RECORD_ONLY_MODES:
            rows.append(build_exclusion_row(config, case))
        else:
            rows.append(build_planned_row(config, case))
    return rows


def _execute_model_case(config: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    from modules.multimodal.builder import (
        build_path_geometry_from_resolved,
        load_routing_assets,
        resolve_point_for_geometry,
    )
    from modules.multimodal.evaluator import evaluate_path
    from modules.ports.ports_nearest import find_nearest_port

    model = _model_defaults(config, case)
    ors, ports, sea_matrix, db_path = load_routing_assets(
        ports_json_path=(None if model.get("ports_json_path") is None else Path(model["ports_json_path"])),
        sea_matrix_path=(None if model.get("sea_matrix_path") is None else Path(model["sea_matrix_path"])),
    )
    origin = resolve_point_for_geometry(case.get("origin"), ors, db_path=db_path)
    destination = resolve_point_for_geometry(case.get("destination"), ors, db_path=db_path)
    if not origin or not destination:
        raise ValidationConfigError(f"Failed to resolve endpoints for case {case.get('case_id')}.")

    automatic_origin_port = find_nearest_port(origin["lat"], origin["lon"], ports)
    automatic_destination_port = find_nearest_port(destination["lat"], destination["lon"], ports)
    forced_origin_port = resolve_port(ports, _port_override_query(case, "origin"))
    forced_destination_port = resolve_port(ports, _port_override_query(case, "destination"))
    final_origin_port = forced_origin_port or automatic_origin_port
    final_destination_port = forced_destination_port or automatic_destination_port

    geometry = build_path_geometry_from_resolved(
        origin,
        destination,
        ors=ors,
        ports=ports,
        sea_matrix=sea_matrix,
        ors_profile=str(model.get("ors_profile") or model.get("profile") or "driving-car"),
        overwrite_road=_as_bool(model.get("overwrite_road"), default=False),
        db_path=db_path,
        port_origin=final_origin_port,
        port_destiny=final_destination_port,
    )
    if not geometry or geometry.get("status") != "ok":
        raise ValidationConfigError(f"Failed to build geometry for case {case.get('case_id')}.")

    override = _case_maritime_override(case)
    if override.required and override.distance_km is None:
        raise ValidationConfigError(
            f"Case {case.get('case_id')} requires a maritime distance override value before execution."
        )
    geometry_for_eval, original_sea_leg = apply_maritime_distance_override(geometry, override)

    same_port = _same_port(_port_name(final_origin_port), _port_name(final_destination_port))
    if same_port and not _as_bool(case.get("allow_same_port_evaluation"), default=False):
        row = build_result_row(
            config,
            case,
            geometry=geometry_for_eval,
            results=None,
            original_sea_leg=original_sea_leg,
            automatic_origin_port=automatic_origin_port,
            automatic_destination_port=automatic_destination_port,
            forced_origin_port=forced_origin_port,
            forced_destination_port=forced_destination_port,
        )
        row["validation_status"] = _clean_text(case.get("validation_status")) or "warning_only"
        row["same_port_flag"] = True
        row["cabotage_inappropriate_flag"] = True
        row["output_status"] = "warning_only"
        return row

    cargo_t = _case_cargo_t(config, case)
    if cargo_t is None:
        raise ValidationConfigError(f"Case {case.get('case_id')} requires cargo_t before execution.")

    allocation_mode = model.get("allocation_mode")
    if str(allocation_mode or "").strip().casefold() == "auto":
        allocation_mode = None
    results = evaluate_path(
        geometry_for_eval,
        cargo_t=float(cargo_t),
        truck_key=str(model.get("truck_key") or model.get("truck") or "semi_27t"),
        vessel_class=str(model.get("vessel_class") or "container_feeder"),
        include_hoteling=_as_bool(model.get("include_hoteling"), default=True),
        hoteling_hours_per_call=float(model.get("hoteling_hours_per_call") or 14.0),
        port_calls=int(model.get("port_calls") or 2),
        include_port_ops=_as_bool(model.get("include_port_ops"), default=True),
        port_moves_per_call=_float_or_none(model.get("port_moves_per_call"), field_name="port_moves_per_call"),
        cargo_teu=_case_teu(config, case),
        t_per_teu_default=float(model.get("t_per_teu_default") or 14.0),
        allocation_mode=allocation_mode,
        allocation_load_factor=_float_or_none(model.get("allocation_load_factor"), field_name="allocation_load_factor"),
        full_call_mode=_as_bool(model.get("full_call_mode"), default=False),
        port_ops_scenario=str(model.get("port_ops_scenario") or "santos_diesel_heavy"),
    )
    if not results:
        raise ValidationConfigError(f"Failed to evaluate case {case.get('case_id')}.")

    return build_result_row(
        config,
        case,
        geometry=geometry_for_eval,
        results=results,
        original_sea_leg=original_sea_leg,
        automatic_origin_port=automatic_origin_port,
        automatic_destination_port=automatic_destination_port,
        forced_origin_port=forced_origin_port,
        forced_destination_port=forced_destination_port,
    )


def build_rows(config: Mapping[str, Any], *, execute: bool = False) -> list[dict[str, Any]]:
    if not execute:
        return build_rows_without_execution(config)

    rows: list[dict[str, Any]] = []
    for case in config.get("cases") or []:
        if not isinstance(case, Mapping):
            raise ValidationConfigError("Each Batch 001B case must be an object.")
        mode = _case_execution_mode(case)
        if mode in RECORD_ONLY_MODES:
            rows.append(build_exclusion_row(config, case))
        elif mode == MODEL_RERUN_MODE:
            rows.append(_execute_model_case(config, case))
        elif mode in PLANNED_MODES:
            rows.append(build_planned_row(config, case))
        else:
            raise ValidationConfigError(f"Unsupported execution_mode for case {case.get('case_id')}: {mode}")
    return rows


def write_output_csv(rows: Sequence[Mapping[str, Any]], path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ALL_OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in ALL_OUTPUT_FIELDS})


def write_output_json(rows: Sequence[Mapping[str, Any]], path: Path | str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(list(rows), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def default_output_csv_path(config: Mapping[str, Any]) -> Path:
    return Path(str(config.get("output_csv") or "docs/validation/tf_validation_batch_001b_output.csv"))


def default_output_json_path(config: Mapping[str, Any]) -> Path:
    return Path(str(config.get("output_json") or "docs/validation/tf_validation_batch_001b_output.json"))
