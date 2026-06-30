#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Summarize timestamped validation reruns for report insertion."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create combined route, delta, and markdown summary files for validation reruns."
    )
    parser.add_argument("--batch001b-csv", type=Path, required=True)
    parser.add_argument("--batch001b-previous-csv", type=Path, required=True)
    parser.add_argument("--batch002-csv", type=Path, required=True)
    parser.add_argument("--batch002-previous-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-label", default="20260630_portops_hoteling")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    batch001b_rows = [_normalize_batch001b(row) for row in _read_csv(args.batch001b_csv)]
    batch001b_previous = [_normalize_batch001b(row) for row in _read_csv(args.batch001b_previous_csv)]
    batch002_rows = [_normalize_batch002(row) for row in _read_csv(args.batch002_csv)]
    batch002_previous = [_normalize_batch002(row) for row in _read_csv(args.batch002_previous_csv)]

    route_rows = batch001b_rows + batch002_rows
    delta_rows = _build_delta_rows(
        current=batch001b_rows,
        previous=batch001b_previous,
    ) + _build_delta_rows(
        current=batch002_rows,
        previous=batch002_previous,
    )

    summary = _build_summary(
        route_rows=route_rows,
        delta_rows=delta_rows,
        run_label=args.run_label,
        input_paths={
            "batch001b_csv": args.batch001b_csv,
            "batch001b_previous_csv": args.batch001b_previous_csv,
            "batch002_csv": args.batch002_csv,
            "batch002_previous_csv": args.batch002_previous_csv,
        },
    )

    route_csv = output_dir / f"tf_validation_{args.run_label}_routes.csv"
    delta_csv = output_dir / f"tf_validation_{args.run_label}_delta.csv"
    summary_json = output_dir / f"tf_validation_{args.run_label}_summary.json"
    summary_md = output_dir / f"tf_validation_{args.run_label}_summary.md"

    _write_csv(route_csv, route_rows)
    _write_csv(delta_csv, delta_rows)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md.write_text(_render_markdown_summary(summary), encoding="utf-8")

    print(
        json.dumps(
            {
                "route_csv": str(route_csv),
                "delta_csv": str(delta_csv),
                "summary_json": str(summary_json),
                "summary_md": str(summary_md),
                "route_rows": len(route_rows),
                "delta_rows": len(delta_rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _to_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "sim"}:
        return True
    if text in {"0", "false", "no", "n", "nao"}:
        return False
    return None


def _winner(road: float | None, cabotage: float | None) -> str | None:
    if road is None or cabotage is None:
        return None
    if abs(cabotage - road) <= 1e-9:
        return "tie"
    return "cabotage_lower_emissions" if cabotage < road else "road_lower_emissions"


def _pct_delta(new: float | None, old: float | None) -> float | None:
    if new is None or old in (None, 0.0):
        return None
    return ((new - old) / old) * 100.0


def _component_sum(*values: float | None) -> float | None:
    if any(value is None for value in values):
        return None
    return float(sum(value for value in values if value is not None))


def _normalize_batch001b(row: dict[str, Any]) -> dict[str, Any]:
    road = _to_float(row.get("road_emissions_kgco2e"))
    cabotage = _to_float(row.get("multimodal_emissions_kgco2e"))
    navigation = _to_float(row.get("navigation_emissions_kgco2e"))
    hoteling = _to_float(row.get("hoteling_emissions_kgco2e"))
    port_ops = _to_float(row.get("port_ops_emissions_kgco2e"))
    pre = _to_float(row.get("pre_carriage_emissions_kgco2e"))
    on = _to_float(row.get("on_carriage_emissions_kgco2e"))
    winner = row.get("emissions_winner") or _winner(road, cabotage)
    case_id = str(row.get("case_id") or "").strip()
    route_label = f"{row.get('origin', '')} -> {row.get('destination', '')}"
    return {
        "batch": "Batch 001B sensitivity",
        "route_key": case_id,
        "case_id": case_id,
        "origin": row.get("origin"),
        "destination": row.get("destination"),
        "route_label": route_label,
        "output_status": row.get("output_status"),
        "validation_status": row.get("validation_status"),
        "road_emissions_kgco2e": road,
        "cabotage_emissions_kgco2e": cabotage,
        "navigation_emissions_kgco2e": navigation,
        "hoteling_emissions_kgco2e": hoteling,
        "port_ops_emissions_kgco2e": port_ops,
        "pre_carriage_emissions_kgco2e": pre,
        "on_carriage_emissions_kgco2e": on,
        "component_total_emissions_kgco2e": _to_float(row.get("component_total_emissions_kgco2e")),
        "component_total_delta_kgco2e": _to_float(row.get("component_total_delta_kgco2e")),
        "road_vs_cabotage_pct_difference": _to_float(row.get("road_vs_cabotage_pct_difference")),
        "cabotage_emissions_savings_pct": _to_float(row.get("cabotage_emissions_savings_pct")),
        "emissions_winner": winner,
        "selected_origin_port": row.get("selected_origin_port"),
        "selected_destination_port": row.get("selected_destination_port"),
        "maritime_distance_km": _to_float(row.get("maritime_distance_km")),
        "maritime_distance_source": row.get("maritime_distance_source"),
        "maritime_distance_source_type": row.get("maritime_distance_source_type"),
        "fallback_flags": row.get("fallback_flags"),
        "hoteling_requested": _to_bool(row.get("hoteling_requested")),
        "hoteling_included": _to_bool(row.get("hoteling_included")),
        "hoteling_exclusion_reason": row.get("hoteling_exclusion_reason"),
        "hoteling_source_level": row.get("hoteling_source_level"),
        "hoteling_fallback_flag": _to_bool(row.get("hoteling_fallback_flag")),
        "port_ops_included": _to_bool(row.get("port_ops_included")),
        "port_ops_source_level": row.get("port_ops_source_level"),
        "port_ops_source_level_counts": row.get("port_ops_source_level_counts"),
        "port_ops_warning_count": _to_float(row.get("port_ops_warning_count")),
        "port_ops_warnings": row.get("port_ops_warnings"),
        "port_ops_fallback_flag": _to_bool(row.get("port_ops_fallback_flag")),
        "component_columns_available": navigation is not None or hoteling is not None or port_ops is not None,
    }


def _normalize_batch002(row: dict[str, Any]) -> dict[str, Any]:
    road = _to_float(row.get("model_road_kg_co2e_per_container"))
    cabotage = _to_float(row.get("model_cabotage_kg_co2e_per_container"))
    navigation = _to_float(row.get("navigation_emissions_kgco2e"))
    hoteling = _to_float(row.get("hoteling_emissions_kgco2e"))
    port_ops = _to_float(row.get("port_ops_emissions_kgco2e"))
    pre = _to_float(row.get("pre_carriage_emissions_kgco2e"))
    on = _to_float(row.get("on_carriage_emissions_kgco2e"))
    route_key = f"{row.get('origin_city', '')}|{row.get('destiny_city', '')}"
    route_label = f"{row.get('origin_city', '')} -> {row.get('destiny_city', '')}"
    return {
        "batch": "Batch 002 Gustavo/Costa benchmark",
        "route_key": route_key,
        "case_id": route_key,
        "origin": row.get("origin_city"),
        "destination": row.get("destiny_city"),
        "route_label": route_label,
        "output_status": row.get("status"),
        "validation_status": row.get("status"),
        "road_emissions_kgco2e": road,
        "cabotage_emissions_kgco2e": cabotage,
        "navigation_emissions_kgco2e": navigation,
        "hoteling_emissions_kgco2e": hoteling,
        "port_ops_emissions_kgco2e": port_ops,
        "pre_carriage_emissions_kgco2e": pre,
        "on_carriage_emissions_kgco2e": on,
        "component_total_emissions_kgco2e": _to_float(row.get("component_total_emissions_kgco2e")),
        "component_total_delta_kgco2e": _to_float(row.get("component_total_delta_kgco2e")),
        "road_vs_cabotage_pct_difference": _to_float(row.get("road_vs_cabotage_pct_difference")),
        "cabotage_emissions_savings_pct": _to_float(row.get("cabotage_emissions_savings_pct")),
        "emissions_winner": row.get("model_emissions_winner") or _winner(road, cabotage),
        "workbook_emissions_winner": row.get("workbook_emissions_winner"),
        "modal_conclusion_matches_workbook": _to_bool(row.get("modal_conclusion_matches_workbook")),
        "selected_origin_port": row.get("port_origin_name"),
        "selected_destination_port": row.get("port_destiny_name"),
        "maritime_distance_km": _to_float(row.get("sea_distance_km")),
        "maritime_distance_source": row.get("sea_fuel_g_per_tnm_source"),
        "maritime_distance_source_type": row.get("sailing_fuel_calc_mode"),
        "fallback_flags": "",
        "hoteling_requested": _to_bool(row.get("hoteling_requested")),
        "hoteling_included": _to_bool(row.get("hoteling_included")),
        "hoteling_exclusion_reason": row.get("hoteling_exclusion_reason"),
        "hoteling_source_level": row.get("hoteling_source_level"),
        "hoteling_fallback_flag": _to_bool(row.get("hoteling_fallback_flag")),
        "port_ops_included": _to_bool(row.get("port_ops_included")),
        "port_ops_source_level": row.get("port_ops_source_level"),
        "port_ops_source_level_counts": row.get("port_ops_source_level_counts"),
        "port_ops_warning_count": _to_float(row.get("port_ops_warning_count")),
        "port_ops_warnings": row.get("port_ops_warnings"),
        "port_ops_fallback_flag": _to_bool(row.get("port_ops_fallback_flag")),
        "component_columns_available": navigation is not None or hoteling is not None or port_ops is not None,
    }


def _build_delta_rows(
    *,
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    previous_by_key = {row["route_key"]: row for row in previous}
    out: list[dict[str, Any]] = []
    for row in current:
        old = previous_by_key.get(row["route_key"], {})
        new_hotel_port = _component_sum(
            row.get("hoteling_emissions_kgco2e"),
            row.get("port_ops_emissions_kgco2e"),
        )
        old_hotel_port = _component_sum(
            old.get("hoteling_emissions_kgco2e"),
            old.get("port_ops_emissions_kgco2e"),
        )
        old_winner = old.get("emissions_winner")
        new_winner = row.get("emissions_winner")
        out.append(
            {
                "batch": row.get("batch"),
                "route_key": row.get("route_key"),
                "case_id": row.get("case_id"),
                "route_label": row.get("route_label"),
                "previous_route_found": bool(old),
                "previous_road_emissions_kgco2e": old.get("road_emissions_kgco2e"),
                "new_road_emissions_kgco2e": row.get("road_emissions_kgco2e"),
                "road_delta_kgco2e": _delta(row.get("road_emissions_kgco2e"), old.get("road_emissions_kgco2e")),
                "road_delta_pct": _pct_delta(row.get("road_emissions_kgco2e"), old.get("road_emissions_kgco2e")),
                "previous_cabotage_emissions_kgco2e": old.get("cabotage_emissions_kgco2e"),
                "new_cabotage_emissions_kgco2e": row.get("cabotage_emissions_kgco2e"),
                "cabotage_delta_kgco2e": _delta(
                    row.get("cabotage_emissions_kgco2e"),
                    old.get("cabotage_emissions_kgco2e"),
                ),
                "cabotage_delta_pct": _pct_delta(
                    row.get("cabotage_emissions_kgco2e"),
                    old.get("cabotage_emissions_kgco2e"),
                ),
                "previous_hoteling_emissions_kgco2e": old.get("hoteling_emissions_kgco2e"),
                "new_hoteling_emissions_kgco2e": row.get("hoteling_emissions_kgco2e"),
                "previous_port_ops_emissions_kgco2e": old.get("port_ops_emissions_kgco2e"),
                "new_port_ops_emissions_kgco2e": row.get("port_ops_emissions_kgco2e"),
                "previous_hoteling_plus_port_ops_kgco2e": old_hotel_port,
                "new_hoteling_plus_port_ops_kgco2e": new_hotel_port,
                "hoteling_plus_port_ops_delta_kgco2e": _delta(new_hotel_port, old_hotel_port),
                "hoteling_plus_port_ops_share_of_cabotage_pct": (
                    (new_hotel_port / row.get("cabotage_emissions_kgco2e")) * 100.0
                    if new_hotel_port is not None and row.get("cabotage_emissions_kgco2e") not in (None, 0.0)
                    else None
                ),
                "previous_emissions_winner": old_winner,
                "new_emissions_winner": new_winner,
                "modal_conclusion_changed": (
                    old_winner != new_winner if old_winner is not None and new_winner is not None else False
                ),
                "component_columns_available_in_previous": bool(old.get("component_columns_available")),
                "component_columns_available_in_new": bool(row.get("component_columns_available")),
                "port_ops_source_level": row.get("port_ops_source_level"),
                "hoteling_source_level": row.get("hoteling_source_level"),
                "hoteling_exclusion_reason": row.get("hoteling_exclusion_reason"),
            }
        )
    return out


def _delta(new: Any, old: Any) -> float | None:
    new_float = _to_float(new)
    old_float = _to_float(old)
    if new_float is None or old_float is None:
        return None
    return new_float - old_float


def _affected_sort_key(row: dict[str, Any]) -> float:
    cabotage_delta = _to_float(row.get("cabotage_delta_kgco2e"))
    hoteling_port_ops = _to_float(row.get("new_hoteling_plus_port_ops_kgco2e")) or 0.0
    return max(abs(cabotage_delta or 0.0), abs(hoteling_port_ops))


def _build_summary(
    *,
    route_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
    run_label: str,
    input_paths: dict[str, Path],
) -> dict[str, Any]:
    executed = [
        row
        for row in route_rows
        if row.get("road_emissions_kgco2e") is not None and row.get("cabotage_emissions_kgco2e") is not None
    ]
    checks = _validation_checks(route_rows)
    affected = sorted(
        [
            row
            for row in delta_rows
            if row.get("new_road_emissions_kgco2e") is not None
            and row.get("new_cabotage_emissions_kgco2e") is not None
        ],
        key=_affected_sort_key,
        reverse=True,
    )
    modal_changes = [row for row in delta_rows if row.get("modal_conclusion_changed")]
    by_batch = {}
    for batch in sorted({row.get("batch") for row in route_rows}):
        rows = [row for row in route_rows if row.get("batch") == batch]
        executed_batch = [
            row
            for row in rows
            if row.get("road_emissions_kgco2e") is not None and row.get("cabotage_emissions_kgco2e") is not None
        ]
        by_batch[batch] = _aggregate_rows(executed_batch)

    return {
        "run_label": run_label,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "methodology": (
            "Current checkout rerun with report component export for hoteling and port operations. "
            "Port operations use observed/estimated-average/documented-default/unavailable source levels; "
            "hoteling uses the current evaluator boundary and records inclusion or explicit exclusion."
        ),
        "input_paths": {key: str(path) for key, path in input_paths.items()},
        "route_rows": len(route_rows),
        "executed_rows": len(executed),
        "aggregate": _aggregate_rows(executed),
        "aggregate_by_batch": by_batch,
        "port_ops_source_levels": dict(Counter(str(row.get("port_ops_source_level") or "") for row in executed)),
        "hoteling_source_levels": dict(Counter(str(row.get("hoteling_source_level") or "") for row in executed)),
        "hoteling_exclusion_reasons": dict(Counter(str(row.get("hoteling_exclusion_reason") or "") for row in executed)),
        "validation_checks": checks,
        "modal_conclusion_changes": modal_changes,
        "routes_most_affected": affected[:10],
        "warnings": _summary_warnings(route_rows, delta_rows, checks),
    }


def _aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "rows": 0,
            "mean_road_emissions_kgco2e": None,
            "mean_cabotage_emissions_kgco2e": None,
            "mean_cabotage_savings_pct": None,
            "sum_hoteling_emissions_kgco2e": None,
            "sum_port_ops_emissions_kgco2e": None,
        }
    return {
        "rows": len(rows),
        "mean_road_emissions_kgco2e": _mean(row.get("road_emissions_kgco2e") for row in rows),
        "mean_cabotage_emissions_kgco2e": _mean(row.get("cabotage_emissions_kgco2e") for row in rows),
        "mean_cabotage_savings_pct": _mean(row.get("cabotage_emissions_savings_pct") for row in rows),
        "sum_hoteling_emissions_kgco2e": _sum_available(row.get("hoteling_emissions_kgco2e") for row in rows),
        "sum_port_ops_emissions_kgco2e": _sum_available(row.get("port_ops_emissions_kgco2e") for row in rows),
        "sum_navigation_emissions_kgco2e": _sum_available(row.get("navigation_emissions_kgco2e") for row in rows),
        "winners": dict(Counter(str(row.get("emissions_winner") or "") for row in rows)),
    }


def _mean(values: Any) -> float | None:
    parsed = [_to_float(value) for value in values]
    parsed = [value for value in parsed if value is not None]
    return None if not parsed else sum(parsed) / len(parsed)


def _sum_available(values: Any) -> float | None:
    parsed = [_to_float(value) for value in values]
    parsed = [value for value in parsed if value is not None]
    return None if not parsed else sum(parsed)


def _validation_checks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    checked = []
    failures: list[str] = []
    warnings: list[str] = []
    for row in rows:
        if row.get("road_emissions_kgco2e") is None or row.get("cabotage_emissions_kgco2e") is None:
            continue
        route = str(row.get("route_label") or row.get("case_id"))
        delta = _to_float(row.get("component_total_delta_kgco2e"))
        if delta is None:
            failures.append(f"{route}: component total delta unavailable")
        elif abs(delta) > 1e-6:
            failures.append(f"{route}: component total delta {delta:.9f} kg CO2e")

        hoteling_requested = row.get("hoteling_requested")
        hoteling_included = row.get("hoteling_included")
        hoteling_value = _to_float(row.get("hoteling_emissions_kgco2e"))
        hoteling_exclusion = row.get("hoteling_exclusion_reason")
        if hoteling_requested and hoteling_included and (hoteling_value is None or hoteling_value <= 0.0):
            failures.append(f"{route}: hoteling included but nonpositive")
        if hoteling_requested and not hoteling_included and not hoteling_exclusion:
            failures.append(f"{route}: hoteling requested but neither included nor explicitly excluded")

        port_ops_included = row.get("port_ops_included")
        port_ops_value = _to_float(row.get("port_ops_emissions_kgco2e"))
        port_ops_source_level = row.get("port_ops_source_level")
        if port_ops_included and (port_ops_value is None or port_ops_value <= 0.0):
            failures.append(f"{route}: port ops included but nonpositive")
        if port_ops_included and not port_ops_source_level:
            failures.append(f"{route}: port ops included without source level")
        if port_ops_included and port_ops_source_level != "observed" and row.get("port_ops_fallback_flag") is not True:
            failures.append(f"{route}: port ops fallback source not flagged")
        if hoteling_included and row.get("hoteling_source_level") != "observed" and row.get("hoteling_fallback_flag") is not True:
            failures.append(f"{route}: hoteling fallback source not flagged")

        if row.get("road_vs_cabotage_pct_difference") is None:
            warnings.append(f"{route}: road/cabotage percent difference unavailable")
        checked.append(route)

    return {
        "checked_executed_rows": len(checked),
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
    }


def _summary_warnings(
    route_rows: list[dict[str, Any]],
    delta_rows: list[dict[str, Any]],
    checks: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not checks.get("passed"):
        warnings.append("Validation checks reported failures; inspect validation_checks.failures.")
    if any(not row.get("component_columns_available_in_previous") for row in delta_rows):
        warnings.append(
            "Previous comparison files did not expose hoteling/port-ops component columns for every row; "
            "component deltas are therefore unavailable for those rows."
        )
    if any(row.get("hoteling_exclusion_reason") == "included_in_transport_work_intensity" for row in route_rows):
        warnings.append(
            "Some rows explicitly exclude separate hoteling because transport-work intensity is used; "
            "this prevents double counting rather than silently zeroing hoteling."
        )
    if any(str(row.get("port_ops_source_level") or "") == "literature_default" for row in route_rows):
        warnings.append(
            "Port-ops rows using literature_default reflect the documented moves-based scenario because no "
            "observed per-port records were supplied in the active artifact."
        )
    return warnings


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _fmt(value: Any, digits: int = 2) -> str:
    parsed = _to_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.{digits}f}"


def _render_markdown_summary(summary: dict[str, Any]) -> str:
    aggregate = summary["aggregate"]
    lines = [
        "# Hoteling and Port-Ops Validation Rerun Summary",
        "",
        f"Run label: `{summary['run_label']}`",
        "",
        f"Generated at: `{summary['generated_at']}`",
        "",
        f"Git SHA: `{summary.get('git_sha') or 'unavailable'}`",
        "",
        "Methodology reflected: current checkout rerun with explicit hoteling and port-operation component export, fallback/source-level flags, and component-total checks.",
        "",
        "## Output Files",
        "",
    ]
    for key, path in summary["input_paths"].items():
        lines.append(f"- Input `{key}`: `{path}`")
    lines.extend(
        [
            "",
            "## Aggregate Results",
            "",
            f"- Route rows: {summary['route_rows']}",
            f"- Executed/model rows with emissions: {summary['executed_rows']}",
            f"- Mean road emissions: {_fmt(aggregate.get('mean_road_emissions_kgco2e'))} kg CO2e",
            f"- Mean cabotage/multimodal emissions: {_fmt(aggregate.get('mean_cabotage_emissions_kgco2e'))} kg CO2e",
            f"- Mean cabotage savings: {_fmt(aggregate.get('mean_cabotage_savings_pct'))}%",
            f"- Sum navigation emissions over executed rows: {_fmt(aggregate.get('sum_navigation_emissions_kgco2e'))} kg CO2e",
            f"- Sum hoteling emissions over executed rows: {_fmt(aggregate.get('sum_hoteling_emissions_kgco2e'))} kg CO2e",
            f"- Sum port-ops emissions over executed rows: {_fmt(aggregate.get('sum_port_ops_emissions_kgco2e'))} kg CO2e",
            "",
            "These aggregate values are unweighted over the rows present in the generated validation outputs; Batch 002 rows are per-container benchmark rows.",
            "",
            "## Validation Checks",
            "",
            f"- Checked executed rows: {summary['validation_checks']['checked_executed_rows']}",
            f"- Passed: `{summary['validation_checks']['passed']}`",
        ]
    )
    if summary["validation_checks"]["failures"]:
        lines.append("- Failures:")
        lines.extend(f"  - {item}" for item in summary["validation_checks"]["failures"])
    if summary["validation_checks"]["warnings"]:
        lines.append("- Warnings:")
        lines.extend(f"  - {item}" for item in summary["validation_checks"]["warnings"])

    lines.extend(
        [
            "",
            "## Routes Most Affected",
            "",
            "| Route | Batch | New hoteling+port-ops kg CO2e | Cabotage delta kg CO2e | Modal change |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in summary["routes_most_affected"][:10]:
        lines.append(
            "| "
            f"{row.get('route_label')} | "
            f"{row.get('batch')} | "
            f"{_fmt(row.get('new_hoteling_plus_port_ops_kgco2e'))} | "
            f"{_fmt(row.get('cabotage_delta_kgco2e'))} | "
            f"{row.get('modal_conclusion_changed')} |"
        )

    lines.extend(["", "## Modal Conclusion Changes", ""])
    if summary["modal_conclusion_changes"]:
        lines.extend(
            f"- {row.get('route_label')}: {row.get('previous_emissions_winner')} -> {row.get('new_emissions_winner')}"
            for row in summary["modal_conclusion_changes"]
        )
    else:
        lines.append("- No route changed road-vs-cabotage emissions winner in the available previous-vs-new comparison.")

    lines.extend(["", "## Warnings And Limits", ""])
    lines.extend(f"- {item}" for item in summary["warnings"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
