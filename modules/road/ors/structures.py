# modules/road/ors/structures.py
# -*- coding: utf-8 -*-

"""
ORS Data Structures.
====================

Defines the configuration, constants, and custom exceptions for the
OpenRouteService client. This module contains no logic, only definitions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://api.openrouteservice.org"
DEFAULT_USER_AGENT = "CarbonFootprint-ORS/2.0"
ENV_API_KEY = "ORS_API_KEY"

# ────────────────────────────────────────────────────────────────────────────────
# Exceptions
# ────────────────────────────────────────────────────────────────────────────────

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

# ────────────────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class ORSConfig:
    """
    Configuration object for the ORS Client.

    Attributes
    ----------
    api_key : str, optional
        The OpenRouteService API key. If None, the client will attempt
        to load it from the `ORS_API_KEY` environment variable.
    base_url : str
        The root URL for the API. Defaults to the public ORS instance.
    cache_path : Path, optional
        Path to the SQLite cache file. If None, caching is disabled.
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
    cache_path: Optional[Path] = field(
        default_factory=lambda: Path(".cache/ors_cache.sqlite")
    )
    cache_ttl_s: int = 2_592_000  # 30 days (30 * 24 * 3600)

    # HTTP Behavior
    timeout: tuple[float, float] = (10.0, 60.0)
    retry_limit: int = 3
    
    # Domain Defaults
    default_profile: str = "driving-hgv"
    default_country: str = "BR"

    def __post_init__(self) -> None:
        """
        Auto-configuration hook.
        Loads the API key from the environment if one wasn't provided explicitly.
        """
        if not self.api_key:
            self.api_key = os.getenv(ENV_API_KEY)


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("--- ORS Structures Smoke Test ---")
    
    # 1. Test Config Defaults
    cfg = ORSConfig()
    print(f"Defaults loaded. Base URL: {cfg.base_url}")
    
    # 2. Test Env Var Loading
    os.environ[ENV_API_KEY] = "test_env_key"
    cfg_env = ORSConfig()
    print(f"Env key loaded: {cfg_env.api_key}")
    
    # 3. Test Exception Hierarchy
    try:
        raise RateLimited("Quota exceeded")
    except ORSError as e:
        print(f"Caught expected error: {e.__class__.__name__} -> {e}")
        
    print("--- Done ---")