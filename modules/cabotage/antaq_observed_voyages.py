from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from modules.infra.data_assets import resolve_data_asset_path
from modules.infra.log_manager import get_logger

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = Path("data/raw/cabotage_data")
DEFAULT_PORTS_PATH = Path("data/processed/cabotage_data/ports_br.json")
DEFAULT_OUTPUT_PATH = Path("data/processed/cabotage_data/antaq_cabotage_observed_voyages.json")
_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def build_and_write_observed_voyages(
    *,
    years: Iterable[str],
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
    raw_dir: Path | str = DEFAULT_RAW_DIR,
    ports_path: Path | str = DEFAULT_PORTS_PATH,
    max_gap_hours: float = 240.0,
) -> tuple[Path, dict[str, Any]]:
    payload = build_observed_voyages_payload(
        years=years,
        raw_dir=raw_dir,
        ports_path=ports_path,
        max_gap_hours=max_gap_hours,
    )
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target, payload


def build_observed_voyages_payload(
    *,
    years: Iterable[str],
    raw_dir: Path | str = DEFAULT_RAW_DIR,
    ports_path: Path | str = DEFAULT_PORTS_PATH,
    max_gap_hours: float = 240.0,
) -> dict[str, Any]:
    normalized_years = _normalize_years(years)
    raw_root = Path(raw_dir).resolve()
    ports_resolved = resolve_data_asset_path(ports_path)

    _log.info(
        "Building observed ANTAQ voyages in Python years=%s raw_dir=%s ports=%s max_gap_hours=%.1f",
        ",".join(normalized_years),
        raw_root,
        ports_resolved,
        float(max_gap_hours),
    )

    alias_map = _build_port_alias_map(ports_resolved)
    atracacao_result = _read_atracacao_map(normalized_years, raw_root)
    tempos_result = _read_tempos_atracacao_map(normalized_years, raw_root)
    carga_result = _read_carga_call_stats(normalized_years, raw_root)
    voyage_result = _build_observed_voyages(
        atracacao_map=atracacao_result["map"],
        call_stats_map=carga_result["map"],
        tempos_atracacao_map=tempos_result["map"],
        alias_map=alias_map,
        gap_hours=float(max_gap_hours),
    )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "years": normalized_years,
        "source_files": {
            "atracacao": [f"data/raw/cabotage_data/{year}Atracacao.txt" for year in normalized_years],
            "carga": [f"data/raw/cabotage_data/{year}Carga.txt" for year in normalized_years],
            "tempos_atracacao": [f"data/raw/cabotage_data/{year}TemposAtracacao.txt" for year in normalized_years],
        },
        "filters": {
            "tipo_navegacao_carga": "Cabotagem",
            "containerized_rule": "TEU > 0 or cargo labels contain 'conteiner'",
            "imo_required": True,
        },
        "segmentation": {
            "consecutive_same_port_calls_collapsed": True,
            "voyage_closed_when_returning_to_origin_port": True,
            "max_gap_hours_between_stops": float(max_gap_hours),
            "note": "First and last voyages for an IMO can be partial because the observation window is limited.",
        },
        "stats": {
            "atracacao_rows": int(atracacao_result["row_count"]),
            "tempos_atracacao_rows": int(tempos_result["row_count"]),
            "carga_rows_processed": int(carga_result["processed_rows"]),
            "carga_rows_kept": int(carga_result["kept_rows"]),
            "joined_calls": int(voyage_result["joined_calls"]),
            "dropped_calls_without_atracacao": int(voyage_result["dropped_without_atracacao"]),
            "dropped_calls_without_imo": int(voyage_result["dropped_without_imo"]),
            "joined_calls_with_time_metrics": int(voyage_result["calls_with_time_metrics"]),
            "joined_calls_without_time_metrics": int(voyage_result["calls_without_time_metrics"]),
            "unique_imos": int(voyage_result["unique_imos"]),
            "collapsed_stops": int(voyage_result["collapsed_stops"]),
            "voyages": len(voyage_result["voyages"]),
        },
        "voyages": voyage_result["voyages"],
    }
    return payload


