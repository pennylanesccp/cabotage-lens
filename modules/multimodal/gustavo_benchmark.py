from __future__ import annotations

import csv
import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from modules.infra.log_manager import get_logger
from modules.multimodal.builder import (
    build_path_geometry_from_resolved,
    load_routing_assets,
    resolve_point_for_geometry,
)
from modules.multimodal.container_efficiency import DEFAULT_VESSEL_CLASS
from modules.multimodal.evaluator import PreparedEvaluationContext, evaluate_path, prepare_evaluation_context
from modules.multimodal.port_ops import DEFAULT_PORT_OPS_SCENARIO

_log = get_logger(__name__)

DEFAULT_GUSTAVO_WORKBOOK_PATH = Path("docs/references/core/Dados Relatorio 2.xlsx")
DEFAULT_BENCHMARK_CSV_PATH = Path("data/processed/cabotage_data/gustavo_excel_benchmark.csv")
DEFAULT_BENCHMARK_JSON_PATH = Path("data/processed/cabotage_data/gustavo_excel_benchmark_summary.json")

_CITY_QUERY_MAP = {
    "Manaus": "Manaus, AM",
    "Fortaleza": "Fortaleza, CE",
    "Recife": "Recife, PE",
    "Salvador": "Salvador, BA",
    "Rio de Janeiro": "Rio de Janeiro, RJ",
    "Sao Paulo": "São Paulo, SP",
}

_CITY_POINT_MAP = {
    "Manaus, AM": {"label": "Manaus, AM", "lat": -3.119028, "lon": -60.021731, "uf": "AM"},
    "Fortaleza, CE": {"label": "Fortaleza, CE", "lat": -3.731862, "lon": -38.526670, "uf": "CE"},
    "Recife, PE": {"label": "Recife, PE", "lat": -8.047562, "lon": -34.877002, "uf": "PE"},
    "Salvador, BA": {"label": "Salvador, BA", "lat": -12.977750, "lon": -38.501630, "uf": "BA"},
    "Rio de Janeiro, RJ": {"label": "Rio de Janeiro, RJ", "lat": -22.906847, "lon": -43.172897, "uf": "RJ"},
    "São Paulo, SP": {"label": "São Paulo, SP", "lat": -23.550520, "lon": -46.633308, "uf": "SP"},
}


@dataclass(frozen=True)
class WorkbookBenchmarkPair:
    origin_city: str
    destiny_city: str
    origin_query: str
    destiny_query: str
    workbook_road_kg_co2e_per_container: float
    workbook_cabotage_kg_co2e_per_container: float
    workbook_savings_pct: float


def load_gustavo_workbook_pairs(
    workbook_path: Path | str = DEFAULT_GUSTAVO_WORKBOOK_PATH,
    *,
    selected_pairs: Iterable[str] | None = None,
) -> tuple[list[WorkbookBenchmarkPair], dict[str, Any]]:
    workbook = Path(workbook_path)
    summary_sheet = pd.read_excel(workbook, sheet_name="Resumo Cenario Base", header=None)
    cabotage_sheet = pd.read_excel(workbook, sheet_name="Cabotagem Total Base", header=None)

    road_matrix = _extract_named_matrix(summary_sheet, header_label="Origem / Destino")
    cabotage_matrix = _extract_named_matrix(cabotage_sheet, header_label="Cidade")

    selected = _normalize_selected_pairs(selected_pairs)
    pairs: list[WorkbookBenchmarkPair] = []
    for origin_city, destinations in road_matrix.items():
        for destiny_city, road_value in destinations.items():
            if origin_city == destiny_city or road_value <= 0.0:
                continue
            cabotage_value = cabotage_matrix.get(origin_city, {}).get(destiny_city)
            if cabotage_value is None or cabotage_value <= 0.0:
                continue
            pair_key = f"{origin_city}|{destiny_city}"
            if selected and pair_key.casefold() not in selected:
                continue

            origin_query = _CITY_QUERY_MAP.get(origin_city)
            destiny_query = _CITY_QUERY_MAP.get(destiny_city)
            if not origin_query or not destiny_query:
                continue

            savings_pct = (1.0 - (float(cabotage_value) / float(road_value))) * 100.0
            pairs.append(
                WorkbookBenchmarkPair(
                    origin_city=origin_city,
                    destiny_city=destiny_city,
                    origin_query=origin_query,
                    destiny_query=destiny_query,
                    workbook_road_kg_co2e_per_container=float(road_value),
                    workbook_cabotage_kg_co2e_per_container=float(cabotage_value),
                    workbook_savings_pct=float(savings_pct),
                )
            )

    summary = {
        "workbook_path": str(workbook.resolve()),
        "pair_count": len(pairs),
        "city_count": len({pair.origin_city for pair in pairs} | {pair.destiny_city for pair in pairs}),
        "weekly_road_kg_co2e": _extract_total_origin_sum(summary_sheet, header_label="Origem / Destino", total_header="Total Origem CO2e (kg)"),
        "weekly_cabotage_kg_co2e": _extract_total_origin_sum(cabotage_sheet, header_label="Cidade", total_header="Total Origem"),
    }
    return pairs, summary


