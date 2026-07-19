# modules/multimodal/evaluator.py
# -*- coding: utf-8 -*-

"""
Multimodal evaluator.

Consumes path geometry and produces cost/emissions comparison between:
- direct road,
- multimodal (first mile + sea leg + last mile).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

# Path bootstrap
if __name__ == "__main__":
    import sys

    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.costs.diesel_prices import (
    DieselPriceLookup,
    build_price_lookup,
    get_average_price,
    get_average_price_from_lookup,
    get_price_for_uf,
    get_price_for_uf_from_lookup,
    normalize_uf,
)
from modules.costs.ship_fuel_prices import DEFAULT_OUTPUT_TXT, get_bunker_price
from modules.fuel.emissions import DIESEL_TTW_KG_CO2E_PER_L, get_ef_kg_per_kg
from modules.fuel.road_fuel_model import estimate_leg_liters
from modules.fuel.truck_specs import (
    AUTO_BY_WEIGHT_TRUCK_KEY,
    get_truck_spec,
    resolve_truck_spec_for_cargo,
)
from modules.infra.log_manager import get_logger
from modules.multimodal.container_efficiency import (
    DEFAULT_VESSEL_CLASS,
    VesselClassEfficiency,
    resolve_vessel_class_efficiency,
)
from modules.multimodal.hoteling import HotelingRateSelection, resolve_hoteling_rate
from modules.multimodal.port_ops import (
    DEFAULT_PORT_OPS_SCENARIO,
    PortOpsScenarioSelection,
    estimate_port_ops,
    resolve_port_ops_scenario,
)

_log = get_logger(__name__)

_MARINE_FUEL_TYPE = "vlsfo"
_BUNKER_EF_KG_CO2E_PER_KG = float(get_ef_kg_per_kg(_MARINE_FUEL_TYPE))
_NM_TO_KM = 1.852
_KG_PER_TONNE = 1000.0
_DEFAULT_TEU_LOAD_FACTOR = 0.80
_PAIR_WEIGHTED_MEAN_METHOD = "transport_work_weighted_mean"
_PAIR_ZERO_WORK_MEAN_METHOD = (
    "unweighted_mean_resolved_same_od_voyages_zero_transport_work"
)
_PAIR_WEIGHTED_MEAN_SOURCE = (
    "antaq_mrv_same_od_transport_work_weighted_mean"
)
_PAIR_ZERO_WORK_MEAN_SOURCE = (
    "antaq_mrv_same_od_unweighted_mean_zero_transport_work"
)


@dataclass(frozen=True)
class PreparedEvaluationContext:
    """Scenario-wide evaluator inputs prepared once and reused across many paths."""

    truck_spec: Dict[str, Any]
    diesel_lookup: DieselPriceLookup | None
    diesel_price_override: float | None
    bunker_price_ton: float
    vessel_eff: VesselClassEfficiency
    hoteling_sel: HotelingRateSelection | None
    port_ops_selection: PortOpsScenarioSelection | None


def _resolve_uf_from_point(point: Dict[str, Any]) -> str:
    """Resolve a UF code from a location or selected-port record."""
    for key in ("uf", "state"):
        uf = normalize_uf(str(point.get(key) or ""))
        if uf:
            return uf

    label = str(point.get("label") or "").strip()
    if "," in label:
        uf = normalize_uf(label.split(",")[-1].strip())
        if uf:
            return uf

    return ""


def _port_name_from_geometry(port: Any) -> str | None:
    if not isinstance(port, Mapping):
        return None
    for key in ("name", "city", "label"):
        value = port.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _resolve_port_call_names(path_data: Mapping[str, Any], port_calls: int) -> list[str]:
    names: list[str] = []
    for key in ("port_origin", "port_destiny"):
        name = _port_name_from_geometry(path_data.get(key))
        if name:
            names.append(name)

    if not names:
        sea_leg = path_data.get("sea_leg") if isinstance(path_data.get("sea_leg"), Mapping) else {}
        corridor_ports = sea_leg.get("corridor_port_path") if isinstance(sea_leg, Mapping) else None
        if isinstance(corridor_ports, list):
            names = [str(item).strip() for item in corridor_ports if str(item or "").strip()]

    calls = max(int(port_calls), 0)
    if len(names) >= calls:
        return names[:calls]
    while len(names) < calls:
        names.append(f"port_call_{len(names) + 1}")
    return names


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


def _positive_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0.0 else None


def _nonnegative_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0.0 else None


def _first_mapping_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _build_selected_corridor_sublegs(
    sea_leg_data: Mapping[str, Any],
    *,
    cargo_t: float,
    pair_intensity_g_per_tnm: float | None = None,
    pair_intensity_source: str | None = None,
) -> tuple[list[Dict[str, Any]], bool]:
    """Apply the OD representative intensity to the selected path geometry."""
    raw_legs = sea_leg_data.get("selected_corridor_sublegs")
    if not isinstance(raw_legs, list):
        return [], False

    scenario_cargo_t = max(float(cargo_t), 0.0)
    enriched_legs: list[Dict[str, Any]] = []
    all_sublegs_resolved = True
    for raw_leg in raw_legs:
        if not isinstance(raw_leg, Mapping):
            all_sublegs_resolved = False
            continue

        distance_km = _positive_float_or_none(raw_leg.get("distance_km"))
        distance_nm = _positive_float_or_none(raw_leg.get("distance_nm"))
        if distance_nm is None and distance_km is not None:
            distance_nm = distance_km / _NM_TO_KM
        if distance_km is None and distance_nm is not None:
            distance_km = distance_nm * _NM_TO_KM

        observed_corridor_fuel_g_per_tnm = _positive_float_or_none(
            _first_mapping_value(
                raw_leg,
                "fuel_g_per_tnm",
                "intensity_g_per_tnm",
                "weighted_fuel_intensity_g_per_tnm",
            )
        )
        scenario_fuel_g_per_tnm = (
            pair_intensity_g_per_tnm
            if pair_intensity_g_per_tnm is not None
            and pair_intensity_g_per_tnm > 0.0
            else observed_corridor_fuel_g_per_tnm
        )
        observed_cargo_t = _nonnegative_float_or_none(
            _first_mapping_value(
                raw_leg,
                "observed_cargo_t",
                "average_cargo_onboard_t",
                "cargo_onboard_t",
                "cargo_weight_t",
            )
        )
        transport_work_tnm = _nonnegative_float_or_none(
            _first_mapping_value(
                raw_leg,
                "transport_work_tnm",
                "observed_transport_work_tnm",
                "tonne_nm",
            )
        )
        if (
            transport_work_tnm is None
            and observed_cargo_t is not None
            and distance_nm is not None
        ):
            transport_work_tnm = observed_cargo_t * distance_nm

        observed_fuel_kg = _nonnegative_float_or_none(
            _first_mapping_value(
                raw_leg,
                "observed_fuel_kg",
                "fuel_consumption_kg",
                "fuel_kg",
            )
        )
        if observed_fuel_kg is None:
            observed_fuel_g = _nonnegative_float_or_none(
                raw_leg.get("fuel_consumption_g")
            )
            if observed_fuel_g is not None:
                observed_fuel_kg = observed_fuel_g / _KG_PER_TONNE
        if (
            observed_fuel_kg is None
            and observed_corridor_fuel_g_per_tnm is not None
            and transport_work_tnm is not None
        ):
            observed_fuel_kg = (
                observed_corridor_fuel_g_per_tnm
                * transport_work_tnm
                / _KG_PER_TONNE
            )

        scenario_fuel_kg = (
            None
            if distance_nm is None or scenario_fuel_g_per_tnm is None
            else scenario_fuel_g_per_tnm
            * scenario_cargo_t
            * distance_nm
            / _KG_PER_TONNE
        )
        if scenario_fuel_kg is None:
            all_sublegs_resolved = False

        observed_intensity_source = _first_mapping_value(
            raw_leg,
            "intensity_source",
            "fuel_g_per_tnm_source",
        )
        observed_intensity_source_level = _first_mapping_value(
            raw_leg,
            "intensity_source_level",
            "source_level",
        )
        raw_observed_source_counts = raw_leg.get("intensity_source_counts")
        observed_intensity_source_counts = (
            dict(raw_observed_source_counts)
            if isinstance(raw_observed_source_counts, Mapping)
            else {}
        )
        uses_pair_intensity = (
            pair_intensity_g_per_tnm is not None
            and pair_intensity_g_per_tnm > 0.0
        )
        scenario_intensity_source = (
            pair_intensity_source
            if uses_pair_intensity and pair_intensity_source
            else observed_intensity_source
        )
        enriched = dict(raw_leg)
        enriched.update(
            {
                "origin_port": _first_mapping_value(
                    raw_leg,
                    "origin_port",
                    "from_port_name",
                    "from_port",
                    "origin",
                ),
                "destination_port": _first_mapping_value(
                    raw_leg,
                    "destination_port",
                    "to_port_name",
                    "to_port",
                    "destination",
                ),
                "distance_km": distance_km,
                "distance_nm": distance_nm,
                "observed_cargo_t": observed_cargo_t,
                "transport_work_tnm": transport_work_tnm,
                "fuel_g_per_tnm": observed_corridor_fuel_g_per_tnm,
                "scenario_fuel_g_per_tnm": scenario_fuel_g_per_tnm,
                "applied_pair_intensity_g_per_tnm": (
                    pair_intensity_g_per_tnm
                    if uses_pair_intensity
                    else None
                ),
                "observed_corridor_fuel_g_per_tnm": (
                    observed_corridor_fuel_g_per_tnm
                ),
                "intensity_source": observed_intensity_source,
                "observed_corridor_intensity_source": observed_intensity_source,
                "observed_corridor_intensity_source_level": (
                    observed_intensity_source_level
                ),
                "observed_corridor_intensity_source_counts": (
                    observed_intensity_source_counts
                ),
                "intensity_source_level": observed_intensity_source_level,
                "scenario_intensity_source": scenario_intensity_source,
                "scenario_intensity_source_level": (
                    "od_pair" if uses_pair_intensity else observed_intensity_source_level
                ),
                "observed_fuel_kg": observed_fuel_kg,
                "scenario_cargo_t": scenario_cargo_t,
                "scenario_fuel_kg": scenario_fuel_kg,
                "scenario_co2e_kg": (
                    None
                    if scenario_fuel_kg is None
                    else scenario_fuel_kg * _BUNKER_EF_KG_CO2E_PER_KG
                ),
                "scenario_fuel_formula": (
                    "scenario_fuel_g_per_tnm * scenario_cargo_t * distance_nm / 1000"
                ),
            }
        )
        enriched_legs.append(enriched)

    return enriched_legs, bool(enriched_legs) and all_sublegs_resolved


def _build_observed_port_pair_legs(
    sea_leg_data: Mapping[str, Any],
    *,
    cargo_t: float,
) -> list[Dict[str, Any]]:
    """Enrich observed port-pair statistics with scenario cargo attribution."""
    raw_legs = sea_leg_data.get("observed_port_pair_legs")
    if not isinstance(raw_legs, list):
        return []

    attributed_cargo_t = max(float(cargo_t), 0.0)
    enriched_legs: list[Dict[str, Any]] = []
    for raw_leg in raw_legs:
        if not isinstance(raw_leg, Mapping):
            continue

        distance_nm = _positive_float_or_none(raw_leg.get("distance_nm"))
        intensity = _positive_float_or_none(
            raw_leg.get("weighted_fuel_intensity_g_per_tnm")
        )
        attributed_fuel_kg = (
            None
            if distance_nm is None or intensity is None
            else intensity * attributed_cargo_t * distance_nm / _KG_PER_TONNE
        )
        attributed_co2e_kg = (
            None
            if attributed_fuel_kg is None
            else attributed_fuel_kg * _BUNKER_EF_KG_CO2E_PER_KG
        )

        enriched_legs.append(
            {
                "origin_port": raw_leg.get("origin_port"),
                "destination_port": raw_leg.get("destination_port"),
                "observed_segment_count": int(
                    raw_leg.get("observed_segment_count") or 0
                ),
                "distinct_voyage_count": int(
                    raw_leg.get("distinct_voyage_count") or 0
                ),
                "distinct_imo_count": int(raw_leg.get("distinct_imo_count") or 0),
                "average_cargo_t": _positive_float_or_none(
                    raw_leg.get("average_cargo_t")
                ),
                "distance_nm": distance_nm,
                "weighted_fuel_intensity_g_per_tnm": intensity,
                "attributed_cargo_t": attributed_cargo_t,
                "attributed_vlsfo_fuel_kg": attributed_fuel_kg,
                "attributed_co2e_kg": attributed_co2e_kg,
                "emission_factor_kg_co2e_per_kg_vlsfo": (
                    _BUNKER_EF_KG_CO2E_PER_KG
                ),
                "matched_segment_count": int(
                    raw_leg.get("matched_segment_count") or 0
                ),
                "matched_voyage_count": int(
                    raw_leg.get("matched_voyage_count") or 0
                ),
                "matched_imo_count": int(raw_leg.get("matched_imo_count") or 0),
                "distance_km": _positive_float_or_none(raw_leg.get("distance_km")),
                "average_cargo_basis": (
                    "cargo_weight_t_total / observed_segment_count"
                ),
                "fuel_attribution_formula": (
                    "weighted_fuel_intensity_g_per_tnm * attributed_cargo_t "
                    "* distance_nm / 1000"
                ),
                "emissions_formula": (
                    "attributed_vlsfo_fuel_kg "
                    "* emission_factor_kg_co2e_per_kg_vlsfo"
                ),
            }
        )

    return enriched_legs


def _resolve_cargo_teu(cargo_t: float, cargo_teu: float | None, t_per_teu_default: float) -> int:
    if cargo_teu is not None:
        try:
            teu = float(cargo_teu)
        except (TypeError, ValueError):
            teu = 0.0
        if teu > 0:
            return max(int(math.ceil(teu)), 1)

    cargo_t = max(float(cargo_t), 0.0)
    t_per_teu_default = max(float(t_per_teu_default), 0.1)
    if cargo_t <= 0.0:
        return 0
    return max(int(math.ceil(cargo_t / t_per_teu_default)), 1)


def _cargo_allocation_share_dwt(cargo_t: float, size_proxy_t_median: float | None) -> float:
    if size_proxy_t_median is None or size_proxy_t_median <= 0:
        return 1.0
    share = float(cargo_t) / float(size_proxy_t_median)
    if share < 0:
        return 0.0
    return min(share, 1.0)


def compute_cargo_allocation_share(
    inputs: Dict[str, Any],
    vessel_meta: Dict[str, Any],
) -> tuple[float, Dict[str, Any]]:
    """
    Compute cargo allocation share for maritime fuel attribution.

    Supported modes:
    - dwt_share: legacy mass proxy share (cargo_t / size_proxy_t_median)
    - teu_share: cargo TEU share over operational loaded TEU capacity
    """
    cargo_t = max(float(inputs.get("cargo_t") or 0.0), 0.0)
    cargo_teu = inputs.get("cargo_teu")
    t_per_teu_default = max(float(inputs.get("t_per_teu_default") or 14.0), 0.1)

    requested_mode_raw = str(inputs.get("allocation_mode") or "").strip().lower()
    requested_mode = requested_mode_raw if requested_mode_raw in {"dwt_share", "teu_share"} else None

    load_factor_requested = inputs.get("load_factor")
    try:
        load_factor = float(load_factor_requested) if load_factor_requested is not None else _DEFAULT_TEU_LOAD_FACTOR
    except (TypeError, ValueError):
        load_factor = _DEFAULT_TEU_LOAD_FACTOR
    if load_factor <= 0:
        load_factor = _DEFAULT_TEU_LOAD_FACTOR
    load_factor = _clamp(float(load_factor), 0.01, 1.0)

    vessel_class = str(vessel_meta.get("vessel_class") or "").strip().lower()

    size_proxy_t_median_raw = vessel_meta.get("size_proxy_t_median")
    try:
        size_proxy_t_median = float(size_proxy_t_median_raw) if size_proxy_t_median_raw is not None else None
    except (TypeError, ValueError):
        size_proxy_t_median = None
    if isinstance(size_proxy_t_median, float) and size_proxy_t_median <= 0:
        size_proxy_t_median = None

    teu_capacity_raw = vessel_meta.get("teu_capacity")
    try:
        teu_capacity = float(teu_capacity_raw) if teu_capacity_raw is not None else None
    except (TypeError, ValueError):
        teu_capacity = None
    if isinstance(teu_capacity, float) and teu_capacity <= 0:
        teu_capacity = None

    lightship_raw = vessel_meta.get("lightship_t")
    try:
        lightship_t = float(lightship_raw) if lightship_raw is not None else None
    except (TypeError, ValueError):
        lightship_t = None
    if isinstance(lightship_t, float) and lightship_t <= 0:
        lightship_t = None

    cargo_teu_resolved = _resolve_cargo_teu(
        cargo_t=cargo_t,
        cargo_teu=cargo_teu,
        t_per_teu_default=t_per_teu_default,
    )

    share_old_dwt = _cargo_allocation_share_dwt(
        cargo_t=cargo_t,
        size_proxy_t_median=size_proxy_t_median,
    )

    teu_loaded = None
    share_new_teu = share_old_dwt
    if teu_capacity is not None and teu_capacity > 0:
        teu_loaded = teu_capacity * load_factor
        if teu_loaded > 0:
            share_new_teu = _clamp(float(cargo_teu_resolved) / float(teu_loaded), 0.0, 1.0)

    default_mode = "teu_share" if vessel_class.startswith("container") else "dwt_share"
    mode_used = requested_mode or default_mode

    if mode_used == "teu_share" and not (isinstance(teu_loaded, (int, float)) and teu_loaded > 0):
        mode_used = "dwt_share"

    share_used = share_new_teu if mode_used == "teu_share" else share_old_dwt
    ratio_new_vs_old = (share_new_teu / share_old_dwt) if share_old_dwt > 0 else None

    debug: Dict[str, Any] = {
        "allocation_mode_requested": requested_mode,
        "allocation_mode_default": default_mode,
        "allocation_mode_used": mode_used,
        "teu_capacity": teu_capacity,
        "load_factor": load_factor,
        "teu_loaded": teu_loaded,
        "cargo_teu_resolved": int(cargo_teu_resolved),
        "share_old_dwt": float(share_old_dwt),
        "share_new_teu": float(share_new_teu),
        "ratio_new_vs_old": (None if ratio_new_vs_old is None else float(ratio_new_vs_old)),
    }

    if (
        lightship_t is not None
        and cargo_teu_resolved > 0
        and isinstance(teu_loaded, (int, float))
        and teu_loaded > 0
    ):
        debug["eff_t_per_teu"] = (cargo_t / float(cargo_teu_resolved)) + (lightship_t / float(teu_loaded))

    return float(share_used), debug


def prepare_evaluation_context(
    *,
    truck_key: str = "semi_27t",
    diesel_price: Optional[float] = None,
    diesel_default_price_r_per_l: float = 6.0,
    diesel_csv_path: Optional[Path] = None,
    vessel_class: str = DEFAULT_VESSEL_CLASS,
    vessel_efficiency_path: Optional[Path] = None,
    include_hoteling: bool = True,
    hoteling_hours_per_call: float = 14.0,
    port_calls: int = 2,
    hoteling_rate_path: Optional[Path] = None,
    include_port_ops: bool = True,
    port_ops_scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    port_ops_params_path: Optional[Path] = None,
    bunker_price_brl_mt: float = 3500.0,
    bunker_price_override_brl_mt: Optional[float] = None,
) -> PreparedEvaluationContext:
    """Prepare scenario-wide evaluator inputs once for reuse across many destinations."""
    hoteling_hours_total = max(float(hoteling_hours_per_call), 0.0) * max(int(port_calls), 0)

    vessel_eff = resolve_vessel_class_efficiency(
        vessel_class=vessel_class,
        efficiency_json_path=vessel_efficiency_path,
    )
    uses_transport_work_intensity = bool(
        isinstance(vessel_eff.fuel_g_per_tnm, (int, float)) and float(vessel_eff.fuel_g_per_tnm) > 0.0
    )

    hoteling_sel = None
    if bool(include_hoteling) and hoteling_hours_total > 0 and not uses_transport_work_intensity:
        hoteling_sel = resolve_hoteling_rate(
            vessel_class=vessel_eff.vessel_class,
            hoteling_rate_path=hoteling_rate_path,
        )

    port_ops_selection = None
    if bool(include_port_ops) and max(int(port_calls), 0) > 0:
        port_ops_selection = resolve_port_ops_scenario(
            scenario=port_ops_scenario,
            params_path=port_ops_params_path,
        )

    diesel_lookup = None
    diesel_price_override = None if diesel_price is None else float(diesel_price)
    if diesel_price_override is None:
        diesel_lookup = build_price_lookup(
            default_price_r_per_l=diesel_default_price_r_per_l,
            csv_path=diesel_csv_path,
        )

    context = PreparedEvaluationContext(
        truck_spec=get_truck_spec(truck_key),
        diesel_lookup=diesel_lookup,
        diesel_price_override=diesel_price_override,
        bunker_price_ton=(
            float(bunker_price_override_brl_mt)
            if bunker_price_override_brl_mt is not None
            else float(get_bunker_price(default_price_brl_mt=bunker_price_brl_mt))
        ),
        vessel_eff=vessel_eff,
        hoteling_sel=hoteling_sel,
        port_ops_selection=port_ops_selection,
    )

    _log.info(
        (
            "Prepared evaluation context: truck=%s vessel_class=%s diesel_mode=%s "
            "diesel_rows=%d bunker_price=R$ %.2f/mt hoteling=%s port_ops=%s"
        ),
        truck_key,
        vessel_eff.vessel_class,
        ("explicit_override" if diesel_price_override is not None else "lookup"),
        (0 if diesel_lookup is None else diesel_lookup.row_count),
        context.bunker_price_ton,
        bool(hoteling_sel is not None),
        bool(port_ops_selection is not None),
    )
    return context


def evaluate_path(
    path_data: Dict[str, Any],
    cargo_t: float,
    truck_key: str = "semi_27t",
    diesel_price: Optional[float] = None,
    vessel_class: str = DEFAULT_VESSEL_CLASS,
    vessel_efficiency_path: Optional[Path] = None,
    include_hoteling: bool = True,
    hoteling_hours_per_call: float = 14.0,
    port_calls: int = 2,
    hoteling_rate_path: Optional[Path] = None,
    include_port_ops: bool = True,
    port_moves_per_call: Optional[float] = None,
    cargo_teu: Optional[float] = None,
    t_per_teu_default: float = 14.0,
    allocation_mode: Optional[str] = None,
    allocation_load_factor: Optional[float] = None,
    full_call_mode: bool = False,
    port_ops_scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    port_ops_params_path: Optional[Path] = None,
    port_ops_stat_key: str = "median",
    port_ops_observed_ports: Optional[Sequence[Mapping[str, Any]]] = None,
    prepared_context: PreparedEvaluationContext | None = None,
    diesel_default_price_r_per_l: float = 6.0,
    diesel_csv_path: Optional[Path] = None,
    bunker_price_override_brl_mt: Optional[float] = None,
    debug_trace: bool = False,
) -> Dict[str, Any]:
    """Assess costs and emissions for a path geometry payload."""

    def _trace(stage: str, status: str, source: str, **details: Any) -> None:
        if not debug_trace:
            return
        detail_text = " ".join(f"{key}={value!r}" for key, value in details.items())
        suffix = f" {detail_text}" if detail_text else ""
        _log.debug(
            "single_eval stage=%s status=%s source=%s%s",
            stage,
            status,
            source,
            suffix,
        )

    if not path_data or path_data.get("status") != "ok":
        _log.warning("Cannot evaluate invalid path geometry.")
        _trace("evaluation", "failed", "path_geometry", reason="invalid_geometry")
        return {}

    _trace(
        "evaluation",
        "start",
        "resolved_path_geometry_and_user_scenario",
        cargo_t=cargo_t,
        truck_key=truck_key,
        vessel_class=vessel_class,
        include_hoteling=include_hoteling,
        include_port_ops=include_port_ops,
    )

    include_hoteling = bool(include_hoteling)
    include_port_ops = bool(include_port_ops)
    hoteling_hours_per_call = max(float(hoteling_hours_per_call), 0.0)
    port_calls = max(int(port_calls), 0)
    hoteling_hours_total_requested = hoteling_hours_per_call * float(port_calls) if include_hoteling else 0.0

    try:
        context = prepared_context or prepare_evaluation_context(
            truck_key=truck_key,
            diesel_price=diesel_price,
            diesel_default_price_r_per_l=diesel_default_price_r_per_l,
            diesel_csv_path=diesel_csv_path,
            vessel_class=vessel_class,
            vessel_efficiency_path=vessel_efficiency_path,
            include_hoteling=include_hoteling,
            hoteling_hours_per_call=hoteling_hours_per_call,
            port_calls=port_calls,
            hoteling_rate_path=hoteling_rate_path,
            include_port_ops=include_port_ops,
            port_ops_scenario=port_ops_scenario,
            port_ops_params_path=port_ops_params_path,
            bunker_price_override_brl_mt=bunker_price_override_brl_mt,
        )
    except Exception as exc:
        _log.error("Failed to prepare evaluation context: %s", exc)
        _trace("evaluation_context", "failed", "tracked_data_assets", error=str(exc))
        return {}

    _trace(
        "evaluation_context",
        "complete",
        "tracked_parameters_and_data_assets",
        prepared_context_reused=prepared_context is not None,
        truck_key=truck_key,
        vessel_class_requested=context.vessel_eff.requested_class,
        vessel_class_resolved=context.vessel_eff.vessel_class,
        vessel_efficiency_path=str(context.vessel_eff.source_path),
        vessel_sample_size=context.vessel_eff.sample_size,
        diesel_mode="explicit_override" if context.diesel_price_override is not None else "csv_lookup",
        diesel_csv_path=None if context.diesel_lookup is None else context.diesel_lookup.source_csv,
        diesel_row_count=0 if context.diesel_lookup is None else context.diesel_lookup.row_count,
        bunker_price_brl_mt=context.bunker_price_ton,
        bunker_price_source="santos_bunker_data_asset_with_default_fallback",
        bunker_price_configured_path=DEFAULT_OUTPUT_TXT,
        hoteling_source=None if context.hoteling_sel is None else str(context.hoteling_sel.source_path),
        port_ops_source=None if context.port_ops_selection is None else str(context.port_ops_selection.source_path),
    )

    try:
        cargo_t = float(cargo_t)
    except (TypeError, ValueError):
        _log.error("Invalid cargo_t for path evaluation: %r", cargo_t)
        _trace("validate_cargo", "failed", "user_input", cargo_t=cargo_t)
        return {}

    calculation_warnings: list[str] = []
    if cargo_t < 0.0:
        calculation_warnings.append(
            "Negative cargo_t is invalid for emissions allocation; cargo mass was treated as zero activity."
        )
        cargo_t = 0.0

    cargo_mass_positive = cargo_t > 0.0
    cargo_teu_positive = _positive_float_or_none(cargo_teu) is not None
    if cargo_mass_positive:
        cargo_activity_status = "positive_cargo_mass"
    elif cargo_teu_positive:
        cargo_activity_status = "positive_teu_without_positive_cargo_mass"
        calculation_warnings.append(
            "Cargo TEU was positive but cargo_t was not; mass-based road, navigation, and hoteling emissions "
            "cannot be interpreted as a loaded-cargo movement."
        )
    else:
        cargo_activity_status = "zero_cargo_activity"
        calculation_warnings.append(
            "No positive cargo mass or TEU activity was provided; cargo-scaled emissions are treated as zero activity."
        )

    if str(truck_key).strip() == AUTO_BY_WEIGHT_TRUCK_KEY:
        truck_spec = resolve_truck_spec_for_cargo(cargo_t, truck_key)
    else:
        truck_spec = context.truck_spec
    vessel_eff = context.vessel_eff
    hoteling_sel = context.hoteling_sel

    origin_uf = _resolve_uf_from_point(path_data.get("origin", {}))
    destiny_uf = _resolve_uf_from_point(path_data.get("destiny", {}))
    port_origin_uf = _resolve_uf_from_point(path_data.get("port_origin", {}))
    port_destiny_uf = _resolve_uf_from_point(path_data.get("port_destiny", {}))
    active_diesel_override = (
        float(diesel_price)
        if diesel_price is not None
        else (
            None
            if context.diesel_price_override is None
            else float(context.diesel_price_override)
        )
    )

    def _explicit_diesel_meta(
        *,
        price_scope: str,
        uf_origin: str = "",
        uf_destiny: str = "",
        uf: str = "",
    ) -> dict[str, Any]:
        assert active_diesel_override is not None
        meta: dict[str, Any] = {
            "price_r_per_l": active_diesel_override,
            "source": "explicit_override",
            "price_method": "explicit_override",
            "price_scope": price_scope,
            "fallback_used": False,
            "csv_path": None,
        }
        if uf:
            meta["uf"] = uf
        else:
            meta["uf_origin"] = uf_origin or None
            meta["uf_destiny"] = uf_destiny or None
        return meta

    def _resolve_pair_diesel_meta(
        uf_start: str,
        uf_end: str,
        *,
        price_scope: str,
    ) -> dict[str, Any]:
        if active_diesel_override is not None:
            return _explicit_diesel_meta(
                price_scope=price_scope,
                uf_origin=uf_start,
                uf_destiny=uf_end,
            )
        if context.diesel_lookup is not None:
            meta = get_average_price_from_lookup(uf_start, uf_end, context.diesel_lookup)
        else:
            meta = get_average_price(
                uf_start,
                uf_end,
                default_price_r_per_l=diesel_default_price_r_per_l,
                csv_path=diesel_csv_path,
            )
        return {
            **meta,
            "price_method": "uf_pair_arithmetic_mean",
            "price_scope": price_scope,
        }

    def _resolve_port_diesel_meta(uf: str, *, price_scope: str) -> dict[str, Any]:
        if active_diesel_override is not None:
            return _explicit_diesel_meta(price_scope=price_scope, uf=uf)
        if context.diesel_lookup is not None:
            meta = get_price_for_uf_from_lookup(uf, context.diesel_lookup)
        else:
            meta = get_price_for_uf(
                uf,
                default_price_r_per_l=diesel_default_price_r_per_l,
                csv_path=diesel_csv_path,
            )
        return {**meta, "price_scope": price_scope}

    diesel_price_metas = {
        "road_direct": _resolve_pair_diesel_meta(
            origin_uf,
            destiny_uf,
            price_scope="road_direct",
        ),
        "first_mile": _resolve_pair_diesel_meta(
            origin_uf,
            port_origin_uf,
            price_scope="first_mile",
        ),
        "last_mile": _resolve_pair_diesel_meta(
            port_destiny_uf,
            destiny_uf,
            price_scope="last_mile",
        ),
        "port_origin": _resolve_port_diesel_meta(
            port_origin_uf,
            price_scope="port_origin",
        ),
        "port_destiny": _resolve_port_diesel_meta(
            port_destiny_uf,
            price_scope="port_destiny",
        ),
    }
    diesel_meta = diesel_price_metas["road_direct"]
    price_l = float(diesel_meta.get("price_r_per_l", diesel_default_price_r_per_l))
    diesel_source = str(diesel_meta.get("source", "latest_diesel_prices_csv"))

    for price_scope, price_meta in diesel_price_metas.items():
        _trace(
            "diesel_price" if price_scope == "road_direct" else f"diesel_price_{price_scope}",
            "complete",
            str(price_meta.get("source", "latest_diesel_prices_csv")),
            price_r_per_l=price_meta.get("price_r_per_l"),
            price_method=price_meta.get("price_method"),
            uf=price_meta.get("uf"),
            uf_origin=price_meta.get("uf_origin"),
            uf_destiny=price_meta.get("uf_destiny"),
            price_origin=price_meta.get("price_origin"),
            price_destiny=price_meta.get("price_destiny"),
            fallback_used=price_meta.get("fallback_used"),
            csv_path=price_meta.get("csv_path") or price_meta.get("source_csv"),
        )

    _log.debug(
        (
            "Evaluator inputs: cargo_t=%.3f truck=%s diesel=R$ %.4f/L uf_o=%s uf_d=%s "
            "vessel_class=%s include_hoteling=%s include_port_ops=%s"
        ),
        cargo_t,
        truck_key,
        price_l,
        origin_uf or "<missing>",
        destiny_uf or "<missing>",
        vessel_eff.vessel_class,
        include_hoteling,
        include_port_ops,
    )

    def _calc_road(
        leg_name: str,
        leg: Dict[str, Any],
        diesel_price_meta: Mapping[str, Any],
    ) -> Dict[str, Any]:
        leg_price_l = float(diesel_price_meta.get("price_r_per_l", diesel_default_price_r_per_l))
        dist_raw = leg.get("distance_km")
        dist_km = float(dist_raw) if dist_raw is not None else 0.0
        if dist_km <= 0.0:
            result = {
                "distance_km": dist_km,
                "trips": 0,
                "liters": 0.0,
                "diesel_price_r_per_l": leg_price_l,
                "diesel_price_meta": dict(diesel_price_meta),
                "cost": 0.0,
                "co2e": 0.0,
            }
            _trace(
                f"calculate_{leg_name}",
                "complete",
                str(leg.get("source") or "route_geometry"),
                distance_km=dist_km,
                trips=0,
                liters=0.0,
                diesel_price_r_per_l=leg_price_l,
                cost_brl=0.0,
                co2e_kg=0.0,
            )
            return result

        liters, _, _, trips, km_per_liter, _ = estimate_leg_liters(
            distance_km=dist_km,
            cargo_t=cargo_t,
            spec=truck_spec,
            empty_backhaul_share=0.0,
        )

        liters = float(liters)
        cost = liters * leg_price_l
        co2e = liters * DIESEL_TTW_KG_CO2E_PER_L

        result = {
            "distance_km": dist_km,
            "trips": int(trips),
            "liters": liters,
            "km_per_liter": float(km_per_liter),
            "diesel_price_r_per_l": leg_price_l,
            "diesel_price_meta": dict(diesel_price_meta),
            "cost": float(cost),
            "co2e": float(co2e),
        }
        _trace(
            f"calculate_{leg_name}",
            "complete",
            str(leg.get("source") or "route_geometry"),
            distance_km=dist_km,
            trips=int(trips),
            liters=liters,
            diesel_price_r_per_l=leg_price_l,
            diesel_emission_factor_kg_co2e_per_l=DIESEL_TTW_KG_CO2E_PER_L,
            diesel_emission_factor_source="tracked_model_constant",
            cost_brl=float(cost),
            co2e_kg=float(co2e),
        )
        return result

    res_direct = _calc_road(
        "road_direct",
        path_data.get("road_direct", {}),
        diesel_price_metas["road_direct"],
    )
    res_first = _calc_road(
        "first_mile",
        path_data.get("first_mile", {}),
        diesel_price_metas["first_mile"],
    )
    res_last = _calc_road(
        "last_mile",
        path_data.get("last_mile", {}),
        diesel_price_metas["last_mile"],
    )

    route_quality_warnings = [
        dict(item)
        for item in (path_data.get("route_quality_warnings") or [])
        if isinstance(item, dict)
    ]
    sea_leg_data = path_data.get("sea_leg", {}) if isinstance(path_data.get("sea_leg"), dict) else {}
    sea_dist_km = float(sea_leg_data.get("distance_km") or 0.0)
    sea_dist_nm = sea_dist_km / _NM_TO_KM if sea_dist_km > 0 else 0.0
    bunker_price_ton = float(context.bunker_price_ton)

    cargo_share, allocation_debug = compute_cargo_allocation_share(
        inputs={
            "cargo_t": cargo_t,
            "cargo_teu": cargo_teu,
            "t_per_teu_default": t_per_teu_default,
            "allocation_mode": allocation_mode,
            "load_factor": allocation_load_factor,
        },
        vessel_meta={
            "vessel_class": vessel_eff.vessel_class,
            "size_proxy_t_median": vessel_eff.size_proxy_t_median,
            "teu_capacity": vessel_eff.teu_capacity,
            "lightship_t": vessel_eff.lightship_t,
        },
    )
    if not cargo_mass_positive:
        cargo_share = 0.0
        allocation_debug["cargo_allocation_suppressed_reason"] = "nonpositive_cargo_mass"

    pair_intensity_g_per_tnm = _positive_float_or_none(
        sea_leg_data.get("pair_intensity_g_per_tnm")
    )
    pair_intensity_method = str(
        sea_leg_data.get("pair_intensity_method") or ""
    ).strip() or None
    pair_intensity_source = str(
        sea_leg_data.get("pair_intensity_source") or ""
    ).strip() or None
    scenario_distance_method = str(
        sea_leg_data.get("scenario_distance_method") or ""
    ).strip() or None
    uses_mean_observed_distance = bool(scenario_distance_method)
    if pair_intensity_g_per_tnm is not None and pair_intensity_source is None:
        pair_intensity_source = (
            _PAIR_ZERO_WORK_MEAN_SOURCE
            if pair_intensity_method == _PAIR_ZERO_WORK_MEAN_METHOD
            else _PAIR_WEIGHTED_MEAN_SOURCE
        )
    sea_leg_fuel_g_per_tnm = _positive_float_or_none(
        sea_leg_data.get("fuel_g_per_tnm")
    )
    selected_corridor_sublegs, selected_corridor_sublegs_complete = (
        _build_selected_corridor_sublegs(
            sea_leg_data,
            cargo_t=cargo_t,
            pair_intensity_g_per_tnm=pair_intensity_g_per_tnm,
            pair_intensity_source=pair_intensity_source,
        )
    )
    if uses_mean_observed_distance:
        # A mean distance represents many complete observed voyages. It has no
        # single corridor whose sublegs could be used in the scenario formula.
        selected_corridor_sublegs = []
        selected_corridor_sublegs_complete = False
    route_observation_mode = str(
        sea_leg_data.get("route_observation_mode") or ""
    ).strip()
    raw_intensity_source_counts = sea_leg_data.get("intensity_source_counts")
    intensity_source_counts = (
        dict(raw_intensity_source_counts)
        if isinstance(raw_intensity_source_counts, Mapping)
        else {}
    )
    raw_pair_intensity_source_counts = sea_leg_data.get(
        "pair_intensity_source_counts"
    )
    pair_intensity_source_counts = (
        dict(raw_pair_intensity_source_counts)
        if isinstance(raw_pair_intensity_source_counts, Mapping)
        else {}
    )
    raw_pair_effective_source_counts = sea_leg_data.get(
        "pair_intensity_effective_source_counts"
    )
    pair_intensity_effective_source_counts = (
        dict(raw_pair_effective_source_counts)
        if isinstance(raw_pair_effective_source_counts, Mapping)
        else dict(pair_intensity_source_counts)
    )
    raw_distance_source_counts = sea_leg_data.get("distance_source_counts")
    distance_source_counts = (
        dict(raw_distance_source_counts)
        if isinstance(raw_distance_source_counts, Mapping)
        else {}
    )
    raw_selected_distance_source_counts = sea_leg_data.get(
        "selected_corridor_distance_source_counts"
    )
    selected_corridor_distance_source_counts = (
        dict(raw_selected_distance_source_counts)
        if isinstance(raw_selected_distance_source_counts, Mapping)
        else {}
    )
    raw_scenario_distance_source_counts = sea_leg_data.get(
        "scenario_distance_source_counts"
    )
    scenario_distance_source_counts = (
        dict(raw_scenario_distance_source_counts)
        if isinstance(raw_scenario_distance_source_counts, Mapping)
        else dict(distance_source_counts)
    )
    if route_observation_mode == "observed_voyage_corridors":
        if uses_mean_observed_distance:
            if int(
                scenario_distance_source_counts.get("haversine_fallback", 0)
                or 0
            ) > 0:
                distance_label = (
                    "observed maritime distance with zero mean onboard cargo"
                    if scenario_distance_method.endswith("_zero_mean_onboard_cargo")
                    else "mean-onboard-cargo-weighted observed maritime distance"
                )
                calculation_warnings.append(
                    f"{distance_label} includes subleg distances estimated by "
                    "coordinate haversine fallback"
                )
        elif not selected_corridor_sublegs:
            calculation_warnings.append(
                "selected observed voyage corridor has no subleg details; "
                "aggregate maritime intensity fallback was applied"
            )
        elif not selected_corridor_sublegs_complete:
            calculation_warnings.append(
                "selected observed voyage corridor has unresolved subleg distance or "
                "intensity; aggregate maritime intensity fallback was applied"
            )
        if not uses_mean_observed_distance and int(
            selected_corridor_distance_source_counts.get(
                "haversine_fallback", 0
            )
            or 0
        ) > 0:
            calculation_warnings.append(
                "selected observed voyage corridor includes subleg distances "
                "estimated by coordinate haversine fallback"
            )

    vessel_fuel_g_per_tnm = _positive_float_or_none(vessel_eff.fuel_g_per_tnm)
    corridor_distance_weighted_intensity = None
    if selected_corridor_sublegs_complete:
        corridor_distance_nm = sum(
            float(item["distance_nm"])
            for item in selected_corridor_sublegs
            if item.get("distance_nm") is not None
        )
        if corridor_distance_nm > 0.0:
            corridor_distance_weighted_intensity = sum(
                float(item["scenario_fuel_g_per_tnm"])
                * float(item["distance_nm"])
                for item in selected_corridor_sublegs
            ) / corridor_distance_nm

    fuel_g_per_tnm = (
        pair_intensity_g_per_tnm
        if pair_intensity_g_per_tnm is not None
        else (
            corridor_distance_weighted_intensity
            if corridor_distance_weighted_intensity is not None
            else (
                sea_leg_fuel_g_per_tnm
                if sea_leg_fuel_g_per_tnm is not None
                else vessel_fuel_g_per_tnm
            )
        )
    )
    if pair_intensity_g_per_tnm is not None:
        sea_fuel_g_per_tnm_source = (
            pair_intensity_source
            or _PAIR_WEIGHTED_MEAN_SOURCE
        )
    elif selected_corridor_sublegs_complete:
        sea_fuel_g_per_tnm_source = (
            str(sea_leg_data.get("fuel_g_per_tnm_source") or "").strip()
            or "observed_voyage_corridor_sublegs"
        )
    else:
        sea_fuel_g_per_tnm_source = (
            str(sea_leg_data.get("fuel_g_per_tnm_source") or "").strip()
            if sea_leg_fuel_g_per_tnm is not None
            else (
                "vessel_class_transport_work_intensity"
                if vessel_fuel_g_per_tnm is not None
                else ""
            )
        ) or None
    sailing_fuel_mode = (
        "sea_matrix_directional_transport_work_intensity"
        if sea_leg_fuel_g_per_tnm is not None
        else "transport_work_intensity"
    )
    hoteling_disabled_for_transport_work = bool(
        include_hoteling
        and hoteling_hours_total_requested > 0
        and isinstance(fuel_g_per_tnm, (int, float))
        and float(fuel_g_per_tnm) > 0.0
    )
    if (
        uses_mean_observed_distance
        and isinstance(fuel_g_per_tnm, (int, float))
        and fuel_g_per_tnm > 0
    ):
        sea_fuel_sailing_kg = (
            float(fuel_g_per_tnm) * cargo_t * sea_dist_nm
        ) / _KG_PER_TONNE
        if pair_intensity_method == _PAIR_ZERO_WORK_MEAN_METHOD:
            sailing_fuel_mode = (
                "same_od_unweighted_mean_with_observed_voyage_distance_"
                "zero_mean_onboard_cargo"
            )
        elif pair_intensity_method == _PAIR_WEIGHTED_MEAN_METHOD:
            sailing_fuel_mode = (
                "same_od_transport_work_weighted_mean_with_"
                "mean_onboard_cargo_weighted_observed_voyage_distance"
            )
        else:
            sailing_fuel_mode = (
                "same_od_representative_intensity_with_"
                "observed_voyage_distance"
            )
    elif selected_corridor_sublegs_complete:
        sea_fuel_sailing_kg = sum(
            float(item["scenario_fuel_kg"])
            for item in selected_corridor_sublegs
            if item.get("scenario_fuel_kg") is not None
        )
        if pair_intensity_g_per_tnm is None:
            sailing_fuel_mode = "observed_voyage_corridor_sublegs"
        elif pair_intensity_method == _PAIR_ZERO_WORK_MEAN_METHOD:
            sailing_fuel_mode = (
                "same_od_unweighted_mean_zero_transport_work_on_selected_corridor"
            )
        elif pair_intensity_method == _PAIR_WEIGHTED_MEAN_METHOD:
            sailing_fuel_mode = (
                "same_od_transport_work_weighted_mean_on_selected_corridor"
            )
        else:
            sailing_fuel_mode = "same_od_representative_intensity_on_selected_corridor"
    elif isinstance(fuel_g_per_tnm, (int, float)) and fuel_g_per_tnm > 0:
        # Preferred MRV metric: g fuel/(t*nm) allocated directly to cargo and distance.
        sea_fuel_sailing_kg = (float(fuel_g_per_tnm) * cargo_t * sea_dist_nm) / _KG_PER_TONNE
    else:
        # Fallback uses vessel-level kg/nm scaled by cargo share proxy.
        ship_fuel_kg = sea_dist_nm * vessel_eff.fuel_per_nm
        sea_fuel_sailing_kg = ship_fuel_kg * cargo_share
        sailing_fuel_mode = "vessel_fuel_share_fallback"

    observed_port_pair_legs = _build_observed_port_pair_legs(
        sea_leg_data,
        cargo_t=cargo_t,
    )

    _trace(
        "calculate_sea_sailing",
        "complete",
        str(sea_fuel_g_per_tnm_source or "vessel_class_efficiency_fallback"),
        distance_km=sea_dist_km,
        distance_nm=sea_dist_nm,
        distance_source=sea_leg_data.get("source"),
        cargo_t=cargo_t,
        cargo_allocation_mode=allocation_debug.get("allocation_mode_used"),
        cargo_allocation_share=cargo_share,
        fuel_g_per_tnm=fuel_g_per_tnm,
        calculation_mode=sailing_fuel_mode,
        fuel_kg=sea_fuel_sailing_kg,
        bunker_price_brl_mt=bunker_price_ton,
        bunker_price_source="santos_bunker_data_asset_with_default_fallback",
        marine_emission_factor_kg_co2e_per_kg=_BUNKER_EF_KG_CO2E_PER_KG,
        marine_emission_factor_source="tracked_fuel_emission_factors",
        observed_port_pair_leg_count=len(observed_port_pair_legs),
        selected_corridor_subleg_count=len(selected_corridor_sublegs),
        selected_corridor_sublegs_complete=selected_corridor_sublegs_complete,
        selected_corridor_id=sea_leg_data.get("selected_corridor_id"),
    )

    hoteling_exclusion_reason: str | None = None
    if hoteling_disabled_for_transport_work:
        hoteling_exclusion_reason = "included_in_transport_work_intensity"
        _log.info(
            "Skipping separate hoteling because MRV transport-work intensity is available for vessel class '%s'.",
            vessel_eff.vessel_class,
        )
    elif not cargo_mass_positive:
        hoteling_exclusion_reason = "zero_cargo_activity"
    elif not include_hoteling:
        hoteling_exclusion_reason = "disabled_by_user"
    elif hoteling_hours_total_requested <= 0.0:
        hoteling_exclusion_reason = "zero_activity"
    elif hoteling_sel is None:
        hoteling_exclusion_reason = "hoteling_rate_unavailable"

    hoteling_effective = bool(
        include_hoteling
        and hoteling_hours_total_requested > 0.0
        and not hoteling_disabled_for_transport_work
        and hoteling_sel is not None
        and cargo_mass_positive
    )
    hoteling_hours_total = hoteling_hours_total_requested if hoteling_effective else 0.0

    hoteling_rate_t_per_h = 0.0
    hoteling_ratio_used = 0.0
    hoteling_aux_main_ratio = 0.0
    hoteling_fuel_kg = 0.0
    hoteling_fuel_ship_kg = 0.0
    hoteling_source_path: str | None = None
    hoteling_source_level: str | None = None
    hoteling_basis: str | None = None
    hoteling_warning: str | None = None
    hoteling_vessel_class = vessel_eff.vessel_class
    if hoteling_exclusion_reason == "hoteling_rate_unavailable":
        hoteling_warning = (
            "Hoteling was requested but no defensible hoteling rate was available; "
            "the separate hoteling component was excluded from numeric totals."
        )

    if hoteling_effective and hoteling_hours_total > 0 and hoteling_sel is not None:
        hoteling_rate_t_per_h = float(hoteling_sel.fuel_rate_hoteling_t_per_h)
        hoteling_ratio_used = float(hoteling_sel.ratio_used)
        hoteling_aux_main_ratio = float(hoteling_sel.aux_main_ratio)
        hoteling_source_path = str(hoteling_sel.source_path)
        hoteling_vessel_class = hoteling_sel.vessel_class
        hoteling_source_level = getattr(hoteling_sel, "source_level", "literature_default")
        hoteling_basis = getattr(hoteling_sel, "basis", "vessel_class_hoteling_rate")
        hoteling_warning = getattr(hoteling_sel, "warning", None)
        if hoteling_vessel_class != vessel_eff.vessel_class:
            _log.warning(
                "Hoteling class fallback differs from sea efficiency class: sea=%s hoteling=%s",
                vessel_eff.vessel_class,
                hoteling_vessel_class,
            )
        hoteling_fuel_ship_kg = hoteling_hours_total * hoteling_rate_t_per_h * _KG_PER_TONNE
        hoteling_fuel_kg = hoteling_fuel_ship_kg * cargo_share

    _trace(
        "calculate_hoteling",
        "complete",
        hoteling_source_path or hoteling_exclusion_reason or "not_included",
        requested=include_hoteling,
        included=hoteling_effective,
        exclusion_reason=hoteling_exclusion_reason,
        source_level=hoteling_source_level,
        basis=hoteling_basis,
        hours_total=hoteling_hours_total,
        fuel_kg=hoteling_fuel_kg,
    )

    sea_fuel_marine_kg = sea_fuel_sailing_kg + hoteling_fuel_kg
    sea_cost_marine = (sea_fuel_marine_kg / _KG_PER_TONNE) * bunker_price_ton
    sea_co2e_marine = sea_fuel_marine_kg * _BUNKER_EF_KG_CO2E_PER_KG
    hoteling_cost_brl = (hoteling_fuel_kg / _KG_PER_TONNE) * bunker_price_ton
    hoteling_co2e_kg = hoteling_fuel_kg * _BUNKER_EF_KG_CO2E_PER_KG

    port_ops_payload: Dict[str, Any] | None = None
    port_ops_fuel_kg = 0.0
    port_ops_co2e_kg = 0.0
    port_ops_cost_brl = 0.0
    port_ops_exclusion_reason: str | None = None
    port_diesel_price_meta_per_call: list[dict[str, Any]] = []

    port_moves_per_call_effective = port_moves_per_call
    if (
        include_port_ops
        and port_calls > 0
        and not full_call_mode
        and port_moves_per_call is None
        and not cargo_mass_positive
        and not cargo_teu_positive
    ):
        port_moves_per_call_effective = 0.0

    if include_port_ops and port_calls > 0:
        try:
            port_call_names = _resolve_port_call_names(path_data, port_calls)
            port_diesel_metas_per_call: list[dict[str, Any]] = []
            for index in range(len(port_call_names)):
                if index == 0:
                    price_meta = diesel_price_metas["port_origin"]
                elif index == 1:
                    price_meta = diesel_price_metas["port_destiny"]
                else:
                    price_meta = _resolve_port_diesel_meta(
                        "",
                        price_scope=f"port_call_{index + 1}_missing_uf",
                    )
                port_diesel_metas_per_call.append(dict(price_meta))
            port_diesel_price_meta_per_call = port_diesel_metas_per_call

            port_ops_payload = estimate_port_ops(
                scenario=port_ops_scenario,
                port_calls=port_calls,
                port_moves_per_call=port_moves_per_call_effective,
                cargo_t=cargo_t,
                cargo_teu=cargo_teu,
                t_per_teu_default=t_per_teu_default,
                full_call_mode=full_call_mode,
                stat_key=port_ops_stat_key,
                diesel_prices_per_call=[
                    float(meta.get("price_r_per_l", diesel_default_price_r_per_l))
                    for meta in port_diesel_metas_per_call
                ],
                params_path=port_ops_params_path,
                selection=context.port_ops_selection,
                port_names=port_call_names,
                observed_port_ops=port_ops_observed_ports,
            )
            if isinstance(port_ops_payload, dict):
                port_ops_payload["diesel_price_meta_per_call"] = [
                    dict(meta) for meta in port_diesel_metas_per_call
                ]
                breakdown = port_ops_payload.get("port_call_breakdown")
                if isinstance(breakdown, list):
                    for index, port_call in enumerate(breakdown):
                        if isinstance(port_call, dict) and index < len(port_diesel_metas_per_call):
                            port_call["diesel_price_meta"] = dict(port_diesel_metas_per_call[index])
            totals = port_ops_payload.get("totals", {}) if isinstance(port_ops_payload, dict) else {}
            port_ops_fuel_kg = float(totals.get("fuel_kg") or 0.0)
            port_ops_co2e_kg = float(totals.get("co2e_kg") or 0.0)
            port_ops_cost_brl = float(totals.get("cost_brl") or 0.0)
        except Exception as exc:
            _log.error("Failed to resolve/evaluate port-ops artifact: %s", exc)
            _trace("calculate_port_ops", "failed", "port_ops_data_asset", error=str(exc))
            return {}
    elif not include_port_ops:
        port_ops_exclusion_reason = "disabled_by_user"
    elif port_calls <= 0:
        port_ops_exclusion_reason = "zero_activity"

    _trace(
        "calculate_port_ops",
        "complete",
        (
            str(port_ops_payload.get("source_path") or "port_ops_data_asset")
            if isinstance(port_ops_payload, dict)
            else (port_ops_exclusion_reason or "not_included")
        ),
        requested=include_port_ops,
        included=isinstance(port_ops_payload, dict),
        exclusion_reason=port_ops_exclusion_reason,
        scenario_requested=port_ops_scenario,
        scenario_resolved=(
            None if not isinstance(port_ops_payload, dict) else port_ops_payload.get("resolved_scenario")
        ),
        calculation_basis=(
            None if not isinstance(port_ops_payload, dict) else port_ops_payload.get("calculation_basis")
        ),
        source_level=(
            None if not isinstance(port_ops_payload, dict) else port_ops_payload.get("source_level")
        ),
        source_level_counts=(
            None if not isinstance(port_ops_payload, dict) else port_ops_payload.get("source_level_counts")
        ),
        observed_record_count=(
            0 if not isinstance(port_ops_payload, dict) else port_ops_payload.get("observed_port_ops_record_count")
        ),
        fuel_kg=port_ops_fuel_kg,
        cost_brl=port_ops_cost_brl,
        co2e_kg=port_ops_co2e_kg,
    )

    sea_fuel_total_kg = sea_fuel_marine_kg + port_ops_fuel_kg
    sea_cost_total = sea_cost_marine + port_ops_cost_brl
    sea_co2e_total = sea_co2e_marine + port_ops_co2e_kg
    port_ops_has_unavailable = (
        False if not isinstance(port_ops_payload, dict) else bool(port_ops_payload.get("has_unavailable_port_ops"))
    )
    port_ops_totals_complete = (
        None if not isinstance(port_ops_payload, dict) else bool(port_ops_payload.get("totals_complete"))
    )
    hoteling_status = "included" if hoteling_effective else (hoteling_exclusion_reason or "not_included")

    res_sea = {
        "distance_km": float(sea_dist_km),
        "distance_nm": float(sea_dist_nm),
        "distance_source": sea_leg_data.get("source"),
        "distance_provenance": sea_leg_data.get("distance_provenance"),
        "scenario_distance_method": scenario_distance_method,
        "scenario_distance_scope": sea_leg_data.get("scenario_distance_scope"),
        "scenario_distance_weight": sea_leg_data.get("scenario_distance_weight"),
        "scenario_distance_mean_onboard_cargo_t_total": _nonnegative_float_or_none(
            sea_leg_data.get("scenario_distance_mean_onboard_cargo_t_total")
        ),
        "scenario_distance_transport_work_tnm": _nonnegative_float_or_none(
            sea_leg_data.get("scenario_distance_transport_work_tnm")
        ),
        "scenario_distance_positive_weight_voyage_count": int(
            sea_leg_data.get("scenario_distance_positive_weight_voyage_count") or 0
        ),
        "scenario_distance_zero_weight_voyage_count": int(
            sea_leg_data.get("scenario_distance_zero_weight_voyage_count") or 0
        ),
        "scenario_distance_effective_voyage_count": int(
            sea_leg_data.get("scenario_distance_effective_voyage_count") or 0
        ),
        "scenario_distance_observation_count": int(
            sea_leg_data.get("scenario_distance_observation_count") or 0
        ),
        "scenario_distance_corridor_count": int(
            sea_leg_data.get("scenario_distance_corridor_count") or 0
        ),
        "scenario_distance_km": _positive_float_or_none(
            sea_leg_data.get("scenario_distance_km")
        ),
        "scenario_distance_nm": _positive_float_or_none(
            sea_leg_data.get("scenario_distance_nm")
        ),
        "scenario_distance_min_km": _positive_float_or_none(
            sea_leg_data.get("scenario_distance_min_km")
        ),
        "scenario_distance_max_km": _positive_float_or_none(
            sea_leg_data.get("scenario_distance_max_km")
        ),
        "scenario_distance_stddev_km": _nonnegative_float_or_none(
            sea_leg_data.get("scenario_distance_stddev_km")
        ),
        "scenario_distance_stddev_method": sea_leg_data.get(
            "scenario_distance_stddev_method"
        ),
        "scenario_distance_source_counts": scenario_distance_source_counts,
        "vessel_class": vessel_eff.vessel_class,
        "fuel_per_nm_kg": float(vessel_eff.fuel_per_nm),
        "fuel_g_per_tnm": (None if fuel_g_per_tnm is None else float(fuel_g_per_tnm)),
        "fuel_g_per_tnm_source": sea_fuel_g_per_tnm_source,
        "pair_intensity_g_per_tnm": pair_intensity_g_per_tnm,
        "pair_intensity_method": pair_intensity_method,
        "pair_intensity_scope": sea_leg_data.get("pair_intensity_scope"),
        "pair_intensity_weight": sea_leg_data.get("pair_intensity_weight"),
        "pair_intensity_source": pair_intensity_source,
        "pair_intensity_candidate_voyage_count": int(
            sea_leg_data.get("pair_intensity_candidate_voyage_count") or 0
        ),
        "pair_intensity_resolved_voyage_count": int(
            sea_leg_data.get("pair_intensity_resolved_voyage_count") or 0
        ),
        "pair_intensity_positive_weight_voyage_count": int(
            sea_leg_data.get("pair_intensity_positive_weight_voyage_count") or 0
        ),
        "pair_intensity_zero_weight_voyage_count": int(
            sea_leg_data.get("pair_intensity_zero_weight_voyage_count") or 0
        ),
        "pair_intensity_unresolved_voyage_count": int(
            sea_leg_data.get("pair_intensity_unresolved_voyage_count") or 0
        ),
        "pair_intensity_effective_voyage_count": int(
            sea_leg_data.get("pair_intensity_effective_voyage_count")
            or sea_leg_data.get("pair_intensity_positive_weight_voyage_count")
            or sea_leg_data.get("pair_intensity_resolved_voyage_count")
            or 0
        ),
        "pair_intensity_transport_work_tnm": _nonnegative_float_or_none(
            sea_leg_data.get("pair_intensity_transport_work_tnm")
        ),
        "pair_intensity_source_counts": pair_intensity_source_counts,
        "pair_intensity_effective_source_counts": (
            pair_intensity_effective_source_counts
        ),
        "selected_corridor_fuel_g_per_tnm_weighted_mean": (
            _positive_float_or_none(
                sea_leg_data.get(
                    "selected_corridor_fuel_g_per_tnm_weighted_mean"
                )
            )
        ),
        "selected_corridor_intensity_weighting": sea_leg_data.get(
            "selected_corridor_intensity_weighting"
        ),
        "route_fuel_g_per_tnm": (None if sea_leg_fuel_g_per_tnm is None else float(sea_leg_fuel_g_per_tnm)),
        "vessel_class_fuel_g_per_tnm": (None if vessel_fuel_g_per_tnm is None else float(vessel_fuel_g_per_tnm)),
        "route_match_rate_segments": _positive_float_or_none(sea_leg_data.get("match_rate_segments")),
        "route_match_rate_tonne_nm": _positive_float_or_none(sea_leg_data.get("match_rate_tonne_nm")),
        "route_segment_count": int(sea_leg_data.get("segment_count") or 0),
        "route_matched_segment_count": int(sea_leg_data.get("matched_segment_count") or 0),
        "route_voyage_count": int(sea_leg_data.get("voyage_count") or 0),
        "route_matched_voyage_count": int(sea_leg_data.get("matched_voyage_count") or 0),
        "route_unique_imo_count": int(sea_leg_data.get("unique_imo_count") or 0),
        "route_matched_imo_count": int(sea_leg_data.get("matched_imo_count") or 0),
        "route_corridor_leg_count": int(sea_leg_data.get("corridor_leg_count") or 0),
        "route_corridor_port_path": list(sea_leg_data.get("corridor_port_path") or []),
        "route_observation_mode": route_observation_mode or None,
        "corridor_count": int(sea_leg_data.get("corridor_count") or 0),
        "candidate_voyage_count": int(
            sea_leg_data.get("candidate_voyage_count") or 0
        ),
        "candidate_voyage_observation_count": int(
            sea_leg_data.get("candidate_voyage_observation_count") or 0
        ),
        "selected_corridor_candidate_voyage_count": int(
            sea_leg_data.get("selected_corridor_candidate_voyage_count") or 0
        ),
        "direct_voyage_count": int(sea_leg_data.get("direct_voyage_count") or 0),
        "multistop_voyage_count": int(
            sea_leg_data.get("multistop_voyage_count") or 0
        ),
        "selection_criterion": sea_leg_data.get("selection_criterion"),
        "selected_corridor_id": sea_leg_data.get("selected_corridor_id"),
        "resolved_voyage_count": int(
            sea_leg_data.get("resolved_voyage_count") or 0
        ),
        "imo_intensity_voyage_count": int(
            sea_leg_data.get("imo_intensity_voyage_count") or 0
        ),
        "class_fallback_voyage_count": int(
            sea_leg_data.get("class_fallback_voyage_count") or 0
        ),
        "type_fallback_voyage_count": int(
            sea_leg_data.get("type_fallback_voyage_count") or 0
        ),
        "fallback_voyage_count": int(
            sea_leg_data.get("fallback_voyage_count") or 0
        ),
        "unresolved_intensity_voyage_count": int(
            sea_leg_data.get("unresolved_intensity_voyage_count") or 0
        ),
        "intensity_source_counts": intensity_source_counts,
        "distance_source_counts": distance_source_counts,
        "selected_corridor_distance_source_counts": (
            selected_corridor_distance_source_counts
        ),
        "haversine_fallback_segment_count": int(
            sea_leg_data.get("haversine_fallback_segment_count") or 0
        ),
        "observed_transport_work_tnm": _nonnegative_float_or_none(
            sea_leg_data.get("observed_transport_work_tnm")
        ),
        "observed_fuel_kg": _nonnegative_float_or_none(
            sea_leg_data.get("observed_fuel_kg")
        ),
        "candidate_observed_transport_work_tnm": _nonnegative_float_or_none(
            sea_leg_data.get("candidate_observed_transport_work_tnm")
        ),
        "candidate_observed_fuel_kg": _nonnegative_float_or_none(
            sea_leg_data.get("candidate_observed_fuel_kg")
        ),
        "selected_corridor_sublegs": selected_corridor_sublegs,
        "selected_corridor_subleg_count": len(selected_corridor_sublegs),
        "selected_corridor_sublegs_complete": selected_corridor_sublegs_complete,
        "observed_port_pair_legs": observed_port_pair_legs,
        "size_proxy_t_median": (
            None if vessel_eff.size_proxy_t_median is None else float(vessel_eff.size_proxy_t_median)
        ),
        "teu_capacity": allocation_debug.get("teu_capacity"),
        "allocation_mode_used": allocation_debug.get("allocation_mode_used"),
        "load_factor": allocation_debug.get("load_factor"),
        "teu_loaded": allocation_debug.get("teu_loaded"),
        "cargo_teu_resolved": allocation_debug.get("cargo_teu_resolved"),
        "share_old_dwt": allocation_debug.get("share_old_dwt"),
        "share_new_teu": allocation_debug.get("share_new_teu"),
        "ratio_new_vs_old": allocation_debug.get("ratio_new_vs_old"),
        "eff_t_per_teu": allocation_debug.get("eff_t_per_teu"),
        "cargo_activity_status": cargo_activity_status,
        "cargo_activity_warnings": list(calculation_warnings),
        "cargo_allocation_suppressed_reason": allocation_debug.get("cargo_allocation_suppressed_reason"),
        "cargo_allocation_share": float(cargo_share),
        "sailing_fuel_calc_mode": sailing_fuel_mode,
        "fuel_kg_sailing": float(sea_fuel_sailing_kg),
        "hoteling_requested": bool(include_hoteling),
        "hoteling_included": bool(hoteling_effective),
        "hoteling_exclusion_reason": hoteling_exclusion_reason,
        "hoteling_hours_per_call": float(hoteling_hours_per_call),
        "port_calls": int(port_calls),
        "hoteling_hours_total": float(hoteling_hours_total),
        "hoteling_hours_total_requested": float(hoteling_hours_total_requested),
        "hoteling_rate_t_per_h": float(hoteling_rate_t_per_h),
        "hoteling_fuel_ship_kg": float(hoteling_fuel_ship_kg),
        "hoteling_fuel_kg": float(hoteling_fuel_kg),
        "hoteling_cost": float(hoteling_cost_brl),
        "hoteling_co2e": float(hoteling_co2e_kg),
        "hoteling_vessel_class": hoteling_vessel_class,
        "hoteling_ratio_used": float(hoteling_ratio_used),
        "hoteling_aux_main_ratio": float(hoteling_aux_main_ratio),
        "hoteling_source_level": hoteling_source_level,
        "hoteling_basis": hoteling_basis,
        "hoteling_warning": hoteling_warning,
        "hoteling_status": hoteling_status,
        "fuel_kg_marine": float(sea_fuel_marine_kg),
        "cost_marine": float(sea_cost_marine),
        "co2e_marine": float(sea_co2e_marine),
        "port_ops_requested": bool(include_port_ops),
        "port_ops_included": bool(include_port_ops and port_calls > 0 and isinstance(port_ops_payload, dict)),
        "port_ops_exclusion_reason": port_ops_exclusion_reason,
        "port_ops_scenario_requested": str(port_ops_scenario),
        "port_ops_stat_key": str(port_ops_stat_key),
        "cargo_teu_requested": (None if cargo_teu is None else float(max(float(cargo_teu), 0.0))),
        "t_per_teu_default": float(t_per_teu_default),
        "full_call_mode": bool(full_call_mode),
        "port_moves_per_call_requested": (
            None if port_moves_per_call is None else float(max(float(port_moves_per_call), 0.0))
        ),
        "port_moves_per_call_effective": (
            None
            if port_moves_per_call_effective is None
            else float(max(float(port_moves_per_call_effective), 0.0))
        ),
        "port_ops_fuel_kg": float(port_ops_fuel_kg),
        "port_ops_cost": float(port_ops_cost_brl),
        "port_ops_co2e": float(port_ops_co2e_kg),
        "port_ops_source_level": (
            None if not isinstance(port_ops_payload, dict) else port_ops_payload.get("source_level")
        ),
        "port_ops_source_level_counts": (
            {} if not isinstance(port_ops_payload, dict) else dict(port_ops_payload.get("source_level_counts") or {})
        ),
        "port_ops_has_unavailable": port_ops_has_unavailable,
        "port_ops_totals_complete": port_ops_totals_complete,
        "port_ops_warnings": (
            [] if not isinstance(port_ops_payload, dict) else list(port_ops_payload.get("warnings") or [])
        ),
        "port_diesel_price_meta_per_call": [
            dict(meta) for meta in port_diesel_price_meta_per_call
        ],
        "port_ops": port_ops_payload,
        "fuel_kg": float(sea_fuel_total_kg),
        "cost": float(sea_cost_total),
        "co2e": float(sea_co2e_total),
    }

    mm_cost = res_first["cost"] + res_last["cost"] + res_sea["cost"]
    mm_co2e = res_first["co2e"] + res_last["co2e"] + res_sea["co2e"]

    road_cost = float(res_direct["cost"])
    road_co2e = float(res_direct["co2e"])

    _trace(
        "evaluation",
        "complete",
        "calculated_single_eval_outputs",
        road_cost_brl=road_cost,
        road_co2e_kg=road_co2e,
        multimodal_cost_brl=mm_cost,
        multimodal_co2e_kg=mm_co2e,
        delta_cost_brl=mm_cost - road_cost,
        delta_co2e_kg=mm_co2e - road_co2e,
        calculation_warning_count=len(calculation_warnings),
        route_quality_warning_count=len(route_quality_warnings),
    )

    return {
        "inputs": {
            "cargo_t": cargo_t,
            "truck": truck_key,
            "road_vehicle": {
                "selection_mode": (
                    AUTO_BY_WEIGHT_TRUCK_KEY
                    if str(truck_key).strip() == AUTO_BY_WEIGHT_TRUCK_KEY
                    else "explicit_preset"
                ),
                "label": str(truck_spec.get("label") or ""),
                "axles": int(truck_spec.get("axles") or 0),
                "payload_t": float(truck_spec.get("payload_t") or 0.0),
                "resolved_key": str(
                    truck_spec.get("resolved_key") or str(truck_key)
                ),
            },
            "diesel_price": price_l,
            "diesel_price_source": diesel_source,
            "diesel_price_meta": diesel_meta,
            "diesel_prices_by_leg": {
                name: dict(meta) for name, meta in diesel_price_metas.items()
            },
            "bunker_price": bunker_price_ton,
            "marine_fuel_type": _MARINE_FUEL_TYPE,
            "marine_ef_kg_per_kg": _BUNKER_EF_KG_CO2E_PER_KG,
            "uf_origin": origin_uf or None,
            "uf_destiny": destiny_uf or None,
            "uf_port_origin": port_origin_uf or None,
            "uf_port_destiny": port_destiny_uf or None,
            "vessel_class_requested": vessel_eff.requested_class,
            "vessel_class": vessel_eff.vessel_class,
            "sea_fuel_per_nm_kg": float(vessel_eff.fuel_per_nm),
            "sea_fuel_g_per_tnm": (None if fuel_g_per_tnm is None else float(fuel_g_per_tnm)),
            "sea_fuel_g_per_tnm_source": sea_fuel_g_per_tnm_source,
            "sea_scenario_distance_method": scenario_distance_method,
            "sea_scenario_distance_scope": sea_leg_data.get(
                "scenario_distance_scope"
            ),
            "sea_scenario_distance_weight": sea_leg_data.get(
                "scenario_distance_weight"
            ),
            "sea_scenario_distance_mean_onboard_cargo_t_total": (
                _nonnegative_float_or_none(
                    sea_leg_data.get(
                        "scenario_distance_mean_onboard_cargo_t_total"
                    )
                )
            ),
            "sea_scenario_distance_transport_work_tnm": _nonnegative_float_or_none(
                sea_leg_data.get("scenario_distance_transport_work_tnm")
            ),
            "sea_scenario_distance_stddev_method": sea_leg_data.get(
                "scenario_distance_stddev_method"
            ),
            "sea_scenario_distance_observation_count": int(
                sea_leg_data.get("scenario_distance_observation_count") or 0
            ),
            "sea_scenario_distance_corridor_count": int(
                sea_leg_data.get("scenario_distance_corridor_count") or 0
            ),
            "sea_scenario_distance_km": _positive_float_or_none(
                sea_leg_data.get("scenario_distance_km")
            ),
            "sea_scenario_distance_nm": _positive_float_or_none(
                sea_leg_data.get("scenario_distance_nm")
            ),
            "sea_scenario_distance_min_km": _positive_float_or_none(
                sea_leg_data.get("scenario_distance_min_km")
            ),
            "sea_scenario_distance_max_km": _positive_float_or_none(
                sea_leg_data.get("scenario_distance_max_km")
            ),
            "sea_scenario_distance_stddev_km": _nonnegative_float_or_none(
                sea_leg_data.get("scenario_distance_stddev_km")
            ),
            "sea_scenario_distance_source_counts": scenario_distance_source_counts,
            "sea_pair_intensity_g_per_tnm": pair_intensity_g_per_tnm,
            "sea_pair_intensity_method": pair_intensity_method,
            "sea_pair_intensity_scope": sea_leg_data.get(
                "pair_intensity_scope"
            ),
            "sea_pair_intensity_weight": sea_leg_data.get(
                "pair_intensity_weight"
            ),
            "sea_pair_intensity_source": pair_intensity_source,
            "sea_pair_intensity_candidate_voyage_count": int(
                sea_leg_data.get("pair_intensity_candidate_voyage_count") or 0
            ),
            "sea_pair_intensity_resolved_voyage_count": int(
                sea_leg_data.get("pair_intensity_resolved_voyage_count") or 0
            ),
            "sea_pair_intensity_positive_weight_voyage_count": int(
                sea_leg_data.get("pair_intensity_positive_weight_voyage_count")
                or 0
            ),
            "sea_pair_intensity_zero_weight_voyage_count": int(
                sea_leg_data.get("pair_intensity_zero_weight_voyage_count") or 0
            ),
            "sea_pair_intensity_unresolved_voyage_count": int(
                sea_leg_data.get("pair_intensity_unresolved_voyage_count") or 0
            ),
            "sea_pair_intensity_effective_voyage_count": int(
                sea_leg_data.get("pair_intensity_effective_voyage_count")
                or sea_leg_data.get("pair_intensity_positive_weight_voyage_count")
                or sea_leg_data.get("pair_intensity_resolved_voyage_count")
                or 0
            ),
            "sea_pair_intensity_transport_work_tnm": _nonnegative_float_or_none(
                sea_leg_data.get("pair_intensity_transport_work_tnm")
            ),
            "sea_pair_intensity_source_counts": pair_intensity_source_counts,
            "sea_pair_intensity_effective_source_counts": (
                pair_intensity_effective_source_counts
            ),
            "sea_selected_corridor_fuel_g_per_tnm_weighted_mean": (
                _positive_float_or_none(
                    sea_leg_data.get(
                        "selected_corridor_fuel_g_per_tnm_weighted_mean"
                    )
                )
            ),
            "sea_selected_corridor_intensity_weighting": sea_leg_data.get(
                "selected_corridor_intensity_weighting"
            ),
            "sea_route_fuel_g_per_tnm": (
                None if sea_leg_fuel_g_per_tnm is None else float(sea_leg_fuel_g_per_tnm)
            ),
            "sea_vessel_class_fuel_g_per_tnm": (
                None if vessel_fuel_g_per_tnm is None else float(vessel_fuel_g_per_tnm)
            ),
            "sea_route_match_rate_segments": _positive_float_or_none(sea_leg_data.get("match_rate_segments")),
            "sea_route_match_rate_tonne_nm": _positive_float_or_none(sea_leg_data.get("match_rate_tonne_nm")),
            "sea_route_segment_count": int(sea_leg_data.get("segment_count") or 0),
            "sea_route_matched_segment_count": int(sea_leg_data.get("matched_segment_count") or 0),
            "sea_route_voyage_count": int(sea_leg_data.get("voyage_count") or 0),
            "sea_route_matched_voyage_count": int(sea_leg_data.get("matched_voyage_count") or 0),
            "sea_route_unique_imo_count": int(sea_leg_data.get("unique_imo_count") or 0),
            "sea_route_matched_imo_count": int(sea_leg_data.get("matched_imo_count") or 0),
            "sea_route_corridor_leg_count": int(sea_leg_data.get("corridor_leg_count") or 0),
            "sea_route_corridor_port_path": list(sea_leg_data.get("corridor_port_path") or []),
            "sea_route_observation_mode": route_observation_mode or None,
            "sea_route_corridor_count": int(
                sea_leg_data.get("corridor_count") or 0
            ),
            "sea_route_candidate_voyage_count": int(
                sea_leg_data.get("candidate_voyage_count") or 0
            ),
            "sea_route_candidate_voyage_observation_count": int(
                sea_leg_data.get("candidate_voyage_observation_count") or 0
            ),
            "sea_route_selected_corridor_candidate_voyage_count": int(
                sea_leg_data.get("selected_corridor_candidate_voyage_count") or 0
            ),
            "sea_route_direct_voyage_count": int(
                sea_leg_data.get("direct_voyage_count") or 0
            ),
            "sea_route_multistop_voyage_count": int(
                sea_leg_data.get("multistop_voyage_count") or 0
            ),
            "sea_route_selection_criterion": sea_leg_data.get(
                "selection_criterion"
            ),
            "sea_route_selected_corridor_id": sea_leg_data.get(
                "selected_corridor_id"
            ),
            "sea_route_resolved_voyage_count": int(
                sea_leg_data.get("resolved_voyage_count") or 0
            ),
            "sea_route_imo_intensity_voyage_count": int(
                sea_leg_data.get("imo_intensity_voyage_count") or 0
            ),
            "sea_route_class_fallback_voyage_count": int(
                sea_leg_data.get("class_fallback_voyage_count") or 0
            ),
            "sea_route_type_fallback_voyage_count": int(
                sea_leg_data.get("type_fallback_voyage_count") or 0
            ),
            "sea_route_fallback_voyage_count": int(
                sea_leg_data.get("fallback_voyage_count") or 0
            ),
            "sea_route_unresolved_intensity_voyage_count": int(
                sea_leg_data.get("unresolved_intensity_voyage_count") or 0
            ),
            "sea_route_intensity_source_counts": intensity_source_counts,
            "sea_route_distance_source_counts": distance_source_counts,
            "sea_route_selected_corridor_distance_source_counts": (
                selected_corridor_distance_source_counts
            ),
            "sea_route_haversine_fallback_segment_count": int(
                sea_leg_data.get("haversine_fallback_segment_count") or 0
            ),
            "sea_route_observed_transport_work_tnm": _nonnegative_float_or_none(
                sea_leg_data.get("observed_transport_work_tnm")
            ),
            "sea_route_observed_fuel_kg": _nonnegative_float_or_none(
                sea_leg_data.get("observed_fuel_kg")
            ),
            "sea_route_candidate_observed_transport_work_tnm": (
                _nonnegative_float_or_none(
                    sea_leg_data.get("candidate_observed_transport_work_tnm")
                )
            ),
            "sea_route_candidate_observed_fuel_kg": _nonnegative_float_or_none(
                sea_leg_data.get("candidate_observed_fuel_kg")
            ),
            "sea_route_selected_corridor_sublegs": selected_corridor_sublegs,
            "sea_route_selected_corridor_subleg_count": len(
                selected_corridor_sublegs
            ),
            "sea_route_selected_corridor_sublegs_complete": (
                selected_corridor_sublegs_complete
            ),
            "size_proxy_t_median": (
                None if vessel_eff.size_proxy_t_median is None else float(vessel_eff.size_proxy_t_median)
            ),
            "teu_capacity": allocation_debug.get("teu_capacity"),
            "allocation_mode_requested": allocation_debug.get("allocation_mode_requested"),
            "allocation_mode_used": allocation_debug.get("allocation_mode_used"),
            "allocation_load_factor": allocation_debug.get("load_factor"),
            "teu_loaded": allocation_debug.get("teu_loaded"),
            "share_old_dwt": allocation_debug.get("share_old_dwt"),
            "share_new_teu": allocation_debug.get("share_new_teu"),
            "ratio_new_vs_old": allocation_debug.get("ratio_new_vs_old"),
            "eff_t_per_teu": allocation_debug.get("eff_t_per_teu"),
            "cargo_activity_status": cargo_activity_status,
            "cargo_activity_warnings": list(calculation_warnings),
            "cargo_allocation_suppressed_reason": allocation_debug.get("cargo_allocation_suppressed_reason"),
            "cargo_allocation_share": float(cargo_share),
            "sailing_fuel_calc_mode": sailing_fuel_mode,
            "vessel_sample_size": int(vessel_eff.sample_size),
            "vessel_efficiency_source": str(vessel_eff.source_path),
            "include_hoteling": bool(hoteling_effective),
            "hoteling_requested": bool(include_hoteling),
            "hoteling_included": bool(hoteling_effective),
            "hoteling_exclusion_reason": hoteling_exclusion_reason,
            "hoteling_status": hoteling_status,
            "hoteling_hours_per_call": float(hoteling_hours_per_call),
            "port_calls": int(port_calls),
            "hoteling_hours_total": float(hoteling_hours_total),
            "hoteling_hours_total_requested": float(hoteling_hours_total_requested),
            "hoteling_rate_t_per_h": float(hoteling_rate_t_per_h),
            "hoteling_fuel_kg": float(hoteling_fuel_kg),
            "hoteling_co2e": float(hoteling_co2e_kg),
            "hoteling_vessel_class": hoteling_vessel_class,
            "hoteling_ratio_used": float(hoteling_ratio_used),
            "hoteling_aux_main_ratio": float(hoteling_aux_main_ratio),
            "hoteling_source": hoteling_source_path,
            "hoteling_source_level": hoteling_source_level,
            "hoteling_basis": hoteling_basis,
            "hoteling_warning": hoteling_warning,
            "include_port_ops": bool(include_port_ops),
            "port_ops_requested": bool(include_port_ops),
            "port_ops_included": bool(include_port_ops and port_calls > 0 and isinstance(port_ops_payload, dict)),
            "port_ops_exclusion_reason": port_ops_exclusion_reason,
            "port_ops_scenario_requested": str(port_ops_scenario),
            "port_ops_stat_key": str(port_ops_stat_key),
            "cargo_teu_requested": (None if cargo_teu is None else float(max(float(cargo_teu), 0.0))),
            "t_per_teu_default": float(t_per_teu_default),
            "full_call_mode": bool(full_call_mode),
            "port_moves_per_call_requested": (
                None if port_moves_per_call is None else float(max(float(port_moves_per_call), 0.0))
            ),
            "port_moves_per_call_effective": (
                None
                if port_moves_per_call_effective is None
                else float(max(float(port_moves_per_call_effective), 0.0))
            ),
            "port_ops_source": (
                None
                if not isinstance(port_ops_payload, dict)
                else str(port_ops_payload.get("source_path") or "")
            ),
            "port_ops_scenario_resolved": (
                None
                if not isinstance(port_ops_payload, dict)
                else str(port_ops_payload.get("resolved_scenario") or "")
            ),
            "port_moves_per_call_resolved": (
                None
                if not isinstance(port_ops_payload, dict)
                else float(port_ops_payload.get("port_moves_per_call") or 0.0)
            ),
            "cargo_teu_resolved": int(allocation_debug.get("cargo_teu_resolved") or 0),
            "cargo_teu_resolved_port_ops": (
                None
                if not isinstance(port_ops_payload, dict)
                else int(port_ops_payload.get("cargo_teu_resolved") or 0)
            ),
            "port_ops_source_level": (
                None if not isinstance(port_ops_payload, dict) else port_ops_payload.get("source_level")
            ),
            "port_ops_source_level_counts": (
                {}
                if not isinstance(port_ops_payload, dict)
                else dict(port_ops_payload.get("source_level_counts") or {})
            ),
            "port_ops_has_unavailable": port_ops_has_unavailable,
            "port_ops_totals_complete": port_ops_totals_complete,
            "port_ops_warning_count": (
                0 if not isinstance(port_ops_payload, dict) else len(port_ops_payload.get("warnings") or [])
            ),
            "route_quality_warning_count": len(route_quality_warnings),
            "calculation_warning_count": len(calculation_warnings),
        },
        "calculation_warnings": calculation_warnings,
        "route_quality_warnings": route_quality_warnings,
        "road_only": res_direct,
        "multimodal": {
            "first_mile": res_first,
            "sea": res_sea,
            "last_mile": res_last,
            "total_cost": float(mm_cost),
            "total_co2e": float(mm_co2e),
        },
        "comparison": {
            "delta_cost": float(mm_cost - road_cost),
            "delta_co2e": float(mm_co2e - road_co2e),
            "savings_pct": float((1 - (mm_cost / road_cost)) * 100) if road_cost > 0 else 0.0,
        },
    }


if __name__ == "__main__":
    import json

    from modules.infra.log_manager import init_logging

    init_logging(level="DEBUG")
    print("--- Evaluator Smoke Test ---")

    geo_dummy = {
        "status": "ok",
        "origin": {"uf": "SP"},
        "destiny": {"uf": "AM"},
        "road_direct": {"distance_km": 4000.0},
        "first_mile": {"distance_km": 100.0},
        "last_mile": {"distance_km": 50.0},
        "sea_leg": {"distance_km": 3500.0},
    }

    res = evaluate_path(geo_dummy, cargo_t=27.0)
    print(json.dumps(res, indent=2))
    print("--- Done ---")
