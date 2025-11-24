# modules/addressing/cep.py
# -*- coding: utf-8 -*-

"""
CEP Resolution Logic.
=====================

Handles parsing Brazilian postal codes (CEP) and resolving them to coordinates.
Strategies:
1. ORS Structured Geocoding (fastest).
2. Free-text Geocoding.
3. ViaCEP Fallback (if ORS fails to understand the CEP directly).
"""

from __future__ import annotations

import re
import requests
from typing import Any, Dict, Optional

# Path Bootstrap (for direct execution)
if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger
from modules.addressing.coords import filter_hits

_log = get_logger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

_CEP_REGEX = re.compile(r"^\s*(\d{5})[-]?(\d{3})\s*$")

# ────────────────────────────────────────────────────────────────────────────────
# Parsing Logic
# ────────────────────────────────────────────────────────────────────────────────

def is_cep(text: str) -> bool:
    """Check if string looks like a CEP (8 digits, optional hyphen)."""
    if not isinstance(text, str):
        return False
    return bool(_CEP_REGEX.match(text))


def format_cep(text: str) -> str:
    """
    Canonicalize CEP string.
    Input: "01310200" -> Output: "01310-200"
    """
    m = _CEP_REGEX.match(text)
    if not m:
        raise ValueError(f"Invalid CEP format: {text}")
    return f"{m.group(1)}-{m.group(2)}"


def parse_cep(text: str) -> Optional[str]:
    """
    Extract raw digits.
    Input: "01310-200" -> Output: "01310200"
    """
    if not isinstance(text, str):
        return None
    m = _CEP_REGEX.match(text)
    if not m:
        return None
    return f"{m.group(1)}{m.group(2)}"


# ────────────────────────────────────────────────────────────────────────────────
# External Lookup (ViaCEP)
# ────────────────────────────────────────────────────────────────────────────────

def viacep_lookup(cep: str) -> Optional[Dict[str, str]]:
    """
    Fetch address details from ViaCEP public API.
    Used as a fallback when ORS doesn't recognize the CEP directly.
    """
    digits = parse_cep(cep)
    if not digits:
        return None
        
    url = f"https://viacep.com.br/ws/{digits}/json/"
    
    try:
        r = requests.get(url, timeout=(3.05, 5)) # Connect, Read
        if not r.ok:
            _log.debug(f"ViaCEP HTTP error: {r.status_code}")
            return None
            
        data = r.json()
        if data.get("erro"):
            _log.debug(f"ViaCEP returned 'erro' for {cep}")
            return None

        return {
            "logradouro": data.get("logradouro") or "",
            "bairro":     data.get("bairro") or "",
            "localidade": data.get("localidade") or "",
            "uf":         data.get("uf") or "",
        }

    except Exception as e:
        _log.warning(f"ViaCEP failed for {cep}: {e}")
        return None


# ────────────────────────────────────────────────────────────────────────────────
# Main Resolution Logic
# ────────────────────────────────────────────────────────────────────────────────

def resolve_cep(value: str, *, ors: Any) -> Dict[str, Any]:
    """
    Resolve a CEP to coordinates using a cascade of strategies.
    
    Returns
    -------
    Dict with {"lat", "lon", "label"}
    
    Raises
    ------
    ValueError if resolution fails completely.
    """
    cep_digits = parse_cep(value)
    if not cep_digits:
        raise ValueError(f"Invalid CEP input: {value}")

    country = getattr(ors.cfg, "default_country", "BR")
    cep_fmt = f"{cep_digits[:5]}-{cep_digits[5:]}"
    
    _log.debug(f"Resolving CEP: {cep_fmt}")

    # Strategy 1: Structured Geocode (Digits)
    # ORS usually prefers raw digits for postal codes
    try:
        raw = ors.geocode_structured(postalcode=cep_digits, country=country, size=1)
        hits = filter_hits(raw, allowed_layers=["postalcode", "postcode", "address", "locality"])
        if hits:
            h = hits[0]
            return {"lat": h["lat"], "lon": h["lon"], "label": h["label"]}
    except Exception:
        pass

    # Strategy 2: Structured Geocode (Hyphenated)
    try:
        raw = ors.geocode_structured(postalcode=cep_fmt, country=country, size=1)
        hits = filter_hits(raw, allowed_layers=["postalcode", "postcode", "address"])
        if hits:
            h = hits[0]
            return {"lat": h["lat"], "lon": h["lon"], "label": h["label"]}
    except Exception:
        pass

    # Strategy 3: ViaCEP Enrichment -> Geocode Text
    # If ORS doesn't know the CEP, ask ViaCEP for the street name and geocode that.
    _log.info(f"ORS failed to resolve CEP {cep_fmt} directly. Trying ViaCEP fallback...")
    addr_info = viacep_lookup(cep_digits)
    
    if addr_info:
        # Construct query: "Rua X, Bairro Y, Cidade Z, UF"
        components = [
            addr_info["logradouro"],
            addr_info["bairro"],
            addr_info["localidade"],
            addr_info["uf"]
        ]
        query = ", ".join([c for c in components if c])
        
        if query:
            _log.debug(f"ViaCEP resolved to address: '{query}'. Geocoding that...")
            try:
                # Free text search is robust here
                raw = ors.geocode_text(query, size=1, country=country)
                hits = filter_hits(raw)
                if hits:
                    h = hits[0]
                    # Use the query as label since it's more descriptive than just the CEP
                    return {"lat": h["lat"], "lon": h["lon"], "label": query}
            except Exception as e:
                _log.warning(f"Geocoding ViaCEP result failed: {e}")

    raise ValueError(f"Could not resolve CEP: {value}")


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging
    init_logging(level="DEBUG")
    
    print("--- CEP Smoke Test ---")
    
    # 1. Test Parsers
    c = " 01310-200 "
    assert is_cep(c)
    assert parse_cep(c) == "01310200"
    assert format_cep(c.strip()) == "01310-200"
    print("✅ Parsers OK")

    # 2. Test ViaCEP (Network)
    print("Testing ViaCEP (Av. Paulista)...")
    info = viacep_lookup("01310200")
    if info:
        print(f"✅ ViaCEP: {info.get('logradouro')}, {info.get('localidade')}")
    else:
        print("⚠️ ViaCEP failed (network issue?)")

    print("--- Done ---")