# modules/addressing/resolver.py
# -*- coding: utf-8 -*-

"""
Address Resolver.
=================

Converts diverse inputs (CEP, Lat/Lon string, Address text) into
resolved GeoPoint objects using OpenRouteService.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Optional

from modules.addressing.coords import parse_lat_lon_string
from modules.addressing.text import ascii_place_text
from modules.core.models import GeoPoint
from modules.road.ors.structures import GeocodeNotFound

if TYPE_CHECKING:
    from logging import Logger
    from modules.road.ors import ORSClient


_VALID_BRAZIL_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

_STATE_NAME_TO_UF = {
    "ACRE": "AC",
    "ALAGOAS": "AL",
    "AMAPA": "AP",
    "AMAZONAS": "AM",
    "BAHIA": "BA",
    "CEARA": "CE",
    "DISTRITO FEDERAL": "DF",
    "ESPIRITO SANTO": "ES",
    "GOIAS": "GO",
    "MARANHAO": "MA",
    "MATO GROSSO": "MT",
    "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG",
    "PARA": "PA",
    "PARAIBA": "PB",
    "PARANA": "PR",
    "PERNAMBUCO": "PE",
    "PIAUI": "PI",
    "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS",
    "RONDONIA": "RO",
    "RORAIMA": "RR",
    "SANTA CATARINA": "SC",
    "SAO PAULO": "SP",
    "SERGIPE": "SE",
    "TOCANTINS": "TO",
}


def _extract_uf_hint(value: Any) -> Optional[str]:
    text = ascii_place_text(value)
    candidate = text.split(",")[-1].strip().upper() if "," in text else text.strip().upper()
    if candidate in _VALID_BRAZIL_UFS:
        return candidate
    return _STATE_NAME_TO_UF.get(candidate)


def _stabilize_label_and_uf(raw_input: str, resolved_label: Any, resolved_uf: Any) -> tuple[str, Optional[str]]:
    """
    Prefer the explicit UF from the user's input when ORS returns an invalid or
    truncated tail such as "R.".
    """
    input_label = ascii_place_text(raw_input)
    input_uf = _extract_uf_hint(input_label)

    label = ascii_place_text(resolved_label or raw_input)
    label_uf = _extract_uf_hint(label)
    uf = _extract_uf_hint(resolved_uf)

    if input_uf and (uf is None or label_uf is None or label_uf != input_uf):
        return input_label, input_uf

    return label, (uf or label_uf)


def resolve_point(
      value: Any
    , ors: ORSClient
    , log: Optional[Logger] = None
) -> Optional[GeoPoint]:
    """
    Resolve a raw input value into a GeoPoint.

    Strategies:
    1. If value is already a dict/GeoPoint with lat/lon -> return it.
    2. If value looks like "lat, lon" -> parse it.
    3. If value looks like a CEP -> structured geocode.
    4. Else -> free text geocode.
    """
    if hasattr(value, "lat") and hasattr(value, "lon"):
        return GeoPoint(
            lat=float(value.lat),
            lon=float(value.lon),
            uf=getattr(value, "uf", None),
            label=ascii_place_text(getattr(value, "label", "Point")),
        )

    if isinstance(value, dict):
        lat = value.get("lat") or value.get("latitude")
        lon = value.get("lon") or value.get("longitude")
        if lat is not None and lon is not None:
            return GeoPoint(
                lat=float(lat),
                lon=float(lon),
                uf=value.get("uf"),
                label=ascii_place_text(value.get("label", "Point")),
            )

    val_str = str(value).strip()
    coords = parse_lat_lon_string(val_str)
    if coords:
        return GeoPoint(
            lat=coords[0],
            lon=coords[1],
            uf=None,
            label=ascii_place_text(val_str),
        )

    if re.match(r"^\d{5}-?\d{3}$", val_str):
        if log:
            log.debug("Resolving CEP: %s", val_str)
        try:
            features = ors.geocode_structured(postalcode=val_str, country="BR", size=1)
            if features:
                feature = features[0]
                coords = feature["geometry"]["coordinates"]
                props = feature.get("properties", {})
                label, uf = _stabilize_label_and_uf(
                    val_str,
                    props.get("label") or f"CEP {val_str}",
                    props.get("region_a") or props.get("region"),
                )
                return GeoPoint(lat=coords[1], lon=coords[0], uf=uf, label=label)
        except GeocodeNotFound:
            pass
        except Exception as exc:
            if log:
                log.warning("CEP geocode failed for %s: %s", val_str, exc)
            raise

    try:
        if log:
            log.debug("Resolving text: %s", val_str)
        features = ors.geocode_text(val_str, size=1)
        if features:
            feature = features[0]
            coords = feature["geometry"]["coordinates"]
            props = feature.get("properties", {})
            label, uf = _stabilize_label_and_uf(
                val_str,
                props.get("label") or val_str,
                props.get("region_a") or props.get("region"),
            )
            return GeoPoint(lat=coords[1], lon=coords[0], uf=uf, label=label)
    except GeocodeNotFound:
        return None
    except Exception as exc:
        if log:
            log.warning("Text geocode failed for %s: %s", val_str, exc)
        raise

    return None


def resolve_point_null_safe(
      value: Any
    , ors: ORSClient
    , log: Optional[Logger] = None
) -> Optional[GeoPoint]:
    """Wrapper that catches all exceptions and returns None on failure."""
    try:
        return resolve_point(value, ors, log)
    except Exception as exc:
        if log:
            log.error("Fatal error resolving '%s': %s", value, exc)
        return None
