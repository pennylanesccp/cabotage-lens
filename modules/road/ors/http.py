# modules/road/ors/http.py
# -*- coding: utf-8 -*-

"""
ORS HTTP Engine.
================

Manages the low-level details of communicating with the ORS API.
Key responsibilities:
1.  **Caching:** Persists responses to SQLite to save quota/money.
2.  **Resilience:** Automatically retries transient failures (5xx).
3.  **Compliance:** Respects Rate Limits (429) by raising specific exceptions.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Path Bootstrap for direct execution
if __name__ == "__main__":
    import sys
    ROOT = Path(__file__).resolve().parents[3]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger
from modules.road.ors.structures import ORSConfig, ORSError, RateLimited

_log = get_logger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Cache Implementation
# ────────────────────────────────────────────────────────────────────────────────

class _SQLiteCache:
    """
    A lightweight, persistent key-value store backed by SQLite.
    Used to store raw JSON responses from the API.
    """
    
    def __init__(self, db_path: Path, ttl_s: int) -> None:
        self.db_path = db_path
        self.ttl_s = ttl_s
        self._init_db()

    def _init_db(self) -> None:
        """Ensure DB file and table exist."""
        if not self.db_path.parent.exists():
            _log.debug(f"Creating cache directory: {self.db_path.parent}")
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS http_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp REAL
                )
            """)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached response if it exists and is not expired."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT data, timestamp FROM http_cache WHERE key = ?", (key,)
            ).fetchone()
            
            if not row:
                return None
            
            data_str, ts = row
            # Check TTL (if ttl_s > 0)
            if self.ttl_s > 0 and (time.time() - ts) > self.ttl_s:
                _log.debug(f"Cache expired for key {key[:8]}...")
                return None
                
            return json.loads(data_str) # type: ignore

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Upsert a response into the cache."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO http_cache VALUES (?, ?, ?)",
                (key, json.dumps(data), time.time())
            )


# ────────────────────────────────────────────────────────────────────────────────
# HTTP Client
# ────────────────────────────────────────────────────────────────────────────────

class ORSHttpClient:
    """
    The raw communication layer for OpenRouteService.
    Does not know about 'Routing' or 'Geocoding', just GET/POST and JSON.
    """

    def __init__(self, config: ORSConfig) -> None:
        self.cfg = config
        
        # Initialize Cache
        self._cache = None
        if self.cfg.cache_path:
            self._cache = _SQLiteCache(self.cfg.cache_path, self.cfg.cache_ttl_s)
        
        # Initialize Session
        self._session = self._build_session()
        _log.debug(f"ORSHttpClient initialized. BaseURL={self.cfg.base_url}")

    def _build_session(self) -> requests.Session:
        """Construct a requests Session with retry logic."""
        sess = requests.Session()
        
        # Global Headers
        sess.headers.update({
            "Authorization": self.cfg.api_key or "",
            "User-Agent": "CarbonFootprint/ORS-Client-v2",
            "Accept": "application/json"
        })

        # Retry Strategy (Transient Errors only)
        retries = Retry(
            total=self.cfg.retry_limit,
            backoff_factor=0.5,
            status_forcelist={500, 502, 503, 504},
            allowed_methods={"GET", "POST"}
        )
        sess.mount("https://", HTTPAdapter(max_retries=retries))
        return sess

    def _generate_cache_key(self, method: str, endpoint: str, payload: Dict[str, Any]) -> str:
        """Create a deterministic hash of the request parameters."""
        # Sort keys to ensure {"a":1, "b":2} == {"b":2, "a":1}
        payload_str = json.dumps(payload, sort_keys=True)
        raw = f"{method.upper()}|{endpoint}|{payload_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Perform an HTTP request with automatic caching and error handling.

        Returns
        -------
        Dict[str, Any]
            The parsed JSON response.
        """
        # 1. Combine params/json for cache key generation
        payload_for_key = params or json_body or {}
        
        # 2. Check Cache
        if use_cache and self._cache:
            key = self._generate_cache_key(method, endpoint, payload_for_key)
            cached_data = self._cache.get(key)
            if cached_data:
                _log.debug(f"CACHE HIT: {method} {endpoint} (Key: {key[:8]})")
                return cached_data

        # 3. Validate API Key before hitting network
        if not self.cfg.api_key:
            _log.error("Attempted API call without ORS_API_KEY.")
            raise ORSError("ORS API Key is missing. Please set ORS_API_KEY env var.")

        # 4. Network Call
        url = f"{self.cfg.base_url}{endpoint}"
        _log.info(f"API CALL: {method} {endpoint}")
        
        try:
            t0 = time.time()
            resp = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                timeout=self.cfg.timeout
            )
            duration_ms = (time.time() - t0) * 1000
            
            # 5. Handle Rate Limits (429) explicitly
            if resp.status_code == 429:
                _log.warning("ORS Rate Limit Exceeded (429).")
                raise RateLimited(f"Quota exceeded: {resp.text}")
            
            # 6. Handle other errors
            resp.raise_for_status()
            
            data = resp.json()
            _log.debug(f"API SUCCESS: {duration_ms:.0f}ms, Size={len(resp.content)}b")

            # 7. Write to Cache
            if use_cache and self._cache:
                # Re-generate key (safe practice)
                key = self._generate_cache_key(method, endpoint, payload_for_key)
                self._cache.set(key, data) # type: ignore
            
            return data

        except requests.RequestException as e:
            _log.error(f"Network Error on {endpoint}: {e}")
            raise ORSError(f"Communication failure: {e}") from e


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging
    init_logging(level="DEBUG")

    print("--- ORS HTTP Engine Smoke Test ---")
    
    # Initialize with a dummy key (expecting auth failure, which proves connectivity)
    cfg = ORSConfig(api_key="TEST_KEY_INVALID", cache_path=Path(".cache/smoke_test.db"))
    client = ORSHttpClient(cfg)
    
    print("1. Testing connectivity (expecting 401/403)...")
    try:
        client.request("GET", "/v2/status", use_cache=False)
    except ORSError as e:
        print(f"✅ Request attempted and failed as expected: {e}")
        
    print("--- Done ---")