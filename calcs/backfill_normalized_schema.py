from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Sequence

from modules.addressing.text import ascii_place_key, ascii_place_text
from modules.infra.db.bulk_runs import (
    DEFAULT_RUNS_TABLE,
    DEFAULT_RUN_RESULTS_TABLE,
    BulkRunSelector,
    insert_run_result,
    upsert_run as upsert_bulk_run,
)
from modules.infra.db.core import (
    DBConnection,
    connect,
    connection_target_summary,
    list_tables,
    safe_table_name,
)
from modules.infra.db.locations import (
    DEFAULT_ALIASES_TABLE,
    DEFAULT_LOCATIONS_TABLE,
    coord_lookup_key,
    find_point,
    get_location_by_coords,
    get_or_create_location,
    normalize_place_key,
    upsert_alias,
)
from modules.infra.db.road_cache import (
    DEFAULT_TABLE as DEFAULT_ROUTE_CACHE_TABLE,
    profile_is_hgv,
    upsert_run as upsert_route_run,
)
from modules.infra.log_manager import bind_log_context, get_logger, init_logging
from modules.multimodal.scenario_keys import build_bulk_scenario_key, normalize_bulk_place_input
from modules.ports.ports_index import load_ports

_log = get_logger(__name__)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "calcs" / "outputs"
_DEFAULT_PORTS_JSON = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"


@dataclass(frozen=True)
class ColumnFingerprint:
    name: str
    data_type: str
    udt_name: str
    is_nullable: bool
    ordinal_position: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "udt_name": self.udt_name,
            "is_nullable": self.is_nullable,
            "ordinal_position": self.ordinal_position,
        }


@dataclass(frozen=True)
class ShapeSpec:
    name: str
    role: str
    required: frozenset[str]
    preferred: frozenset[str] = frozenset()
    forbidden: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ShapeMatch:
    spec_name: str
    role: str
    score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_name": self.spec_name,
            "role": self.role,
            "score": self.score,
        }


@dataclass
class TableFingerprint:
    table_name: str
    row_count: int
    columns: list[ColumnFingerprint]
    matches: list[ShapeMatch] = field(default_factory=list)

    @property
    def column_names(self) -> set[str]:
        return {column.name for column in self.columns}

    @property
    def primary_match(self) -> Optional[ShapeMatch]:
        return self.matches[0] if self.matches else None

    def matches_spec(self, spec_name: str) -> bool:
        return any(match.spec_name == spec_name for match in self.matches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "row_count": self.row_count,
            "columns": [column.to_dict() for column in self.columns],
            "matches": [match.to_dict() for match in self.matches],
            "primary_match": (None if self.primary_match is None else self.primary_match.to_dict()),
        }


@dataclass(frozen=True)
class TargetTables:
    locations: str = DEFAULT_LOCATIONS_TABLE
    aliases: str = DEFAULT_ALIASES_TABLE
    route_cache: str = DEFAULT_ROUTE_CACHE_TABLE
    bulk_runs: str = DEFAULT_RUNS_TABLE
    bulk_items: str = DEFAULT_RUN_RESULTS_TABLE

    def validated(self) -> "TargetTables":
        return TargetTables(
            locations=safe_table_name(self.locations),
            aliases=safe_table_name(self.aliases),
            route_cache=safe_table_name(self.route_cache),
            bulk_runs=safe_table_name(self.bulk_runs),
            bulk_items=safe_table_name(self.bulk_items),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "locations": self.locations,
            "location_aliases": self.aliases,
            "route_cache_entries": self.route_cache,
            "bulk_runs": self.bulk_runs,
            "bulk_run_items": self.bulk_items,
        }


@dataclass
class PhaseStats:
    name: str
    rows_read: int = 0
    rows_created: int = 0
    rows_reused: int = 0
    rows_skipped: int = 0
    conflicts_handled: int = 0
    anomalies_found: int = 0

    def to_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "rows_read": self.rows_read,
            "rows_created": self.rows_created,
            "rows_reused": self.rows_reused,
            "rows_skipped": self.rows_skipped,
            "conflicts_handled": self.conflicts_handled,
            "anomalies_found": self.anomalies_found,
        }


@dataclass
class MigrationReport:
    mode: str
    database_target: str
    targets: TargetTables
    fingerprint_path: Path
    summary_path: Path
    anomaly_path: Path
    fingerprint: dict[str, TableFingerprint] = field(default_factory=dict)
    source_tables: dict[str, list[str]] = field(default_factory=dict)
    target_tables: dict[str, str] = field(default_factory=dict)
    inspect_only_tables: dict[str, list[str]] = field(default_factory=dict)
    phases: dict[str, PhaseStats] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    post_migration_checklist: list[str] = field(default_factory=list)

    def phase(self, name: str) -> PhaseStats:
        if name not in self.phases:
            self.phases[name] = PhaseStats(name=name)
        return self.phases[name]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "database_target": self.database_target,
            "targets": self.targets.to_dict(),
            "fingerprint_path": str(self.fingerprint_path),
            "summary_path": str(self.summary_path),
            "anomaly_path": str(self.anomaly_path),
            "source_tables": self.source_tables,
            "target_tables": self.target_tables,
            "inspect_only_tables": self.inspect_only_tables,
            "phases": {name: stats.to_dict() for name, stats in sorted(self.phases.items())},
            "notes": list(self.notes),
            "post_migration_checklist": list(self.post_migration_checklist),
        }


@dataclass
class RowContext:
    table_name: str
    row: dict[str, Any]


@dataclass(frozen=True)
class LocationSeed:
    lat: Any
    lon: Any
    label: Optional[str]
    state: Optional[str]
    provider: Optional[str]
    source: str
    insertion_timestamp: Any
    updated_timestamp: Any
    aliases: tuple[str, ...]
    city: Optional[str] = None
    provider_payload: Any = None


@dataclass
class BackfillContext:
    conn: DBConnection
    dry_run: bool
    targets: TargetTables
    port_index: dict[str, dict[str, Any]]
    report: MigrationReport
    anomalies: "AnomalyRecorder"
    seen_location_keys: set[tuple[str, str]] = field(default_factory=set)
    seen_alias_keys: set[str] = field(default_factory=set)
    seen_route_keys: set[tuple[int, int, bool]] = field(default_factory=set)
    seen_bulk_run_ids: set[str] = field(default_factory=set)
    seen_bulk_item_keys: set[tuple[str, str]] = field(default_factory=set)


class AnomalyRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")
        self.count = 0

    def record(
        self,
        *,
        category: str,
        message: str,
        table_name: Optional[str] = None,
        row: Optional[Mapping[str, Any]] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "category": str(category),
            "message": str(message),
            "table_name": (None if table_name in (None, "") else str(table_name)),
            "row_ref": _row_reference(row or {}),
            "payload": dict(payload or {}),
        }
        self._handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        self._handle.flush()
        self.count += 1

    def close(self) -> None:
        self._handle.close()