def compare_gustavo_pairs_with_model(
    pairs: Iterable[WorkbookBenchmarkPair],
    *,
    cargo_t: float = 14.0,
    cargo_teu: float = 1.0,
    t_per_teu_default: float = 14.0,
    allocation_load_factor: float = 0.8,
    include_hoteling: bool = True,
    hoteling_hours_per_call: float = 14.0,
    port_calls: int = 2,
    include_port_ops: bool = True,
    full_call_mode: bool = False,
    port_ops_scenario: str = DEFAULT_PORT_OPS_SCENARIO,
    vessel_class: str = DEFAULT_VESSEL_CLASS,
) -> list[dict[str, Any]]:
    comparison_rows: list[dict[str, Any]] = []
    pairs_list = list(pairs)
    if not pairs_list:
        return comparison_rows

    ors, ports, sea_matrix, db_path = load_routing_assets()
    point_cache: dict[str, dict[str, Any]] = {}
    prepared_context = prepare_evaluation_context(
        vessel_class=vessel_class,
        include_hoteling=include_hoteling,
        hoteling_hours_per_call=hoteling_hours_per_call,
        port_calls=port_calls,
        include_port_ops=include_port_ops,
        port_ops_scenario=port_ops_scenario,
    )

    for pair in pairs_list:
        row = asdict(pair)
        row.update(
            {
                "cargo_t": float(cargo_t),
                "cargo_teu": float(cargo_teu),
                "status": "pending",
                "error": None,
            }
        )
        try:
            comparison = _evaluate_pair(
                pair,
                ors=ors,
                ports=ports,
                sea_matrix=sea_matrix,
                db_path=db_path,
                point_cache=point_cache,
                prepared_context=prepared_context,
                cargo_t=float(cargo_t),
                cargo_teu=float(cargo_teu),
                t_per_teu_default=float(t_per_teu_default),
                allocation_load_factor=float(allocation_load_factor),
                include_hoteling=bool(include_hoteling),
                hoteling_hours_per_call=float(hoteling_hours_per_call),
                port_calls=int(port_calls),
                include_port_ops=bool(include_port_ops),
                full_call_mode=bool(full_call_mode),
                port_ops_scenario=str(port_ops_scenario),
                vessel_class=str(vessel_class),
            )
            row.update(comparison)
            row["status"] = "ok"
        except Exception as exc:
            row["status"] = "error"
            row["error"] = str(exc)
            _log.warning(
                "Gustavo benchmark failed for %s -> %s: %s",
                pair.origin_query,
                pair.destiny_query,
                exc,
            )
        comparison_rows.append(row)

    return comparison_rows


