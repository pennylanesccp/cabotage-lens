from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.infra.database_manager import (
    db_session,
    find_place_point,
    finish_bulk_run,
    list_bulk_result_points_by_input_keys,
    list_bulk_results,
    list_cached_place_points,
    start_bulk_run,
    upsert_place_points,
    upsert_runs,
)
from modules.infra.db.bulk_runs import selector_hash
from modules.infra.log_manager import get_log_context, get_logger, set_log_context
from modules.multimodal.builder import build_path_geometry_from_resolved, build_port_node, load_routing_assets
from modules.multimodal.bulk import (
    BulkPerformanceTracker,
    BulkPersistenceBuffer,
    DestinationWorkItem,
    build_failure_diagnostic,
    NearestPortMemo,
    PendingApproximation,
    RouteRequestCoordinator,
    RouteRequestSpec,
    _build_approximated_geometry,
    _build_bulk_outcome_rows,
    _build_failure_summary_row,
    _build_run_selector,
    _build_scenario_payload,
    _build_success_summary_row,
    _classify_failure,
    _dedupe_preserve_order,
    _emit_progress,
    _estimate_road_distance_from_reference,
    _evaluate_and_flatten,
    _make_exact_reference,
    _point_from_cached_record,
    _point_from_result_record,
    _require_distance,
    _route_source_for_result,
    _select_nearest_exact_reference,
    _shuffle_destinations,
    _resolve_point_without_db,
)
from modules.multimodal.evaluator import prepare_evaluation_context
from modules.multimodal.scenario_keys import normalize_bulk_place_input
from modules.multimodal.scenario_keys import build_bulk_scenario_key

_log = get_logger(__name__)

_STEP_LABELS: dict[str, str] = {
    "bootstrap": "bootstrap",
    "origin_alias_cache": "origin alias cache lookup",
    "origin_geocoding": "origin geocoding",
    "nearest_port_origin": "nearest port origin",
    "routing_origin_to_port_origin": "routing origin to port origin",
    "destination_alias_cache": "destination alias cache lookup",
    "destination_geocoding": "destination geocoding",
    "nearest_port_destiny": "nearest port destiny",
    "routing_road_only": "routing road only",
    "routing_port_destiny_to_destiny": "routing port destiny to destiny",
    "build_multimodal_route": "build multimodal route",
    "geometry_acquisition": "geometry acquisition",
    "calculating_costs_emissions": "calculating costs and emissions",
    "approximation_fallback": "approximation fallback",
    "persist_results": "database persistence",
    "start_bulk_run": "bulk run registration",
    "finish_bulk_run": "bulk run completion",
}
_LEG_FAILURE_STEPS: dict[str, str] = {
    "road_direct": "routing_road_only",
    "first_mile": "routing_origin_to_port_origin",
    "last_mile": "routing_port_destiny_to_destiny",
}


class _BulkStepError(RuntimeError):
    def __init__(
        self,
        *,
        step: str,
        system: str,
        error: Exception,
        provider: Optional[str] = None,
    ) -> None:
        message = str(error).strip() or error.__class__.__name__
        super().__init__(message)
        self.step = str(step).strip() or "bootstrap"
        self.system = str(system).strip() or "application"
        self.provider = (None if provider in (None, "") else str(provider).strip())
        self.original = error


def _step_label(step: Optional[str]) -> str:
    key = str(step or "").strip()
    if not key:
        return "unknown"
    return _STEP_LABELS.get(key, key.replace("_", " "))


def _format_log_fields(**fields: Any) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        if value in (None, ""):
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


def _log_step_banner(step: str, **fields: Any) -> None:
    details = _format_log_fields(**fields)
    if details:
        _log.info("=== BULK STEP %s (%s) %s ===", step, _step_label(step), details)
        return
    _log.info("=== BULK STEP %s (%s) ===", step, _step_label(step))


def _failure_step(exc: Exception, *, default: str) -> str:
    return str(getattr(exc, "step", None) or default).strip() or default


def _failure_system(exc: Exception, *, default: str) -> str:
    return str(getattr(exc, "system", None) or default).strip() or default


def _failure_provider(exc: Exception) -> Optional[str]:
    provider = getattr(exc, "provider", None)
    if provider not in (None, ""):
        return str(provider).strip()
    provider_name = getattr(exc, "provider_name", None)
    if provider_name not in (None, ""):
        return str(provider_name).strip()
    provider_names = getattr(exc, "provider_names", None)
    if isinstance(provider_names, (list, tuple)):
        names = [str(name).strip() for name in provider_names if str(name).strip()]
        if names:
            return ",".join(names)
    return None


def _route_provider_for_step(geo: Optional[Dict[str, Any]], step: Optional[str]) -> Optional[str]:
    if not isinstance(geo, dict):
        return None
    leg_name = {
        "routing_origin_to_port_origin": "first_mile",
        "routing_road_only": "road_direct",
        "routing_port_destiny_to_destiny": "last_mile",
    }.get(str(step or "").strip())
    if leg_name is None:
        return None
    leg = geo.get(leg_name)
    if not isinstance(leg, dict):
        return None
    provider = leg.get("provider") or leg.get("source")
    return None if provider in (None, "") else str(provider).strip()


def _assign_destination_failure(
    item: DestinationWorkItem,
    *,
    status: str,
    error_message: str,
    step: str,
    system: str,
    provider: Optional[str] = None,
    provider_operation: Optional[str] = None,
) -> None:
    diagnostic = build_failure_diagnostic(
        status=status,
        step=step,
        failure_detail=error_message,
        system=system,
        provider=provider,
        provider_operation=provider_operation,
        raw_input=item.destiny_input,
    )
    item.failure_status = status
    item.error_message = error_message
    item.failure_step = diagnostic.failed_step
    item.failure_system = system
    item.failure_provider = diagnostic.provider
    item.failed_leg = diagnostic.failed_leg
    item.failure_reason = diagnostic.failure_reason
    item.failure_detail = diagnostic.failure_detail
    item.retryable = diagnostic.retryable
    item.failure_provider_operation = diagnostic.provider_operation


def _format_point_coords(point: Optional[Dict[str, Any]]) -> str:
    if not isinstance(point, dict):
        return "<none>"
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is None or lon is None:
        return "<none>"
    return f"{float(lat):.5f},{float(lon):.5f}"


def _format_port_name(port: Optional[Dict[str, Any]]) -> str:
    if not isinstance(port, dict):
        return "<none>"
    return str(port.get("name") or port.get("label") or "<none>")


def _format_leg_debug(geo: Optional[Dict[str, Any]], leg_name: str) -> str:
    if not isinstance(geo, dict):
        return f"{leg_name}[source=<none> km=<none> profile=<none> cached=?]"
    leg = geo.get(leg_name)
    if not isinstance(leg, dict):
        return f"{leg_name}[source=<none> km=<none> profile=<none> cached=?]"
    distance_km = leg.get("distance_km")
    if distance_km is None:
        distance_text = "<none>"
    else:
        distance_text = f"{float(distance_km):.1f}"
    cached = leg.get("cached")
    if cached is None:
        cached_text = "?"
    else:
        cached_text = str(bool(cached)).lower()
    return (
        f"{leg_name}[source={leg.get('source') or '<none>'} km={distance_text} "
        f"profile={leg.get('profile_used') or '<none>'} cached={cached_text}]"
    )


def _log_destination_failure_context(
    *,
    phase: str,
    origin_pt: Dict[str, Any],
    origin_port: Optional[Dict[str, Any]],
    item: DestinationWorkItem,
    status: str,
    error_message: str,
    geo: Optional[Dict[str, Any]] = None,
) -> None:
    destiny_point = item.point if isinstance(item.point, dict) else None
    _log.warning(
        (
            "Bulk destination failure phase=%s step=%s step_label=%s leg=%s reason=%s retryable=%s "
            "system=%s provider=%s provider_operation=%s route=%s@%s -> %s@%s "
            "input_destiny=%s status=%s point_source=%s ports=%s -> %s %s %s error=%s"
        ),
        phase,
        item.failure_step or "<unknown>",
        _step_label(item.failure_step),
        item.failed_leg or "<unknown>",
        item.failure_reason or "<unknown>",
        item.retryable,
        item.failure_system or "<unknown>",
        item.failure_provider or "<unknown>",
        item.failure_provider_operation or "<unknown>",
        origin_pt.get("label") or "<origin>",
        _format_point_coords(origin_pt),
        item.destiny_name or item.destiny_input,
        _format_point_coords(destiny_point),
        item.destiny_input,
        status,
        item.point_source or "<none>",
        _format_port_name(origin_port),
        _format_port_name(item.port_destiny),
        _format_leg_debug(geo, "road_direct"),
        _format_leg_debug(geo, "last_mile"),
        item.failure_detail or error_message,
    )


def _provider_operation_totals(provider_calls: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, float]:
    totals: dict[str, float] = {
        "geocode_attempts": 0.0,
        "route_attempts": 0.0,
        "rate_limited": 0.0,
        "timeout": 0.0,
        "network_error": 0.0,
        "cooldown_skips": 0.0,
    }
    for operations in provider_calls.values():
        for operation_name, metrics in operations.items():
            attempts = float(metrics.get("attempts", 0.0) or 0.0)
            if operation_name in {"geocode_text", "geocode_structured"}:
                totals["geocode_attempts"] += attempts
            elif operation_name == "route_road":
                totals["route_attempts"] += attempts
            totals["rate_limited"] += float(metrics.get("rate_limited", 0.0) or 0.0)
            totals["timeout"] += float(metrics.get("timeout", 0.0) or 0.0)
            totals["network_error"] += float(metrics.get("network_error", 0.0) or 0.0)
            totals["cooldown_skips"] += float(metrics.get("skipped_cooldown", 0.0) or 0.0)
    return totals