def _normalize_years(years: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in years:
        year = str(raw).strip()
        if not re.fullmatch(r"\d{4}", year):
            raise ValueError(f"Invalid ANTAQ year: {raw!r}")
        if year in seen:
            continue
        normalized.append(year)
        seen.add(year)
    if not normalized:
        raise ValueError("At least one ANTAQ year must be provided.")
    return normalized


def _to_ascii_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _NON_ALNUM_RE.sub("_", text.lower())
    return text.strip("_")


def _normalize_port_key(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip().lower()


def _parse_decimal(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    text = re.sub(r"[^\d,.\-+]", "", text.replace(" ", ""))
    if not text:
        return 0.0
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _parse_antaq_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    return datetime.strptime(text, _DATE_FORMAT)


def _format_date_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def _round_number(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def _row_accessor(header: list[str]) -> tuple[dict[str, int], callable]:
    index_map = {_to_ascii_key(name): idx for idx, name in enumerate(header)}

    def _get(fields: list[str], key: str) -> str:
        idx = index_map.get(key)
        if idx is None or idx >= len(fields):
            return ""
        return fields[idx]

    return index_map, _get


def _iter_txt_rows(path: Path) -> Iterable[tuple[list[str], callable]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        try:
            header = next(reader)
        except StopIteration:
            return
        _, getter = _row_accessor(header)
        for fields in reader:
            yield fields, getter


def _build_port_alias_map(path: Path | str) -> dict[str, str]:
    resolved = resolve_data_asset_path(path)
    ports = json.loads(Path(resolved).read_text(encoding="utf-8-sig"))
    alias_map: dict[str, str] = {}
    for port in ports if isinstance(ports, list) else []:
        if not isinstance(port, dict):
            continue
        canonical_name = str(port.get("name") or "").strip()
        if not canonical_name:
            continue
        aliases = [canonical_name, str(port.get("city") or "").strip()]
        raw_aliases = port.get("aliases")
        if isinstance(raw_aliases, list):
            aliases.extend(str(item or "").strip() for item in raw_aliases)
        for alias in aliases:
            key = _normalize_port_key(alias)
            if key and key not in alias_map:
                alias_map[key] = canonical_name
    return alias_map


def _required_raw_path(raw_root: Path, year: str, table: str) -> Path:
    path = raw_root / f"{year}{table}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path


def _read_atracacao_map(years: list[str], raw_root: Path) -> dict[str, Any]:
    mapping: dict[str, dict[str, Any]] = {}
    row_count = 0
    for year in years:
        path = _required_raw_path(raw_root, year, "Atracacao")
        _log.info("Reading ANTAQ atracacao file year=%s path=%s", year, path)
        for fields, get_field in _iter_txt_rows(path):
            row_count += 1
            id_atracacao = get_field(fields, "idatracacao").strip()
            if not id_atracacao:
                continue
            mapping[id_atracacao] = {
                "id_atracacao": id_atracacao,
                "year": year,
                "imo": get_field(fields, "n_do_imo").strip(),
                "atracacao_at": _parse_antaq_date(get_field(fields, "data_atracacao")),
                "chegada_at": _parse_antaq_date(get_field(fields, "data_chegada")),
                "desatracacao_at": _parse_antaq_date(get_field(fields, "data_desatracacao")),
                "porto_atracacao": get_field(fields, "porto_atracacao").strip(),
                "municipio": get_field(fields, "municipio").strip(),
                "uf": get_field(fields, "uf").strip(),
                "terminal": get_field(fields, "terminal").strip(),
                "cdtup": get_field(fields, "cdtup").strip(),
                "tipo_navegacao_atracacao": get_field(fields, "tipo_de_navegacao_da_atracacao").strip(),
                "tipo_operacao": get_field(fields, "tipo_de_operacao").strip(),
            }
    return {"map": mapping, "row_count": row_count}


def _new_time_metrics_empty() -> dict[str, Any]:
    return {
        "wait_for_berth_hours": 0.0,
        "wait_for_operation_start_hours": 0.0,
        "operation_hours": 0.0,
        "wait_for_departure_hours": 0.0,
        "berth_time_hours": 0.0,
        "port_stay_hours": 0.0,
        "source_row_count": 0,
    }


def _copy_time_metrics(time_metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "wait_for_berth_hours": float(time_metrics["wait_for_berth_hours"]),
        "wait_for_operation_start_hours": float(time_metrics["wait_for_operation_start_hours"]),
        "operation_hours": float(time_metrics["operation_hours"]),
        "wait_for_departure_hours": float(time_metrics["wait_for_departure_hours"]),
        "berth_time_hours": float(time_metrics["berth_time_hours"]),
        "port_stay_hours": float(time_metrics["port_stay_hours"]),
        "source_row_count": int(time_metrics["source_row_count"]),
    }


def _merge_time_metrics(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key in (
        "wait_for_berth_hours",
        "wait_for_operation_start_hours",
        "operation_hours",
        "wait_for_departure_hours",
        "berth_time_hours",
        "port_stay_hours",
    ):
        target[key] += float(incoming[key])
    target["source_row_count"] += int(incoming["source_row_count"])


def _read_tempos_atracacao_map(years: list[str], raw_root: Path) -> dict[str, Any]:
    mapping: dict[str, dict[str, Any]] = {}
    row_count = 0
    for year in years:
        path = _required_raw_path(raw_root, year, "TemposAtracacao")
        _log.info("Reading ANTAQ tempos de atracacao file year=%s path=%s", year, path)
        for fields, get_field in _iter_txt_rows(path):
            row_count += 1
            id_atracacao = get_field(fields, "idatracacao").strip()
            if not id_atracacao:
                continue
            mapping[id_atracacao] = {
                "id_atracacao": id_atracacao,
                "wait_for_berth_hours": _parse_decimal(get_field(fields, "tesperaatracacao")),
                "wait_for_operation_start_hours": _parse_decimal(get_field(fields, "tesperainicioop")),
                "operation_hours": _parse_decimal(get_field(fields, "toperacao")),
                "wait_for_departure_hours": _parse_decimal(get_field(fields, "tesperadesatracacao")),
                "berth_time_hours": _parse_decimal(get_field(fields, "tatracado")),
                "port_stay_hours": _parse_decimal(get_field(fields, "testadia")),
            }
    return {"map": mapping, "row_count": row_count}


def _new_call_stats(id_atracacao: str) -> dict[str, Any]:
    return {
        "id_atracacao": id_atracacao,
        "rows": 0,
        "moved_teu": 0.0,
        "moved_weight_t": 0.0,
        "loaded_teu": 0.0,
        "loaded_weight_t": 0.0,
        "unloaded_teu": 0.0,
        "unloaded_weight_t": 0.0,
        "local_codes": {},
    }


def _add_local_code_sample(call_stats: dict[str, Any], code: str, teu: float, weight_t: float) -> None:
    key = _normalize_port_key(code)
    if not key:
        return
    bucket = call_stats["local_codes"].setdefault(
        key,
        {"rows": 0, "teu": 0.0, "weight_t": 0.0},
    )
    bucket["rows"] += 1
    bucket["teu"] += float(teu)
    bucket["weight_t"] += float(weight_t)


def _is_containerized_cabotage(tipo_navegacao: str, teu: float, natureza: str, acondicionamento: str) -> bool:
    if _normalize_text(tipo_navegacao) != "cabotagem":
        return False
    if teu > 0:
        return True
    natureza_text = _normalize_text(natureza)
    acondicionamento_text = _normalize_text(acondicionamento)
    return (
        "conteiner" in natureza_text
        or "conteiner" in acondicionamento_text
        or "container" in natureza_text
        or "container" in acondicionamento_text
    )


def _read_carga_call_stats(years: list[str], raw_root: Path) -> dict[str, Any]:
    call_stats_map: dict[str, dict[str, Any]] = {}
    processed_rows = 0
    kept_rows = 0
    for year in years:
        path = _required_raw_path(raw_root, year, "Carga")
        _log.info("Reading ANTAQ carga file year=%s path=%s", year, path)
        for fields, get_field in _iter_txt_rows(path):
            processed_rows += 1
            teu = _parse_decimal(get_field(fields, "teu"))
            tipo_navegacao = get_field(fields, "tipo_navegacao")
            natureza = get_field(fields, "natureza_da_carga")
            acondicionamento = get_field(fields, "carga_geral_acondicionamento")
            if not _is_containerized_cabotage(tipo_navegacao, teu, natureza, acondicionamento):
                continue

            id_atracacao = get_field(fields, "idatracacao").strip()
            if not id_atracacao:
                continue
            stats = call_stats_map.setdefault(id_atracacao, _new_call_stats(id_atracacao))
            weight_t = _parse_decimal(get_field(fields, "vlpesocargabruta"))
            sentido = _normalize_text(get_field(fields, "sentido"))
            origem = get_field(fields, "origem")
            destino = get_field(fields, "destino")

            stats["rows"] += 1
            stats["moved_teu"] += teu
            stats["moved_weight_t"] += weight_t
            kept_rows += 1

            if sentido.startswith(("embarc", "embarq")):
                stats["loaded_teu"] += teu
                stats["loaded_weight_t"] += weight_t
                _add_local_code_sample(stats, origem, teu, weight_t)
            elif sentido.startswith(("desembarc", "desembarq")):
                stats["unloaded_teu"] += teu
                stats["unloaded_weight_t"] += weight_t
                _add_local_code_sample(stats, destino, teu, weight_t)
            else:
                _add_local_code_sample(stats, origem, teu, weight_t)
                _add_local_code_sample(stats, destino, teu, weight_t)
    return {"map": call_stats_map, "processed_rows": processed_rows, "kept_rows": kept_rows}


def _resolve_dominant_port_code(call_stats: dict[str, Any]) -> str:
    best_code = ""
    best_weight = -1.0
    best_teu = -1.0
    best_rows = -1
    for code, stats in call_stats["local_codes"].items():
        weight = float(stats["weight_t"])
        teu = float(stats["teu"])
        rows = int(stats["rows"])
        if (
            weight > best_weight
            or (weight == best_weight and teu > best_teu)
            or (weight == best_weight and teu == best_teu and rows > best_rows)
            or (weight == best_weight and teu == best_teu and rows == best_rows and (not best_code or code < best_code))
        ):
            best_code = str(code)
            best_weight = weight
            best_teu = teu
            best_rows = rows
    return best_code


def _resolve_port_name(port_code: str, fallback_name: str, alias_map: dict[str, str]) -> str:
    code = _normalize_port_key(port_code)
    if code and code in alias_map:
        return alias_map[code]
    fallback = str(fallback_name or "").strip()
    if fallback:
        fallback_key = _normalize_port_key(fallback)
        if fallback_key in alias_map:
            return alias_map[fallback_key]
        return fallback
    return code


def _new_stop_internal(
    meta: dict[str, Any],
    call_stats: dict[str, Any],
    alias_map: dict[str, str],
    time_row: dict[str, Any] | None,
) -> dict[str, Any]:
    port_code = _resolve_dominant_port_code(call_stats)
    port_name = _resolve_port_name(port_code, str(meta["porto_atracacao"]), alias_map)
    port_key = port_code or _normalize_port_key(meta["porto_atracacao"])
    if time_row is None:
        time_metrics = _new_time_metrics_empty()
    else:
        time_metrics = {
            "wait_for_berth_hours": float(time_row["wait_for_berth_hours"]),
            "wait_for_operation_start_hours": float(time_row["wait_for_operation_start_hours"]),
            "operation_hours": float(time_row["operation_hours"]),
            "wait_for_departure_hours": float(time_row["wait_for_departure_hours"]),
            "berth_time_hours": float(time_row["berth_time_hours"]),
            "port_stay_hours": float(time_row["port_stay_hours"]),
            "source_row_count": 1,
        }
    return {
        "port_key": port_key,
        "port_code": port_code,
        "port_name": port_name,
        "atracacao_port_name": meta["porto_atracacao"],
        "municipio": meta["municipio"],
        "uf": meta["uf"],
        "first_at": meta["atracacao_at"],
        "last_at": meta["desatracacao_at"] or meta["atracacao_at"],
        "call_ids": [meta["id_atracacao"]],
        "call_count": 1,
        "time": time_metrics,
        "cargo": {
            "loaded_teu": float(call_stats["loaded_teu"]),
            "loaded_weight_t": float(call_stats["loaded_weight_t"]),
            "unloaded_teu": float(call_stats["unloaded_teu"]),
            "unloaded_weight_t": float(call_stats["unloaded_weight_t"]),
            "moved_teu": float(call_stats["moved_teu"]),
            "moved_weight_t": float(call_stats["moved_weight_t"]),
            "net_teu": float(call_stats["loaded_teu"] - call_stats["unloaded_teu"]),
            "net_weight_t": float(call_stats["loaded_weight_t"] - call_stats["unloaded_weight_t"]),
        },
    }


def _copy_stop_internal(stop: dict[str, Any]) -> dict[str, Any]:
    return {
        "port_key": stop["port_key"],
        "port_code": stop["port_code"],
        "port_name": stop["port_name"],
        "atracacao_port_name": stop["atracacao_port_name"],
        "municipio": stop["municipio"],
        "uf": stop["uf"],
        "first_at": stop["first_at"],
        "last_at": stop["last_at"],
        "call_ids": list(stop["call_ids"]),
        "call_count": int(stop["call_count"]),
        "time": _copy_time_metrics(stop["time"]),
        "cargo": {key: float(value) for key, value in stop["cargo"].items()},
    }


def _merge_stops_internal(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    if incoming["first_at"] is not None and (target["first_at"] is None or incoming["first_at"] < target["first_at"]):
        target["first_at"] = incoming["first_at"]
    if incoming["last_at"] is not None and (target["last_at"] is None or incoming["last_at"] > target["last_at"]):
        target["last_at"] = incoming["last_at"]
    target["call_count"] += int(incoming["call_count"])
    _merge_time_metrics(target["time"], incoming["time"])
    target["call_ids"].extend(incoming["call_ids"])
    for key in (
        "loaded_teu",
        "loaded_weight_t",
        "unloaded_teu",
        "unloaded_weight_t",
        "moved_teu",
        "moved_weight_t",
        "net_teu",
        "net_weight_t",
    ):
        target["cargo"][key] += float(incoming["cargo"][key])


def _convert_stop_to_output(stop: dict[str, Any], sequence: int) -> dict[str, Any]:
    observed_span_hours = None
    if stop["first_at"] is not None and stop["last_at"] is not None:
        observed_span_hours = _round_number((stop["last_at"] - stop["first_at"]).total_seconds() / 3600.0)
    return {
        "sequence": int(sequence),
        "port_key": stop["port_key"],
        "port_code": stop["port_code"],
        "port_name": stop["port_name"],
        "atracacao_port_name": stop["atracacao_port_name"],
        "municipality": stop["municipio"],
        "state": stop["uf"],
        "first_atracacao_at": _format_date_iso(stop["first_at"]),
        "last_atracacao_at": _format_date_iso(stop["last_at"]),
        "call_count": int(stop["call_count"]),
        "call_ids": list(stop["call_ids"]),
        "time": {
            "observed_span_hours": observed_span_hours,
            "wait_for_berth_hours": _round_number(stop["time"]["wait_for_berth_hours"]),
            "wait_for_operation_start_hours": _round_number(stop["time"]["wait_for_operation_start_hours"]),
            "operation_hours": _round_number(stop["time"]["operation_hours"]),
            "wait_for_departure_hours": _round_number(stop["time"]["wait_for_departure_hours"]),
            "berth_time_hours": _round_number(stop["time"]["berth_time_hours"]),
            "port_stay_hours": _round_number(stop["time"]["port_stay_hours"]),
            "source_row_count": int(stop["time"]["source_row_count"]),
        },
        "cargo": {
            "loaded_teu": _round_number(stop["cargo"]["loaded_teu"]),
            "loaded_weight_t": _round_number(stop["cargo"]["loaded_weight_t"]),
            "unloaded_teu": _round_number(stop["cargo"]["unloaded_teu"]),
            "unloaded_weight_t": _round_number(stop["cargo"]["unloaded_weight_t"]),
            "moved_teu": _round_number(stop["cargo"]["moved_teu"]),
            "moved_weight_t": _round_number(stop["cargo"]["moved_weight_t"]),
            "net_teu": _round_number(stop["cargo"]["net_teu"]),
            "net_weight_t": _round_number(stop["cargo"]["net_weight_t"]),
        },
    }


def _finalize_voyage(
    imo: str,
    voyage_index: int,
    stops: list[dict[str, Any]],
    closed_loop: bool,
    closed_by: str,
) -> dict[str, Any] | None:
    if len(stops) < 2:
        return None
    output_stops = [_convert_stop_to_output(stop, sequence) for sequence, stop in enumerate(stops)]
    origin = output_stops[0]
    destination = output_stops[-1]
    intermediate_stops = output_stops[1:-1] if len(output_stops) > 2 else []
    return {
        "voyage_id": f"voyage_{imo}_{voyage_index:05d}",
        "imo": imo,
        "closed_loop": bool(closed_loop),
        "closed_by": closed_by,
        "stop_count": len(output_stops),
        "started_at": origin["first_atracacao_at"],
        "ended_at": destination["last_atracacao_at"],
        "origin_port_code": origin["port_code"],
        "origin_port_name": origin["port_name"],
        "destination_port_code": destination["port_code"],
        "destination_port_name": destination["port_name"],
        "origin_time": origin["time"],
        "destination_time": destination["time"],
        "origin_cargo": origin["cargo"],
        "destination_cargo": destination["cargo"],
        "intermediate_stop_count": len(intermediate_stops),
        "intermediate_stops": intermediate_stops,
        "stops": output_stops,
    }


def _build_observed_voyages(
    *,
    atracacao_map: dict[str, dict[str, Any]],
    call_stats_map: dict[str, dict[str, Any]],
    tempos_atracacao_map: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
    gap_hours: float,
) -> dict[str, Any]:
    calls_by_imo: dict[str, list[dict[str, Any]]] = {}
    joined_calls = 0
    dropped_without_atracacao = 0
    dropped_without_imo = 0
    calls_with_time_metrics = 0
    calls_without_time_metrics = 0

    for id_atracacao, call_stats in call_stats_map.items():
        meta = atracacao_map.get(str(id_atracacao))
        if meta is None:
            dropped_without_atracacao += 1
            continue
        imo = str(meta.get("imo") or "").strip()
        if not imo:
            dropped_without_imo += 1
            continue

        time_row = tempos_atracacao_map.get(str(id_atracacao))
        if time_row is None:
            calls_without_time_metrics += 1
        else:
            calls_with_time_metrics += 1

        stop = _new_stop_internal(meta, call_stats, alias_map, time_row)
        calls_by_imo.setdefault(imo, []).append(stop)
        joined_calls += 1

    voyages: list[dict[str, Any]] = []
    collapsed_stops = 0
    for imo in sorted(calls_by_imo):
        ordered_calls = sorted(
            calls_by_imo[imo],
            key=lambda item: (
                item["first_at"] or datetime.min,
                item["last_at"] or datetime.min,
                str(item["port_key"] or ""),
            ),
        )
        if not ordered_calls:
            continue

        collapsed: list[dict[str, Any]] = []
        current_stop = _copy_stop_internal(ordered_calls[0])
        for next_stop in ordered_calls[1:]:
            if current_stop["port_key"] and current_stop["port_key"] == next_stop["port_key"]:
                _merge_stops_internal(current_stop, next_stop)
                continue
            collapsed.append(current_stop)
            current_stop = _copy_stop_internal(next_stop)
        collapsed.append(current_stop)
        collapsed_stops += len(collapsed)

        if len(collapsed) < 2:
            continue

        voyage_index = 1
        working_stops: list[dict[str, Any]] = [_copy_stop_internal(collapsed[0])]
        for next_stop in collapsed[1:]:
            prev_stop = working_stops[-1]
            gap = ((next_stop["first_at"] or datetime.min) - (prev_stop["last_at"] or datetime.min)).total_seconds() / 3600.0
            if gap > float(gap_hours):
                voyage = _finalize_voyage(imo, voyage_index, working_stops, False, "gap")
                if voyage is not None:
                    voyages.append(voyage)
                    voyage_index += 1
                working_stops = [_copy_stop_internal(next_stop)]
                continue

            working_stops.append(_copy_stop_internal(next_stop))
            if len(working_stops) >= 3 and working_stops[-1]["port_key"] == working_stops[0]["port_key"]:
                voyage = _finalize_voyage(imo, voyage_index, working_stops, True, "return_to_origin")
                if voyage is not None:
                    voyages.append(voyage)
                    voyage_index += 1
                working_stops = [_copy_stop_internal(next_stop)]

        tail_voyage = _finalize_voyage(imo, voyage_index, working_stops, False, "open_tail")
        if tail_voyage is not None:
            voyages.append(tail_voyage)

    return {
        "voyages": voyages,
        "joined_calls": joined_calls,
        "dropped_without_atracacao": dropped_without_atracacao,
        "dropped_without_imo": dropped_without_imo,
        "calls_with_time_metrics": calls_with_time_metrics,
        "calls_without_time_metrics": calls_without_time_metrics,
        "unique_imos": len(calls_by_imo),
        "collapsed_stops": collapsed_stops,
    }