def summarize_gustavo_comparison(
    comparison_rows: Iterable[dict[str, Any]],
    workbook_summary: dict[str, Any],
) -> dict[str, Any]:
    rows = list(comparison_rows)
    successful = [row for row in rows if row.get("status") == "ok"]
    skipped = [row for row in rows if row.get("status") == "skipped_model"]

    road_abs_pct_diff = [
        abs(float(row["road_pct_diff"]))
        for row in successful
        if isinstance(row.get("road_pct_diff"), (int, float))
    ]
    cabotage_abs_pct_diff = [
        abs(float(row["cabotage_pct_diff"]))
        for row in successful
        if isinstance(row.get("cabotage_pct_diff"), (int, float))
    ]

    summary = {
        "workbook": workbook_summary,
        "comparison": {
            "rows_total": len(rows),
            "rows_successful": len(successful),
            "rows_skipped_model": len(skipped),
            "rows_failed": len(rows) - len(successful) - len(skipped),
            "directional_route_metric_rows": sum(
                1
                for row in successful
                if str(row.get("sea_fuel_g_per_tnm_source") or "").startswith("sea_matrix_directional")
            ),
            "mean_abs_pct_diff_road": _safe_mean(road_abs_pct_diff),
            "median_abs_pct_diff_road": _safe_median(road_abs_pct_diff),
            "mean_abs_pct_diff_cabotage": _safe_mean(cabotage_abs_pct_diff),
            "median_abs_pct_diff_cabotage": _safe_median(cabotage_abs_pct_diff),
            "mean_workbook_savings_pct": _safe_mean(
                [float(row["workbook_savings_pct"]) for row in rows if isinstance(row.get("workbook_savings_pct"), (int, float))]
            ),
            "mean_model_savings_pct": _safe_mean(
                [float(row["model_savings_pct"]) for row in successful if isinstance(row.get("model_savings_pct"), (int, float))]
            ),
        },
    }
    return summary