def _format_provider_summary(provider_calls: Dict[str, Dict[str, Dict[str, float]]]) -> str:
    segments: list[str] = []
    for provider_name, operations in sorted(provider_calls.items()):
        operation_segments: list[str] = []
        for operation_name, metrics in sorted(operations.items()):
            attempts = int(metrics.get("attempts", 0.0) or 0.0)
            successes = int(metrics.get("successes", 0.0) or 0.0)
            failures = int(metrics.get("failures", 0.0) or 0.0)
            rate_limited = int(metrics.get("rate_limited", 0.0) or 0.0)
            timeout = int(metrics.get("timeout", 0.0) or 0.0)
            network_error = int(metrics.get("network_error", 0.0) or 0.0)
            cooldown_skips = int(metrics.get("skipped_cooldown", 0.0) or 0.0)
            operation_segments.append(
                (
                    f"{operation_name}:attempts={attempts},ok={successes},fail={failures},"
                    f"rate_limited={rate_limited},timeout={timeout},network={network_error},cooldown={cooldown_skips}"
                )
            )
        if operation_segments:
            segments.append(f"{provider_name}[{' | '.join(operation_segments)}]")
    return "; ".join(segments) if segments else "none"


def _status_counts(summary_rows: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: dict[str, int] = {}
    for row in summary_rows:
        status = str(row.get("status") or "").strip().lower() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _failure_counts(summary_rows: List[Dict[str, Any]], *, field_name: str) -> Dict[str, int]:
    counts: dict[str, int] = {}
    for row in summary_rows:
        status = str(row.get("status") or "").strip().lower() or "unknown"
        if status == "ok":
            continue
        key = str(row.get(field_name) or "").strip() or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _top_failed_destinations(summary_rows: List[Dict[str, Any]], *, limit: int = 10) -> List[Dict[str, Any]]:
    failures: list[Dict[str, Any]] = []
    for row in summary_rows:
        status = str(row.get("status") or "").strip().lower() or "unknown"
        if status == "ok":
            continue
        failures.append(
            {
                "destination": str(
                    row.get("destination_label")
                    or row.get("destiny_name")
                    or row.get("destiny_input")
                    or "<unknown>"
                ).strip()
                or "<unknown>",
                "port_origin": str(row.get("port_origin_name") or "").strip() or None,
                "port_destiny": str(row.get("port_destiny_name") or "").strip() or None,
                "failed_step": str(row.get("failed_step") or row.get("failure_step") or "").strip() or None,
                "failed_leg": str(row.get("failed_leg") or "").strip() or None,
                "failure_reason": str(row.get("failure_reason") or "").strip() or None,
            }
        )
    return failures[:limit]


def _format_counter_summary(counts: Dict[str, int], *, max_items: int = 8) -> str:
    if not counts:
        return "none"
    return ", ".join(
        f"{key}={count}"
        for key, count in list(counts.items())[:max_items]
    )


def _format_top_failed_destinations(rows: List[Dict[str, Any]], *, max_items: int = 5) -> str:
    if not rows:
        return "none"
    segments: list[str] = []
    for row in rows[:max_items]:
        segments.append(
            (
                f"{row.get('destination') or '<unknown>'} "
                f"ports={row.get('port_origin') or '<none>'}->{row.get('port_destiny') or '<none>'} "
                f"step={row.get('failed_step') or '<none>'} "
                f"leg={row.get('failed_leg') or '<none>'} "
                f"reason={row.get('failure_reason') or '<none>'}"
            )
        )
    return "; ".join(segments)


def _finalize_bulk_outcome(
    *,
    ors: Any,
    perf: BulkPerformanceTracker,
    summary_rows: List[Dict[str, Any]],
    success_count: int,
    fail_count: int,
    exact_success_count: int,
    approximated_success_count: int,
    unresolved_fail_count: int,
    duration: float,
    run_id: Optional[str],
    selector_hash_value: Optional[str],
    shuffle_seed_used: Optional[int],
    requested_destination_count: int,
    unique_destination_count: int,
    max_geocode_workers: int,
    max_route_workers: int,
) -> Dict[str, Any]:
    provider_calls = ors.metrics_snapshot() if hasattr(ors, "metrics_snapshot") else {}
    provider_totals = _provider_operation_totals(provider_calls)
    performance = perf.snapshot()
    performance["provider_calls"] = provider_calls
    status_counts = _status_counts(summary_rows)
    failure_counts_by_step = _failure_counts(summary_rows, field_name="failed_step")
    failure_counts_by_leg = _failure_counts(summary_rows, field_name="failed_leg")
    failure_counts_by_reason = _failure_counts(summary_rows, field_name="failure_reason")
    top_failed_destinations = _top_failed_destinations(summary_rows)
    top_failure_reasons = ", ".join(
        f"{reason}={count}"
        for reason, count in list(failure_counts_by_reason.items())[:5]
    ) or "none"
    total_route_cache_hits = (
        perf.counters.get("first_mile_cache_hits", 0.0)
        + perf.counters.get("road_direct_cache_hits", 0.0)
        + perf.counters.get("last_mile_cache_hits", 0.0)
    )
    total_route_cache_misses = (
        perf.counters.get("first_mile_cache_misses", 0.0)
        + perf.counters.get("road_direct_cache_misses", 0.0)
        + perf.counters.get("last_mile_cache_misses", 0.0)
    )

    _log.info(
        (
            "Bulk performance summary run_id=%s selector_hash=%s bootstrap=%.2fs normalize=%.2fs geocode=%.2fs "
            "geometry=%.2fs exact=%.2fs approx=%.2fs db_read=%.2fs db_write=%.2fs total_runtime=%.2fs"
        ),
        run_id,
        selector_hash_value or "<none>",
        performance["timings_s"].get("bootstrap_s", 0.0),
        performance["timings_s"].get("destination_normalization_s", 0.0),
        performance["timings_s"].get("destination_geocode_s", 0.0),
        performance["timings_s"].get("geometry_acquisition_s", 0.0),
        performance["timings_s"].get("exact_pass_s", 0.0),
        performance["timings_s"].get("approximation_pass_s", 0.0),
        performance["timings_s"].get("db_read_s", 0.0),
        performance["timings_s"].get("db_write_s", 0.0),
        duration,
    )
    _log.info(
        (
            "Bulk evaluation summary run_id=%s requested=%d unique=%d location_alias_cache_hits=%.0f location_alias_cache_misses=%.0f "
            "route_cache_hits=%.0f route_cache_misses=%.0f geocode_provider_calls=%.0f route_provider_calls=%.0f "
            "successes=%d failures=%d approximations=%d rows_persisted=%.0f workers=geocode:%d route:%d "
            "rate_limited=%.0f timeout=%.0f network_error=%.0f cooldown_skips=%.0f duration_s=%.2f"
        ),
        run_id,
        requested_destination_count,
        unique_destination_count,
        perf.counters.get("destination_cache_hits", 0.0),
        perf.counters.get("destination_cache_misses", 0.0),
        total_route_cache_hits,
        total_route_cache_misses,
        provider_totals["geocode_attempts"],
        provider_totals["route_attempts"],
        success_count,
        fail_count,
        approximated_success_count,
        perf.counters.get("bulk_rows_persisted", 0.0),
        int(max_geocode_workers),
        int(max_route_workers),
        provider_totals["rate_limited"],
        provider_totals["timeout"],
        provider_totals["network_error"],
        provider_totals["cooldown_skips"],
        duration,
    )
    _log.info(
        "Bulk failure summary run_id=%s top_failures=%s statuses=%s by_step=%s by_leg=%s by_reason=%s top_failed_destinations=%s",
        run_id,
        top_failure_reasons,
        status_counts,
        _format_counter_summary(failure_counts_by_step),
        _format_counter_summary(failure_counts_by_leg),
        _format_counter_summary(failure_counts_by_reason),
        _format_top_failed_destinations(top_failed_destinations),
    )
    _log.info(
        "Bulk provider summary run_id=%s providers=%s",
        run_id,
        _format_provider_summary(provider_calls),
    )
    return {
        "summary_rows": summary_rows,
        "success_count": success_count,
        "fail_count": fail_count,
        "exact_success_count": exact_success_count,
        "approximated_success_count": approximated_success_count,
        "unresolved_fail_count": unresolved_fail_count,
        "duration_s": duration,
        "run_id": run_id,
        "selector_hash": selector_hash_value,
        "shuffle_seed_used": shuffle_seed_used,
        "status_counts": status_counts,
        "failure_counts_by_step": failure_counts_by_step,
        "failure_counts_by_leg": failure_counts_by_leg,
        "failure_counts_by_reason": failure_counts_by_reason,
        "top_failed_destinations": top_failed_destinations,
        "performance": performance,
    }


def _materialize_run_wide_failure(
    *,
    persistence: BulkPersistenceBuffer,
    summary_rows: List[Dict[str, Any]],
    work_items: List[DestinationWorkItem],
    run_id: str,
    destination_set_id: str,
    origin_input: str,
    origin_pt: Dict[str, Any],
    origin_port: Optional[Dict[str, Any]],
    cargo_t: float,
    truck_key: str,
    profile: str,
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    port_moves_per_call: Optional[float],
    cargo_teu: Optional[float],
    t_per_teu_default: float,
    allocation_mode: Optional[str],
    allocation_load_factor: float,
    full_call_mode: bool,
    port_ops_scenario: str,
    status: str,
    error_message: str,
    failure_step: str,
    failure_system: str,
    failure_provider: Optional[str] = None,
    failure_provider_operation: Optional[str] = None,
) -> int:
    run_wide_diagnostic = build_failure_diagnostic(
        status=status,
        step=failure_step,
        failure_detail=error_message,
        system=failure_system,
        provider=failure_provider,
        provider_operation=failure_provider_operation,
    )
    _log.warning(
        (
            "Bulk run-wide failure materialized run_id=%s step=%s leg=%s reason=%s destinations=%d "
            "provider=%s provider_operation=%s error=%s"
        ),
        run_id,
        failure_step,
        run_wide_diagnostic.failed_leg or "<unknown>",
        run_wide_diagnostic.failure_reason,
        len(work_items),
        run_wide_diagnostic.provider or "<unknown>",
        run_wide_diagnostic.provider_operation or "<unknown>",
        error_message,
    )
    for item in work_items:
        _assign_destination_failure(
            item,
            status=status,
            error_message=error_message,
            step=failure_step,
            system=failure_system,
            provider=failure_provider,
            provider_operation=failure_provider_operation,
        )
        failure_geo: Dict[str, Any] = {"origin": origin_pt}
        if origin_port is not None:
            failure_geo["port_origin"] = origin_port
        if item.point is not None:
            failure_geo["destiny"] = item.point
        if item.port_destiny is not None:
            failure_geo["port_destiny"] = item.port_destiny

        bulk_row, run_row = _build_bulk_outcome_rows(
            run_id=str(run_id),
            destination_set_id=destination_set_id,
            scenario_key=item.scenario_key,
            input_origin=origin_input,
            input_destiny=item.scenario_payload["input_destiny"],
            origin_location_id=origin_pt.get("location_id"),
            destination_location_id=(None if item.point is None else item.point.get("location_id")),
            destination_lat=(None if item.point is None else item.point.get("lat")),
            destination_lon=(None if item.point is None else item.point.get("lon")),
            destination_uf=(None if item.point is None else item.point.get("uf")),
            origin_name=origin_pt["label"],
            destiny_name=item.destiny_name or item.destiny_input,
            truck_key=truck_key,
            ors_profile=profile,
            cargo_t=cargo_t,
            vessel_class=vessel_class,
            include_hoteling=include_hoteling,
            hoteling_hours_per_call=hoteling_hours_per_call,
            port_calls=port_calls,
            include_port_ops=include_port_ops,
            port_moves_per_call=port_moves_per_call,
            cargo_teu=cargo_teu,
            t_per_teu_default=t_per_teu_default,
            allocation_mode=allocation_mode,
            allocation_load_factor=allocation_load_factor,
            full_call_mode=full_call_mode,
            port_ops_scenario=port_ops_scenario,
            status=status,
            error_message=error_message,
            geo=failure_geo,
            port_origin_location_id=(None if origin_port is None else origin_port.get("location_id")),
            port_origin_name=(None if origin_port is None else origin_port.get("name")),
            port_origin_lat=(None if origin_port is None else origin_port.get("lat")),
            port_origin_lon=(None if origin_port is None else origin_port.get("lon")),
            port_destiny_location_id=(None if item.port_destiny is None else item.port_destiny.get("location_id")),
            port_destiny_name=(None if item.port_destiny is None else item.port_destiny.get("name")),
            port_destiny_lat=(None if item.port_destiny is None else item.port_destiny.get("lat")),
            port_destiny_lon=(None if item.port_destiny is None else item.port_destiny.get("lon")),
            failure_step=item.failure_step,
            failed_leg=item.failed_leg,
            failure_reason=item.failure_reason,
            failure_detail=item.failure_detail or error_message,
            retryable=item.retryable,
            failure_provider=item.failure_provider,
            failure_provider_operation=item.failure_provider_operation,
        )
        persistence.add(bulk_row, run_row)
        summary_rows.append(
            _build_failure_summary_row(
                str(run_id),
                origin_pt["label"],
                item.destiny_input,
                item.destiny_name or item.destiny_input,
                destination_lat=(None if item.point is None else item.point.get("lat")),
                destination_lon=(None if item.point is None else item.point.get("lon")),
                port_origin_name=(None if origin_port is None else origin_port.get("name")),
                port_destiny_name=(None if item.port_destiny is None else item.port_destiny.get("name")),
                status=status,
                error_message=error_message,
                failure_detail=item.failure_detail or error_message,
                failure_step=item.failure_step,
                failure_system=item.failure_system,
                failure_provider=item.failure_provider,
                failed_leg=item.failed_leg,
                failure_reason=item.failure_reason,
                retryable=item.retryable,
                failure_provider_operation=item.failure_provider_operation,
            )
        )
    persistence.flush()
    return len(work_items)


def _persistable_point_row(*, place: str, point: Dict[str, Any], source: str) -> Dict[str, Any]:
    return {
        "place": place,
        "label": point["label"],
        "lat": point["lat"],
        "lon": point["lon"],
        "uf": point.get("uf"),
        "source": source,
    }


def _apply_destination_point_reuse(
    work_items: List[DestinationWorkItem],
    *,
    cached_points: Dict[str, Dict[str, Any]],
    latest_result_points: Dict[str, Dict[str, Any]],
    historical_result_points: Dict[str, Dict[str, Any]],
    perf: BulkPerformanceTracker,
    point_rows_to_persist: List[Dict[str, Any]],
) -> None:
    for item in work_items:
        place_key = item.normalized_input.casefold()
        cached = cached_points.get(place_key)
        if cached is not None:
            item.point = _point_from_cached_record(cached)
            item.destiny_name = item.point["label"]
            item.point_source = "location_alias_cache"
            perf.incr("destination_cache_hits")
            continue

        latest_result_point = latest_result_points.get(place_key)
        if latest_result_point is not None:
            item.point = dict(latest_result_point)
            item.destiny_name = item.point["label"]
            item.point_source = "bulk_results"
            perf.incr("destination_cache_hits")
            perf.incr("destination_result_hits")
            point_rows_to_persist.append(
                _persistable_point_row(
                    place=item.normalized_input,
                    point=item.point,
                    source="bulk_results",
                )
            )
            continue

        historical_result_point = historical_result_points.get(place_key)
        if historical_result_point is not None:
            item.point = dict(historical_result_point)
            item.destiny_name = item.point["label"]
            item.point_source = "bulk_result_history"
            perf.incr("destination_cache_hits")
            perf.incr("destination_history_hits")
            point_rows_to_persist.append(
                _persistable_point_row(
                    place=item.normalized_input,
                    point=item.point,
                    source="bulk_result_history",
                )
            )
            continue

        perf.incr("destination_cache_misses")


def run_bulk_evaluation_pipeline(
    origin: str,
    dest_list: List[str],
    *,
    cargo_t: float,
    truck_key: str,
    profile: str,
    overwrite_road: bool = False,
    db_path: Path | str | None = None,
    results_table: str,
    runs_table: str,
    run_results_table: str,
    destination_set_id: str,
    vessel_class: str,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    port_moves_per_call: Optional[float],
    cargo_teu: Optional[float],
    t_per_teu_default: float,
    allocation_mode: Optional[str],
    allocation_load_factor: float,
    full_call_mode: bool,
    port_ops_scenario: str,
    progress_callback: Optional[Any] = None,
    shuffle_destinations: bool = True,
    shuffle_seed: Optional[int] = None,
    approximation_fallback: bool = True,
    max_geocode_workers: int = 2,
    max_route_workers: int = 2,
    persist_batch_size: int = 64,
) -> Dict[str, Any]:
    deduped_destinations = _dedupe_preserve_order(dest_list)
    requested_destination_count = len([item for item in dest_list if str(item).strip()])
    if not deduped_destinations:
        return {
            "summary_rows": [],
            "success_count": 0,
            "fail_count": 0,
            "exact_success_count": 0,
            "approximated_success_count": 0,
            "unresolved_fail_count": 0,
            "duration_s": 0.0,
            "run_id": None,
            "shuffle_seed_used": None,
            "performance": {"timings_s": {}, "counts": {}, "provider_calls": {}},
        }

    shuffled_destinations, shuffle_seed_used = _shuffle_destinations(
        deduped_destinations,
        enabled=shuffle_destinations,
        seed=shuffle_seed,
    )

    summary_rows: List[Dict[str, Any]] = []
    pending_approximations: List[PendingApproximation] = []
    exact_references = []
    perf = BulkPerformanceTracker()
    exact_success_count = 0
    approximated_success_count = 0
    unresolved_fail_count = 0
    success_count = 0
    fail_count = 0
    run_id: Optional[str] = None
    selector_hash_value: Optional[str] = None
    active_run_step = "bootstrap"

    started_global = time.perf_counter()
    ors, ports, sea_matrix, resolved_db_path = load_routing_assets(db_path=db_path)
    if hasattr(ors, "reset_metrics"):
        ors.reset_metrics()
    previous_cooldown_callback = None
    if progress_callback is not None and hasattr(ors, "set_cooldown_callback"):
        previous_cooldown_callback = ors.set_cooldown_callback(
            lambda payload: _emit_progress(progress_callback, **payload)
        )

    perf.incr("destinations_requested", requested_destination_count)
    perf.incr("destinations_unique", len(shuffled_destinations))
    perf.incr("destinations_deduped", max(requested_destination_count - len(shuffled_destinations), 0))

    origin_input_norm = normalize_bulk_place_input(origin)
    set_log_context(
        origin=origin_input_norm or origin,
        destination_set_id=destination_set_id,
        ors_profile=profile,
        entrypoint="bulk",
    )
    _log.info(
        (
            "Starting staged bulk evaluation origin=%r requested=%d unique=%d destination_set=%s "
            "shuffle=%s shuffle_seed=%s approximation_fallback=%s geocode_workers=%d route_workers=%d batch_size=%d "
            "profile=%s timeout_s=%s http_retries=%d"
        ),
        origin,
        requested_destination_count,
        len(shuffled_destinations),
        destination_set_id,
        shuffle_destinations,
        (shuffle_seed_used if shuffle_seed_used is not None else "disabled"),
        approximation_fallback,
        int(max_geocode_workers),
        int(max_route_workers),
        int(persist_batch_size),
        profile,
        getattr(getattr(ors, "cfg", None), "timeout", None),
        int(getattr(getattr(ors, "cfg", None), "retry_limit", 0) or 0),
    )
    _log_step_banner(
        "bootstrap",
        origin=origin_input_norm or origin,
        destination_set=destination_set_id,
        requested=requested_destination_count,
        unique=len(shuffled_destinations),
        profile=profile,
    )
    _emit_progress(
        progress_callback,
        phase="start",
        current=0,
        total=len(shuffled_destinations),
        shuffle_seed_used=shuffle_seed_used,
        approximation_fallback=approximation_fallback,
        message="Phase 0/4 bootstrap",
    )

    def _ensure_live_connection(conn: Any, *, context: str) -> None:
        if not hasattr(conn, "ping") or not hasattr(conn, "reconnect"):
            return
        try:
            conn.ping()
        except Exception as exc:
            _log.warning("Bulk pipeline DB connection lost before %s; reconnecting: %s", context, exc)
            conn.reconnect()

    def _flush_point_rows(conn: Any, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        try:
            _ensure_live_connection(conn, context="place-point flush")
            deduped = {}
            for row in rows:
                place = str(row.get("place") or "").strip()
                if not place:
                    continue
                deduped[place.casefold()] = row
            if not deduped:
                return
            perf.incr("db_write_ops")
            with perf.measure("db_write_s"):
                upsert_place_points(conn, rows=deduped.values())
                conn.commit()
            perf.incr("place_points_persisted", len(deduped))
            rows.clear()
        except Exception as exc:
            raise _BulkStepError(step="persist_results", system="database", provider="postgres", error=exc) from exc

    def _flush_route_rows(conn: Any, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        try:
            _ensure_live_connection(conn, context="route-cache flush")
            perf.incr("db_write_ops")
            with perf.measure("db_write_s"):
                upsert_runs(conn, rows=rows)
                conn.commit()
            perf.incr("route_cache_rows_persisted", len(rows))
            rows.clear()
        except Exception as exc:
            raise _BulkStepError(step="persist_results", system="database", provider="postgres", error=exc) from exc

    try:
        with db_session(resolved_db_path) as conn:
            nearest_port_memo = NearestPortMemo(ports)
            point_rows_to_persist: list[Dict[str, Any]] = []
            work_items: list[DestinationWorkItem] = []
            with perf.measure("destination_normalization_s"):
                for index, destiny_input in enumerate(shuffled_destinations, start=1):
                    scenario_payload = _build_scenario_payload(
                        origin_input=origin_input_norm,
                        destiny_input=destiny_input,
                        cargo_t=cargo_t,
                        truck_key=truck_key,
                        profile=profile,
                        vessel_class=vessel_class,
                        include_hoteling=include_hoteling,
                        hoteling_hours_per_call=hoteling_hours_per_call,
                        port_calls=port_calls,
                        include_port_ops=include_port_ops,
                        port_moves_per_call=port_moves_per_call,
                        cargo_teu=cargo_teu,
                        t_per_teu_default=t_per_teu_default,
                        allocation_mode=allocation_mode,
                        allocation_load_factor=allocation_load_factor,
                        full_call_mode=full_call_mode,
                        port_ops_scenario=port_ops_scenario,
                    )
                    work_items.append(
                        DestinationWorkItem(
                            index=index,
                            destiny_input=str(destiny_input),
                            normalized_input=str(scenario_payload["input_destiny"]),
                            scenario_key=build_bulk_scenario_key(scenario_payload),
                            scenario_payload=scenario_payload,
                            destiny_name=str(destiny_input).strip(),
                        )
                    )

            with perf.measure("bootstrap_s"):
                active_run_step = "origin_alias_cache"
                _log_step_banner("origin_alias_cache", origin=origin_input_norm)
                perf.incr("db_read_ops")
                with perf.measure("db_read_s"):
                    origin_cached = find_place_point(conn, place=origin_input_norm)
                if origin_cached:
                    origin_pt = _point_from_cached_record(origin_cached)
                    perf.incr("origin_cache_hits")
                    _log.info(
                        "Bulk origin alias cache hit origin=%s canonical=%s coords=%s",
                        origin_input_norm,
                        origin_pt["label"],
                        _format_point_coords(origin_pt),
                    )
                else:
                    perf.incr("origin_cache_misses")
                    active_run_step = "origin_geocoding"
                    _log_step_banner(
                        "origin_geocoding",
                        origin=origin_input_norm,
                        timeout_s="5/5",
                        http_retries=0,
                    )
                    try:
                        with perf.measure("origin_geocode_s"):
                            origin_pt = _resolve_point_without_db(origin, ors)
                    except Exception as exc:
                        raise _BulkStepError(
                            step="origin_geocoding",
                            system="geocoding",
                            provider=_failure_provider(exc),
                            error=exc,
                        ) from exc
                    if not origin_pt:
                        raise _BulkStepError(
                            step="origin_geocoding",
                            system="geocoding",
                            error=RuntimeError(f"Failed to resolve bulk origin: {origin}"),
                        )
                    point_rows_to_persist.append(
                        {
                            "place": origin_input_norm,
                            "label": origin_pt["label"],
                            "lat": origin_pt["lat"],
                            "lon": origin_pt["lon"],
                            "uf": origin_pt.get("uf"),
                            "source": "provider",
                        }
                    )

                active_run_step = "persist_results"
                _log_step_banner("persist_results", target="location_aliases")
                _flush_point_rows(conn, point_rows_to_persist)
                origin_cached_point = find_place_point(conn, place=origin_input_norm)
                if origin_cached_point and origin_cached_point.get("location_id") is not None:
                    origin_pt["location_id"] = int(origin_cached_point["location_id"])
                origin_location_id = origin_pt.get("location_id")
                if origin_location_id is None:
                    raise RuntimeError(f"Failed to canonicalize bulk origin: {origin}")
                run_selector = _build_run_selector(
                    origin_location_id=int(origin_location_id),
                    cargo_t=cargo_t,
                    truck_key=truck_key,
                    profile=profile,
                    vessel_class=vessel_class,
                    include_hoteling=include_hoteling,
                    hoteling_hours_per_call=hoteling_hours_per_call,
                    port_calls=port_calls,
                    include_port_ops=include_port_ops,
                    port_moves_per_call=port_moves_per_call,
                    cargo_teu=cargo_teu,
                    t_per_teu_default=t_per_teu_default,
                    allocation_mode=allocation_mode,
                    allocation_load_factor=allocation_load_factor,
                    full_call_mode=full_call_mode,
                    port_ops_scenario=port_ops_scenario,
                    destination_set_id=destination_set_id,
                )
                selector_hash_value = selector_hash(run_selector)

                evaluation_kwargs = {
                    "cargo_t": cargo_t,
                    "truck_key": truck_key,
                    "vessel_class": vessel_class,
                    "include_hoteling": include_hoteling,
                    "hoteling_hours_per_call": hoteling_hours_per_call,
                    "port_calls": port_calls,
                    "include_port_ops": include_port_ops,
                    "port_moves_per_call": port_moves_per_call,
                    "cargo_teu": cargo_teu,
                    "t_per_teu_default": t_per_teu_default,
                    "allocation_mode": allocation_mode,
                    "allocation_load_factor": allocation_load_factor,
                    "full_call_mode": full_call_mode,
                    "port_ops_scenario": port_ops_scenario,
                    "prepared_context": prepare_evaluation_context(
                        truck_key=truck_key,
                        vessel_class=vessel_class,
                        include_hoteling=include_hoteling,
                        hoteling_hours_per_call=hoteling_hours_per_call,
                        port_calls=port_calls,
                        include_port_ops=include_port_ops,
                        port_ops_scenario=port_ops_scenario,
                    ),
                }

                active_run_step = "start_bulk_run"
                _log_step_banner(
                    "start_bulk_run",
                    origin=origin_pt["label"],
                    destination_set=destination_set_id,
                    cargo_t=f"{cargo_t:.3f}",
                )
                try:
                    perf.incr("db_write_ops")
                    with perf.measure("db_write_s"):
                        run_id = start_bulk_run(
                            conn,
                            selector=run_selector,
                            origin_name=origin_pt["label"],
                            input_origin=origin_input_norm,
                            destination_count=len(shuffled_destinations),
                            origin_location_id=int(origin_location_id),
                            table_name=runs_table,
                        )
                        conn.commit()
                except Exception as exc:
                    raise _BulkStepError(
                        step="start_bulk_run",
                        system="database",
                        provider="postgres",
                        error=exc,
                    ) from exc
                set_log_context(
                    run_id=str(run_id),
                    selector_hash=selector_hash_value,
                    origin=origin_pt["label"],
                    destination_set_id=destination_set_id,
                    ors_profile=profile,
                    entrypoint="bulk",
                )
                _log.info(
                    (
                        "Bulk run initialized run_id=%s selector_hash=%s origin=%s destination_set=%s "
                        "cargo_t=%.3f truck_key=%s profile=%s"
                    ),
                    run_id,
                    selector_hash_value,
                    origin_pt["label"],
                    destination_set_id,
                    cargo_t,
                    truck_key,
                    profile,
                )
                persistence = BulkPersistenceBuffer(
                    conn,
                    results_table=results_table,
                    run_results_table=run_results_table,
                    batch_size=persist_batch_size,
                    perf=perf,
                )
                route_coordinator = RouteRequestCoordinator(
                    ors,
                    profile=profile,
                    overwrite=overwrite_road,
                    perf=perf,
                )
                origin_port = None
                try:
                    active_run_step = "nearest_port_origin"
                    _log_step_banner("nearest_port_origin", origin=origin_pt["label"])
                    try:
                        origin_port = nearest_port_memo.resolve(origin_pt, perf)
                    except Exception as exc:
                        raise _BulkStepError(
                            step="nearest_port_origin",
                            system="ports",
                            provider="nearest_port_lookup",
                            error=exc,
                        ) from exc
                    origin_port_node = build_port_node(origin_port)
                    first_mile_spec = RouteRequestSpec(
                        leg_name="first_mile",
                        origin=origin_pt,
                        destiny=origin_port_node,
                        profile=profile,
                    )
                    active_run_step = "routing_origin_to_port_origin"
                    _log_step_banner(
                        "routing_origin_to_port_origin",
                        origin=origin_pt["label"],
                        port_origin=origin_port.get("name"),
                        profile=profile,
                    )
                    route_coordinator.prime(conn, [first_mile_spec])
                    try:
                        first_mile_leg = route_coordinator.resolve(first_mile_spec)
                        _require_distance(first_mile_leg, "first_mile")
                    except Exception as exc:
                        raise _BulkStepError(
                            step="routing_origin_to_port_origin",
                            system="routing",
                            provider=_failure_provider(exc),
                            error=exc,
                        ) from exc
                    _log.info(
                        (
                            "Bulk origin first-mile route origin=%s port_origin=%s km=%.1f source=%s "
                            "profile_used=%s cached=%s"
                        ),
                        origin_pt["label"],
                        origin_port.get("name"),
                        float(first_mile_leg.get("distance_km") or 0.0),
                        first_mile_leg.get("source") or "<none>",
                        first_mile_leg.get("profile_used") or profile,
                        first_mile_leg.get("cached"),
                    )
                    active_run_step = "persist_results"
                    _log_step_banner("persist_results", target="route_cache")
                    _flush_route_rows(conn, route_coordinator.drain_pending_rows())
                except Exception as exc:
                    failure_status, failure_message, log_trace = _classify_failure(exc)
                    failure_step = _failure_step(exc, default=active_run_step)
                    failure_system = _failure_system(exc, default="routing")
                    failure_provider = _failure_provider(exc)
                    if log_trace:
                        _log.error("Bulk origin setup failed: %s", failure_message, exc_info=True)
                    fail_count = _materialize_run_wide_failure(
                        persistence=persistence,
                        summary_rows=summary_rows,
                        work_items=work_items,
                        run_id=str(run_id),
                        destination_set_id=destination_set_id,
                        origin_input=origin_input_norm,
                        origin_pt=origin_pt,
                        origin_port=origin_port,
                        cargo_t=cargo_t,
                        truck_key=truck_key,
                        profile=profile,
                        vessel_class=vessel_class,
                        include_hoteling=include_hoteling,
                        hoteling_hours_per_call=hoteling_hours_per_call,
                        port_calls=port_calls,
                        include_port_ops=include_port_ops,
                        port_moves_per_call=port_moves_per_call,
                        cargo_teu=cargo_teu,
                        t_per_teu_default=t_per_teu_default,
                        allocation_mode=allocation_mode,
                        allocation_load_factor=allocation_load_factor,
                        full_call_mode=full_call_mode,
                        port_ops_scenario=port_ops_scenario,
                        status=failure_status,
                        error_message=failure_message,
                        failure_step=failure_step,
                        failure_system=failure_system,
                        failure_provider=failure_provider,
                    )
                    unresolved_fail_count += fail_count
                    duration = time.perf_counter() - started_global
                    perf.add_duration("total_run_s", duration)
                    active_run_step = "finish_bulk_run"
                    _log_step_banner("finish_bulk_run", run_id=run_id, status="completed")
                    try:
                        perf.incr("db_write_ops")
                        with perf.measure("db_write_s"):
                            finish_bulk_run(
                                conn,
                                run_id=str(run_id),
                                status="completed",
                                success_count=success_count,
                                fail_count=fail_count,
                                duration_s=duration,
                                error_message=None,
                                table_name=runs_table,
                            )
                            conn.commit()
                    except Exception as finish_exc:
                        raise _BulkStepError(
                            step="finish_bulk_run",
                            system="database",
                            provider="postgres",
                            error=finish_exc,
                        ) from finish_exc
                    _emit_progress(
                        progress_callback,
                        phase="complete",
                        current=len(shuffled_destinations),
                        total=len(shuffled_destinations),
                        success_count=success_count,
                        fail_count=fail_count,
                        exact_success_count=exact_success_count,
                        approximated_success_count=approximated_success_count,
                        unresolved_fail_count=unresolved_fail_count,
                        duration_s=duration,
                        run_id=run_id,
                        shuffle_seed_used=shuffle_seed_used,
                        message="Phase 4/4 persistence complete",
                    )
                    if hasattr(ors, "set_cooldown_callback"):
                        ors.set_cooldown_callback(previous_cooldown_callback)
                    return _finalize_bulk_outcome(
                        ors=ors,
                        perf=perf,
                        summary_rows=summary_rows,
                        success_count=success_count,
                        fail_count=fail_count,
                        exact_success_count=exact_success_count,
                        approximated_success_count=approximated_success_count,
                        unresolved_fail_count=unresolved_fail_count,
                        duration=duration,
                        run_id=run_id,
                        selector_hash_value=selector_hash_value,
                        shuffle_seed_used=shuffle_seed_used,
                        requested_destination_count=requested_destination_count,
                        unique_destination_count=len(shuffled_destinations),
                        max_geocode_workers=max_geocode_workers,
                        max_route_workers=max_route_workers,
                    )

            _emit_progress(
                progress_callback,
                phase="resolution_start",
                current=0,
                total=len(work_items),
                message="Phase 1/4 destination normalization and resolution",
            )

            active_run_step = "destination_alias_cache"
            _log_step_banner("destination_alias_cache", destinations=len(work_items))
            perf.incr("db_read_ops")
            with perf.measure("db_read_s"):
                cached_points = list_cached_place_points(conn, places=[item.normalized_input for item in work_items])
            latest_result_points: dict[str, Dict[str, Any]] = {}
            perf.incr("db_read_ops")
            with perf.measure("db_read_s"):
                latest_result_rows = list_bulk_results(conn, selector=run_selector, only_success=None)
            for record in latest_result_rows:
                input_destiny = normalize_bulk_place_input(getattr(record, "input_destiny", ""))
                if not input_destiny:
                    continue
                point = _point_from_result_record(record)
                if point is None:
                    continue
                latest_result_points.setdefault(input_destiny.casefold(), point)
            perf.incr("db_read_ops")
            with perf.measure("db_read_s"):
                historical_result_points = list_bulk_result_points_by_input_keys(
                    conn,
                    input_keys=[item.normalized_input for item in work_items],
                )

            _apply_destination_point_reuse(
                work_items,
                cached_points=cached_points,
                latest_result_points=latest_result_points,
                historical_result_points=historical_result_points,
                perf=perf,
                point_rows_to_persist=point_rows_to_persist,
            )

            unresolved_items = [item for item in work_items if item.point is None]
            resolution_log_context = get_log_context()

            def _resolve_destination(item: DestinationWorkItem):
                if resolution_log_context:
                    set_log_context(**resolution_log_context)
                started = time.perf_counter()
                try:
                    point = _resolve_point_without_db(item.destiny_input, ors)
                    return item, point, None, (time.perf_counter() - started)
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    return item, None, exc, (time.perf_counter() - started)

            if unresolved_items:
                workers = max(1, min(int(max_geocode_workers), len(unresolved_items)))
                active_run_step = "destination_geocoding"
                _log_step_banner(
                    "destination_geocoding",
                    unresolved=len(unresolved_items),
                    workers=workers,
                    timeout_s="5/5",
                    http_retries=0,
                )
                completed = 0
                if workers == 1:
                    geocode_results = (_resolve_destination(item) for item in unresolved_items)
                    executor = None
                else:
                    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bulk-geocode")
                    futures = [executor.submit(_resolve_destination, item) for item in unresolved_items]
                    geocode_results = (future.result() for future in as_completed(futures))
                try:
                    for item, point, error, duration_s in geocode_results:
                        perf.add_duration("destination_geocode_s", duration_s)
                        completed += 1
                        if error is not None:
                            failure_status, failure_message, _ = _classify_failure(error)
                            _assign_destination_failure(
                                item,
                                status=failure_status,
                                error_message=failure_message,
                                step="destination_geocoding",
                                system="geocoding",
                                provider=_failure_provider(error),
                            )
                            _log_destination_failure_context(
                                phase="resolution",
                                origin_pt=origin_pt,
                                origin_port=origin_port,
                                item=item,
                                status=failure_status,
                                error_message=failure_message,
                            )
                        elif point is None:
                            _assign_destination_failure(
                                item,
                                status="geocode_failed",
                                error_message=f"Failed to resolve destination: {item.destiny_input}",
                                step="destination_geocoding",
                                system="geocoding",
                            )
                            _log_destination_failure_context(
                                phase="resolution",
                                origin_pt=origin_pt,
                                origin_port=origin_port,
                                item=item,
                                status=item.failure_status or "geocode_failed",
                                error_message=item.error_message or f"Failed to resolve destination: {item.destiny_input}",
                            )
                        else:
                            item.point = point
                            item.destiny_name = point["label"]
                            item.point_source = "provider"
                            point_rows_to_persist.append(
                                {
                                    "place": item.normalized_input,
                                    "label": point["label"],
                                    "lat": point["lat"],
                                    "lon": point["lon"],
                                    "uf": point.get("uf"),
                                    "source": "provider",
                                }
                            )
                        _emit_progress(
                            progress_callback,
                            phase="resolution",
                            current=completed,
                            total=len(unresolved_items),
                            success_count=success_count,
                            fail_count=fail_count,
                            message=f"Resolved {completed}/{len(unresolved_items)} uncached destinations",
                        )
                finally:
                    if executor is not None:
                        executor.shutdown(wait=True)

            _flush_point_rows(conn, point_rows_to_persist)
            _log.info(
                (
                    "Bulk destination resolution summary run_id=%s total=%d alias_cache_hits=%.0f alias_cache_misses=%.0f "
                    "latest_result_hits=%.0f historical_result_hits=%.0f geocode_attempts=%d failures=%d"
                ),
                run_id,
                len(work_items),
                perf.counters.get("destination_cache_hits", 0.0),
                perf.counters.get("destination_cache_misses", 0.0),
                perf.counters.get("destination_result_hits", 0.0),
                perf.counters.get("destination_history_hits", 0.0),
                len(unresolved_items),
                sum(1 for item in work_items if item.failure_status is not None),
            )

            geometry_items = [item for item in work_items if item.point is not None and item.failure_status is None]
            _emit_progress(
                progress_callback,
                phase="geometry_start",
                current=0,
                total=len(geometry_items),
                message="Phase 2/4 geometry and routing acquisition",
            )

            active_run_step = "nearest_port_destiny"
            _log_step_banner("nearest_port_destiny", destinations=len(geometry_items))
            route_specs: list[RouteRequestSpec] = []
            for item in geometry_items:
                assert item.point is not None
                try:
                    item.port_destiny = nearest_port_memo.resolve(item.point, perf)
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    _assign_destination_failure(
                        item,
                        status="nearest_port_failed",
                        error_message=str(exc).strip() or "Nearest-port lookup failed",
                        step="nearest_port_destiny",
                        system="ports",
                        provider="nearest_port_lookup",
                        provider_operation="nearest_port_lookup",
                    )
                    _log_destination_failure_context(
                        phase="nearest_port",
                        origin_pt=origin_pt,
                        origin_port=origin_port,
                        item=item,
                        status=item.failure_status or "nearest_port_failed",
                        error_message=item.error_message or "Nearest-port lookup failed",
                    )
                    continue
                route_specs.append(RouteRequestSpec("road_direct", origin_pt, item.point, profile))
                route_specs.append(RouteRequestSpec("last_mile", build_port_node(item.port_destiny), item.point, profile))
            routable_items = [
                item for item in geometry_items if item.failure_status is None and item.port_destiny is not None
            ]
            active_run_step = "routing_road_only"
            _log_step_banner(
                "routing_road_only",
                destinations=len(routable_items),
                workers=max(1, min(int(max_route_workers), len(routable_items))) if routable_items else 0,
                profile=profile,
            )
            _log_step_banner(
                "routing_port_destiny_to_destiny",
                destinations=len(routable_items),
                workers=max(1, min(int(max_route_workers), len(routable_items))) if routable_items else 0,
                profile=profile,
            )
            route_coordinator.prime(conn, route_specs)
            geometry_log_context = get_log_context()

            def _build_geometry(item: DestinationWorkItem):
                if geometry_log_context:
                    set_log_context(**geometry_log_context)
                started = time.perf_counter()
                try:
                    assert item.point is not None
                    assert item.port_destiny is not None

                    def _resolve_geometry_leg(start: Dict[str, Any], end: Dict[str, Any], leg_name: str):
                        step = _LEG_FAILURE_STEPS.get(leg_name, "geometry_acquisition")
                        try:
                            return route_coordinator.resolve(
                                RouteRequestSpec(leg_name=leg_name, origin=start, destiny=end, profile=profile)
                            )
                        except Exception as exc:
                            raise _BulkStepError(
                                step=step,
                                system="routing",
                                provider=_failure_provider(exc),
                                error=exc,
                            ) from exc

                    geometry = build_path_geometry_from_resolved(
                        origin_pt,
                        item.point,
                        ors=ors,
                        ports=ports,
                        sea_matrix=sea_matrix,
                        ors_profile=profile,
                        overwrite_road=overwrite_road,
                        db_path=resolved_db_path,
                        port_origin=origin_port,
                        port_destiny=item.port_destiny,
                        first_mile_leg=first_mile_leg,
                        route_resolver=_resolve_geometry_leg,
                    )
                    return item, geometry, None, (time.perf_counter() - started)
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    return item, None, exc, (time.perf_counter() - started)

            if routable_items:
                workers = max(1, min(int(max_route_workers), len(routable_items)))
                completed = 0
                if workers == 1:
                    geometry_results = (_build_geometry(item) for item in routable_items)
                    executor = None
                else:
                    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bulk-route")
                    futures = [executor.submit(_build_geometry, item) for item in routable_items]
                    geometry_results = (future.result() for future in as_completed(futures))
                try:
                    for item, geometry, error, duration_s in geometry_results:
                        perf.add_duration("geometry_acquisition_s", duration_s)
                        completed += 1
                        if error is not None:
                            failure_status, failure_message, _ = _classify_failure(error)
                            _assign_destination_failure(
                                item,
                                status=failure_status,
                                error_message=failure_message,
                                step=_failure_step(error, default="build_multimodal_route"),
                                system=_failure_system(error, default="routing"),
                                provider=_failure_provider(error),
                            )
                            _log_destination_failure_context(
                                phase="geometry",
                                origin_pt=origin_pt,
                                origin_port=origin_port,
                                item=item,
                                status=failure_status,
                                error_message=failure_message,
                                geo=geometry,
                            )
                        elif not geometry or geometry.get("status") != "ok":
                            _assign_destination_failure(
                                item,
                                status="geometry_failed",
                                error_message="Geometry build failed",
                                step="build_multimodal_route",
                                system="routing",
                            )
                            _log_destination_failure_context(
                                phase="geometry",
                                origin_pt=origin_pt,
                                origin_port=origin_port,
                                item=item,
                                status=item.failure_status or "geometry_failed",
                                error_message=item.error_message or "Geometry build failed",
                                geo=geometry,
                            )
                        else:
                            item.geo = geometry
                        _emit_progress(
                            progress_callback,
                            phase="geometry",
                            current=completed,
                            total=len(routable_items),
                            success_count=success_count,
                            fail_count=fail_count,
                            message=f"Built geometry {completed}/{len(routable_items)}",
                        )
                finally:
                    if executor is not None:
                        executor.shutdown(wait=True)

            _flush_route_rows(conn, route_coordinator.drain_pending_rows())
            routing_provider_totals = _provider_operation_totals(
                ors.metrics_snapshot() if hasattr(ors, "metrics_snapshot") else {}
            )
            _log.info(
                (
                    "Bulk routing summary run_id=%s routable=%d direct_cache_hits=%.0f direct_cache_misses=%.0f "
                    "last_mile_cache_hits=%.0f last_mile_cache_misses=%.0f route_provider_calls=%.0f geometry_failures=%d"
                ),
                run_id,
                len(routable_items),
                perf.counters.get("road_direct_cache_hits", 0.0),
                perf.counters.get("road_direct_cache_misses", 0.0),
                perf.counters.get("last_mile_cache_hits", 0.0),
                perf.counters.get("last_mile_cache_misses", 0.0),
                routing_provider_totals["route_attempts"],
                sum(1 for item in work_items if item.failure_status is not None),
            )

            active_run_step = "calculating_costs_emissions"
            _log_step_banner("calculating_costs_emissions", destinations=len(work_items))
            with perf.measure("exact_pass_s"):
                for item in work_items:
                    geo = item.geo
                    _emit_progress(
                        progress_callback,
                        phase="progress",
                        pass_name="exact",
                        current=item.index - 1,
                        total=len(work_items),
                        destination=item.destiny_input,
                        success_count=success_count,
                        fail_count=fail_count,
                        exact_success_count=exact_success_count,
                        approximated_success_count=approximated_success_count,
                        message=f"Phase 3/4 exact evaluation for {item.destiny_input}",
                    )
                    try:
                        if item.failure_status is not None:
                            failure_status = item.failure_status
                            failure_message = item.error_message or item.failure_status
                            bulk_row, run_row = _build_bulk_outcome_rows(
                                run_id=str(run_id),
                                destination_set_id=destination_set_id,
                                scenario_key=item.scenario_key,
                                input_origin=item.scenario_payload["input_origin"],
                                input_destiny=item.scenario_payload["input_destiny"],
                                origin_location_id=origin_pt.get("location_id"),
                                destination_location_id=(None if item.point is None else item.point.get("location_id")),
                                origin_name=origin_pt["label"],
                                destiny_name=item.destiny_name or item.destiny_input,
                                truck_key=truck_key,
                                ors_profile=profile,
                                cargo_t=cargo_t,
                                vessel_class=vessel_class,
                                include_hoteling=include_hoteling,
                                hoteling_hours_per_call=hoteling_hours_per_call,
                                port_calls=port_calls,
                                include_port_ops=include_port_ops,
                                port_moves_per_call=port_moves_per_call,
                                cargo_teu=cargo_teu,
                                t_per_teu_default=t_per_teu_default,
                                allocation_mode=allocation_mode,
                                allocation_load_factor=allocation_load_factor,
                                full_call_mode=full_call_mode,
                                port_ops_scenario=port_ops_scenario,
                                status=failure_status,
                                error_message=failure_message,
                                geo=geo,
                                is_approximation=False,
                                failure_step=item.failure_step,
                                failed_leg=item.failed_leg,
                                failure_reason=item.failure_reason,
                                failure_detail=item.failure_detail or failure_message,
                                retryable=item.retryable,
                                failure_provider=item.failure_provider,
                                failure_provider_operation=item.failure_provider_operation,
                            )
                            persistence.add(bulk_row, run_row)
                            summary_rows.append(
                                _build_failure_summary_row(
                                    str(run_id),
                                    origin_pt["label"],
                                    item.destiny_input,
                                    item.destiny_name or item.destiny_input,
                                    destination_lat=(None if item.point is None else item.point.get("lat")),
                                    destination_lon=(None if item.point is None else item.point.get("lon")),
                                    port_origin_name=(None if origin_port is None else origin_port.get("name")),
                                    port_destiny_name=(None if item.port_destiny is None else item.port_destiny.get("name")),
                                    status=failure_status,
                                    error_message=failure_message,
                                    failure_detail=item.failure_detail or failure_message,
                                    failure_step=item.failure_step,
                                    failure_system=item.failure_system,
                                    failure_provider=item.failure_provider,
                                    failed_leg=item.failed_leg,
                                    failure_reason=item.failure_reason,
                                    retryable=item.retryable,
                                    failure_provider_operation=item.failure_provider_operation,
                                )
                            )
                            fail_count += 1
                            unresolved_fail_count += 1
                            continue
                        if not geo or geo.get("status") != "ok":
                            raise _BulkStepError(
                                step="build_multimodal_route",
                                system="routing",
                                error=RuntimeError("Geometry build failed"),
                            )
                        try:
                            _require_distance(geo["last_mile"], "last_mile")
                        except Exception as exc:
                            raise _BulkStepError(
                                step="routing_port_destiny_to_destiny",
                                system="routing",
                                provider=_route_provider_for_step(geo, "routing_port_destiny_to_destiny"),
                                error=exc,
                            ) from exc
                        if geo["road_direct"].get("distance_km") is None:
                            if approximation_fallback:
                                approximation_diagnostic = build_failure_diagnostic(
                                    status="no_road_route",
                                    step="routing_road_only",
                                    failure_detail="road_direct road distance is unavailable",
                                    system="routing",
                                    provider=_route_provider_for_step(geo, "routing_road_only"),
                                    raw_input=item.destiny_input,
                                )
                                pending_approximations.append(
                                    PendingApproximation(
                                        index=item.index,
                                        destiny_input=item.destiny_input,
                                        destiny_name=item.destiny_name,
                                        scenario_key=item.scenario_key,
                                        scenario_payload=item.scenario_payload,
                                        geo=geo,
                                        failure_status="no_road_route",
                                        error_message="road_direct road distance is unavailable",
                                        failure_step=approximation_diagnostic.failed_step,
                                        failure_system="routing",
                                        failure_provider=approximation_diagnostic.provider,
                                        failed_leg=approximation_diagnostic.failed_leg,
                                        failure_reason=approximation_diagnostic.failure_reason,
                                        failure_detail=approximation_diagnostic.failure_detail,
                                        retryable=approximation_diagnostic.retryable,
                                        failure_provider_operation=approximation_diagnostic.provider_operation,
                                    )
                                )
                                continue
                            raise _BulkStepError(
                                step="routing_road_only",
                                system="routing",
                                provider=_route_provider_for_step(geo, "routing_road_only"),
                                error=RuntimeError("road_direct road distance is unavailable"),
                            )
                        try:
                            res, flat = _evaluate_and_flatten(
                                geo,
                                origin_name=origin_pt["label"],
                                destiny_name=item.destiny_name,
                                evaluation_kwargs=evaluation_kwargs,
                            )
                        except Exception as exc:
                            raise _BulkStepError(
                                step="calculating_costs_emissions",
                                system="evaluation",
                                error=exc,
                            ) from exc
                        route_source = _route_source_for_result(geo, is_approximation=False)
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=item.scenario_key,
                            input_origin=item.scenario_payload["input_origin"],
                            input_destiny=item.scenario_payload["input_destiny"],
                            origin_location_id=origin_pt.get("location_id"),
                            destination_location_id=(None if item.point is None else item.point.get("location_id")),
                            origin_name=origin_pt["label"],
                            destiny_name=item.destiny_name,
                            truck_key=truck_key,
                            ors_profile=profile,
                            cargo_t=cargo_t,
                            vessel_class=vessel_class,
                            include_hoteling=include_hoteling,
                            hoteling_hours_per_call=hoteling_hours_per_call,
                            port_calls=port_calls,
                            include_port_ops=include_port_ops,
                            port_moves_per_call=port_moves_per_call,
                            cargo_teu=cargo_teu,
                            t_per_teu_default=t_per_teu_default,
                            allocation_mode=allocation_mode,
                            allocation_load_factor=allocation_load_factor,
                            full_call_mode=full_call_mode,
                            port_ops_scenario=port_ops_scenario,
                            status="ok",
                            geo=geo,
                            res=res,
                            flat=flat,
                            is_approximation=False,
                            route_source=route_source,
                        )
                        persistence.add(bulk_row, run_row)
                        reference = _make_exact_reference(geo, flat)
                        if reference is not None:
                            exact_references.append(reference)
                        summary_rows.append(
                            _build_success_summary_row(
                                str(run_id),
                                origin_pt["label"],
                                item.destiny_input,
                                geo,
                                res,
                                flat,
                                is_approximation=False,
                                route_source=route_source,
                                approximation_meta=None,
                            )
                        )
                        success_count += 1
                        exact_success_count += 1
                    except Exception as exc:
                        fail_count += 1
                        unresolved_fail_count += 1
                        failure_status, failure_message, log_trace = _classify_failure(exc)
                        failure_step = _failure_step(exc, default="calculating_costs_emissions")
                        _assign_destination_failure(
                            item,
                            status=failure_status,
                            error_message=failure_message,
                            step=failure_step,
                            system=_failure_system(exc, default="evaluation"),
                            provider=(_failure_provider(exc) or _route_provider_for_step(geo, failure_step)),
                        )
                        if log_trace:
                            _log.error("Bulk destination failed: %s", failure_message, exc_info=True)
                        _log_destination_failure_context(
                            phase="exact",
                            origin_pt=origin_pt,
                            origin_port=origin_port,
                            item=item,
                            status=failure_status,
                            error_message=failure_message,
                            geo=geo,
                        )
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=item.scenario_key,
                            input_origin=item.scenario_payload["input_origin"],
                            input_destiny=item.scenario_payload["input_destiny"],
                            origin_location_id=origin_pt.get("location_id"),
                            destination_location_id=(None if item.point is None else item.point.get("location_id")),
                            origin_name=origin_pt["label"],
                            destiny_name=item.destiny_name or item.destiny_input,
                            truck_key=truck_key,
                            ors_profile=profile,
                            cargo_t=cargo_t,
                            vessel_class=vessel_class,
                            include_hoteling=include_hoteling,
                            hoteling_hours_per_call=hoteling_hours_per_call,
                            port_calls=port_calls,
                            include_port_ops=include_port_ops,
                            port_moves_per_call=port_moves_per_call,
                            cargo_teu=cargo_teu,
                            t_per_teu_default=t_per_teu_default,
                            allocation_mode=allocation_mode,
                            allocation_load_factor=allocation_load_factor,
                            full_call_mode=full_call_mode,
                            port_ops_scenario=port_ops_scenario,
                            status=failure_status,
                            error_message=failure_message,
                            geo=geo,
                            is_approximation=False,
                            failure_step=item.failure_step,
                            failed_leg=item.failed_leg,
                            failure_reason=item.failure_reason,
                            failure_detail=item.failure_detail or failure_message,
                            retryable=item.retryable,
                            failure_provider=item.failure_provider,
                            failure_provider_operation=item.failure_provider_operation,
                        )
                        persistence.add(bulk_row, run_row)
                        summary_rows.append(
                            _build_failure_summary_row(
                                str(run_id),
                                origin_pt["label"],
                                item.destiny_input,
                                item.destiny_name or item.destiny_input,
                                destination_lat=(None if item.point is None else item.point.get("lat")),
                                destination_lon=(None if item.point is None else item.point.get("lon")),
                                port_origin_name=(None if origin_port is None else origin_port.get("name")),
                                port_destiny_name=(None if item.port_destiny is None else item.port_destiny.get("name")),
                                status=failure_status,
                                error_message=failure_message,
                                failure_detail=item.failure_detail or failure_message,
                                failure_step=item.failure_step,
                                failure_system=item.failure_system,
                                failure_provider=item.failure_provider,
                                failed_leg=item.failed_leg,
                                failure_reason=item.failure_reason,
                                retryable=item.retryable,
                                failure_provider_operation=item.failure_provider_operation,
                            )
                        )
                    finally:
                        _emit_progress(
                            progress_callback,
                            phase="progress",
                            pass_name="exact",
                            current=item.index,
                            total=len(work_items),
                            destination=item.destiny_input,
                            success_count=success_count,
                            fail_count=fail_count,
                            exact_success_count=exact_success_count,
                            approximated_success_count=approximated_success_count,
                            pending_approximations=len(pending_approximations),
                        )

            active_run_step = "persist_results"
            persistence.flush()

            if pending_approximations:
                active_run_step = "approximation_fallback"
                _log_step_banner("approximation_fallback", pending=len(pending_approximations))
                _emit_progress(
                    progress_callback,
                    phase="approximation_start",
                    current=0,
                    total=len(pending_approximations),
                    success_count=success_count,
                    fail_count=fail_count,
                    exact_success_count=exact_success_count,
                    approximated_success_count=approximated_success_count,
                    message="Phase 3/4 approximation fallback",
                )

            with perf.measure("approximation_pass_s"):
                for approx_index, pending in enumerate(pending_approximations, start=1):
                    try:
                        if not exact_references:
                            raise RuntimeError(
                                "Approximation fallback unavailable: no exact successful road routes were solved in this bulk run"
                            )
                        destiny_point = pending.geo.get("destiny", {})
                        reference = _select_nearest_exact_reference(destiny_point, exact_references)
                        if reference is None:
                            raise RuntimeError(
                                "Approximation fallback unavailable: destination coordinates are missing for nearest-reference selection"
                            )
                        estimated_distance_km, approximation_meta = _estimate_road_distance_from_reference(
                            origin_pt,
                            destiny_point,
                            reference,
                        )
                        approx_geo = _build_approximated_geometry(pending.geo, estimated_distance_km)
                        res, flat = _evaluate_and_flatten(
                            approx_geo,
                            origin_name=origin_pt["label"],
                            destiny_name=pending.destiny_name,
                            evaluation_kwargs=evaluation_kwargs,
                        )
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=pending.scenario_key,
                            input_origin=pending.scenario_payload["input_origin"],
                            input_destiny=pending.scenario_payload["input_destiny"],
                            origin_location_id=origin_pt.get("location_id"),
                            destination_location_id=pending.geo.get("destiny", {}).get("location_id"),
                            origin_name=origin_pt["label"],
                            destiny_name=pending.destiny_name,
                            truck_key=truck_key,
                            ors_profile=profile,
                            cargo_t=cargo_t,
                            vessel_class=vessel_class,
                            include_hoteling=include_hoteling,
                            hoteling_hours_per_call=hoteling_hours_per_call,
                            port_calls=port_calls,
                            include_port_ops=include_port_ops,
                            port_moves_per_call=port_moves_per_call,
                            cargo_teu=cargo_teu,
                            t_per_teu_default=t_per_teu_default,
                            allocation_mode=allocation_mode,
                            allocation_load_factor=allocation_load_factor,
                            full_call_mode=full_call_mode,
                            port_ops_scenario=port_ops_scenario,
                            status="ok",
                            geo=approx_geo,
                            res=res,
                            flat=flat,
                            is_approximation=True,
                            route_source=approximation_meta.route_source,
                            approximation_reference_destiny=approximation_meta.reference_destiny,
                            approximation_reference_distance_km=approximation_meta.reference_distance_km,
                            approximation_delta_straight_line_km=approximation_meta.delta_straight_line_km,
                            approximation_notes=approximation_meta.notes,
                        )
                        persistence.add(bulk_row, run_row)
                        summary_rows.append(
                            _build_success_summary_row(
                                str(run_id),
                                origin_pt["label"],
                                pending.destiny_input,
                                approx_geo,
                                res,
                                flat,
                                is_approximation=True,
                                route_source=approximation_meta.route_source,
                                approximation_meta=approximation_meta,
                            )
                        )
                        success_count += 1
                        approximated_success_count += 1
                    except Exception as exc:
                        fail_count += 1
                        unresolved_fail_count += 1
                        approximation_failure = str(exc).strip() or "Approximation fallback failed"
                        combined_error = f"{pending.error_message}; {approximation_failure}"
                        failure_provider = _failure_provider(exc) or pending.failure_provider
                        approximation_diagnostic = build_failure_diagnostic(
                            status=pending.failure_status,
                            step="approximation_fallback",
                            failure_detail=combined_error,
                            system="approximation",
                            provider=failure_provider,
                            provider_operation="approximation_fallback",
                            raw_input=pending.destiny_input,
                        )
                        _log_destination_failure_context(
                            phase="approximation",
                            origin_pt=origin_pt,
                            origin_port=origin_port,
                            item=DestinationWorkItem(
                                index=pending.index,
                                destiny_input=pending.destiny_input,
                                normalized_input=pending.destiny_input,
                                scenario_key=pending.scenario_key,
                                scenario_payload=pending.scenario_payload,
                                destiny_name=pending.destiny_name,
                                point=pending.geo.get("destiny"),
                                point_source=pending.geo.get("destiny", {}).get("source"),
                                port_destiny=pending.geo.get("port_destiny"),
                                geo=pending.geo,
                                failure_step=approximation_diagnostic.failed_step,
                                failure_system="approximation",
                                failure_provider=approximation_diagnostic.provider,
                                failed_leg=approximation_diagnostic.failed_leg,
                                failure_reason=approximation_diagnostic.failure_reason,
                                failure_detail=approximation_diagnostic.failure_detail,
                                retryable=approximation_diagnostic.retryable,
                                failure_provider_operation=approximation_diagnostic.provider_operation,
                            ),
                            status=pending.failure_status,
                            error_message=combined_error,
                            geo=pending.geo,
                        )
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=pending.scenario_key,
                            input_origin=pending.scenario_payload["input_origin"],
                            input_destiny=pending.scenario_payload["input_destiny"],
                            origin_location_id=origin_pt.get("location_id"),
                            destination_location_id=pending.geo.get("destiny", {}).get("location_id"),
                            origin_name=origin_pt["label"],
                            destiny_name=pending.destiny_name,
                            truck_key=truck_key,
                            ors_profile=profile,
                            cargo_t=cargo_t,
                            vessel_class=vessel_class,
                            include_hoteling=include_hoteling,
                            hoteling_hours_per_call=hoteling_hours_per_call,
                            port_calls=port_calls,
                            include_port_ops=include_port_ops,
                            port_moves_per_call=port_moves_per_call,
                            cargo_teu=cargo_teu,
                            t_per_teu_default=t_per_teu_default,
                            allocation_mode=allocation_mode,
                            allocation_load_factor=allocation_load_factor,
                            full_call_mode=full_call_mode,
                            port_ops_scenario=port_ops_scenario,
                            status=pending.failure_status,
                            error_message=combined_error,
                            geo=pending.geo,
                            approximation_notes=approximation_failure,
                            failure_step=approximation_diagnostic.failed_step,
                            failed_leg=approximation_diagnostic.failed_leg,
                            failure_reason=approximation_diagnostic.failure_reason,
                            failure_detail=approximation_diagnostic.failure_detail,
                            retryable=approximation_diagnostic.retryable,
                            failure_provider=approximation_diagnostic.provider,
                            failure_provider_operation=approximation_diagnostic.provider_operation,
                        )
                        persistence.add(bulk_row, run_row)
                        summary_rows.append(
                            _build_failure_summary_row(
                                str(run_id),
                                origin_pt["label"],
                                pending.destiny_input,
                                pending.destiny_name,
                                destination_lat=pending.geo.get("destiny", {}).get("lat"),
                                destination_lon=pending.geo.get("destiny", {}).get("lon"),
                                port_origin_name=(None if origin_port is None else origin_port.get("name")),
                                port_destiny_name=pending.geo.get("port_destiny", {}).get("name"),
                                status=pending.failure_status,
                                error_message=combined_error,
                                approximation_notes=approximation_failure,
                                is_approximation=True,
                                failure_detail=approximation_diagnostic.failure_detail,
                                failure_step=approximation_diagnostic.failed_step,
                                failure_system="approximation",
                                failure_provider=approximation_diagnostic.provider,
                                failed_leg=approximation_diagnostic.failed_leg,
                                failure_reason=approximation_diagnostic.failure_reason,
                                retryable=approximation_diagnostic.retryable,
                                failure_provider_operation=approximation_diagnostic.provider_operation,
                            )
                        )
                    finally:
                        _emit_progress(
                            progress_callback,
                            phase="progress",
                            pass_name="approximation",
                            current=approx_index,
                            total=len(pending_approximations),
                            destination=pending.destiny_input,
                            success_count=success_count,
                            fail_count=fail_count,
                            exact_success_count=exact_success_count,
                            approximated_success_count=approximated_success_count,
                        )

            active_run_step = "persist_results"
            persistence.flush()

            duration = time.perf_counter() - started_global
            perf.add_duration("total_run_s", duration)
            active_run_step = "finish_bulk_run"
            _log_step_banner("finish_bulk_run", run_id=run_id, status="completed")
            try:
                perf.incr("db_write_ops")
                with perf.measure("db_write_s"):
                    finish_bulk_run(
                        conn,
                        run_id=str(run_id),
                        status="completed",
                        success_count=success_count,
                        fail_count=fail_count,
                        duration_s=duration,
                        error_message=None,
                        table_name=runs_table,
                    )
                    conn.commit()
            except Exception as exc:
                raise _BulkStepError(
                    step="finish_bulk_run",
                    system="database",
                    provider="postgres",
                    error=exc,
                ) from exc
    except Exception as exc:
        duration = time.perf_counter() - started_global
        perf.add_duration("total_run_s", duration)
        _log.error(
            "Bulk run failed step=%s step_label=%s system=%s provider=%s error=%s",
            _failure_step(exc, default=active_run_step),
            _step_label(_failure_step(exc, default=active_run_step)),
            _failure_system(exc, default="application"),
            _failure_provider(exc) or "<unknown>",
            str(exc).strip() or exc.__class__.__name__,
        )
        if run_id is not None:
            with db_session(resolved_db_path) as conn:
                try:
                    perf.incr("db_write_ops")
                    with perf.measure("db_write_s"):
                        finish_bulk_run(
                            conn,
                            run_id=str(run_id),
                            status="failed",
                            success_count=success_count,
                            fail_count=fail_count,
                            duration_s=duration,
                            error_message=str(exc),
                            table_name=runs_table,
                        )
                        conn.commit()
                except Exception as finish_exc:
                    _log.error("Bulk run failure status persistence failed: %s", finish_exc)
        _emit_progress(
            progress_callback,
            phase="error",
            current=success_count + fail_count,
            total=len(shuffled_destinations),
            success_count=success_count,
            fail_count=fail_count,
            exact_success_count=exact_success_count,
            approximated_success_count=approximated_success_count,
            message=str(exc),
        )
        if hasattr(ors, "set_cooldown_callback"):
            ors.set_cooldown_callback(previous_cooldown_callback)
        raise

    duration = time.perf_counter() - started_global
    perf.add_duration("total_run_s", duration)
    _emit_progress(
        progress_callback,
        phase="complete",
        current=len(shuffled_destinations),
        total=len(shuffled_destinations),
        success_count=success_count,
        fail_count=fail_count,
        exact_success_count=exact_success_count,
        approximated_success_count=approximated_success_count,
        unresolved_fail_count=unresolved_fail_count,
        duration_s=duration,
        run_id=run_id,
        shuffle_seed_used=shuffle_seed_used,
        message="Phase 4/4 persistence complete",
    )
    if hasattr(ors, "set_cooldown_callback"):
        ors.set_cooldown_callback(previous_cooldown_callback)
    return _finalize_bulk_outcome(
        ors=ors,
        perf=perf,
        summary_rows=summary_rows,
        success_count=success_count,
        fail_count=fail_count,
        exact_success_count=exact_success_count,
        approximated_success_count=approximated_success_count,
        unresolved_fail_count=unresolved_fail_count,
        duration=duration,
        run_id=run_id,
        selector_hash_value=selector_hash_value,
        shuffle_seed_used=shuffle_seed_used,
        requested_destination_count=requested_destination_count,
        unique_destination_count=len(shuffled_destinations),
        max_geocode_workers=max_geocode_workers,
        max_route_workers=max_route_workers,
    )
