from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.infra.database_manager import (
    db_session,
    find_place_point,
    finish_bulk_run,
    list_cached_place_points,
    list_route_place_points,
    start_bulk_run,
    upsert_place_points,
    upsert_runs,
)
from modules.infra.log_manager import get_logger
from modules.multimodal.builder import build_path_geometry_from_resolved, build_port_node, load_routing_assets
from modules.multimodal.bulk import (
    BulkPerformanceTracker,
    BulkPersistenceBuffer,
    DestinationWorkItem,
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
    max_geocode_workers: int = 4,
    max_route_workers: int = 8,
    persist_batch_size: int = 64,
) -> Dict[str, Any]:
    deduped_destinations = _dedupe_preserve_order(dest_list)
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

    started_global = time.perf_counter()
    ors, ports, sea_matrix, resolved_db_path = load_routing_assets(db_path=db_path)
    if hasattr(ors, "reset_metrics"):
        ors.reset_metrics()

    origin_input_norm = normalize_bulk_place_input(origin)
    run_selector = _build_run_selector(
        origin_input=origin_input_norm,
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

    _log.info(
        (
            "Starting staged bulk evaluation: origin=%r destinations=%d destination_set=%s "
            "shuffle=%s shuffle_seed=%s approximation_fallback=%s geocode_workers=%d route_workers=%d batch_size=%d"
        ),
        origin,
        len(shuffled_destinations),
        destination_set_id,
        shuffle_destinations,
        (shuffle_seed_used if shuffle_seed_used is not None else "disabled"),
        approximation_fallback,
        int(max_geocode_workers),
        int(max_route_workers),
        int(persist_batch_size),
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

    def _flush_point_rows(conn: Any, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
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

    def _flush_route_rows(conn: Any, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        perf.incr("db_write_ops")
        with perf.measure("db_write_s"):
            upsert_runs(conn, rows=rows)
            conn.commit()
        perf.incr("route_cache_rows_persisted", len(rows))
        rows.clear()

    try:
        with db_session(resolved_db_path) as conn:
            nearest_port_memo = NearestPortMemo(ports)
            point_rows_to_persist: list[Dict[str, Any]] = []

            with perf.measure("bootstrap_s"):
                perf.incr("db_read_ops")
                with perf.measure("db_read_s"):
                    origin_cached = find_place_point(conn, place=origin_input_norm)
                if origin_cached:
                    origin_pt = _point_from_cached_record(origin_cached)
                    perf.incr("origin_cache_hits")
                else:
                    perf.incr("origin_cache_misses")
                    with perf.measure("origin_geocode_s"):
                        origin_pt = _resolve_point_without_db(origin, ors)
                    if not origin_pt:
                        raise RuntimeError(f"Failed to resolve bulk origin: {origin}")
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

                origin_port = nearest_port_memo.resolve(origin_pt, perf)
                origin_port_node = build_port_node(origin_port)
                route_coordinator = RouteRequestCoordinator(
                    ors,
                    profile=profile,
                    overwrite=overwrite_road,
                    perf=perf,
                )
                first_mile_spec = RouteRequestSpec(
                    leg_name="first_mile",
                    origin=origin_pt,
                    destiny=origin_port_node,
                    profile=profile,
                )
                route_coordinator.prime(conn, [first_mile_spec])
                first_mile_leg = route_coordinator.resolve(first_mile_spec)
                _require_distance(first_mile_leg, "first_mile")
                _flush_route_rows(conn, route_coordinator.drain_pending_rows())
                _flush_point_rows(conn, point_rows_to_persist)

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

                perf.incr("db_write_ops")
                with perf.measure("db_write_s"):
                    run_id = start_bulk_run(
                        conn,
                        selector=run_selector,
                        origin_name=origin_pt["label"],
                        input_origin=origin_input_norm,
                        destination_count=len(shuffled_destinations),
                        table_name=runs_table,
                    )
                    conn.commit()

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

            _emit_progress(
                progress_callback,
                phase="resolution_start",
                current=0,
                total=len(work_items),
                message="Phase 1/4 destination normalization and resolution",
            )

            perf.incr("db_read_ops")
            with perf.measure("db_read_s"):
                cached_points = list_cached_place_points(conn, places=[item.normalized_input for item in work_items])
            unresolved_keys = [
                item.normalized_input
                for item in work_items
                if item.normalized_input.casefold() not in cached_points
            ]
            route_point_rows: dict[str, Dict[str, Any]] = {}
            if unresolved_keys:
                perf.incr("db_read_ops")
                with perf.measure("db_read_s"):
                    route_point_rows = list_route_place_points(conn, places=unresolved_keys)

            for item in work_items:
                place_key = item.normalized_input.casefold()
                cached = cached_points.get(place_key)
                if cached is not None:
                    item.point = _point_from_cached_record(cached)
                    item.destiny_name = item.point["label"]
                    item.point_source = "place_cache"
                    perf.incr("destination_cache_hits")
                    continue
                cached = route_point_rows.get(place_key)
                if cached is not None:
                    item.point = _point_from_cached_record(cached)
                    item.destiny_name = item.point["label"]
                    item.point_source = "route_cache"
                    perf.incr("destination_cache_hits")
                    point_rows_to_persist.append(
                        {
                            "place": item.normalized_input,
                            "label": item.point["label"],
                            "lat": item.point["lat"],
                            "lon": item.point["lon"],
                            "uf": item.point.get("uf"),
                            "source": "route_cache",
                        }
                    )
                    continue
                perf.incr("destination_cache_misses")

            unresolved_items = [item for item in work_items if item.point is None]

            def _resolve_destination(item: DestinationWorkItem):
                started = time.perf_counter()
                try:
                    point = _resolve_point_without_db(item.destiny_input, ors)
                    return item, point, None, (time.perf_counter() - started)
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    return item, None, exc, (time.perf_counter() - started)

            if unresolved_items:
                workers = max(1, min(int(max_geocode_workers), len(unresolved_items)))
                with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bulk-geocode") as executor:
                    futures = [executor.submit(_resolve_destination, item) for item in unresolved_items]
                    completed = 0
                    for future in as_completed(futures):
                        item, point, error, duration_s = future.result()
                        perf.add_duration("destination_geocode_s", duration_s)
                        completed += 1
                        if error is not None:
                            item.failure_status = "geocode_failed"
                            item.error_message = str(error).strip() or f"Failed to resolve destination: {item.destiny_input}"
                        elif point is None:
                            item.failure_status = "geocode_failed"
                            item.error_message = f"Failed to resolve destination: {item.destiny_input}"
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

            _flush_point_rows(conn, point_rows_to_persist)

            geometry_items = [item for item in work_items if item.point is not None and item.failure_status is None]
            _emit_progress(
                progress_callback,
                phase="geometry_start",
                current=0,
                total=len(geometry_items),
                message="Phase 2/4 geometry and routing acquisition",
            )

            route_specs: list[RouteRequestSpec] = []
            for item in geometry_items:
                assert item.point is not None
                try:
                    item.port_destiny = nearest_port_memo.resolve(item.point, perf)
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    item.failure_status = "nearest_port_failed"
                    item.error_message = str(exc).strip() or "Nearest-port lookup failed"
                    continue
                route_specs.append(RouteRequestSpec("road_direct", origin_pt, item.point, profile))
                route_specs.append(RouteRequestSpec("last_mile", build_port_node(item.port_destiny), item.point, profile))
            routable_items = [
                item for item in geometry_items if item.failure_status is None and item.port_destiny is not None
            ]
            route_coordinator.prime(conn, route_specs)

            def _build_geometry(item: DestinationWorkItem):
                started = time.perf_counter()
                try:
                    assert item.point is not None
                    assert item.port_destiny is not None
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
                        route_resolver=lambda start, end, leg_name: route_coordinator.resolve(
                            RouteRequestSpec(leg_name=leg_name, origin=start, destiny=end, profile=profile)
                        ),
                    )
                    return item, geometry, None, (time.perf_counter() - started)
                except Exception as exc:  # pragma: no cover - defensive worker isolation
                    return item, None, exc, (time.perf_counter() - started)

            if routable_items:
                workers = max(1, min(int(max_route_workers), len(routable_items)))
                with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bulk-route") as executor:
                    futures = [executor.submit(_build_geometry, item) for item in routable_items]
                    completed = 0
                    for future in as_completed(futures):
                        item, geometry, error, duration_s = future.result()
                        perf.add_duration("geometry_acquisition_s", duration_s)
                        completed += 1
                        if error is not None:
                            item.failure_status = "geometry_failed"
                            item.error_message = str(error).strip() or "Geometry build failed"
                        elif not geometry or geometry.get("status") != "ok":
                            item.failure_status = "geometry_failed"
                            item.error_message = "Geometry build failed"
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

            _flush_route_rows(conn, route_coordinator.drain_pending_rows())

            persistence = BulkPersistenceBuffer(
                conn,
                results_table=results_table,
                run_results_table=run_results_table,
                batch_size=persist_batch_size,
                perf=perf,
            )

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
                            )
                            persistence.add(bulk_row, run_row)
                            summary_rows.append(
                                _build_failure_summary_row(
                                    item.destiny_input,
                                    item.destiny_name or item.destiny_input,
                                    status=failure_status,
                                    error_message=failure_message,
                                )
                            )
                            fail_count += 1
                            unresolved_fail_count += 1
                            continue
                        if not geo or geo.get("status") != "ok":
                            raise RuntimeError("Geometry build failed")
                        _require_distance(geo["last_mile"], "last_mile")
                        if geo["road_direct"].get("distance_km") is None:
                            if approximation_fallback:
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
                                    )
                                )
                                continue
                            raise RuntimeError("road_direct road distance is unavailable")
                        res, flat = _evaluate_and_flatten(
                            geo,
                            origin_name=origin_pt["label"],
                            destiny_name=item.destiny_name,
                            evaluation_kwargs=evaluation_kwargs,
                        )
                        route_source = _route_source_for_result(geo, is_approximation=False)
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=item.scenario_key,
                            input_origin=item.scenario_payload["input_origin"],
                            input_destiny=item.scenario_payload["input_destiny"],
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
                        if log_trace:
                            _log.error("Bulk destination failed: %s", failure_message, exc_info=True)
                        else:
                            _log.warning("Bulk destination skipped: %s (%s)", item.destiny_input, failure_message)
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=item.scenario_key,
                            input_origin=item.scenario_payload["input_origin"],
                            input_destiny=item.scenario_payload["input_destiny"],
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
                        )
                        persistence.add(bulk_row, run_row)
                        summary_rows.append(
                            _build_failure_summary_row(
                                item.destiny_input,
                                item.destiny_name or item.destiny_input,
                                status=failure_status,
                                error_message=failure_message,
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

            persistence.flush()

            if pending_approximations:
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
                        bulk_row, run_row = _build_bulk_outcome_rows(
                            run_id=str(run_id),
                            destination_set_id=destination_set_id,
                            scenario_key=pending.scenario_key,
                            input_origin=pending.scenario_payload["input_origin"],
                            input_destiny=pending.scenario_payload["input_destiny"],
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
                        )
                        persistence.add(bulk_row, run_row)
                        summary_rows.append(
                            _build_failure_summary_row(
                                pending.destiny_input,
                                pending.destiny_name,
                                status=pending.failure_status,
                                error_message=combined_error,
                                approximation_notes=approximation_failure,
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

            persistence.flush()

            duration = time.perf_counter() - started_global
            perf.add_duration("total_run_s", duration)
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
        duration = time.perf_counter() - started_global
        perf.add_duration("total_run_s", duration)
        if run_id is not None:
            with db_session(resolved_db_path) as conn:
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
        raise

    duration = time.perf_counter() - started_global
    perf.add_duration("total_run_s", duration)
    provider_calls = ors.metrics_snapshot() if hasattr(ors, "metrics_snapshot") else {}
    performance = perf.snapshot()
    performance["provider_calls"] = provider_calls

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
    _log.info(
        (
            "Bulk performance summary run_id=%s bootstrap=%.2fs normalize=%.2fs geocode=%.2fs geometry=%.2fs "
            "exact=%.2fs approx=%.2fs db_read=%.2fs db_write=%.2fs direct_hit=%.0f direct_miss=%.0f "
            "last_hit=%.0f last_miss=%.0f providers=%s"
        ),
        run_id,
        performance["timings_s"].get("bootstrap_s", 0.0),
        performance["timings_s"].get("destination_normalization_s", 0.0),
        performance["timings_s"].get("destination_geocode_s", 0.0),
        performance["timings_s"].get("geometry_acquisition_s", 0.0),
        performance["timings_s"].get("exact_pass_s", 0.0),
        performance["timings_s"].get("approximation_pass_s", 0.0),
        performance["timings_s"].get("db_read_s", 0.0),
        performance["timings_s"].get("db_write_s", 0.0),
        performance["counts"].get("road_direct_cache_hits", 0.0),
        performance["counts"].get("road_direct_cache_misses", 0.0),
        performance["counts"].get("last_mile_cache_hits", 0.0),
        performance["counts"].get("last_mile_cache_misses", 0.0),
        provider_calls,
    )
    _log.info(
        (
            "Bulk evaluation complete: total=%d exact_success=%d approximated_success=%d "
            "unresolved_failures=%d duration_s=%.2f run_id=%s"
        ),
        len(shuffled_destinations),
        exact_success_count,
        approximated_success_count,
        unresolved_fail_count,
        duration,
        run_id,
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
        "shuffle_seed_used": shuffle_seed_used,
        "performance": performance,
    }
