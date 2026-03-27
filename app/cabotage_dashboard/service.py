from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from modules.infra.db.core import DBConnection, db_session, table_exists

_VOYAGES_QUERY = """
SELECT
      voyage_id
    , imo
    , started_at
    , ended_at
    , duration_hours
    , closed_loop
    , closed_by
    , origin_port_code
    , origin_port_name
    , destination_port_code
    , destination_port_name
    , stop_count
    , intermediate_stop_count
    , call_count_total
    , loaded_teu_total
    , unloaded_teu_total
    , moved_teu_total
    , net_teu_total
    , loaded_weight_t_total
    , unloaded_weight_t_total
    , moved_weight_t_total
    , net_weight_t_total
FROM antaq_voyages
"""

_STOPS_QUERY = """
SELECT
      voyage_id
    , sequence
    , stop_type
    , port_key
    , port_code
    , port_name
    , atracacao_port_name
    , municipality
    , state
    , first_atracacao_at
    , last_atracacao_at
    , call_count
    , loaded_teu
    , unloaded_teu
    , moved_teu
    , net_teu
    , loaded_weight_t
    , unloaded_weight_t
    , moved_weight_t
    , net_weight_t
    , observed_span_hours
    , wait_for_berth_hours
    , wait_for_operation_start_hours
    , operation_hours
    , wait_for_departure_hours
    , berth_time_hours
    , port_stay_hours
FROM antaq_voyage_stops
"""

_VOYAGE_NUMERIC_COLUMNS: tuple[str, ...] = (
    "duration_hours",
    "stop_count",
    "intermediate_stop_count",
    "call_count_total",
    "loaded_teu_total",
    "unloaded_teu_total",
    "moved_teu_total",
    "net_teu_total",
    "loaded_weight_t_total",
    "unloaded_weight_t_total",
    "moved_weight_t_total",
    "net_weight_t_total",
)
_STOP_NUMERIC_COLUMNS: tuple[str, ...] = (
    "sequence",
    "call_count",
    "loaded_teu",
    "unloaded_teu",
    "moved_teu",
    "net_teu",
    "loaded_weight_t",
    "unloaded_weight_t",
    "moved_weight_t",
    "net_weight_t",
    "observed_span_hours",
    "wait_for_berth_hours",
    "wait_for_operation_start_hours",
    "operation_hours",
    "wait_for_departure_hours",
    "berth_time_hours",
    "port_stay_hours",
)
_REQUIRED_TABLES: tuple[str, ...] = (
    "antaq_voyages",
    "antaq_voyage_stops",
)


class CabotageDashboardDataError(RuntimeError):
    """Raised when the dashboard source tables are unavailable or invalid."""


@dataclass(frozen=True)
class CabotageDashboardDataset:
    voyages: pd.DataFrame
    stops: pd.DataFrame
    segments: pd.DataFrame
    loaded_at: datetime
    db_target: str


@dataclass(frozen=True)
class CabotageDashboardView:
    voyages: pd.DataFrame
    stops: pd.DataFrame
    segments: pd.DataFrame


def load_dashboard_dataset(database_url: str | None = None) -> CabotageDashboardDataset:
    with db_session(database_url) as conn:
        _ensure_required_tables(conn)
        voyages = _fetch_dataframe(conn, _VOYAGES_QUERY)
        stops = _fetch_dataframe(conn, _STOPS_QUERY)
        db_target = str(conn.target)

    voyages = _normalize_voyages(voyages)
    stops = _normalize_stops(stops)
    segments = build_voyage_segments(voyages=voyages, stops=stops)

    return CabotageDashboardDataset(
        voyages=voyages,
        stops=stops,
        segments=segments,
        loaded_at=datetime.now(UTC),
        db_target=db_target,
    )


def filter_dashboard_dataset(
    dataset: CabotageDashboardDataset,
    *,
    years: list[int] | None = None,
    focus_port: str | None = None,
    closure_modes: list[str] | None = None,
) -> CabotageDashboardView:
    voyages = dataset.voyages.copy()

    if years is not None:
        voyages = voyages[voyages["reference_year"].isin(years)].copy()

    if closure_modes is not None:
        voyages = voyages[voyages["closure_label"].isin(closure_modes)].copy()

    if focus_port:
        port_name = str(focus_port).strip()
        relevant_stop_ids = set(
            dataset.stops.loc[dataset.stops["port_label"] == port_name, "voyage_id"].astype(str)
        )
        relevant_origin_ids = set(
            voyages.loc[voyages["origin_port_label"] == port_name, "voyage_id"].astype(str)
        )
        relevant_destination_ids = set(
            voyages.loc[voyages["destination_port_label"] == port_name, "voyage_id"].astype(str)
        )
        relevant_ids = relevant_stop_ids | relevant_origin_ids | relevant_destination_ids
        voyages = voyages[voyages["voyage_id"].isin(relevant_ids)].copy()

    voyage_ids = set(voyages["voyage_id"].astype(str))
    stops = dataset.stops[dataset.stops["voyage_id"].isin(voyage_ids)].copy()
    segments = dataset.segments[dataset.segments["voyage_id"].isin(voyage_ids)].copy()

    return CabotageDashboardView(voyages=voyages, stops=stops, segments=segments)


