# modules/road/ors/structures.py
# -*- coding: utf-8 -*-

"""
ORS Data Structures.
====================

Defines the configuration, constants, secret helpers, and custom exceptions
for the OpenRouteService client.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from modules.core.secrets import get_secret

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Constants
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

DEFAULT_BASE_URL = "https://api.openrouteservice.org"
DEFAULT_USER_AGENT = "CarbonFootprint-ORS/2.0"
SECRET_API_KEYS = "ORS_API_KEYS"
SECRET_API_KEY = "ORS_API_KEY"
SECONDARY_SECRET_API_KEY = "ORS_API_KEY_2"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Exceptions
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ORSError(Exception):
    """Base class for all ORS-related errors."""
    pass

class RateLimited(ORSError):
    """
    Raised when the API returns 429 (Too Many Requests).
    Used by consumers to trigger backoff or stop processing.
    """
    pass

class NoRoute(ORSError):
    """
    Raised when the API returns 404 or 422.
    Indicates that no path could be found between points.
    """
    pass

class GeocodeNotFound(ORSError):
    """
    Raised when a geocoding query returns zero results.
    """
    pass


def _append_secret_values(target: list[str], raw: Any) -> None:
    if raw is None:
        return
    if isinstance(raw, (list, tuple)):
        for item in raw:
            _append_secret_values(target, item)
        return

    text = str(raw).strip()
    if not text:
        return

    for part in text.replace("\r", "\n").replace(";", ",").replace("\n", ",").split(","):
        value = part.strip()
        if value and value not in target:
            target.append(value)


def get_configured_ors_api_keys(
    *,
    explicit_api_key: Optional[str] = None,
    path: Path | None = None,
    include_runtime: bool = True,
) -> list[str]:
    """Return ORS API keys in configured failover order."""
    keys: list[str] = []
    _append_secret_values(keys, explicit_api_key)

    configured_list = get_secret(
        SECRET_API_KEYS,
        None,
        path=path,
        include_runtime=include_runtime,
    )
    list_keys: list[str] = []
    _append_secret_values(list_keys, configured_list)
    if list_keys:
        for key in list_keys:
            if key not in keys:
                keys.append(key)
        return keys

    _append_secret_values(
        keys,
        get_secret(
            SECRET_API_KEY,
            None,
            path=path,
            include_runtime=include_runtime,
        ),
    )
    _append_secret_values(
        keys,
        get_secret(
            SECONDARY_SECRET_API_KEY,
            None,
            path=path,
            include_runtime=include_runtime,
        ),
    )
    return keys

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Configuration
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class ORSConfig:
    """
    Configuration object for the ORS Client.

    Attributes
    ----------
    api_key : str, optional
        The OpenRouteService API key. If None, the client will attempt
        to load the first configured key from `ORS_API_KEYS` or the
        legacy `ORS_API_KEY` Streamlit secret.
    base_url : str
        The root URL for the API. Defaults to the public ORS instance.
    cache_enabled : bool
        Enables the in-process HTTP response cache.
    cache_ttl_s : int
        Cache expiration in seconds. 0 means infinite (never expire).
    timeout : tuple[float, float]
        (connect_timeout, read_timeout) in seconds.
    retry_limit : int
        Maximum number of retries for transient HTTP errors (500, 502, etc.).
    default_profile : str
        Default routing profile (e.g., 'driving-hgv', 'driving-car').
    default_country : str
        ISO-3166 alpha-2 country code for geocoding bias (default: 'BR').
    """
    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    
    # Caching Defaults
    cache_enabled: bool = True
    cache_ttl_s: int = 2_592_000  # 30 days (30 * 24 * 3600)

    # HTTP Behavior
    timeout: tuple[float, float] = (10.0, 5.0)
    retry_limit: int = 1
    
    # Domain Defaults
    default_profile: str = "driving-hgv"
    default_country: str = "BR"

    def __post_init__(self) -> None:
        """
        Auto-configuration hook.
        Loads the API key from Streamlit secrets if one wasn't provided explicitly.
        """
        if not self.api_key:
            keys = get_configured_ors_api_keys()
            self.api_key = keys[0] if keys else None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Smoke Test
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    print("--- ORS Structures Smoke Test ---")
    
    # 1. Test Config Defaults
    cfg = ORSConfig()
    print(f"Defaults loaded. Base URL: {cfg.base_url}")
    
    # 2. Test Explicit Key Loading
    cfg_key = ORSConfig(api_key="test_secret_key")
    print(f"Explicit key loaded: {cfg_key.api_key}")
    
    # 3. Test Exception Hierarchy
    try:
        raise RateLimited("Quota exceeded")
    except ORSError as e:
        print(f"Caught expected error: {e.__class__.__name__} -> {e}")
        
    print("--- Done ---")
