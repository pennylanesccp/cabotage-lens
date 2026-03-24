from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from modules.infra.db.core import DBConnection, mark_schema_ready, safe_table_name, schema_is_ready, to_float

_DDL_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
      origin_name         TEXT      NOT NULL
    , destiny_name        TEXT      NOT NULL
    , cargo_t             REAL      NOT NULL
    , road_distance_km    REAL
    , road_fuel_liters    REAL
    , road_fuel_kg        REAL
    , road_fuel_cost_r    REAL
    , road_co2e_kg        REAL
    , mm_road_fuel_liters REAL
    , mm_road_fuel_kg     REAL
    , mm_road_fuel_cost_r REAL
    , mm_road_co2e_kg     REAL
    , sea_km              REAL
    , sea_fuel_kg         REAL
    , sea_fuel_cost_r     REAL
    , sea_co2e_kg         REAL
    , total_fuel_cost_r   REAL
    , total_co2e_kg       REAL
    , total_fuel_kg       REAL
    , delta_cost_r        REAL
    , delta_co2e_kg       REAL
    , insertion_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_IDX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_{table}_dest
    ON {table} (destiny_name);
"""


@dataclass(frozen=True)
class MultimodalHeatmapRecord:
    origin_name: str
    destiny_name: str
    cargo_t: float
    destiny_lat: Optional[float]
    destiny_lon: Optional[float]
    destiny_uf: Optional[str]
    port_destiny_name: Optional[str]
    road_cost_r: Optional[float]
    multimodal_cost_r: Optional[float]
    cost_delta_r: Optional[float]
    cost_savings_pct: Optional[float]
    road_emissions_kg: Optional[float]
    multimodal_emissions_kg: Optional[float]
    emissions_delta_kg: Optional[float]
    emissions_savings_pct: Optional[float]
    road_distance_km: Optional[float]
    sea_km: Optional[float]
    updated_timestamp: Any


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _derive_delta_and_pct(baseline: Optional[float], alternative: Optional[float]) -> tuple[Optional[float], Optional[float]]:
    baseline_value = to_float(baseline)
    alternative_value = to_float(alternative)
    if baseline_value is None or alternative_value is None:
        return None, None
    delta_value = float(baseline_value) - float(alternative_value)
    if float(baseline_value) <= 0.0:
        return delta_value, None
    return delta_value, (delta_value / float(baseline_value)) * 100.0


def ensure_results_table(conn: DBConnection, table_name: str) -> None:
    table = safe_table_name(table_name)
    if schema_is_ready(conn, "multimodal_results", table):
        return
    conn.execute(_DDL_SQL.format(table=table))
    conn.execute(_IDX_SQL.format(table=table))
    mark_schema_ready(conn, "multimodal_results", table)


def upsert_result(
    conn: DBConnection,
    table_name: str,
    *,
    origin_name: str,
    destiny_name: str,
    cargo_t: float,
    road_distance_km: Optional[float] = None,
    road_fuel_liters: Optional[float] = None,
    road_fuel_kg: Optional[float] = None,
    road_fuel_cost_r: Optional[float] = None,
    road_co2e_kg: Optional[float] = None,
    mm_road_fuel_liters: Optional[float] = None,
    mm_road_fuel_kg: Optional[float] = None,
    mm_road_fuel_cost_r: Optional[float] = None,
    mm_road_co2e_kg: Optional[float] = None,
    sea_km: Optional[float] = None,
    sea_fuel_kg: Optional[float] = None,
    sea_fuel_cost_r: Optional[float] = None,
    sea_co2e_kg: Optional[float] = None,
    total_fuel_kg: Optional[float] = None,
    total_fuel_cost_r: Optional[float] = None,
    total_co2e_kg: Optional[float] = None,
    delta_cost_r: Optional[float] = None,
    delta_co2e_kg: Optional[float] = None,
) -> None:
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)

    conn.execute(
        f"""
        INSERT INTO {table} (
              origin_name
            , destiny_name
            , cargo_t
            , road_distance_km
            , road_fuel_liters
            , road_fuel_kg
            , road_fuel_cost_r
            , road_co2e_kg
            , mm_road_fuel_liters
            , mm_road_fuel_kg
            , mm_road_fuel_cost_r
            , mm_road_co2e_kg
            , sea_km
            , sea_fuel_kg
            , sea_fuel_cost_r
            , sea_co2e_kg
            , total_fuel_kg
            , total_fuel_cost_r
            , total_co2e_kg
            , delta_cost_r
            , delta_co2e_kg
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(destiny_name) DO UPDATE SET
              origin_name         = excluded.origin_name
            , cargo_t             = excluded.cargo_t
            , road_distance_km    = excluded.road_distance_km
            , road_fuel_liters    = excluded.road_fuel_liters
            , road_fuel_kg        = excluded.road_fuel_kg
            , road_fuel_cost_r    = excluded.road_fuel_cost_r
            , road_co2e_kg        = excluded.road_co2e_kg
            , mm_road_fuel_liters = excluded.mm_road_fuel_liters
            , mm_road_fuel_kg     = excluded.mm_road_fuel_kg
            , mm_road_fuel_cost_r = excluded.mm_road_fuel_cost_r
            , mm_road_co2e_kg     = excluded.mm_road_co2e_kg
            , sea_km              = excluded.sea_km
            , sea_fuel_kg         = excluded.sea_fuel_kg
            , sea_fuel_cost_r     = excluded.sea_fuel_cost_r
            , sea_co2e_kg         = excluded.sea_co2e_kg
            , total_fuel_kg       = excluded.total_fuel_kg
            , total_fuel_cost_r   = excluded.total_fuel_cost_r
            , total_co2e_kg       = excluded.total_co2e_kg
            , delta_cost_r        = excluded.delta_cost_r
            , delta_co2e_kg       = excluded.delta_co2e_kg
        """,
        (
            origin_name,
            destiny_name,
            to_float(cargo_t),
            to_float(road_distance_km),
            to_float(road_fuel_liters),
            to_float(road_fuel_kg),
            to_float(road_fuel_cost_r),
            to_float(road_co2e_kg),
            to_float(mm_road_fuel_liters),
            to_float(mm_road_fuel_kg),
            to_float(mm_road_fuel_cost_r),
            to_float(mm_road_co2e_kg),
            to_float(sea_km),
            to_float(sea_fuel_kg),
            to_float(sea_fuel_cost_r),
            to_float(sea_co2e_kg),
            to_float(total_fuel_kg),
            to_float(total_fuel_cost_r),
            to_float(total_co2e_kg),
            to_float(delta_cost_r),
            to_float(delta_co2e_kg),
        ),
    )


def list_heatmap_results(
    conn: DBConnection,
    *,
    origin_names: Iterable[str],
    cargo_t: float,
    table_name: str,
) -> List[MultimodalHeatmapRecord]:
    table = safe_table_name(table_name)
    ensure_results_table(conn, table)

    normalized_origins = sorted(
        {
            str(value).strip().lower()
            for value in origin_names
            if str(value).strip()
        }
    )
    if not normalized_origins:
        return []

    placeholders = ", ".join(["?"] * len(normalized_origins))
    rows = conn.execute(
        f"""
        WITH ranked AS (
            SELECT
                  origin_name
                , destiny_name
                , cargo_t
                , road_distance_km
                , road_fuel_cost_r
                , total_fuel_cost_r
                , road_co2e_kg
                , total_co2e_kg
                , sea_km
                , insertion_timestamp
                , ROW_NUMBER() OVER (
                      PARTITION BY LOWER(TRIM(destiny_name))
                      ORDER BY insertion_timestamp DESC, destiny_name ASC
                  ) AS row_rank
            FROM {table}
            WHERE cargo_t = ?
              AND LOWER(TRIM(origin_name)) IN ({placeholders})
        )
        SELECT
              origin_name
            , destiny_name
            , cargo_t
            , road_distance_km
            , road_fuel_cost_r
            , total_fuel_cost_r
            , road_co2e_kg
            , total_co2e_kg
            , sea_km
            , insertion_timestamp
        FROM ranked
        WHERE row_rank = 1
        ORDER BY destiny_name ASC, insertion_timestamp DESC
        """,
        [to_float(cargo_t), *normalized_origins],
    ).fetchall()

    records: list[MultimodalHeatmapRecord] = []
    for row in rows:
        road_cost_r = to_float(row[4])
        multimodal_cost_r = to_float(row[5])
        road_emissions_kg = to_float(row[6])
        multimodal_emissions_kg = to_float(row[7])
        cost_delta_r, cost_savings_pct = _derive_delta_and_pct(road_cost_r, multimodal_cost_r)
        emissions_delta_kg, emissions_savings_pct = _derive_delta_and_pct(road_emissions_kg, multimodal_emissions_kg)
        records.append(
            MultimodalHeatmapRecord(
                origin_name=str(row[0]),
                destiny_name=str(row[1]),
                cargo_t=float(row[2]),
                destiny_lat=None,
                destiny_lon=None,
                destiny_uf=None,
                port_destiny_name=None,
                road_cost_r=road_cost_r,
                multimodal_cost_r=multimodal_cost_r,
                cost_delta_r=cost_delta_r,
                cost_savings_pct=cost_savings_pct,
                road_emissions_kg=road_emissions_kg,
                multimodal_emissions_kg=multimodal_emissions_kg,
                emissions_delta_kg=emissions_delta_kg,
                emissions_savings_pct=emissions_savings_pct,
                road_distance_km=to_float(row[3]),
                sea_km=to_float(row[8]),
                updated_timestamp=row[9],
            )
        )
    return records
