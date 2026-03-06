from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.main.map.routing.marine_waypoints import normalize_port_name
from modules.infra.log_manager import get_logger
from modules.ports.ports_index import load_ports

_log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PORTS_JSON_PATH = _REPO_ROOT / "data" / "processed" / "cabotage_data" / "ports_br.json"
BELEM_PORT_KEY = normalize_port_name("Porto de Belem")


@dataclass(frozen=True)
class MarineRoutePort:
    name: str
    key: str
    latlon: tuple[float, float]


MASTER_ROUTE_PORT_NAMES: tuple[str, ...] = (
    "Porto do Rio Grande",
    "Porto de Imbituba",
    "Porto de Itajai",
    "Porto de Navegantes",
    "Porto de Sao Francisco do Sul",
    "Porto de Itapoa",
    "Porto de Paranagua",
    "Porto de Santos",
    "Porto de Sao Sebastiao",
    "Porto de Angra dos Reis",
    "Porto de Itaguai",
    "Porto do Rio de Janeiro",
    "Porto de Vitoria",
    "Porto de Salvador",
    "Porto de Aratu",
    "Porto de Maceio",
    "Porto de Suape",
    "Porto do Recife",
    "Porto de Cabedelo",
    "Porto de Natal",
    "Porto de Fortaleza",
    "Porto do Pecem",
    "Porto do Itaqui",
    "Porto de Belem",
    "Porto de Vila do Conde",
    "Porto de Santana",
    "Porto de Santarem",
    "Porto de Manaus",
)


@lru_cache(maxsize=1)
def load_master_route_catalog() -> tuple[tuple[MarineRoutePort, ...], dict[str, str]]:
    records = load_ports(str(_PORTS_JSON_PATH))
    records_by_name, alias_to_key = _build_record_lookups(records)

    route_ports: list[MarineRoutePort] = []
    for canonical_name in MASTER_ROUTE_PORT_NAMES:
        canonical_key = normalize_port_name(canonical_name)
        record = records_by_name.get(canonical_key)
        if record is None:
            record = records_by_name.get(alias_to_key.get(canonical_key, ""))
        if record is None:
            _log.warning("Master maritime port '%s' was not found in %s.", canonical_name, _PORTS_JSON_PATH)
            continue

        route_ports.append(
            MarineRoutePort(
                name=canonical_name,
                key=canonical_key,
                latlon=_plot_latlon(record),
            )
        )

    return tuple(route_ports), alias_to_key


def load_master_route_ports() -> tuple[MarineRoutePort, ...]:
    route_ports, _ = load_master_route_catalog()
    return route_ports


@lru_cache(maxsize=1)
def load_master_route_indices() -> dict[str, int]:
    return {route_port.key: idx for idx, route_port in enumerate(load_master_route_ports())}


def resolve_master_route_slice(
    *,
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
) -> list[MarineRoutePort]:
    route_ports, alias_to_key = load_master_route_catalog()
    if not route_ports:
        return _fallback_slice(origin_port_name, dest_port_name, origin_latlon, dest_latlon)

    origin_key = _canonical_master_key(origin_port_name, alias_to_key)
    dest_key = _canonical_master_key(dest_port_name, alias_to_key)

    origin_idx = _find_port_index(origin_key, route_ports)
    dest_idx = _find_port_index(dest_key, route_ports)

    if origin_idx is None or dest_idx is None:
        _log.warning(
            "Failed to resolve master maritime slice for origin='%s' destination='%s'. Falling back to endpoints only.",
            origin_port_name,
            dest_port_name,
        )
        return _fallback_slice(origin_port_name, dest_port_name, origin_latlon, dest_latlon)

    if origin_idx <= dest_idx:
        selected = list(route_ports[origin_idx : dest_idx + 1])
    else:
        selected = list(reversed(route_ports[dest_idx : origin_idx + 1]))

    selected[0] = MarineRoutePort(name=selected[0].name, key=selected[0].key, latlon=_as_latlon(origin_latlon))
    selected[-1] = MarineRoutePort(name=selected[-1].name, key=selected[-1].key, latlon=_as_latlon(dest_latlon))
    return selected


def get_master_route_index(port_key: str) -> int | None:
    return load_master_route_indices().get(normalize_port_name(port_key))


def is_river_leg(
    start_port_key: str,
    end_port_key: str,
) -> bool:
    belem_idx = get_master_route_index(BELEM_PORT_KEY)
    start_idx = get_master_route_index(start_port_key)
    end_idx = get_master_route_index(end_port_key)
    if belem_idx is None or start_idx is None or end_idx is None:
        return False
    return min(start_idx, end_idx) >= belem_idx


def _build_record_lookups(records: list[dict[str, object]]) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    records_by_name: dict[str, dict[str, object]] = {}
    alias_to_key: dict[str, str] = {}

    for record in records:
        name = str(record.get("name") or "")
        key = normalize_port_name(name)
        records_by_name[key] = record
        alias_to_key[key] = key

        for alias in record.get("aliases") or []:
            alias_key = normalize_port_name(alias)
            if alias_key:
                alias_to_key[alias_key] = key

    return records_by_name, alias_to_key


def _canonical_master_key(port_name: str, alias_to_key: dict[str, str]) -> str:
    port_key = normalize_port_name(port_name)
    return alias_to_key.get(port_key, port_key)


def _find_port_index(port_key: str, route_ports: tuple[MarineRoutePort, ...]) -> int | None:
    for idx, route_port in enumerate(route_ports):
        if route_port.key == port_key:
            return idx
    return None


def _plot_latlon(record: dict[str, object]) -> tuple[float, float]:
    gates = record.get("gates") or []
    if isinstance(gates, list) and gates:
        gate = gates[0]
        if isinstance(gate, dict):
            return float(gate["lat"]), float(gate["lon"])
    return float(record["lat"]), float(record["lon"])


def _as_latlon(latlon: tuple[float, float]) -> tuple[float, float]:
    return float(latlon[0]), float(latlon[1])


def _fallback_slice(
    origin_port_name: str,
    dest_port_name: str,
    origin_latlon: tuple[float, float],
    dest_latlon: tuple[float, float],
) -> list[MarineRoutePort]:
    return [
        MarineRoutePort(
            name=origin_port_name,
            key=normalize_port_name(origin_port_name),
            latlon=_as_latlon(origin_latlon),
        ),
        MarineRoutePort(
            name=dest_port_name,
            key=normalize_port_name(dest_port_name),
            latlon=_as_latlon(dest_latlon),
        ),
    ]
