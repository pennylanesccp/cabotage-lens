from __future__ import annotations

import re
import unicodedata
from typing import Iterable


def normalize_port_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name or "").strip())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


NAMED_MARINE_POINTS: dict[str, tuple[float, float]] = {
    "rio-grande-bar": (-32.0033177, -51.9103981),
    "rio-grande-offshore": (-31.0886323, -50.5679546),
    "imbituba-offshore": (-28.5946528, -48.7221994),
    "itajai-offshore": (-26.9000000, -48.4300000),
    "sao-francisco-offshore": (-26.2400000, -48.3800000),
    "paranagua-offshore": (-25.5810196, -48.3159652),
    "santos-offshore": (-23.7242888, -45.3660921),
    "sepetiba-exit": (-23.3120185, -44.4925682),
    "rio-bay-exit": (-22.7912770, -41.0846480),
    "vitoria-offshore": (-19.4552003, -39.4830264),
    "salvador-offshore": (-12.7043191, -38.0223385),
    "maceio-offshore": (-9.1903872, -35.1638094),
    "suape-offshore": (-7.9344795, -34.7573153),
    "natal-corner": (-5.1585348, -35.2820574),
    "fortaleza-offshore": (-3.8500000, -38.2500000),
    "maranhao-offshore": (-2.1351123, -43.7856584),
    "itaqui-offshore": (-2.4500000, -44.2000000),
    "belem-bar": (-0.4723604, -47.9934220),
    "vila-do-conde-channel": (-1.5423359, -48.7501834),
    "amazon-mouth": (-0.0988306, -49.7292619),
    "macapa-channel": (-1.4480950, -51.6499695),
    "santana-channel": (0.0540000, -51.1740000),
    "santarem-channel": (-2.4220000, -54.7190000),
    "obidos-channel": (-2.1728258, -56.1543641),
    "itacoatiara-channel": (-3.1500000, -59.3500000),
    "manaus-channel": (-3.1567000, -60.0079000),
}

FALLBACK_TRUNK_POINT_NAMES: tuple[str, ...] = (
    "rio-grande-offshore",
    "imbituba-offshore",
    "itajai-offshore",
    "sao-francisco-offshore",
    "paranagua-offshore",
    "santos-offshore",
    "rio-bay-exit",
    "vitoria-offshore",
    "salvador-offshore",
    "maceio-offshore",
    "suape-offshore",
    "natal-corner",
    "fortaleza-offshore",
    "maranhao-offshore",
    "itaqui-offshore",
    "belem-bar",
    "amazon-mouth",
    "macapa-channel",
    "santana-channel",
    "santarem-channel",
    "obidos-channel",
    "itacoatiara-channel",
    "manaus-channel",
)

PORT_APPROACH_POINT_NAMES: dict[str, tuple[str, ...]] = {
    normalize_port_name("Porto do Rio Grande"): ("rio-grande-bar", "rio-grande-offshore"),
    normalize_port_name("Porto de Imbituba"): ("imbituba-offshore",),
    normalize_port_name("Porto de Navegantes"): ("itajai-offshore",),
    normalize_port_name("Porto de Itajai"): ("itajai-offshore",),
    normalize_port_name("Porto de Itapoa"): ("sao-francisco-offshore",),
    normalize_port_name("Porto de Sao Francisco do Sul"): ("sao-francisco-offshore",),
    normalize_port_name("Porto de Paranagua"): ("paranagua-offshore",),
    normalize_port_name("Porto de Santos"): ("santos-offshore",),
    normalize_port_name("Porto de Sao Sebastiao"): ("santos-offshore",),
    normalize_port_name("Porto do Rio de Janeiro"): ("rio-bay-exit",),
    normalize_port_name("Porto de Itaguai"): ("sepetiba-exit", "rio-bay-exit"),
    normalize_port_name("Porto de Angra dos Reis"): ("sepetiba-exit", "rio-bay-exit"),
    normalize_port_name("Porto de Vitoria"): ("vitoria-offshore",),
    normalize_port_name("Porto de Aratu"): ("salvador-offshore",),
    normalize_port_name("Porto de Salvador"): ("salvador-offshore",),
    normalize_port_name("Porto de Maceio"): ("maceio-offshore",),
    normalize_port_name("Porto do Recife"): ("suape-offshore",),
    normalize_port_name("Porto de Suape"): ("suape-offshore",),
    normalize_port_name("Porto de Cabedelo"): ("natal-corner",),
    normalize_port_name("Porto de Natal"): ("natal-corner",),
    normalize_port_name("Porto do Pecem"): ("fortaleza-offshore",),
    normalize_port_name("Porto de Fortaleza"): ("fortaleza-offshore",),
    normalize_port_name("Porto do Itaqui"): ("itaqui-offshore",),
    normalize_port_name("Porto de Vila do Conde"): ("vila-do-conde-channel", "amazon-mouth"),
    normalize_port_name("Porto de Belem"): ("belem-bar", "amazon-mouth"),
    normalize_port_name("Porto de Santana"): ("santana-channel",),
    normalize_port_name("Porto de Santarem"): ("santarem-channel",),
    normalize_port_name("Porto de Manaus"): ("manaus-channel",),
}