_SHAPE_SPECS: tuple[ShapeSpec, ...] = (
    ShapeSpec(
        name="normalized_locations",
        role="target",
        required=frozenset({"id", "lat6", "lon6"}),
        preferred=frozenset({"label", "provider", "provider_payload", "updated_timestamp"}),
        forbidden=frozenset({"place_key", "origin_key", "scenario_key"}),
    ),
    ShapeSpec(
        name="normalized_location_aliases",
        role="target",
        required=frozenset({"place_key", "alias_label", "location_id"}),
        preferred=frozenset({"provider", "source", "updated_timestamp"}),
        forbidden=frozenset({"lat", "lon", "origin_key", "scenario_key"}),
    ),
    ShapeSpec(
        name="normalized_route_cache",
        role="target",
        required=frozenset({"origin_location_id", "destiny_location_id", "is_hgv"}),
        preferred=frozenset({"provider", "distance_km", "duration_s", "fallback_profile"}),
        forbidden=frozenset({"origin_key", "destiny_key", "origin_lat", "destiny_lat"}),
    ),
    ShapeSpec(
        name="normalized_bulk_runs",
        role="target",
        required=frozenset({"run_id", "selector_hash", "origin_location_id", "destination_set_id", "status"}),
        preferred=frozenset({"input_origin", "cargo_t", "truck_key", "ors_profile", "updated_timestamp"}),
        forbidden=frozenset({"origin_key", "origin_name", "origin_lat"}),
    ),
    ShapeSpec(
        name="normalized_bulk_run_items",
        role="target",
        required=frozenset({"run_id", "scenario_key", "input_destiny", "status"}),
        preferred=frozenset(
            {
                "destination_location_id",
                "road_route_id",
                "port_origin_location_id",
                "port_destiny_location_id",
                "updated_timestamp",
            }
        ),
        forbidden=frozenset({"origin_key", "origin_name", "origin_lat", "destination_set_id"}),
    ),
    ShapeSpec(
        name="legacy_place_points",
        role="source",
        required=frozenset({"place_key", "label", "lat", "lon"}),
        preferred=frozenset({"uf", "provider", "source", "updated_timestamp"}),
        forbidden=frozenset({"location_id", "alias_label"}),
    ),
    ShapeSpec(
        name="legacy_routes",
        role="source",
        required=frozenset({"origin_key", "origin_name", "destiny_key", "destiny_name", "distance_km"}),
        preferred=frozenset({"origin_lat", "origin_lon", "destiny_lat", "destiny_lon", "profile_requested"}),
        forbidden=frozenset({"origin_location_id", "destiny_location_id"}),
    ),
    ShapeSpec(
        name="legacy_bulk_runs",
        role="source",
        required=frozenset({"run_id", "origin_key", "origin_name", "destination_set_id", "status"}),
        preferred=frozenset({"input_origin", "cargo_t", "truck_key", "ors_profile", "updated_timestamp"}),
        forbidden=frozenset({"selector_hash", "origin_location_id"}),
    ),
    ShapeSpec(
        name="legacy_bulk_run_items",
        role="source",
        required=frozenset({"run_id", "scenario_key", "origin_key", "destiny_key", "input_destiny", "status"}),
        preferred=frozenset({"destiny_lat", "destiny_lon", "road_cost_r", "updated_timestamp"}),
        forbidden=frozenset({"destination_location_id", "road_route_id"}),
    ),
    ShapeSpec(
        name="legacy_bulk_results_wide",
        role="source",
        required=frozenset({"scenario_key", "origin_name", "destiny_name", "input_origin", "input_destiny", "status"}),
        preferred=frozenset({"run_id", "origin_key", "destiny_key", "destiny_lat", "destiny_lon", "updated_timestamp"}),
        forbidden=frozenset({"selector_hash", "destination_location_id", "road_route_id"}),
    ),
    ShapeSpec(
        name="legacy_analysis_results",
        role="inspect_only",
        required=frozenset({"origin_name", "destiny_name", "cargo_t", "road_distance_km"}),
        preferred=frozenset({"delta_cost_r", "delta_co2e_kg", "insertion_timestamp"}),
        forbidden=frozenset({"run_id", "scenario_key", "destination_location_id"}),
    ),
)


def _now_stamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _row_reference(row: Mapping[str, Any]) -> dict[str, Any]:
    for keys in (
        ("run_id", "scenario_key"),
        ("scenario_key",),
        ("run_id",),
        ("place_key",),
        ("origin_key", "destiny_key"),
        ("origin_name", "destiny_name"),
    ):
        payload = {key: row.get(key) for key in keys if row.get(key) not in (None, "")}
        if len(payload) == len(keys):
            return payload
    return {}


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")


def _safe_row_count(conn: DBConnection, table_name: str) -> int:
    table = safe_table_name(table_name)
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0] or 0) if row else 0