def build_voyage_segments(*, voyages: pd.DataFrame, stops: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "voyage_id",
        "imo",
        "segment_sequence",
        "from_port_code",
        "from_port_label",
        "to_port_code",
        "to_port_label",
        "from_stop_type",
        "to_stop_type",
        "cargo_weight_t",
        "cargo_teu",
        "departed_at",
        "arrived_at",
    ]
    if voyages.empty or stops.empty:
        return pd.DataFrame(columns=columns)

    voyage_lookup = voyages.set_index("voyage_id")[["imo"]].to_dict("index")
    ordered_stops = (
        stops.sort_values(
            ["voyage_id", "sequence", "first_atracacao_at", "last_atracacao_at"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    rows: list[dict[str, Any]] = []
    for voyage_id, group in ordered_stops.groupby("voyage_id", sort=False):
        sequence_rows = group.reset_index(drop=True)
        cumulative_weight_t = 0.0
        cumulative_teu = 0.0
        imo = str(voyage_lookup.get(voyage_id, {}).get("imo") or "").strip()

        for idx in range(len(sequence_rows) - 1):
            current = sequence_rows.iloc[idx]
            nxt = sequence_rows.iloc[idx + 1]

            cumulative_weight_t += float(current.get("net_weight_t") or 0.0)
            cumulative_teu += float(current.get("net_teu") or 0.0)
            cargo_weight_t = max(cumulative_weight_t, 0.0)
            cargo_teu = max(cumulative_teu, 0.0)
            if cargo_weight_t <= 0.0 and cargo_teu <= 0.0:
                continue

            rows.append(
                {
                    "voyage_id": str(voyage_id),
                    "imo": imo,
                    "segment_sequence": idx,
                    "from_port_code": _text_or_blank(current.get("port_code")),
                    "from_port_label": _text_or_blank(current.get("port_label")),
                    "to_port_code": _text_or_blank(nxt.get("port_code")),
                    "to_port_label": _text_or_blank(nxt.get("port_label")),
                    "from_stop_type": _text_or_blank(current.get("stop_type")),
                    "to_stop_type": _text_or_blank(nxt.get("stop_type")),
                    "cargo_weight_t": cargo_weight_t,
                    "cargo_teu": cargo_teu,
                    "departed_at": current.get("last_atracacao_at"),
                    "arrived_at": nxt.get("first_atracacao_at"),
                }
            )

    out = pd.DataFrame(rows, columns=columns)
    if out.empty:
        return out

    out["cargo_weight_t"] = pd.to_numeric(out["cargo_weight_t"], errors="coerce").fillna(0.0)
    out["cargo_teu"] = pd.to_numeric(out["cargo_teu"], errors="coerce").fillna(0.0)
    for column in ("departed_at", "arrived_at"):
        out[column] = pd.to_datetime(out[column], utc=True, errors="coerce")
    return out


def _ensure_required_tables(conn: DBConnection) -> None:
    missing = [name for name in _REQUIRED_TABLES if not table_exists(conn, name)]
    if missing:
        raise CabotageDashboardDataError(
            "Cabotage dashboard tables are missing in Supabase Postgres. "
            "Apply the voyage migration and load the normalized ANTAQ tables first: "
            + ", ".join(missing)
        )


def _fetch_dataframe(conn: DBConnection, sql: str) -> pd.DataFrame:
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    description = getattr(cursor, "description", None) or []
    columns = [getattr(item, "name", item[0]) for item in description]
    return pd.DataFrame(rows, columns=columns)


def _normalize_voyages(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in _VOYAGE_NUMERIC_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
    for column in ("started_at", "ended_at"):
        if column in out.columns:
            out[column] = pd.to_datetime(out[column], utc=True, errors="coerce")

    out["closed_loop"] = out["closed_loop"].fillna(False).astype(bool)
    out["closed_by"] = out["closed_by"].astype("string")
    out["closure_label"] = out["closed_by"].fillna("unknown").astype(str).str.strip().replace("", "unknown")
    out["origin_port_label"] = _coalesce_label(
        out.get("origin_port_name"),
        out.get("origin_port_code"),
        fallback="Unknown origin",
    )
    out["destination_port_label"] = _coalesce_label(
        out.get("destination_port_name"),
        out.get("destination_port_code"),
        fallback="Unknown destination",
    )
    reference_ts = out["started_at"].combine_first(out["ended_at"])
    out["reference_year"] = reference_ts.dt.year.astype("Int64")
    out["reference_month"] = reference_ts.dt.strftime("%Y-%m").fillna("")
    return out


def _normalize_stops(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in _STOP_NUMERIC_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
    for column in ("first_atracacao_at", "last_atracacao_at"):
        if column in out.columns:
            out[column] = pd.to_datetime(out[column], utc=True, errors="coerce")

    out["stop_type"] = out["stop_type"].astype("string").fillna("unknown").astype(str).str.strip()
    out["port_label"] = _coalesce_label(
        out.get("port_name"),
        out.get("atracacao_port_name"),
        out.get("port_code"),
        out.get("port_key"),
        fallback="Unknown port",
    )
    return out


def _coalesce_label(*series: Any, fallback: str) -> pd.Series:
    resolved: pd.Series | None = None
    for candidate in series:
        if candidate is None:
            continue
        current = pd.Series(candidate, copy=False).fillna("").astype(str).str.strip()
        if resolved is None:
            resolved = current
        else:
            resolved = resolved.where(resolved != "", current)
    if resolved is None:
        return pd.Series(dtype="string")
    return resolved.where(resolved != "", fallback)


def _text_or_blank(value: Any) -> str:
    return str(value or "").strip()