_TO_MANAUS_FROM_SOUTH = (
    "imbituba-offshore",
    "itajai-offshore",
    "sao-francisco-offshore",
    "paranagua-offshore",
    "santos-offshore",
    "rio-bay-exit",
    "vitoria-offshore",
    "salvador-offshore",
    "suape-offshore",
    "fortaleza-offshore",
    "itaqui-offshore",
    "amazon-mouth",
    "macapa-channel",
    "santarem-channel",
    "obidos-channel",
    "itacoatiara-channel",
)
_TO_MANAUS_FROM_SOUTHEAST = (
    "rio-bay-exit",
    "vitoria-offshore",
    "salvador-offshore",
    "suape-offshore",
    "fortaleza-offshore",
    "itaqui-offshore",
    "amazon-mouth",
    "macapa-channel",
    "santarem-channel",
    "obidos-channel",
    "itacoatiara-channel",
)
_TO_MANAUS_FROM_BAHIA = (
    "suape-offshore",
    "fortaleza-offshore",
    "itaqui-offshore",
    "amazon-mouth",
    "macapa-channel",
    "santarem-channel",
    "obidos-channel",
    "itacoatiara-channel",
)
_TO_MANAUS_FROM_NORTHEAST = (
    "fortaleza-offshore",
    "itaqui-offshore",
    "amazon-mouth",
    "macapa-channel",
    "santarem-channel",
    "obidos-channel",
    "itacoatiara-channel",
)

MAJOR_MARINE_CORRIDOR_POINT_NAMES: dict[tuple[str, str], tuple[str, ...]] = {
    (normalize_port_name("Porto do Rio Grande"), normalize_port_name("Porto de Manaus")): _TO_MANAUS_FROM_SOUTH,
    (normalize_port_name("Porto de Santos"), normalize_port_name("Porto de Manaus")): _TO_MANAUS_FROM_SOUTHEAST,
    (normalize_port_name("Porto do Rio de Janeiro"), normalize_port_name("Porto de Manaus")): (
        "vitoria-offshore",
        "salvador-offshore",
        "suape-offshore",
        "fortaleza-offshore",
        "itaqui-offshore",
        "amazon-mouth",
        "macapa-channel",
        "santarem-channel",
        "obidos-channel",
        "itacoatiara-channel",
    ),
    (normalize_port_name("Porto de Itaguai"), normalize_port_name("Porto de Manaus")): _TO_MANAUS_FROM_SOUTHEAST,
    (normalize_port_name("Porto de Vitoria"), normalize_port_name("Porto de Manaus")): (
        "salvador-offshore",
        "suape-offshore",
        "fortaleza-offshore",
        "itaqui-offshore",
        "amazon-mouth",
        "macapa-channel",
        "santarem-channel",
        "obidos-channel",
        "itacoatiara-channel",
    ),
    (normalize_port_name("Porto de Salvador"), normalize_port_name("Porto de Manaus")): _TO_MANAUS_FROM_BAHIA,
    (normalize_port_name("Porto de Suape"), normalize_port_name("Porto de Manaus")): _TO_MANAUS_FROM_NORTHEAST,
    (normalize_port_name("Porto de Fortaleza"), normalize_port_name("Porto de Manaus")): (
        "itaqui-offshore",
        "amazon-mouth",
        "macapa-channel",
        "santarem-channel",
        "obidos-channel",
        "itacoatiara-channel",
    ),
    (normalize_port_name("Porto de Belem"), normalize_port_name("Porto de Manaus")): (
        "amazon-mouth",
        "macapa-channel",
        "santarem-channel",
        "obidos-channel",
        "itacoatiara-channel",
    ),
    (normalize_port_name("Porto de Vila do Conde"), normalize_port_name("Porto de Manaus")): (
        "amazon-mouth",
        "macapa-channel",
        "santarem-channel",
        "obidos-channel",
        "itacoatiara-channel",
    ),
    (normalize_port_name("Porto de Santana"), normalize_port_name("Porto de Manaus")): (
        "macapa-channel",
        "santarem-channel",
        "obidos-channel",
        "itacoatiara-channel",
    ),
    (normalize_port_name("Porto de Santarem"), normalize_port_name("Porto de Manaus")): (
        "obidos-channel",
        "itacoatiara-channel",
    ),
}


def point_names_to_latlon(point_names: Iterable[str]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for point_name in point_names:
        point = NAMED_MARINE_POINTS.get(point_name)
        if point is not None:
            points.append(point)
    return points


def resolve_port_approach_point_names(port_name: str) -> tuple[str, ...]:
    return PORT_APPROACH_POINT_NAMES.get(normalize_port_name(port_name), ())


def resolve_major_corridor_point_names(origin_port_name: str, dest_port_name: str) -> list[str]:
    origin_key = normalize_port_name(origin_port_name)
    dest_key = normalize_port_name(dest_port_name)

    direct = MAJOR_MARINE_CORRIDOR_POINT_NAMES.get((origin_key, dest_key))
    if direct is not None:
        return list(direct)

    reversed_route = MAJOR_MARINE_CORRIDOR_POINT_NAMES.get((dest_key, origin_key))
    if reversed_route is not None:
        return list(reversed(reversed_route))

    return []