def _fetch_columns(conn: DBConnection, table_name: str) -> list[ColumnFingerprint]:
    table = safe_table_name(table_name)
    rows = conn.execute(
        """
        SELECT
              column_name
            , data_type
            , udt_name
            , is_nullable
            , ordinal_position
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ?
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return [
        ColumnFingerprint(
            name=str(row[0]),
            data_type=str(row[1]),
            udt_name=str(row[2]),
            is_nullable=str(row[3]).strip().upper() == "YES",
            ordinal_position=int(row[4]),
        )
        for row in rows
    ]


def _match_shapes(columns: set[str]) -> list[ShapeMatch]:
    matches: list[ShapeMatch] = []
    for spec in _SHAPE_SPECS:
        if not spec.required.issubset(columns):
            continue
        if spec.forbidden and (spec.forbidden & columns):
            continue
        score = len(spec.required) * 100 + len(spec.preferred & columns)
        matches.append(ShapeMatch(spec_name=spec.name, role=spec.role, score=score))
    return sorted(matches, key=lambda item: (-item.score, item.spec_name))


def fingerprint_schema(conn: DBConnection) -> dict[str, TableFingerprint]:
    fingerprints: dict[str, TableFingerprint] = {}
    for table_name in list_tables(conn):
        columns = _fetch_columns(conn, table_name)
        fingerprint = TableFingerprint(
            table_name=table_name,
            row_count=_safe_row_count(conn, table_name),
            columns=columns,
            matches=_match_shapes({column.name for column in columns}),
        )
        fingerprints[table_name] = fingerprint
    return fingerprints


def classify_tables(fingerprints: Mapping[str, TableFingerprint], *, targets: TargetTables) -> tuple[dict[str, list[str]], dict[str, str], dict[str, list[str]]]:
    source_tables: dict[str, list[str]] = {}
    target_tables: dict[str, str] = {}
    inspect_only_tables: dict[str, list[str]] = {}

    for shape_name in (
        "legacy_place_points",
        "legacy_routes",
        "legacy_bulk_runs",
        "legacy_bulk_run_items",
        "legacy_bulk_results_wide",
    ):
        source_tables[shape_name] = sorted(
            fingerprint.table_name
            for fingerprint in fingerprints.values()
            if fingerprint.matches_spec(shape_name)
        )

    inspect_only_tables["legacy_analysis_results"] = sorted(
        fingerprint.table_name
        for fingerprint in fingerprints.values()
        if fingerprint.matches_spec("legacy_analysis_results")
    )

    required_targets = {
        "normalized_locations": targets.locations,
        "normalized_location_aliases": targets.aliases,
        "normalized_route_cache": targets.route_cache,
        "normalized_bulk_runs": targets.bulk_runs,
        "normalized_bulk_run_items": targets.bulk_items,
    }
    for shape_name, table_name in required_targets.items():
        target_tables[shape_name] = table_name

    return source_tables, target_tables, inspect_only_tables


def validate_target_tables(fingerprints: Mapping[str, TableFingerprint], targets: TargetTables) -> None:
    failures: list[str] = []
    requirements = (
        (targets.locations, "normalized_locations"),
        (targets.aliases, "normalized_location_aliases"),
        (targets.route_cache, "normalized_route_cache"),
        (targets.bulk_runs, "normalized_bulk_runs"),
        (targets.bulk_items, "normalized_bulk_run_items"),
    )
    for table_name, shape_name in requirements:
        fingerprint = fingerprints.get(table_name)
        if fingerprint is None:
            failures.append(f"missing required target table {table_name!r}")
            continue
        if not fingerprint.matches_spec(shape_name):
            matched = ", ".join(match.spec_name for match in fingerprint.matches) or "no known shape"
            failures.append(f"target table {table_name!r} does not match {shape_name}; matched: {matched}")
    if failures:
        raise RuntimeError("Normalized target validation failed:\n- " + "\n- ".join(failures))


def _default_order_columns(available: set[str]) -> list[str]:
    candidates = (
        ("id",),
        ("run_id", "scenario_key"),
        ("scenario_key",),
        ("place_key",),
        ("updated_timestamp", "insertion_timestamp"),
        ("origin_key", "destiny_key"),
        ("origin_name", "destiny_name"),
    )
    for candidate in candidates:
        if all(column in available for column in candidate):
            return list(candidate)
    return sorted(available)[:1]


def iter_dict_rows(
    conn: DBConnection,
    table_name: str,
    *,
    columns: Iterable[str],
    chunk_size: int,
    order_by: Optional[Sequence[str]] = None,
) -> Iterator[dict[str, Any]]:
    table = safe_table_name(table_name)
    available = {column.name for column in _fetch_columns(conn, table)}
    selected = [column for column in columns if column in available]
    if not selected:
        return

    ordered = list(order_by or _default_order_columns(available))
    ordered = [column for column in ordered if column in available]
    order_sql = ""
    if ordered:
        order_sql = " ORDER BY " + ", ".join(f"{safe_table_name(column)} ASC" for column in ordered)

    offset = 0
    while True:
        cursor = conn.execute(
            f"SELECT {', '.join(safe_table_name(column) for column in selected)} FROM {table}{order_sql} LIMIT ? OFFSET ?",
            (int(chunk_size), int(offset)),
        )
        rows = cursor.fetchall()
        if not rows:
            break
        names = [str(item[0]) for item in cursor.description] if cursor.description else list(selected)
        for row in rows:
            yield dict(zip(names, row))
        offset += len(rows)


def _port_lookup(path: Path = _DEFAULT_PORTS_JSON) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for port in load_ports(str(path)):
        aliases = [port.get("name")]
        aliases.extend(port.get("aliases") or [])
        for alias in aliases:
            key = ascii_place_key(alias)
            if key:
                lookup[key] = port
    return lookup


def _find_port(port_index: Mapping[str, dict[str, Any]], value: Any) -> Optional[dict[str, Any]]:
    key = ascii_place_key(value)
    if not key:
        return None
    return port_index.get(key)


def _candidate_aliases(*values: Any) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = ascii_place_text(value)
        key = ascii_place_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        aliases.append(text)
    return aliases


def _location_seed_from_port(
    port: Mapping[str, Any],
    *,
    source: str,
    insertion_timestamp: Any,
    updated_timestamp: Any,
) -> LocationSeed:
    aliases = tuple(_candidate_aliases(port.get("name"), *(port.get("aliases") or [])))
    return LocationSeed(
        lat=port.get("lat"),
        lon=port.get("lon"),
        label=ascii_place_text(port.get("name")),
        state=ascii_place_text(port.get("state")) or None,
        city=ascii_place_text(port.get("city")) or None,
        provider="ports_json",
        provider_payload=None,
        source=source,
        insertion_timestamp=insertion_timestamp,
        updated_timestamp=updated_timestamp,
        aliases=aliases,
    )


def _location_seeds_from_row(context: RowContext, port_index: Mapping[str, dict[str, Any]]) -> list[LocationSeed]:
    row = context.row
    table_name = context.table_name
    insertion_timestamp = row.get("insertion_timestamp")
    updated_timestamp = row.get("updated_timestamp")

    if {"place_key", "label", "lat", "lon"}.issubset(row):
        return [
            LocationSeed(
                lat=row.get("lat"),
                lon=row.get("lon"),
                label=ascii_place_text(row.get("label")),
                state=ascii_place_text(row.get("uf")) or None,
                city=None,
                provider=ascii_place_text(row.get("provider")) or None,
                provider_payload=None,
                source=f"{table_name}:place_points",
                insertion_timestamp=insertion_timestamp,
                updated_timestamp=updated_timestamp,
                aliases=tuple(_candidate_aliases(row.get("place_key"), row.get("label"))),
            )
        ]

    seeds: list[LocationSeed] = []
    for prefix in ("origin", "destiny"):
        lat_key = f"{prefix}_lat"
        lon_key = f"{prefix}_lon"
        if lat_key not in row or lon_key not in row:
            continue
        if row.get(lat_key) is None or row.get(lon_key) is None:
            continue
        state_key = f"{prefix}_uf"
        aliases = tuple(_candidate_aliases(row.get(f"{prefix}_key"), row.get(f"{prefix}_name")))
        seeds.append(
            LocationSeed(
                lat=row.get(lat_key),
                lon=row.get(lon_key),
                label=ascii_place_text(row.get(f"{prefix}_name")) or None,
                state=ascii_place_text(row.get(state_key)) or None,
                city=None,
                provider=ascii_place_text(row.get("source") or row.get("provider")) or None,
                provider_payload=None,
                source=f"{table_name}:{prefix}",
                insertion_timestamp=insertion_timestamp,
                updated_timestamp=updated_timestamp,
                aliases=aliases,
            )
        )

    for field_name in ("port_origin_name", "port_destiny_name"):
        port = _find_port(port_index, row.get(field_name))
        if port is None:
            continue
        seeds.append(
            _location_seed_from_port(
                port,
                source=f"{table_name}:{field_name}",
                insertion_timestamp=insertion_timestamp,
                updated_timestamp=updated_timestamp,
            )
        )

    return seeds


def _location_from_coords(
    context: BackfillContext,
    *,
    lat: Any,
    lon: Any,
    label: Any = None,
    state: Any = None,
    city: Any = None,
    provider: Any = None,
    provider_payload: Any = None,
    source: str,
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
) -> Optional[dict[str, Any]]:
    if lat in (None, "") or lon in (None, ""):
        return None
    coord_key = coord_lookup_key(lat, lon)
    if coord_key is None:
        return None
    existing = get_location_by_coords(
        context.conn,
        lat=lat,
        lon=lon,
        table_name=context.targets.locations,
    )
    location = get_or_create_location(
        context.conn,
        lat=lat,
        lon=lon,
        label=label,
        city=city,
        state=state,
        provider=provider,
        provider_payload=provider_payload,
        insertion_timestamp=insertion_timestamp,
        updated_timestamp=updated_timestamp,
        table_name=context.targets.locations,
    )
    if coord_key not in context.seen_location_keys:
        context.seen_location_keys.add(coord_key)
        stats = context.report.phase("locations")
        if existing is None:
            stats.rows_created += 1
        else:
            stats.rows_reused += 1
    return location


def _resolve_location_id(
    context: BackfillContext,
    *,
    lat: Any = None,
    lon: Any = None,
    aliases: Iterable[Any] = (),
    label: Any = None,
    state: Any = None,
    city: Any = None,
    provider: Any = None,
    source: str,
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
) -> Optional[int]:
    if lat not in (None, "") and lon not in (None, ""):
        location = _location_from_coords(
            context,
            lat=lat,
            lon=lon,
            label=label,
            state=state,
            city=city,
            provider=provider,
            source=source,
            insertion_timestamp=insertion_timestamp,
            updated_timestamp=updated_timestamp,
        )
        if location is not None:
            return int(location["location_id"])

    for candidate in _candidate_aliases(label, *aliases):
        cached = find_point(
            context.conn,
            place=candidate,
            table_name=context.targets.aliases,
            locations_table=context.targets.locations,
        )
        if cached is not None:
            return int(cached["location_id"])
    return None


def _upsert_alias_with_report(
    context: BackfillContext,
    *,
    place: Any,
    alias_label: Any,
    location_id: int,
    provider: Any = None,
    source: str,
    insertion_timestamp: Any = None,
    updated_timestamp: Any = None,
    table_name: Optional[str] = None,
    row: Optional[Mapping[str, Any]] = None,
) -> None:
    stats = context.report.phase("aliases")
    place_key = normalize_place_key(place)
    label = ascii_place_text(alias_label or place)
    if not place_key or not label:
        return

    existing = find_point(
        context.conn,
        place=place_key,
        table_name=context.targets.aliases,
        locations_table=context.targets.locations,
    )
    if existing is not None and int(existing["location_id"]) != int(location_id):
        stats.conflicts_handled += 1
        context.anomalies.record(
            category="alias_conflict",
            message=f"alias {place_key!r} already pointed to location {existing['location_id']}, overwriting with {location_id}",
            table_name=table_name,
            row=row,
            payload={"place_key": place_key, "existing_location_id": existing["location_id"], "new_location_id": location_id},
        )

    upsert_alias(
        context.conn,
        place=place_key,
        location_id=int(location_id),
        alias_label=label,
        provider=provider,
        source=source,
        insertion_timestamp=insertion_timestamp,
        updated_timestamp=updated_timestamp,
        table_name=context.targets.aliases,
        locations_table=context.targets.locations,
    )
    if place_key not in context.seen_alias_keys:
        context.seen_alias_keys.add(place_key)
        if existing is None:
            stats.rows_created += 1
        else:
            stats.rows_reused += 1


def _route_entry_id(
    conn: DBConnection,
    *,
    table_name: str,
    origin_location_id: int,
    destiny_location_id: int,
    is_hgv: bool,
) -> Optional[int]:
    table = safe_table_name(table_name)
    row = conn.execute(
        f"""
        SELECT id
        FROM {table}
        WHERE origin_location_id = ?
          AND destiny_location_id = ?
          AND is_hgv = ?
        LIMIT 1
        """,
        (int(origin_location_id), int(destiny_location_id), bool(is_hgv)),
    ).fetchone()
    if not row:
        return None
    return int(row[0])


def _bulk_run_exists(conn: DBConnection, *, table_name: str, run_id: str) -> bool:
    table = safe_table_name(table_name)
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE run_id = ? LIMIT 1",
        (str(run_id),),
    ).fetchone()
    return bool(row)


def _bulk_item_exists(conn: DBConnection, *, table_name: str, run_id: str, scenario_key: str) -> bool:
    table = safe_table_name(table_name)
    row = conn.execute(
        f"SELECT 1 FROM {table} WHERE run_id = ? AND scenario_key = ? LIMIT 1",
        (str(run_id), str(scenario_key)),
    ).fetchone()
    return bool(row)


def _record_route_write(context: BackfillContext, *, origin_location_id: int, destiny_location_id: int, is_hgv: bool, existed: bool) -> None:
    route_key = (int(origin_location_id), int(destiny_location_id), bool(is_hgv))
    if route_key in context.seen_route_keys:
        return
    context.seen_route_keys.add(route_key)
    stats = context.report.phase("routes")
    if existed:
        stats.rows_reused += 1
    else:
        stats.rows_created += 1


def _record_bulk_run_write(context: BackfillContext, *, run_id: str, existed: bool) -> None:
    normalized_run_id = str(run_id)
    if normalized_run_id in context.seen_bulk_run_ids:
        return
    context.seen_bulk_run_ids.add(normalized_run_id)
    stats = context.report.phase("bulk_runs")
    if existed:
        stats.rows_reused += 1
    else:
        stats.rows_created += 1


def _record_bulk_item_write(context: BackfillContext, *, run_id: str, scenario_key: str, existed: bool) -> None:
    item_key = (str(run_id), str(scenario_key))
    if item_key in context.seen_bulk_item_keys:
        return
    context.seen_bulk_item_keys.add(item_key)
    stats = context.report.phase("bulk_run_items")
    if existed:
        stats.rows_reused += 1
    else:
        stats.rows_created += 1


def _selector_from_legacy_row(row: Mapping[str, Any], *, origin_location_id: int) -> BulkRunSelector:
    return BulkRunSelector(
        origin_location_id=int(origin_location_id),
        cargo_t=float(row.get("cargo_t") or 0.0),
        truck_key=str(row.get("truck_key") or ""),
        ors_profile=str(row.get("ors_profile") or "driving-hgv"),
        vessel_class=(None if row.get("vessel_class") in (None, "") else str(row.get("vessel_class"))),
        include_hoteling=bool(row.get("include_hoteling", True)),
        hoteling_hours_per_call=float(row.get("hoteling_hours_per_call") or 0.0),
        port_calls=int(row.get("port_calls") or 0),
        include_port_ops=bool(row.get("include_port_ops", True)),
        port_moves_per_call=(None if row.get("port_moves_per_call") in (None, "") else float(row["port_moves_per_call"])),
        cargo_teu=(None if row.get("cargo_teu") in (None, "") else float(row["cargo_teu"])),
        t_per_teu_default=float(row.get("t_per_teu_default") or 0.0),
        allocation_mode=(None if row.get("allocation_mode") in (None, "") else str(row.get("allocation_mode"))),
        allocation_load_factor=float(row.get("allocation_load_factor") or 0.0),
        full_call_mode=bool(row.get("full_call_mode", False)),
        port_ops_scenario=str(row.get("port_ops_scenario") or ""),
        destination_set_id=str(row.get("destination_set_id") or "legacy"),
    )


def _synthetic_run_id(row: Mapping[str, Any], *, origin_location_id: int) -> str:
    selector = _selector_from_legacy_row(row, origin_location_id=origin_location_id)
    payload = {
        "origin_location_id": selector.origin_location_id,
        "input_origin": normalize_bulk_place_input(row.get("input_origin") or row.get("origin_name") or ""),
        "destination_set_id": selector.destination_set_id,
        "cargo_t": selector.cargo_t,
        "truck_key": selector.truck_key,
        "ors_profile": selector.ors_profile,
        "vessel_class": selector.vessel_class,
        "include_hoteling": selector.include_hoteling,
        "hoteling_hours_per_call": selector.hoteling_hours_per_call,
        "port_calls": selector.port_calls,
        "include_port_ops": selector.include_port_ops,
        "port_moves_per_call": selector.port_moves_per_call,
        "cargo_teu": selector.cargo_teu,
        "t_per_teu_default": selector.t_per_teu_default,
        "allocation_mode": selector.allocation_mode,
        "allocation_load_factor": selector.allocation_load_factor,
        "full_call_mode": selector.full_call_mode,
        "port_ops_scenario": selector.port_ops_scenario,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]
    return f"legacy-{digest}"


def _scenario_key_for_row(row: Mapping[str, Any]) -> str:
    existing = str(row.get("scenario_key") or "").strip()
    if existing:
        return existing
    payload = {
        "input_origin": normalize_bulk_place_input(row.get("input_origin") or row.get("origin_name") or ""),
        "input_destiny": normalize_bulk_place_input(row.get("input_destiny") or row.get("destiny_name") or ""),
        "cargo_t": row.get("cargo_t"),
        "truck_key": row.get("truck_key"),
        "ors_profile": row.get("ors_profile"),
        "destination_set_id": row.get("destination_set_id"),
    }
    return build_bulk_scenario_key(payload)


def _relevant_table_log(fingerprint: TableFingerprint) -> str:
    columns = ", ".join(f"{column.name}:{column.data_type}" for column in fingerprint.columns)
    matches = ", ".join(match.spec_name for match in fingerprint.matches) or "none"
    primary = fingerprint.primary_match.spec_name if fingerprint.primary_match is not None else "unclassified"
    return f"{fingerprint.table_name} rows={fingerprint.row_count} primary={primary} matches=[{matches}] columns=[{columns}]"


def _iter_source_rows(context: BackfillContext, shape_name: str, *, columns: Iterable[str], chunk_size: int) -> Iterator[RowContext]:
    for table_name in context.report.source_tables.get(shape_name, []):
        for row in iter_dict_rows(context.conn, table_name, columns=columns, chunk_size=chunk_size):
            yield RowContext(table_name=table_name, row=row)


def backfill_locations(context: BackfillContext, *, chunk_size: int) -> None:
    stats = context.report.phase("locations")
    columns = (
        "place_key",
        "label",
        "lat",
        "lon",
        "uf",
        "provider",
        "source",
        "origin_key",
        "origin_name",
        "origin_lat",
        "origin_lon",
        "origin_uf",
        "destiny_key",
        "destiny_name",
        "destiny_lat",
        "destiny_lon",
        "destiny_uf",
        "port_origin_name",
        "port_destiny_name",
        "insertion_timestamp",
        "updated_timestamp",
    )
    for shape_name in (
        "legacy_place_points",
        "legacy_routes",
        "legacy_bulk_run_items",
        "legacy_bulk_results_wide",
    ):
        for item in _iter_source_rows(context, shape_name, columns=columns, chunk_size=chunk_size):
            seeds = _location_seeds_from_row(item, context.port_index)
            stats.rows_read += 1
            if not seeds:
                stats.rows_skipped += 1
                continue
            for seed in seeds:
                if coord_lookup_key(seed.lat, seed.lon) is None:
                    stats.rows_skipped += 1
                    stats.anomalies_found += 1
                    context.anomalies.record(
                        category="invalid_location_coordinates",
                        message="skipping location seed with missing or invalid coordinates",
                        table_name=item.table_name,
                        row=item.row,
                        payload={"label": seed.label, "lat": seed.lat, "lon": seed.lon, "source": seed.source},
                    )
                    continue
                _location_from_coords(
                    context,
                    lat=seed.lat,
                    lon=seed.lon,
                    label=seed.label,
                    state=seed.state,
                    city=seed.city,
                    provider=seed.provider,
                    provider_payload=seed.provider_payload,
                    source=seed.source,
                    insertion_timestamp=seed.insertion_timestamp,
                    updated_timestamp=seed.updated_timestamp,
                )


def backfill_aliases(context: BackfillContext, *, chunk_size: int) -> None:
    stats = context.report.phase("aliases")
    columns = (
        "place_key",
        "label",
        "lat",
        "lon",
        "uf",
        "provider",
        "source",
        "origin_key",
        "origin_name",
        "origin_lat",
        "origin_lon",
        "origin_uf",
        "destiny_key",
        "destiny_name",
        "destiny_lat",
        "destiny_lon",
        "destiny_uf",
        "input_origin",
        "input_destiny",
        "port_origin_name",
        "port_destiny_name",
        "insertion_timestamp",
        "updated_timestamp",
    )
    for shape_name in (
        "legacy_place_points",
        "legacy_routes",
        "legacy_bulk_runs",
        "legacy_bulk_run_items",
        "legacy_bulk_results_wide",
    ):
        for item in _iter_source_rows(context, shape_name, columns=columns, chunk_size=chunk_size):
            row = item.row
            stats.rows_read += 1
            pairs = (
                (
                    _resolve_location_id(
                        context,
                        lat=row.get("lat"),
                        lon=row.get("lon"),
                        aliases=(row.get("place_key"), row.get("label")),
                        label=row.get("label"),
                        state=row.get("uf"),
                        provider=row.get("provider"),
                        source=f"{item.table_name}:place_points",
                        insertion_timestamp=row.get("insertion_timestamp"),
                        updated_timestamp=row.get("updated_timestamp"),
                    ),
                    _candidate_aliases(row.get("place_key"), row.get("label")),
                    row.get("provider"),
                ),
                (
                    _resolve_location_id(
                        context,
                        lat=row.get("origin_lat"),
                        lon=row.get("origin_lon"),
                        aliases=(row.get("origin_key"), row.get("origin_name"), row.get("input_origin")),
                        label=row.get("origin_name") or row.get("input_origin"),
                        state=row.get("origin_uf"),
                        provider=row.get("source") or row.get("provider"),
                        source=f"{item.table_name}:origin",
                        insertion_timestamp=row.get("insertion_timestamp"),
                        updated_timestamp=row.get("updated_timestamp"),
                    ),
                    _candidate_aliases(row.get("origin_key"), row.get("origin_name"), row.get("input_origin")),
                    row.get("source") or row.get("provider"),
                ),
                (
                    _resolve_location_id(
                        context,
                        lat=row.get("destiny_lat"),
                        lon=row.get("destiny_lon"),
                        aliases=(row.get("destiny_key"), row.get("destiny_name"), row.get("input_destiny")),
                        label=row.get("destiny_name") or row.get("input_destiny"),
                        state=row.get("destiny_uf"),
                        provider=row.get("source") or row.get("provider"),
                        source=f"{item.table_name}:destiny",
                        insertion_timestamp=row.get("insertion_timestamp"),
                        updated_timestamp=row.get("updated_timestamp"),
                    ),
                    _candidate_aliases(row.get("destiny_key"), row.get("destiny_name"), row.get("input_destiny")),
                    row.get("source") or row.get("provider"),
                ),
            )
            wrote_any = False
            for location_id, aliases, provider in pairs:
                if location_id is None:
                    continue
                for alias in aliases:
                    _upsert_alias_with_report(
                        context,
                        place=alias,
                        alias_label=alias,
                        location_id=int(location_id),
                        provider=provider,
                        source=f"{item.table_name}:alias",
                        insertion_timestamp=row.get("insertion_timestamp"),
                        updated_timestamp=row.get("updated_timestamp"),
                        table_name=item.table_name,
                        row=row,
                    )
                    wrote_any = True

            for field_name in ("port_origin_name", "port_destiny_name"):
                port = _find_port(context.port_index, row.get(field_name))
                if port is None:
                    continue
                location_id = _resolve_location_id(
                    context,
                    lat=port.get("lat"),
                    lon=port.get("lon"),
                    aliases=(port.get("name"), *(port.get("aliases") or [])),
                    label=port.get("name"),
                    state=port.get("state"),
                    city=port.get("city"),
                    provider="ports_json",
                    source=f"{item.table_name}:{field_name}",
                    insertion_timestamp=row.get("insertion_timestamp"),
                    updated_timestamp=row.get("updated_timestamp"),
                )
                if location_id is None:
                    continue
                for alias in _candidate_aliases(port.get("name"), *(port.get("aliases") or [])):
                    _upsert_alias_with_report(
                        context,
                        place=alias,
                        alias_label=alias,
                        location_id=int(location_id),
                        provider="ports_json",
                        source=f"{item.table_name}:{field_name}",
                        insertion_timestamp=row.get("insertion_timestamp"),
                        updated_timestamp=row.get("updated_timestamp"),
                        table_name=item.table_name,
                        row=row,
                    )
                    wrote_any = True

            if not wrote_any:
                stats.rows_skipped += 1


def backfill_routes(context: BackfillContext, *, chunk_size: int) -> None:
    stats = context.report.phase("routes")
    columns = (
        "origin_key",
        "origin_name",
        "origin_lat",
        "origin_lon",
        "destiny_key",
        "destiny_name",
        "destiny_lat",
        "destiny_lon",
        "profile_requested",
        "profile_used",
        "is_hgv",
        "source",
        "distance_km",
        "duration_s",
        "insertion_timestamp",
        "updated_timestamp",
    )
    for item in _iter_source_rows(context, "legacy_routes", columns=columns, chunk_size=chunk_size):
        row = item.row
        stats.rows_read += 1
        origin_location_id = _resolve_location_id(
            context,
            lat=row.get("origin_lat"),
            lon=row.get("origin_lon"),
            aliases=(row.get("origin_key"), row.get("origin_name")),
            label=row.get("origin_name"),
            provider=row.get("source"),
            source=f"{item.table_name}:origin",
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        destiny_location_id = _resolve_location_id(
            context,
            lat=row.get("destiny_lat"),
            lon=row.get("destiny_lon"),
            aliases=(row.get("destiny_key"), row.get("destiny_name")),
            label=row.get("destiny_name"),
            provider=row.get("source"),
            source=f"{item.table_name}:destiny",
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        if origin_location_id is None or destiny_location_id is None:
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            context.anomalies.record(
                category="route_unresolved_location",
                message="skipping legacy route because origin or destiny could not be resolved to canonical locations",
                table_name=item.table_name,
                row=row,
            )
            continue

        requested_is_hgv = bool(row.get("is_hgv")) if row.get("is_hgv") is not None else profile_is_hgv(row.get("profile_requested"))
        existing = _route_entry_id(
            context.conn,
            table_name=context.targets.route_cache,
            origin_location_id=int(origin_location_id),
            destiny_location_id=int(destiny_location_id),
            is_hgv=requested_is_hgv,
        )
        upsert_route_run(
            context.conn,
            origin=str(row.get("origin_name") or row.get("origin_key") or ""),
            destiny=str(row.get("destiny_name") or row.get("destiny_key") or ""),
            origin_lat=row.get("origin_lat"),
            origin_lon=row.get("origin_lon"),
            destiny_lat=row.get("destiny_lat"),
            destiny_lon=row.get("destiny_lon"),
            distance_km=row.get("distance_km"),
            duration_s=row.get("duration_s"),
            profile_requested=row.get("profile_requested"),
            profile_used=row.get("profile_used"),
            source=str(row.get("source") or "legacy_routes"),
            is_hgv=requested_is_hgv,
            origin_location_id=int(origin_location_id),
            destiny_location_id=int(destiny_location_id),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
            table_name=context.targets.route_cache,
            aliases_table=context.targets.aliases,
            locations_table=context.targets.locations,
        )
        _record_route_write(
            context,
            origin_location_id=int(origin_location_id),
            destiny_location_id=int(destiny_location_id),
            is_hgv=requested_is_hgv,
            existed=(existing is not None),
        )


def backfill_bulk_runs(context: BackfillContext, *, chunk_size: int) -> None:
    stats = context.report.phase("bulk_runs")
    columns = (
        "run_id",
        "origin_key",
        "origin_name",
        "input_origin",
        "cargo_t",
        "truck_key",
        "ors_profile",
        "vessel_class",
        "include_hoteling",
        "hoteling_hours_per_call",
        "port_calls",
        "include_port_ops",
        "port_moves_per_call",
        "cargo_teu",
        "t_per_teu_default",
        "allocation_mode",
        "allocation_load_factor",
        "full_call_mode",
        "port_ops_scenario",
        "destination_set_id",
        "destination_count",
        "success_count",
        "fail_count",
        "status",
        "error_message",
        "duration_s",
        "started_timestamp",
        "completed_timestamp",
        "updated_timestamp",
    )
    for item in _iter_source_rows(context, "legacy_bulk_runs", columns=columns, chunk_size=chunk_size):
        row = item.row
        stats.rows_read += 1
        run_id = str(row.get("run_id") or "").strip()
        if not run_id:
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            context.anomalies.record(
                category="bulk_run_missing_run_id",
                message="skipping legacy bulk run without run_id",
                table_name=item.table_name,
                row=row,
            )
            continue

        origin_location_id = _resolve_location_id(
            context,
            aliases=(row.get("origin_key"), row.get("origin_name"), row.get("input_origin")),
            label=row.get("origin_name") or row.get("input_origin"),
            source=f"{item.table_name}:origin",
            insertion_timestamp=row.get("started_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        if origin_location_id is None:
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            context.anomalies.record(
                category="bulk_run_unresolved_origin",
                message="skipping legacy bulk run because origin could not be resolved to a canonical location",
                table_name=item.table_name,
                row=row,
            )
            continue

        selector = _selector_from_legacy_row(row, origin_location_id=int(origin_location_id))
        existed = _bulk_run_exists(context.conn, table_name=context.targets.bulk_runs, run_id=run_id)
        upsert_bulk_run(
            context.conn,
            run_id=run_id,
            selector=selector,
            origin_name=str(row.get("origin_name") or row.get("input_origin") or row.get("origin_key") or ""),
            input_origin=str(row.get("input_origin") or row.get("origin_name") or ""),
            destination_count=int(row.get("destination_count") or 0),
            success_count=int(row.get("success_count") or 0),
            fail_count=int(row.get("fail_count") or 0),
            status=str(row.get("status") or "completed"),
            error_message=row.get("error_message"),
            duration_s=row.get("duration_s"),
            started_timestamp=row.get("started_timestamp"),
            completed_timestamp=row.get("completed_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
            origin_location_id=int(origin_location_id),
            table_name=context.targets.bulk_runs,
            locations_table=context.targets.locations,
        )
        _record_bulk_run_write(context, run_id=run_id, existed=existed)


def backfill_bulk_run_items(context: BackfillContext, *, chunk_size: int) -> None:
    stats = context.report.phase("bulk_run_items")
    columns = (
        "run_id",
        "scenario_key",
        "origin_key",
        "origin_name",
        "origin_lat",
        "origin_lon",
        "origin_uf",
        "destiny_key",
        "destiny_name",
        "destiny_lat",
        "destiny_lon",
        "destiny_uf",
        "input_origin",
        "input_destiny",
        "destination_set_id",
        "port_origin_name",
        "port_destiny_name",
        "status",
        "error_message",
        "road_cost_r",
        "multimodal_cost_r",
        "cost_delta_r",
        "cost_savings_pct",
        "road_emissions_kg",
        "multimodal_emissions_kg",
        "emissions_delta_kg",
        "emissions_savings_pct",
        "road_distance_km",
        "sea_km",
        "is_approximation",
        "route_source",
        "approximation_reference_destiny",
        "approximation_reference_distance_km",
        "approximation_delta_straight_line_km",
        "approximation_notes",
        "ors_profile",
        "insertion_timestamp",
        "updated_timestamp",
    )
    for item in _iter_source_rows(context, "legacy_bulk_run_items", columns=columns, chunk_size=chunk_size):
        row = item.row
        stats.rows_read += 1
        run_id = str(row.get("run_id") or "").strip()
        scenario_key = _scenario_key_for_row(row)
        if not run_id or not scenario_key:
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            context.anomalies.record(
                category="bulk_item_missing_identity",
                message="skipping legacy bulk run item without run_id or scenario_key",
                table_name=item.table_name,
                row=row,
            )
            continue
        if not _bulk_run_exists(context.conn, table_name=context.targets.bulk_runs, run_id=run_id):
            stats.rows_skipped += 1
            stats.anomalies_found += 1
            context.anomalies.record(
                category="bulk_item_missing_run_header",
                message="skipping legacy bulk run item because normalized run header does not exist yet",
                table_name=item.table_name,
                row=row,
                payload={"run_id": run_id},
            )
            continue

        port_origin = _find_port(context.port_index, row.get("port_origin_name"))
        port_destiny = _find_port(context.port_index, row.get("port_destiny_name"))
        existed = _bulk_item_exists(
            context.conn,
            table_name=context.targets.bulk_items,
            run_id=run_id,
            scenario_key=scenario_key,
        )
        insert_run_result(
            context.conn,
            run_id=run_id,
            scenario_key=scenario_key,
            input_destiny=str(row.get("input_destiny") or row.get("destiny_name") or ""),
            destiny_name=row.get("destiny_name"),
            destiny_lat=row.get("destiny_lat"),
            destiny_lon=row.get("destiny_lon"),
            destiny_uf=row.get("destiny_uf"),
            port_origin_name=row.get("port_origin_name"),
            port_origin_lat=(None if port_origin is None else port_origin.get("lat")),
            port_origin_lon=(None if port_origin is None else port_origin.get("lon")),
            port_destiny_name=row.get("port_destiny_name"),
            port_destiny_lat=(None if port_destiny is None else port_destiny.get("lat")),
            port_destiny_lon=(None if port_destiny is None else port_destiny.get("lon")),
            status=str(row.get("status") or "ok"),
            error_message=row.get("error_message"),
            road_cost_r=row.get("road_cost_r"),
            multimodal_cost_r=row.get("multimodal_cost_r"),
            cost_delta_r=row.get("cost_delta_r"),
            cost_savings_pct=row.get("cost_savings_pct"),
            road_emissions_kg=row.get("road_emissions_kg"),
            multimodal_emissions_kg=row.get("multimodal_emissions_kg"),
            emissions_delta_kg=row.get("emissions_delta_kg"),
            emissions_savings_pct=row.get("emissions_savings_pct"),
            road_distance_km=row.get("road_distance_km"),
            sea_km=row.get("sea_km"),
            is_approximation=bool(row.get("is_approximation", False)),
            route_source=row.get("route_source"),
            approximation_reference_destiny=row.get("approximation_reference_destiny"),
            approximation_reference_distance_km=row.get("approximation_reference_distance_km"),
            approximation_delta_straight_line_km=row.get("approximation_delta_straight_line_km"),
            approximation_notes=row.get("approximation_notes"),
            ors_profile=str(row.get("ors_profile") or "driving-hgv"),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
            table_name=context.targets.bulk_items,
            runs_table=context.targets.bulk_runs,
            locations_table=context.targets.locations,
            route_table=context.targets.route_cache,
            aliases_table=context.targets.aliases,
        )
        _record_bulk_item_write(context, run_id=run_id, scenario_key=scenario_key, existed=existed)


def _wide_bulk_run_aggregates(context: BackfillContext, *, chunk_size: int) -> dict[str, dict[str, Any]]:
    aggregates: dict[str, dict[str, Any]] = {}
    columns = (
        "run_id",
        "scenario_key",
        "origin_key",
        "origin_name",
        "origin_lat",
        "origin_lon",
        "origin_uf",
        "input_origin",
        "destination_set_id",
        "cargo_t",
        "truck_key",
        "ors_profile",
        "vessel_class",
        "include_hoteling",
        "hoteling_hours_per_call",
        "port_calls",
        "include_port_ops",
        "port_moves_per_call",
        "cargo_teu",
        "t_per_teu_default",
        "allocation_mode",
        "allocation_load_factor",
        "full_call_mode",
        "port_ops_scenario",
        "status",
        "error_message",
        "insertion_timestamp",
        "updated_timestamp",
    )
    for item in _iter_source_rows(context, "legacy_bulk_results_wide", columns=columns, chunk_size=chunk_size):
        row = item.row
        origin_location_id = _resolve_location_id(
            context,
            lat=row.get("origin_lat"),
            lon=row.get("origin_lon"),
            aliases=(row.get("origin_key"), row.get("origin_name"), row.get("input_origin")),
            label=row.get("origin_name") or row.get("input_origin"),
            state=row.get("origin_uf"),
            source=f"{item.table_name}:origin",
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        if origin_location_id is None:
            context.report.phase("legacy_bulk_results").rows_skipped += 1
            context.report.phase("legacy_bulk_results").anomalies_found += 1
            context.anomalies.record(
                category="wide_bulk_unresolved_origin",
                message="skipping legacy wide bulk row because origin could not be resolved to a canonical location",
                table_name=item.table_name,
                row=row,
            )
            continue
        run_id = str(row.get("run_id") or _synthetic_run_id(row, origin_location_id=int(origin_location_id)))
        bucket = aggregates.setdefault(
            run_id,
            {
                "header_row": row,
                "origin_location_id": int(origin_location_id),
                "destination_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "started_timestamp": row.get("insertion_timestamp"),
                "completed_timestamp": row.get("updated_timestamp"),
                "updated_timestamp": row.get("updated_timestamp"),
            },
        )
        bucket["destination_count"] += 1
        if str(row.get("status") or "").strip().lower() == "ok":
            bucket["success_count"] += 1
        else:
            bucket["fail_count"] += 1
        if bucket["started_timestamp"] in (None, "") or (
            row.get("insertion_timestamp") not in (None, "") and row.get("insertion_timestamp") < bucket["started_timestamp"]
        ):
            bucket["started_timestamp"] = row.get("insertion_timestamp")
        if row.get("updated_timestamp") not in (None, ""):
            if bucket["completed_timestamp"] in (None, "") or row.get("updated_timestamp") > bucket["completed_timestamp"]:
                bucket["completed_timestamp"] = row.get("updated_timestamp")
            if bucket["updated_timestamp"] in (None, "") or row.get("updated_timestamp") > bucket["updated_timestamp"]:
                bucket["updated_timestamp"] = row.get("updated_timestamp")
    return aggregates


def backfill_wide_bulk_results(context: BackfillContext, *, chunk_size: int) -> None:
    stats = context.report.phase("legacy_bulk_results")
    aggregates = _wide_bulk_run_aggregates(context, chunk_size=chunk_size)
    for run_id, aggregate in sorted(aggregates.items()):
        row = aggregate["header_row"]
        selector = _selector_from_legacy_row(row, origin_location_id=int(aggregate["origin_location_id"]))
        existed = _bulk_run_exists(context.conn, table_name=context.targets.bulk_runs, run_id=run_id)
        upsert_bulk_run(
            context.conn,
            run_id=run_id,
            selector=selector,
            origin_name=str(row.get("origin_name") or row.get("input_origin") or row.get("origin_key") or ""),
            input_origin=str(row.get("input_origin") or row.get("origin_name") or ""),
            destination_count=int(aggregate["destination_count"]),
            success_count=int(aggregate["success_count"]),
            fail_count=int(aggregate["fail_count"]),
            status=str(row.get("status") or "completed"),
            error_message=row.get("error_message"),
            duration_s=None,
            started_timestamp=aggregate["started_timestamp"],
            completed_timestamp=aggregate["completed_timestamp"],
            updated_timestamp=aggregate["updated_timestamp"],
            origin_location_id=int(aggregate["origin_location_id"]),
            table_name=context.targets.bulk_runs,
            locations_table=context.targets.locations,
        )
        _record_bulk_run_write(context, run_id=run_id, existed=existed)

    columns = (
        "run_id",
        "scenario_key",
        "destination_set_id",
        "origin_key",
        "origin_name",
        "origin_lat",
        "origin_lon",
        "origin_uf",
        "input_origin",
        "input_destiny",
        "cargo_t",
        "truck_key",
        "ors_profile",
        "vessel_class",
        "include_hoteling",
        "hoteling_hours_per_call",
        "port_calls",
        "include_port_ops",
        "port_moves_per_call",
        "cargo_teu",
        "t_per_teu_default",
        "allocation_mode",
        "allocation_load_factor",
        "full_call_mode",
        "port_ops_scenario",
        "port_origin_name",
        "port_destiny_name",
        "destiny_name",
        "destiny_lat",
        "destiny_lon",
        "destiny_uf",
        "status",
        "error_message",
        "road_distance_km",
        "road_fuel_cost_r",
        "total_fuel_cost_r",
        "delta_cost_r",
        "savings_pct",
        "road_co2e_kg",
        "total_co2e_kg",
        "delta_co2e_kg",
        "emissions_savings_pct",
        "is_approximation",
        "route_source",
        "approximation_reference_destiny",
        "approximation_reference_distance_km",
        "approximation_delta_straight_line_km",
        "approximation_notes",
        "sea_km",
        "insertion_timestamp",
        "updated_timestamp",
    )
    for item in _iter_source_rows(context, "legacy_bulk_results_wide", columns=columns, chunk_size=chunk_size):
        row = item.row
        stats.rows_read += 1
        origin_location_id = _resolve_location_id(
            context,
            lat=row.get("origin_lat"),
            lon=row.get("origin_lon"),
            aliases=(row.get("origin_key"), row.get("origin_name"), row.get("input_origin")),
            label=row.get("origin_name") or row.get("input_origin"),
            state=row.get("origin_uf"),
            source=f"{item.table_name}:origin",
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
        )
        if origin_location_id is None:
            stats.rows_skipped += 1
            continue
        run_id = str(row.get("run_id") or _synthetic_run_id(row, origin_location_id=int(origin_location_id)))
        scenario_key = _scenario_key_for_row(row)
        port_origin = _find_port(context.port_index, row.get("port_origin_name"))
        port_destiny = _find_port(context.port_index, row.get("port_destiny_name"))
        existed = _bulk_item_exists(
            context.conn,
            table_name=context.targets.bulk_items,
            run_id=run_id,
            scenario_key=scenario_key,
        )
        insert_run_result(
            context.conn,
            run_id=run_id,
            scenario_key=scenario_key,
            input_destiny=str(row.get("input_destiny") or row.get("destiny_name") or ""),
            destiny_name=row.get("destiny_name"),
            destiny_lat=row.get("destiny_lat"),
            destiny_lon=row.get("destiny_lon"),
            destiny_uf=row.get("destiny_uf"),
            port_origin_name=row.get("port_origin_name"),
            port_origin_lat=(None if port_origin is None else port_origin.get("lat")),
            port_origin_lon=(None if port_origin is None else port_origin.get("lon")),
            port_destiny_name=row.get("port_destiny_name"),
            port_destiny_lat=(None if port_destiny is None else port_destiny.get("lat")),
            port_destiny_lon=(None if port_destiny is None else port_destiny.get("lon")),
            status=str(row.get("status") or "ok"),
            error_message=row.get("error_message"),
            road_cost_r=row.get("road_fuel_cost_r"),
            multimodal_cost_r=row.get("total_fuel_cost_r"),
            cost_delta_r=row.get("delta_cost_r"),
            cost_savings_pct=row.get("savings_pct"),
            road_emissions_kg=row.get("road_co2e_kg"),
            multimodal_emissions_kg=row.get("total_co2e_kg"),
            emissions_delta_kg=row.get("delta_co2e_kg"),
            emissions_savings_pct=row.get("emissions_savings_pct"),
            road_distance_km=row.get("road_distance_km"),
            sea_km=row.get("sea_km"),
            is_approximation=bool(row.get("is_approximation", False)),
            route_source=row.get("route_source"),
            approximation_reference_destiny=row.get("approximation_reference_destiny"),
            approximation_reference_distance_km=row.get("approximation_reference_distance_km"),
            approximation_delta_straight_line_km=row.get("approximation_delta_straight_line_km"),
            approximation_notes=row.get("approximation_notes"),
            ors_profile=str(row.get("ors_profile") or "driving-hgv"),
            insertion_timestamp=row.get("insertion_timestamp"),
            updated_timestamp=row.get("updated_timestamp"),
            table_name=context.targets.bulk_items,
            runs_table=context.targets.bulk_runs,
            locations_table=context.targets.locations,
            route_table=context.targets.route_cache,
            aliases_table=context.targets.aliases,
        )
        _record_bulk_item_write(context, run_id=run_id, scenario_key=scenario_key, existed=existed)


def inspect_analysis_results(context: BackfillContext) -> None:
    tables = context.report.inspect_only_tables.get("legacy_analysis_results", [])
    if not tables:
        return
    stats = context.report.phase("analysis_results")
    for table_name in tables:
        fingerprint = context.report.fingerprint.get(table_name)
        stats.rows_read += 0 if fingerprint is None else int(fingerprint.row_count)
    context.report.notes.append(
        "Legacy analysis_results tables were inspected only. They are not backfilled because they do not carry canonical coordinates or normalized run identity."
    )


def _build_post_migration_checklist(report: MigrationReport) -> list[str]:
    return [
        f"Review the anomaly report at {report.anomaly_path}.",
        f"Compare source row counts to normalized writes in {report.summary_path}.",
        "Sample a few migrated routes and confirm route_cache_entries rows resolve by canonical location ids.",
        "Sample a few migrated bulk runs and bulk_run_items rows and confirm heatmap reads resolve through normalized selectors.",
        "Validate unresolved legacy rows before deleting or archiving any legacy tables.",
    ]


def _log_schema_fingerprint(fingerprints: Mapping[str, TableFingerprint], *, targets: TargetTables) -> None:
    relevant_targets = {targets.locations, targets.aliases, targets.route_cache, targets.bulk_runs, targets.bulk_items}
    relevant = [
        fingerprint
        for fingerprint in fingerprints.values()
        if fingerprint.matches or fingerprint.table_name in relevant_targets
    ]
    for fingerprint in sorted(relevant, key=lambda item: item.table_name):
        _log.info("Schema fingerprint: %s", _relevant_table_log(fingerprint))


def build_report_paths(report_dir: Path) -> tuple[Path, Path, Path]:
    stamp = _now_stamp()
    base = report_dir / f"backfill_normalized_schema_{stamp}"
    return (
        base.with_name(base.name + "_fingerprint.json"),
        base.with_name(base.name + "_summary.json"),
        base.with_name(base.name + "_anomalies.jsonl"),
    )


def run_backfill(
    *,
    apply_changes: bool,
    chunk_size: int,
    report_dir: Path,
    targets: TargetTables,
    ports_json: Path,
) -> MigrationReport:
    fingerprint_path, summary_path, anomaly_path = build_report_paths(report_dir)
    mode = "apply" if apply_changes else "dry-run"
    conn = connect()
    anomalies = AnomalyRecorder(anomaly_path)
    try:
        report = MigrationReport(
            mode=mode,
            database_target=connection_target_summary(),
            targets=targets,
            fingerprint_path=fingerprint_path,
            summary_path=summary_path,
            anomaly_path=anomaly_path,
        )
        report.fingerprint = fingerprint_schema(conn)
        _write_json(fingerprint_path, {name: fingerprint.to_dict() for name, fingerprint in sorted(report.fingerprint.items())})
        _log_schema_fingerprint(report.fingerprint, targets=targets)

        validate_target_tables(report.fingerprint, targets)
        source_tables, target_tables, inspect_only_tables = classify_tables(report.fingerprint, targets=targets)
        report.source_tables = source_tables
        report.target_tables = target_tables
        report.inspect_only_tables = inspect_only_tables
        report.notes.append(
            "Current runtime place_points compatibility is satisfied by location_aliases. "
            "This utility reads legacy place_points-shaped tables as sources but does not write a separate wide place_points target table."
        )

        if not report.source_tables.get("legacy_routes") and not report.source_tables.get("legacy_bulk_results_wide") and not report.source_tables.get("legacy_bulk_run_items"):
            report.notes.append("No legacy route or bulk result source tables were detected by shape.")

        context = BackfillContext(
            conn=conn,
            dry_run=not apply_changes,
            targets=targets,
            port_index=_port_lookup(ports_json),
            report=report,
            anomalies=anomalies,
        )

        backfill_locations(context, chunk_size=chunk_size)
        backfill_aliases(context, chunk_size=chunk_size)
        backfill_routes(context, chunk_size=chunk_size)
        backfill_bulk_runs(context, chunk_size=chunk_size)
        backfill_bulk_run_items(context, chunk_size=chunk_size)
        backfill_wide_bulk_results(context, chunk_size=chunk_size)
        inspect_analysis_results(context)

        report.post_migration_checklist = _build_post_migration_checklist(report)

        if apply_changes:
            conn.commit()
            report.notes.append("Writes were committed.")
        else:
            conn.rollback()
            report.notes.append("Dry-run mode executed the full write path inside a transaction and rolled it back.")

        _write_json(summary_path, report.to_dict())
        return report
    except Exception:
        conn.rollback()
        raise
    finally:
        anomalies.close()
        conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="One-time backfill of legacy/wide Postgres tables into the current normalized runtime schema."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit writes. Default behavior is a dry-run that executes the write path inside a transaction and rolls it back.",
    )
    parser.add_argument("--chunk-size", type=int, default=1_000, help="Batch size for source table reads.")
    parser.add_argument("--report-dir", type=Path, default=_DEFAULT_OUTPUT_DIR, help="Directory for fingerprint, summary, and anomaly reports.")
    parser.add_argument("--ports-json", type=Path, default=_DEFAULT_PORTS_JSON, help="Port metadata JSON used to resolve port labels to canonical coordinates.")
    parser.add_argument("--log-level", default="INFO", help="Logging level.")
    parser.add_argument("--allow-network-enrichment", action="store_true", help="Reserved flag. External enrichment is intentionally disabled in this utility.")
    parser.add_argument("--locations-table", default=DEFAULT_LOCATIONS_TABLE)
    parser.add_argument("--aliases-table", default=DEFAULT_ALIASES_TABLE)
    parser.add_argument("--route-cache-table", default=DEFAULT_ROUTE_CACHE_TABLE)
    parser.add_argument("--bulk-runs-table", default=DEFAULT_RUNS_TABLE)
    parser.add_argument("--bulk-items-table", default=DEFAULT_RUN_RESULTS_TABLE)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.allow_network_enrichment:
        raise RuntimeError(
            "--allow-network-enrichment is intentionally not implemented. "
            "This utility migrates only data already present in Postgres."
        )

    init_logging(level=str(args.log_level), archive_to_storage=False)
    targets = TargetTables(
        locations=str(args.locations_table),
        aliases=str(args.aliases_table),
        route_cache=str(args.route_cache_table),
        bulk_runs=str(args.bulk_runs_table),
        bulk_items=str(args.bulk_items_table),
    ).validated()
    run_id = f"backfill-normalized-schema-{_now_stamp().lower()}"
    with bind_log_context(run_id=run_id):
        _log.info("Starting normalized schema backfill. mode=%s target=%s", "apply" if args.apply else "dry-run", connection_target_summary())
        report = run_backfill(
            apply_changes=bool(args.apply),
            chunk_size=max(int(args.chunk_size), 1),
            report_dir=Path(args.report_dir),
            targets=targets,
            ports_json=Path(args.ports_json),
        )
        _log.info(
            "Backfill complete. fingerprint=%s summary=%s anomalies=%s",
            report.fingerprint_path,
            report.summary_path,
            report.anomaly_path,
        )
        _log.info("Backfill summary: %s", json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