def write_gustavo_benchmark_outputs(
    comparison_rows: Iterable[dict[str, Any]],
    summary: dict[str, Any],
    *,
    output_csv_path: Path | str = DEFAULT_BENCHMARK_CSV_PATH,
    output_json_path: Path | str = DEFAULT_BENCHMARK_JSON_PATH,
) -> tuple[Path, Path]:
    rows = list(comparison_rows)
    csv_path = Path(output_csv_path).resolve()
    json_path = Path(output_json_path).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    payload = {
        "summary": summary,
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def _evaluate_pair(
    pair: WorkbookBenchmarkPair,
    *,
    ors: Any,
    ports: list[dict[str, Any]],
    sea_matrix: Any,
    db_path: Path | str | None,
    point_cache: dict[str, dict[str, Any]],
    prepared_context: PreparedEvaluationContext,
    cargo_t: float,
    cargo_teu: float,
    t_per_teu_default: float,
    allocation_load_factor: float,
    include_hoteling: bool,
    hoteling_hours_per_call: float,
    port_calls: int,
    include_port_ops: bool,
    full_call_mode: bool,
    port_ops_scenario: str,
    vessel_class: str,
) -> dict[str, Any]:
    origin_pt = _resolve_benchmark_point(
        pair.origin_query,
        ors=ors,
        db_path=db_path,
        point_cache=point_cache,
    )
    destiny_pt = _resolve_benchmark_point(
        pair.destiny_query,
        ors=ors,
        db_path=db_path,
        point_cache=point_cache,
    )
    if not origin_pt or not destiny_pt:
        raise RuntimeError("Failed to resolve origin or destiny coordinates.")

    geometry = build_path_geometry_from_resolved(
        origin_pt,
        destiny_pt,
        ors=ors,
        ports=ports,
        sea_matrix=sea_matrix,
        db_path=db_path,
    )
    if not geometry or geometry.get("status") != "ok":
        raise RuntimeError("Failed to build path geometry.")

    result = evaluate_path(
        geometry,
        cargo_t=cargo_t,
        cargo_teu=cargo_teu,
        t_per_teu_default=t_per_teu_default,
        allocation_load_factor=allocation_load_factor,
        allocation_mode=None,
        include_hoteling=include_hoteling,
        hoteling_hours_per_call=hoteling_hours_per_call,
        port_calls=port_calls,
        include_port_ops=include_port_ops,
        full_call_mode=full_call_mode,
        port_ops_scenario=port_ops_scenario,
        vessel_class=vessel_class,
        prepared_context=prepared_context,
    )
    if not result:
        raise RuntimeError("Failed to evaluate path.")

    road_model_kg = float(result["road_only"]["co2e"])
    cabotage_model_kg = float(result["multimodal"]["total_co2e"])
    model_savings_pct = ((1.0 - (cabotage_model_kg / road_model_kg)) * 100.0) if road_model_kg > 0.0 else None
    sea_inputs = result.get("inputs", {})
    sea_result = result.get("multimodal", {}).get("sea", {})

    return {
        "origin_label": geometry["origin"]["label"],
        "destiny_label": geometry["destiny"]["label"],
        "port_origin_name": geometry["port_origin"]["name"],
        "port_destiny_name": geometry["port_destiny"]["name"],
        "road_distance_km": float(geometry["road_direct"].get("distance_km") or 0.0),
        "sea_distance_km": float(geometry["sea_leg"].get("distance_km") or 0.0),
        "model_road_kg_co2e_per_container": road_model_kg,
        "model_cabotage_kg_co2e_per_container": cabotage_model_kg,
        "road_pct_diff": _pct_diff(road_model_kg, pair.workbook_road_kg_co2e_per_container),
        "cabotage_pct_diff": _pct_diff(cabotage_model_kg, pair.workbook_cabotage_kg_co2e_per_container),
        "model_savings_pct": model_savings_pct,
        "sea_fuel_g_per_tnm": sea_inputs.get("sea_fuel_g_per_tnm"),
        "sea_fuel_g_per_tnm_source": sea_inputs.get("sea_fuel_g_per_tnm_source"),
        "sea_route_match_rate_tonne_nm": sea_inputs.get("sea_route_match_rate_tonne_nm"),
        "sea_route_matched_segment_count": sea_inputs.get("sea_route_matched_segment_count"),
        "sea_route_voyage_count": sea_inputs.get("sea_route_voyage_count"),
        "sea_route_matched_imo_count": sea_inputs.get("sea_route_matched_imo_count"),
        "sea_route_corridor_leg_count": sea_inputs.get("sea_route_corridor_leg_count"),
        "sea_route_corridor_port_path": sea_inputs.get("sea_route_corridor_port_path"),
        "road_cost_brl": float(result["road_only"]["cost"]),
        "multimodal_cost_brl": float(result["multimodal"]["total_cost"]),
        "sea_sailing_fuel_kg": float(sea_result.get("fuel_kg_sailing") or 0.0),
        "sea_total_fuel_kg": float(sea_result.get("fuel_kg") or 0.0),
    }


def _resolve_benchmark_point(
    query: str,
    *,
    ors: Any,
    db_path: Path | str | None,
    point_cache: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    static_point = _CITY_POINT_MAP.get(str(query or "").strip())
    if static_point:
        point_cache.setdefault(static_point["label"], dict(static_point))
        return dict(static_point)
    return resolve_point_for_geometry(query, ors, db_path=db_path, point_cache=point_cache)


def _normalize_selected_pairs(selected_pairs: Iterable[str] | None) -> set[str]:
    normalized: set[str] = set()
    for item in selected_pairs or []:
        text = str(item or "").strip()
        if not text:
            continue
        if "|" in text:
            origin_city, destiny_city = text.split("|", 1)
            normalized.add(
                f"{_normalize_city_name(origin_city)}|{_normalize_city_name(destiny_city)}".casefold()
            )
        else:
            normalized.add(text.casefold())
    return normalized


def _extract_named_matrix(sheet: pd.DataFrame, *, header_label: str) -> dict[str, dict[str, float]]:
    header_row = _find_row_by_first_label(sheet, header_label)
    if header_row is None:
        raise ValueError(f"Matrix header not found: {header_label}")

    columns = _extract_header_values(sheet, row_index=header_row, start_col=2)
    matrix: dict[str, dict[str, float]] = {}
    row_index = header_row + 1
    while row_index < len(sheet.index):
        row_label = _normalize_city_name(sheet.iat[row_index, 1] if 1 < sheet.shape[1] else None)
        if not row_label:
            break
        if row_label.casefold().startswith("total "):
            break

        row_values: dict[str, float] = {}
        for column_offset, destiny_city in enumerate(columns, start=2):
            if column_offset >= sheet.shape[1]:
                continue
            numeric_value = _float_or_none(sheet.iat[row_index, column_offset])
            if numeric_value is None:
                continue
            row_values[destiny_city] = float(numeric_value)
        if row_values:
            matrix[row_label] = row_values
        row_index += 1
    return matrix


def _extract_total_origin_sum(
    sheet: pd.DataFrame,
    *,
    header_label: str,
    total_header: str,
) -> float | None:
    header_row = _find_row_with_total_header(sheet, header_label=header_label, total_header=total_header)
    if header_row is None:
        return None

    total_column = None
    for column_index in range(2, sheet.shape[1]):
        value = str(sheet.iat[header_row, column_index] or "").strip()
        if value == total_header:
            total_column = column_index
            break
    if total_column is None:
        return None

    values: list[float] = []
    row_index = header_row + 1
    while row_index < len(sheet.index):
        row_label = _normalize_city_name(sheet.iat[row_index, 1] if 1 < sheet.shape[1] else None)
        if not row_label:
            break
        if row_label.casefold().startswith("total "):
            break
        numeric_value = _float_or_none(sheet.iat[row_index, total_column])
        if numeric_value is not None:
            values.append(float(numeric_value))
        row_index += 1
    return round(sum(values), 6) if values else None


def _find_row_with_total_header(sheet: pd.DataFrame, *, header_label: str, total_header: str) -> int | None:
    for row_index in range(len(sheet.index)):
        if 1 >= sheet.shape[1]:
            break
        value = str(sheet.iat[row_index, 1] or "").strip()
        if value != header_label:
            continue
        for column_index in range(2, sheet.shape[1]):
            if str(sheet.iat[row_index, column_index] or "").strip() == total_header:
                return row_index
    return None


def _find_row_by_first_label(sheet: pd.DataFrame, header_label: str) -> int | None:
    for row_index in range(len(sheet.index)):
        if 1 >= sheet.shape[1]:
            break
        value = str(sheet.iat[row_index, 1] or "").strip()
        if value == header_label:
            return row_index
    return None


def _extract_header_values(sheet: pd.DataFrame, *, row_index: int, start_col: int) -> list[str]:
    values: list[str] = []
    column_index = start_col
    while column_index < sheet.shape[1]:
        city_name = _normalize_city_name(sheet.iat[row_index, column_index])
        if not city_name:
            break
        values.append(city_name)
        column_index += 1
    return values


def _normalize_city_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""
    normalized = (
        text.replace("Manaus (via Belém)", "Manaus")
        .replace("São Paulo", "Sao Paulo")
    )
    return normalized


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_diff(model_value: float, workbook_value: float) -> float | None:
    if workbook_value <= 0.0:
        return None
    return ((float(model_value) - float(workbook_value)) / float(workbook_value)) * 100.0


def _safe_mean(values: Iterable[float]) -> float | None:
    sequence = [float(value) for value in values]
    if not sequence:
        return None
    return float(statistics.fmean(sequence))


def _safe_median(values: Iterable[float]) -> float | None:
    sequence = [float(value) for value in values]
    if not sequence:
        return None
    return float(statistics.median(sequence))
