from __future__ import annotations

import copy
import random
import time
import threading
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from modules.addressing.resolver import resolve_point
from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.database_manager import (
    DEFAULT_BULK_RESULTS_TABLE,
    DEFAULT_BULK_RUN_RESULTS_TABLE,
    DEFAULT_BULK_RUNS_TABLE,
    BulkRunSelector,
    db_session,
    finish_bulk_run,
    find_place_point,
    insert_bulk_run_result,
    insert_bulk_run_results,
    list_bulk_result_input_destiny_keys,
    list_cached_place_points,
    list_route_place_points,
    list_runs_by_coord_keys,
    list_runs_by_label_keys,
    start_bulk_run,
    upsert_bulk_result,
    upsert_bulk_results,
    upsert_place_points,
    upsert_runs,
)
from modules.infra.db.locations import coord_lookup_key
from modules.infra.log_manager import get_logger
from modules.multimodal.builder import (
    build_path_geometry_from_resolved,
    build_port_node,
    load_routing_assets,
    resolve_point_for_geometry,
)
from modules.multimodal.evaluator import evaluate_path, prepare_evaluation_context
from modules.multimodal.persistence import flatten_evaluation_for_db
from modules.multimodal.scenario_keys import build_bulk_scenario_key, normalize_bulk_place_input
from modules.ports.ports_nearest import find_nearest_port, haversine_km
from modules.road.router import ORSClient, _calculate_route

_log = get_logger(__name__)
ProgressCallback = Callable[[Dict[str, Any]], None]

_APPROX_ROUTE_SOURCE = "nearest_exact_delta_straight_line"
_MIN_APPROX_ROAD_DISTANCE_KM = 1.0
_DEFAULT_RUNTIME_PROFILE = "driving-car"
_HGV_PROFILE = "driving-hgv"
_RETRYABLE_FAILURE_STATUSES = frozenset({"rate_limited", "timeout", "network_error"})
_TERMINAL_FAILURE_STATUSES = frozenset(
    {
        "geocode_failed",
        "no_road_route",
        "last_mile_no_road_route",
        "nearest_port_failed",
        "geometry_failed",
        "evaluation_failed",
        "error",
    }
)


@dataclass(frozen=True)
class ExactRoadReference:
    destiny_name: str
    destiny_lat: float
    destiny_lon: float
    road_distance_km: float


@dataclass(frozen=True)
class ApproximationMetadata:
    route_source: str
    reference_destiny: str
    reference_distance_km: float
    delta_straight_line_km: float
    notes: str


@dataclass(frozen=True)
class PendingApproximation:
    index: int
    destiny_input: str
    destiny_name: str
    scenario_key: str
    scenario_payload: Dict[str, Any]
    geo: Dict[str, Any]
    failure_status: str
    error_message: str
    failure_step: Optional[str] = None
    failure_system: Optional[str] = None
    failure_provider: Optional[str] = None


@dataclass
class DestinationWorkItem:
    index: int
    destiny_input: str
    normalized_input: str
    scenario_key: str
    scenario_payload: Dict[str, Any]
    destiny_name: str = ""
    point: Optional[Dict[str, Any]] = None
    point_source: Optional[str] = None
    port_destiny: Optional[Dict[str, Any]] = None
    geo: Optional[Dict[str, Any]] = None
    failure_status: Optional[str] = None
    error_message: Optional[str] = None
    failure_step: Optional[str] = None
    failure_system: Optional[str] = None
    failure_provider: Optional[str] = None


@dataclass(frozen=True)
class RouteRequestSpec:
    leg_name: str
    origin: Dict[str, Any]
    destiny: Dict[str, Any]
    profile: str

    @property
    def label_key(self) -> tuple[str, str, str]:
        return (
            ascii_place_key(self.origin.get("label")),
            ascii_place_key(self.destiny.get("label")),
            str(self.profile).strip().lower() or _DEFAULT_RUNTIME_PROFILE,
        )

    @property
    def coord_lookup_key(self) -> Optional[tuple[float, float, float, float, str]]:
        origin_lat = self.origin.get("lat")
        origin_lon = self.origin.get("lon")
        destiny_lat = self.destiny.get("lat")
        destiny_lon = self.destiny.get("lon")
        if None in (origin_lat, origin_lon, destiny_lat, destiny_lon):
            return None
        return (
            float(origin_lat),
            float(origin_lon),
            float(destiny_lat),
            float(destiny_lon),
            str(self.profile).strip().lower() or _DEFAULT_RUNTIME_PROFILE,
        )

    @property
    def inflight_key(self) -> tuple[Any, ...]:
        if self.coord_lookup_key is not None:
            return ("coord", *self.coord_lookup_key)
        return ("label", *self.label_key)


@dataclass
class BulkPerformanceTracker:
    durations_s: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    counters: Dict[str, float] = field(default_factory=lambda: defaultdict(float))

    @contextmanager
    def measure(self, key: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.durations_s[key] += time.perf_counter() - started

    def add_duration(self, key: str, duration_s: float) -> None:
        self.durations_s[key] += float(duration_s)

    def incr(self, key: str, amount: float = 1.0) -> None:
        self.counters[key] += float(amount)

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        return {
            "timings_s": {key: round(float(value), 6) for key, value in sorted(self.durations_s.items())},
            "counts": {key: float(value) for key, value in sorted(self.counters.items())},
        }


class NearestPortMemo:
    def __init__(self, ports: list[Dict[str, Any]], *, precision: int = 4) -> None:
        self._ports = ports
        self._precision = precision
        self._cache: dict[tuple[float, float], Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def resolve(self, point: Dict[str, Any], perf: BulkPerformanceTracker) -> Dict[str, Any]:
        key = (
            round(float(point["lat"]), self._precision),
            round(float(point["lon"]), self._precision),
        )
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            perf.incr("nearest_port_cache_hits")
            return cached

        perf.incr("nearest_port_cache_misses")
        with perf.measure("nearest_port_s"):
            resolved = find_nearest_port(float(point["lat"]), float(point["lon"]), self._ports)
        with self._lock:
            self._cache[key] = resolved
        return resolved


def _cache_leg_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    requested_profile = str(row.get("profile_requested") or _DEFAULT_RUNTIME_PROFILE)
    return {
        "id": row.get("id"),
        "route_id": row.get("id"),
        "origin_name": row["origin"],
        "destiny_name": row["destiny"],
        "distance_km": row.get("distance_km"),
        "duration_s": row.get("duration_s"),
        "is_hgv": row.get("is_hgv"),
        "origin_location_id": row.get("origin_location_id"),
        "destiny_location_id": row.get("destiny_location_id"),
        "profile_requested": requested_profile,
        "profile_used": row.get("profile_used") or requested_profile,
        "cached": True,
        "source": "cache",
        "provider": row.get("source") or "ors",
    }


class RouteRequestCoordinator:
    def __init__(
        self,
        ors: ORSClient,
        *,
        profile: str,
        overwrite: bool,
        perf: BulkPerformanceTracker,
    ) -> None:
        self._ors = ors
        self._profile = str(profile).strip().lower() or _DEFAULT_RUNTIME_PROFILE
        self._overwrite = bool(overwrite)
        self._perf = perf
        self._label_cache: dict[tuple[str, str, str], Dict[str, Any]] = {}
        self._coord_cache: dict[tuple[str, str, str], Dict[str, Any]] = {}
        self._pending_rows: list[Dict[str, Any]] = []
        self._inflight: dict[tuple[Any, ...], Future] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _coord_cache_key(spec: RouteRequestSpec) -> Optional[tuple[str, str, str]]:
        coord_key = spec.coord_lookup_key
        if coord_key is None:
            return None
        origin_key = coord_lookup_key(coord_key[0], coord_key[1])
        destiny_key = coord_lookup_key(coord_key[2], coord_key[3])
        if origin_key is None or destiny_key is None:
            return None
        return (
            str(coord_key[4]).strip().lower() or _DEFAULT_RUNTIME_PROFILE,
            f"{origin_key[0]},{origin_key[1]}",
            f"{destiny_key[0]},{destiny_key[1]}",
        )

    def prime(self, conn: Any, specs: Iterable[RouteRequestSpec]) -> None:
        if self._overwrite:
            return
        unique_specs = list({spec.inflight_key: spec for spec in specs}.values())
        label_keys = [spec.label_key for spec in unique_specs]
        coord_keys = [spec.coord_lookup_key for spec in unique_specs if spec.coord_lookup_key is not None]

        if label_keys:
            self._perf.incr("db_read_ops")
            with self._perf.measure("db_read_s"):
                cached_by_label = list_runs_by_label_keys(conn, keys=label_keys)
            self._label_cache.update(cached_by_label)
        if coord_keys:
            self._perf.incr("db_read_ops")
            with self._perf.measure("db_read_s"):
                cached_by_coord = list_runs_by_coord_keys(conn, keys=coord_keys)
            self._coord_cache.update(cached_by_coord)

    def resolve(self, spec: RouteRequestSpec) -> Dict[str, Any]:
        if not self._overwrite:
            cached = self._lookup(spec)
            if cached is not None:
                self._perf.incr(f"{spec.leg_name}_cache_hits")
                return cached

        self._perf.incr(f"{spec.leg_name}_cache_misses")
        owner = False
        with self._lock:
            cached = None if self._overwrite else self._lookup(spec)
            if cached is not None:
                self._perf.incr(f"{spec.leg_name}_cache_hits")
                return cached
            future = self._inflight.get(spec.inflight_key)
            if future is None:
                future = Future()
                self._inflight[spec.inflight_key] = future
                owner = True

        if not owner:
            return future.result()

        try:
            with self._perf.measure(f"{spec.leg_name}_provider_s"):
                profile_used, distance_km, route_source = _calculate_route(
                    self._ors,
                    spec.origin,
                    spec.destiny,
                    self._profile,
                    False,
                )
            leg = {
                "origin_name": spec.origin.get("label"),
                "destiny_name": spec.destiny.get("label"),
                "distance_km": distance_km,
                "is_hgv": (None if distance_km is None or profile_used is None else profile_used == _HGV_PROFILE),
                "profile_requested": self._profile,
                "profile_used": profile_used,
                "cached": False,
                "source": route_source or "ors",
                "provider": route_source or "ors",
            }
            if distance_km is not None:
                row = {
                    "origin": str(spec.origin.get("label") or ""),
                    "origin_lat": spec.origin.get("lat"),
                    "origin_lon": spec.origin.get("lon"),
                    "destiny": str(spec.destiny.get("label") or ""),
                    "destiny_lat": spec.destiny.get("lat"),
                    "destiny_lon": spec.destiny.get("lon"),
                    "distance_km": distance_km,
                    "profile_requested": self._profile,
                    "profile_used": profile_used,
                    "source": route_source or "ors",
                    "lookup_mode": "coords",
                    "is_hgv": leg["is_hgv"],
                }
                with self._lock:
                    self._label_cache[spec.label_key] = {
                        "origin": row["origin"],
                        "destiny": row["destiny"],
                        "distance_km": row["distance_km"],
                        "is_hgv": row["is_hgv"],
                        "origin_lat": row["origin_lat"],
                        "origin_lon": row["origin_lon"],
                        "destiny_lat": row["destiny_lat"],
                        "destiny_lon": row["destiny_lon"],
                        "profile_requested": row["profile_requested"],
                        "profile_used": row["profile_used"],
                        "source": row["source"],
                    }
                    coord_cache_key = self._coord_cache_key(spec)
                    if coord_cache_key is not None:
                        self._coord_cache[coord_cache_key] = self._label_cache[spec.label_key]
                    self._pending_rows.append(row)
            future.set_result(leg)
            return leg
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._inflight.pop(spec.inflight_key, None)

    def drain_pending_rows(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = list(self._pending_rows)
            self._pending_rows.clear()
        return rows

    def _lookup(self, spec: RouteRequestSpec) -> Optional[Dict[str, Any]]:
        row = None
        coord_cache_key = self._coord_cache_key(spec)
        if coord_cache_key is not None:
            row = self._coord_cache.get(coord_cache_key)
        if row is None:
            row = self._label_cache.get(spec.label_key)
        if row is None:
            return None
        return _cache_leg_from_row(row)


class BulkPersistenceBuffer:
    def __init__(
        self,
        conn: Any,
        *,
        results_table: str,
        run_results_table: str,
        batch_size: int,
        perf: BulkPerformanceTracker,
    ) -> None:
        self._conn = conn
        self._results_table = results_table
        self._run_results_table = run_results_table
        self._batch_size = max(int(batch_size), 1)
        self._perf = perf
        self._bulk_rows: list[Dict[str, Any]] = []
        self._run_rows: list[Dict[str, Any]] = []

    def add(self, bulk_row: Dict[str, Any], run_row: Dict[str, Any]) -> None:
        self._bulk_rows.append(bulk_row)
        self._run_rows.append(run_row)
        if len(self._bulk_rows) >= self._batch_size:
            self.flush()

    def flush(self) -> None:
        if not self._bulk_rows:
            return
        if hasattr(self._conn, "ping") and hasattr(self._conn, "reconnect"):
            try:
                self._conn.ping()
            except Exception as exc:
                _log.warning("Bulk persistence DB connection lost before flush; reconnecting: %s", exc)
                self._conn.reconnect()
        self._perf.incr("db_write_ops")
        with self._perf.measure("db_write_s"):
            if self._results_table != self._run_results_table:
                upsert_bulk_results(self._conn, rows=self._bulk_rows, table_name=self._results_table)
            insert_bulk_run_results(self._conn, rows=self._run_rows, table_name=self._run_results_table)
            self._conn.commit()
        self._perf.incr("bulk_rows_persisted", len(self._bulk_rows))
        self._bulk_rows.clear()
        self._run_rows.clear()

def load_destinations(path: Path) -> List[str]:
    """Read clean non-empty destination lines from a text file."""
    if not path.exists():
        raise FileNotFoundError(f"Destinations file not found: {path}")

    destinations: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = str(line).strip().lstrip("\ufeff")
            if text and not text.startswith("#"):
                destinations.append(text)
    return destinations


def _dedupe_preserve_order(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    duplicates = 0

    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = normalize_bulk_place_input(text).casefold()
        if not key:
            continue
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        ordered.append(text)

    if duplicates:
        _log.warning("Skipped %d duplicated destination entries in bulk input.", duplicates)

    return ordered


def _shuffle_destinations(
    values: Sequence[str],
    *,
    enabled: bool,
    seed: Optional[int],
) -> tuple[List[str], Optional[int]]:
    ordered = list(values)
    if not enabled:
        return ordered, None

    seed_used = int(seed) if seed is not None else random.SystemRandom().randrange(0, 2**32)
    if len(ordered) > 1:
        random.Random(seed_used).shuffle(ordered)
    return ordered, seed_used


def _require_distance(leg: Dict[str, Any], leg_name: str) -> None:
    if leg.get("distance_km") is None:
        raise RuntimeError(f"{leg_name} road distance is unavailable")


def _classify_failure(exc: Exception) -> tuple[str, str, bool]:
    """
    Classify expected per-destination failures so they are logged cleanly and
    persisted with a more useful status.
    """
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if any(token in lowered for token in ("quota", "rate limit", "too many requests", "429")):
        return "rate_limited", message, False
    if any(token in lowered for token in ("timed out", "timeout", "read timed out", "connect timeout")):
        return "timeout", message, False
    if any(
        token in lowered
        for token in (
            "communication failure",
            "connection aborted",
            "connection reset",
            "connection refused",
            "max retries exceeded",
            "temporary failure",
            "network is unreachable",
            "name resolution",
        )
    ):
        return "network_error", message, False
    if "last_mile road distance is unavailable" in lowered:
        return "last_mile_no_road_route", message, False
    if "road_direct road distance is unavailable" in lowered or "road distance is unavailable" in lowered:
        return "no_road_route", message, False
    if "failed to resolve destination" in lowered:
        return "geocode_failed", message, False
    if "nearest-port lookup failed" in lowered or "nearest port" in lowered:
        return "nearest_port_failed", message, False
    if "geometry build failed" in lowered:
        return "geometry_failed", message, False
    if "path evaluation failed" in lowered:
        return "evaluation_failed", message, False

    return "error", message, True


def bulk_failure_is_retryable(status: str) -> bool:
    return str(status or "").strip().lower() in _RETRYABLE_FAILURE_STATUSES


def _route_source_for_result(
    geo: Optional[Dict[str, Any]],
    *,
    is_approximation: bool,
) -> Optional[str]:
    if not isinstance(geo, dict):
        return None
    direct_leg = geo.get("road_direct", {})
    if not isinstance(direct_leg, dict):
        return None
    source = str(direct_leg.get("source") or "").strip()
    if not source:
        return None
    if is_approximation:
        return source
    if source == "api":
        return "ors_exact"
    if source == "cache":
        return "cache_exact"
    if source.endswith("_exact"):
        return source
    return f"{source}_exact"


def _build_success_summary_row(
    destiny_input: str,
    geo: Dict[str, Any],
    res: Dict[str, Any],
    flat: Dict[str, Any],
    *,
    is_approximation: bool,
    route_source: Optional[str],
    approximation_meta: Optional[ApproximationMetadata],
) -> Dict[str, Any]:
    inputs = res.get("inputs", {})
    comparison = res.get("comparison", {})

    return {
        "destiny_input": destiny_input,
        "destiny_name": geo["destiny"]["label"],
        "status": "ok",
        "is_approximation": bool(is_approximation),
        "route_source": route_source,
        "approximation_reference_destiny": (
            None if approximation_meta is None else approximation_meta.reference_destiny
        ),
        "approximation_reference_distance_km": (
            None if approximation_meta is None else approximation_meta.reference_distance_km
        ),
        "approximation_delta_straight_line_km": (
            None if approximation_meta is None else approximation_meta.delta_straight_line_km
        ),
        "approximation_notes": None if approximation_meta is None else approximation_meta.notes,
        "road_direct_source": geo["road_direct"].get("source"),
        "first_mile_source": geo["first_mile"].get("source"),
        "last_mile_source": geo["last_mile"].get("source"),
        "road_direct_profile_used": geo["road_direct"].get("profile_used"),
        "first_mile_profile_used": geo["first_mile"].get("profile_used"),
        "last_mile_profile_used": geo["last_mile"].get("profile_used"),
        "road_cost": flat.get("road_fuel_cost_r"),
        "mm_cost": flat.get("total_fuel_cost_r"),
        "delta_cost": flat.get("delta_cost_r"),
        "savings_pct": comparison.get("savings_pct"),
        "road_co2e": flat.get("road_co2e_kg"),
        "mm_co2e": flat.get("total_co2e_kg"),
        "diesel_price_source": inputs.get("diesel_price_source"),
        "port_ops_scenario": inputs.get("port_ops_scenario_resolved"),
        "allocation_mode_used": inputs.get("allocation_mode_used"),
    }


def _build_failure_summary_row(
    destiny_input: str,
    destiny_name: str,
    *,
    status: str,
    error_message: str,
    route_source: Optional[str] = None,
    approximation_notes: Optional[str] = None,
    is_approximation: bool = False,
    failure_step: Optional[str] = None,
    failure_system: Optional[str] = None,
    failure_provider: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "destiny_input": destiny_input,
        "destiny_name": destiny_name,
        "status": status,
        "is_approximation": bool(is_approximation),
        "route_source": route_source,
        "approximation_reference_destiny": None,
        "approximation_reference_distance_km": None,
        "approximation_delta_straight_line_km": None,
        "approximation_notes": approximation_notes,
        "failure_step": failure_step,
        "failure_system": failure_system,
        "failure_provider": failure_provider,
        "error_msg": error_message,
    }


def _build_run_selector(
    *,
    origin_location_id: Optional[int],
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
    destination_set_id: str,
) -> BulkRunSelector:
    return BulkRunSelector(
        origin_location_id=origin_location_id,
        cargo_t=float(cargo_t),
        truck_key=str(truck_key),
        ors_profile=str(profile),
        vessel_class=str(vessel_class),
        include_hoteling=bool(include_hoteling),
        hoteling_hours_per_call=float(hoteling_hours_per_call),
        port_calls=int(port_calls),
        include_port_ops=bool(include_port_ops),
        port_moves_per_call=(None if port_moves_per_call is None else float(port_moves_per_call)),
        cargo_teu=(None if cargo_teu is None else float(cargo_teu)),
        t_per_teu_default=float(t_per_teu_default),
        allocation_mode=allocation_mode,
        allocation_load_factor=float(allocation_load_factor),
        full_call_mode=bool(full_call_mode),
        port_ops_scenario=str(port_ops_scenario),
        destination_set_id=str(destination_set_id),
    )


def _emissions_savings_pct(flat: Dict[str, Any]) -> Optional[float]:
    road_co2e = float(flat.get("road_co2e_kg") or 0.0)
    multimodal_co2e = float(flat.get("total_co2e_kg") or 0.0)
    if road_co2e <= 0.0:
        return None
    return float((1 - (multimodal_co2e / road_co2e)) * 100.0)


def _emit_progress(progress_callback: Optional[ProgressCallback], **payload: Any) -> None:
    if progress_callback is None:
        return
    try:
        progress_callback(payload)
    except Exception as exc:
        _log.warning("Bulk progress callback failed: %s", exc)


def _point_coords(point: Optional[Dict[str, Any]]) -> Optional[tuple[float, float]]:
    if not isinstance(point, dict):
        return None
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def _point_from_cached_record(record: Dict[str, Any]) -> Dict[str, Any]:
    point = {
        "label": ascii_place_text(record.get("label")),
        "lat": float(record["lat"]),
        "lon": float(record["lon"]),
        "uf": record.get("uf"),
    }
    if record.get("location_id") is not None:
        point["location_id"] = int(record["location_id"])
    return point


def _point_from_result_record(record: Any) -> Optional[Dict[str, Any]]:
    destiny_lat = getattr(record, "destiny_lat", None)
    destiny_lon = getattr(record, "destiny_lon", None)
    if destiny_lat is None or destiny_lon is None:
        return None

    point = {
        "label": ascii_place_text(getattr(record, "destiny_name", None) or getattr(record, "input_destiny", None)),
        "lat": float(destiny_lat),
        "lon": float(destiny_lon),
        "uf": getattr(record, "destiny_uf", None),
    }
    destination_location_id = getattr(record, "destination_location_id", None)
    if destination_location_id is not None:
        point["location_id"] = int(destination_location_id)
    return point


def _resolve_point_without_db(value: Any, ors: ORSClient) -> Optional[Dict[str, Any]]:
    point = resolve_point(value, ors, _log)
    if not point:
        return None
    return {
        "label": ascii_place_text(point.label),
        "lat": float(point.lat),
        "lon": float(point.lon),
        "uf": point.uf,
    }


def _build_scenario_payload(
    *,
    origin_input: str,
    destiny_input: str,
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
) -> Dict[str, Any]:
    return {
        "input_origin": normalize_bulk_place_input(origin_input),
        "input_destiny": normalize_bulk_place_input(destiny_input),
        "cargo_t": float(cargo_t),
        "truck_key": str(truck_key),
        "ors_profile": str(profile),
        "vessel_class": str(vessel_class),
        "include_hoteling": bool(include_hoteling),
        "hoteling_hours_per_call": float(hoteling_hours_per_call),
        "port_calls": int(port_calls),
        "include_port_ops": bool(include_port_ops),
        "port_moves_per_call": port_moves_per_call,
        "cargo_teu": cargo_teu,
        "t_per_teu_default": float(t_per_teu_default),
        "allocation_mode": allocation_mode,
        "allocation_load_factor": float(allocation_load_factor),
        "full_call_mode": bool(full_call_mode),
        "port_ops_scenario": str(port_ops_scenario),
    }


def _make_exact_reference(geo: Dict[str, Any], flat: Dict[str, Any]) -> Optional[ExactRoadReference]:
    destiny = geo.get("destiny", {})
    coords = _point_coords(destiny)
    road_distance_km = flat.get("road_distance_km")
    if coords is None or road_distance_km is None:
        return None
    return ExactRoadReference(
        destiny_name=str(destiny.get("label") or geo.get("destiny_name") or ""),
        destiny_lat=coords[0],
        destiny_lon=coords[1],
        road_distance_km=float(road_distance_km),
    )


def _select_nearest_exact_reference(
    destiny_point: Dict[str, Any],
    exact_references: Sequence[ExactRoadReference],
) -> Optional[ExactRoadReference]:
    coords = _point_coords(destiny_point)
    if coords is None or not exact_references:
        return None
    lat, lon = coords
    return min(
        exact_references,
        key=lambda candidate: haversine_km(lat, lon, candidate.destiny_lat, candidate.destiny_lon),
    )


def _estimate_road_distance_from_reference(
    origin_point: Dict[str, Any],
    destiny_point: Dict[str, Any],
    reference: ExactRoadReference,
) -> tuple[float, ApproximationMetadata]:
    origin_coords = _point_coords(origin_point)
    destiny_coords = _point_coords(destiny_point)
    if origin_coords is None:
        raise RuntimeError("Approximation fallback unavailable: origin coordinates are missing")
    if destiny_coords is None:
        raise RuntimeError("Approximation fallback unavailable: destination coordinates are missing")

    origin_lat, origin_lon = origin_coords
    destiny_lat, destiny_lon = destiny_coords

    straight_origin_to_missing_km = haversine_km(origin_lat, origin_lon, destiny_lat, destiny_lon)
    straight_origin_to_reference_km = haversine_km(
        origin_lat,
        origin_lon,
        reference.destiny_lat,
        reference.destiny_lon,
    )
    delta_straight_line_km = straight_origin_to_missing_km - straight_origin_to_reference_km
    raw_estimated_distance_km = reference.road_distance_km + delta_straight_line_km
    estimated_distance_km = max(raw_estimated_distance_km, _MIN_APPROX_ROAD_DISTANCE_KM)

    notes = "Approximate direct-road distance from the nearest exact destination in the same bulk run."
    if estimated_distance_km != raw_estimated_distance_km:
        notes = (
            f"{notes} Clamped from {raw_estimated_distance_km:.3f} km "
            f"to {_MIN_APPROX_ROAD_DISTANCE_KM:.3f} km."
        )

    return float(estimated_distance_km), ApproximationMetadata(
        route_source=_APPROX_ROUTE_SOURCE,
        reference_destiny=reference.destiny_name,
        reference_distance_km=float(reference.road_distance_km),
        delta_straight_line_km=float(delta_straight_line_km),
        notes=notes,
    )


def _build_approximated_geometry(geo: Dict[str, Any], estimated_distance_km: float) -> Dict[str, Any]:
    approx_geo = copy.deepcopy(geo)
    approx_geo.setdefault("road_direct", {})
    approx_geo["road_direct"]["distance_km"] = float(estimated_distance_km)
    approx_geo["road_direct"]["cached"] = False
    approx_geo["road_direct"]["is_hgv"] = None
    approx_geo["road_direct"]["profile_used"] = None
    approx_geo["road_direct"]["source"] = _APPROX_ROUTE_SOURCE
    return approx_geo


def _evaluate_and_flatten(
    geo: Dict[str, Any],
    *,
    origin_name: str,
    destiny_name: str,
    evaluation_kwargs: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    res = evaluate_path(geo, **evaluation_kwargs)
    if not res:
        raise RuntimeError("Path evaluation failed")
    flat = flatten_evaluation_for_db(origin_name, destiny_name, res)
    return res, flat


def _safe_persist_bulk_outcome(
    destiny_input: str,
    *,
    status: str,
    **kwargs: Any,
) -> None:
    try:
        _persist_bulk_outcome(status=status, **kwargs)
    except Exception as persist_exc:
        kind = "success" if status == "ok" else "error"
        _log.error(
            "Failed to persist bulk %s outcome for %s: %s",
            kind,
            destiny_input,
            persist_exc,
            exc_info=True,
        )


def _build_bulk_outcome_rows(
    *,
    run_id: str,
    destination_set_id: str,
    scenario_key: str,
    input_origin: str,
    input_destiny: str,
    origin_name: str,
    destiny_name: str,
    truck_key: str,
    ors_profile: str,
    cargo_t: float,
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
    error_message: Optional[str] = None,
    geo: Optional[Dict[str, Any]] = None,
    res: Optional[Dict[str, Any]] = None,
    flat: Optional[Dict[str, Any]] = None,
    is_approximation: bool = False,
    route_source: Optional[str] = None,
    origin_location_id: Optional[int] = None,
    destination_location_id: Optional[int] = None,
    port_origin_location_id: Optional[int] = None,
    port_destiny_location_id: Optional[int] = None,
    road_route_id: Optional[int] = None,
    first_mile_route_id: Optional[int] = None,
    last_mile_route_id: Optional[int] = None,
    approximation_reference_route_id: Optional[int] = None,
    approximation_reference_destiny: Optional[str] = None,
    approximation_reference_distance_km: Optional[float] = None,
    approximation_delta_straight_line_km: Optional[float] = None,
    approximation_notes: Optional[str] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    inputs = res.get("inputs", {}) if isinstance(res, dict) else {}
    flat = flat or {}
    origin_point = geo.get("origin", {}) if isinstance(geo, dict) else {}
    destiny_point = geo.get("destiny", {}) if isinstance(geo, dict) else {}
    port_origin = geo.get("port_origin", {}) if isinstance(geo, dict) else {}
    port_destiny = geo.get("port_destiny", {}) if isinstance(geo, dict) else {}

    road_cost_r = flat.get("road_fuel_cost_r")
    multimodal_cost_r = flat.get("total_fuel_cost_r")
    road_emissions_kg = flat.get("road_co2e_kg")
    multimodal_emissions_kg = flat.get("total_co2e_kg")
    emissions_savings_pct = _emissions_savings_pct(flat)
    resolved_route_source = route_source or _route_source_for_result(geo, is_approximation=is_approximation)

    cost_delta_r = None
    if road_cost_r is not None and multimodal_cost_r is not None:
        cost_delta_r = float(road_cost_r) - float(multimodal_cost_r)

    emissions_delta_kg = None
    if road_emissions_kg is not None and multimodal_emissions_kg is not None:
        emissions_delta_kg = float(road_emissions_kg) - float(multimodal_emissions_kg)

    shared = {
        "run_id": run_id,
        "scenario_key": scenario_key,
        "destination_set_id": destination_set_id,
        "origin_location_id": origin_location_id,
        "origin_name": origin_name,
        "origin_lat": origin_point.get("lat"),
        "origin_lon": origin_point.get("lon"),
        "origin_uf": origin_point.get("uf"),
        "destination_location_id": destination_location_id,
        "destiny_name": destiny_name,
        "destiny_lat": destiny_point.get("lat"),
        "destiny_lon": destiny_point.get("lon"),
        "destiny_uf": destiny_point.get("uf"),
        "input_origin": input_origin,
        "input_destiny": input_destiny,
        "input_destiny_key": ascii_place_key(input_destiny),
        "cargo_t": cargo_t,
        "truck_key": truck_key,
        "ors_profile": ors_profile,
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
        "port_origin_location_id": port_origin_location_id,
        "port_origin_name": (None if not isinstance(port_origin, dict) else port_origin.get("name")),
        "port_origin_lat": (None if not isinstance(port_origin, dict) else port_origin.get("lat")),
        "port_origin_lon": (None if not isinstance(port_origin, dict) else port_origin.get("lon")),
        "port_destiny_location_id": port_destiny_location_id,
        "port_destiny_name": (None if not isinstance(port_destiny, dict) else port_destiny.get("name")),
        "port_destiny_lat": (None if not isinstance(port_destiny, dict) else port_destiny.get("lat")),
        "port_destiny_lon": (None if not isinstance(port_destiny, dict) else port_destiny.get("lon")),
        "status": status,
        "error_message": error_message,
        "is_approximation": is_approximation,
        "route_source": resolved_route_source,
        "road_route_id": road_route_id,
        "first_mile_route_id": first_mile_route_id,
        "last_mile_route_id": last_mile_route_id,
        "approximation_reference_route_id": approximation_reference_route_id,
        "approximation_reference_destiny": approximation_reference_destiny,
        "approximation_reference_distance_km": approximation_reference_distance_km,
        "approximation_delta_straight_line_km": approximation_delta_straight_line_km,
        "approximation_notes": approximation_notes,
    }

    bulk_row = {
        **shared,
        "geometry_status": (None if not isinstance(geo, dict) else geo.get("status")),
        "road_direct_source": (None if not isinstance(geo, dict) else geo.get("road_direct", {}).get("source")),
        "first_mile_source": (None if not isinstance(geo, dict) else geo.get("first_mile", {}).get("source")),
        "last_mile_source": (None if not isinstance(geo, dict) else geo.get("last_mile", {}).get("source")),
        "road_direct_profile_used": (None if not isinstance(geo, dict) else geo.get("road_direct", {}).get("profile_used")),
        "first_mile_profile_used": (None if not isinstance(geo, dict) else geo.get("first_mile", {}).get("profile_used")),
        "last_mile_profile_used": (None if not isinstance(geo, dict) else geo.get("last_mile", {}).get("profile_used")),
        "road_distance_km": flat.get("road_distance_km"),
        "road_fuel_liters": flat.get("road_fuel_liters"),
        "road_fuel_kg": flat.get("road_fuel_kg"),
        "road_fuel_cost_r": road_cost_r,
        "road_co2e_kg": road_emissions_kg,
        "mm_road_fuel_liters": flat.get("mm_road_fuel_liters"),
        "mm_road_fuel_kg": flat.get("mm_road_fuel_kg"),
        "mm_road_fuel_cost_r": flat.get("mm_road_fuel_cost_r"),
        "mm_road_co2e_kg": flat.get("mm_road_co2e_kg"),
        "sea_km": flat.get("sea_km"),
        "sea_fuel_kg": flat.get("sea_fuel_kg"),
        "sea_fuel_cost_r": flat.get("sea_fuel_cost_r"),
        "sea_co2e_kg": flat.get("sea_co2e_kg"),
        "total_fuel_kg": flat.get("total_fuel_kg"),
        "total_fuel_cost_r": multimodal_cost_r,
        "total_co2e_kg": multimodal_emissions_kg,
        "delta_cost_r": flat.get("delta_cost_r"),
        "delta_co2e_kg": flat.get("delta_co2e_kg"),
        "savings_pct": (None if not isinstance(res, dict) else res.get("comparison", {}).get("savings_pct")),
        "emissions_savings_pct": emissions_savings_pct,
        "diesel_price_r_per_l": inputs.get("diesel_price"),
        "diesel_price_source": inputs.get("diesel_price_source"),
        "bunker_price_r_per_t": inputs.get("bunker_price"),
    }

    run_row = {
        "run_id": run_id,
        "scenario_key": scenario_key,
        "input_destiny": input_destiny,
        "destination_location_id": destination_location_id,
        "destiny_name": destiny_name,
        "destiny_lat": destiny_point.get("lat"),
        "destiny_lon": destiny_point.get("lon"),
        "destiny_uf": destiny_point.get("uf"),
        "port_origin_location_id": port_origin_location_id,
        "port_origin_name": (None if not isinstance(port_origin, dict) else port_origin.get("name")),
        "port_origin_lat": (None if not isinstance(port_origin, dict) else port_origin.get("lat")),
        "port_origin_lon": (None if not isinstance(port_origin, dict) else port_origin.get("lon")),
        "port_destiny_location_id": port_destiny_location_id,
        "port_destiny_name": (None if not isinstance(port_destiny, dict) else port_destiny.get("name")),
        "port_destiny_lat": (None if not isinstance(port_destiny, dict) else port_destiny.get("lat")),
        "port_destiny_lon": (None if not isinstance(port_destiny, dict) else port_destiny.get("lon")),
        "status": status,
        "error_message": error_message,
        "road_cost_r": road_cost_r,
        "multimodal_cost_r": multimodal_cost_r,
        "cost_delta_r": cost_delta_r,
        "cost_savings_pct": (None if not isinstance(res, dict) else res.get("comparison", {}).get("savings_pct")),
        "road_emissions_kg": road_emissions_kg,
        "multimodal_emissions_kg": multimodal_emissions_kg,
        "emissions_delta_kg": emissions_delta_kg,
        "emissions_savings_pct": emissions_savings_pct,
        "road_distance_km": flat.get("road_distance_km"),
        "sea_km": flat.get("sea_km"),
        "is_approximation": is_approximation,
        "route_source": resolved_route_source,
        "road_route_id": road_route_id,
        "first_mile_route_id": first_mile_route_id,
        "last_mile_route_id": last_mile_route_id,
        "approximation_reference_route_id": approximation_reference_route_id,
        "approximation_reference_destiny": approximation_reference_destiny,
        "approximation_reference_distance_km": approximation_reference_distance_km,
        "approximation_delta_straight_line_km": approximation_delta_straight_line_km,
        "approximation_notes": approximation_notes,
        "ors_profile": ors_profile,
    }
    return bulk_row, run_row


def _persist_bulk_outcome(
    *,
    db_path: Path | str | None,
    table_name: str,
    run_results_table: str,
    run_id: str,
    destination_set_id: str,
    scenario_key: str,
    input_origin: str,
    input_destiny: str,
    origin_name: str,
    destiny_name: str,
    truck_key: str,
    ors_profile: str,
    cargo_t: float,
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
    error_message: Optional[str] = None,
    geo: Optional[Dict[str, Any]] = None,
    res: Optional[Dict[str, Any]] = None,
    flat: Optional[Dict[str, Any]] = None,
    is_approximation: bool = False,
    route_source: Optional[str] = None,
    approximation_reference_destiny: Optional[str] = None,
    approximation_reference_distance_km: Optional[float] = None,
    approximation_delta_straight_line_km: Optional[float] = None,
    approximation_notes: Optional[str] = None,
) -> None:
    bulk_row, run_row = _build_bulk_outcome_rows(
        run_id=run_id,
        destination_set_id=destination_set_id,
        scenario_key=scenario_key,
        input_origin=input_origin,
        input_destiny=input_destiny,
        origin_name=origin_name,
        destiny_name=destiny_name,
        truck_key=truck_key,
        ors_profile=ors_profile,
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
        geo=geo,
        res=res,
        flat=flat,
        is_approximation=is_approximation,
        route_source=route_source,
        approximation_reference_destiny=approximation_reference_destiny,
        approximation_reference_distance_km=approximation_reference_distance_km,
        approximation_delta_straight_line_km=approximation_delta_straight_line_km,
        approximation_notes=approximation_notes,
    )

    with db_session(db_path) as conn:
        upsert_bulk_result(conn, table_name=table_name, **bulk_row)
        insert_bulk_run_result(conn, table_name=run_results_table, **run_row)


def run_bulk_evaluation(
    origin: str,
    dest_list: List[str],
    *,
    cargo_t: float,
    truck_key: str,
    profile: str,
    overwrite_road: bool = False,
    db_path: Path | str | None = None,
    results_table: str = DEFAULT_BULK_RESULTS_TABLE,
    runs_table: str = DEFAULT_BULK_RUNS_TABLE,
    run_results_table: str = DEFAULT_BULK_RUN_RESULTS_TABLE,
    destination_set_id: str = "ad_hoc",
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
    progress_callback: Optional[ProgressCallback] = None,
    shuffle_destinations: bool = True,
    shuffle_seed: Optional[int] = None,
    approximation_fallback: bool = True,
    max_geocode_workers: int = 2,
    max_route_workers: int = 2,
    persist_batch_size: int = 64,
) -> Dict[str, Any]:
    from modules.multimodal.bulk_pipeline import run_bulk_evaluation_pipeline

    return run_bulk_evaluation_pipeline(
        origin=origin,
        dest_list=dest_list,
        cargo_t=cargo_t,
        truck_key=truck_key,
        profile=profile,
        overwrite_road=overwrite_road,
        db_path=db_path,
        results_table=results_table,
        runs_table=runs_table,
        run_results_table=run_results_table,
        destination_set_id=destination_set_id,
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
        progress_callback=progress_callback,
        shuffle_destinations=shuffle_destinations,
        shuffle_seed=shuffle_seed,
        approximation_fallback=approximation_fallback,
        max_geocode_workers=max_geocode_workers,
        max_route_workers=max_route_workers,
        persist_batch_size=persist_batch_size,
    )
