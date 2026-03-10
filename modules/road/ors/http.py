# modules/road/ors/http.py
# -*- coding: utf-8 -*-

"""
ORS HTTP Engine.

Manages low-level communication with the ORS API.
Key responsibilities:
1. In-process response caching.
2. Retry handling for transient 5xx failures.
3. Explicit rate-limit detection for 429 responses.
"""

from __future__ import annotations

import hashlib
import json
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


class _MemoryCache:
    """A lightweight in-process key-value store with TTL support."""

    def __init__(self, ttl_s: int) -> None:
        self.ttl_s = ttl_s
        self._items: dict[str, tuple[float, Dict[str, Any]]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        record = self._items.get(key)
        if record is None:
            return None

        inserted_at, payload = record
        if self.ttl_s > 0 and (time.time() - inserted_at) > self.ttl_s:
            _log.debug("Cache expired for key %s...", key[:8])
            self._items.pop(key, None)
            return None

        return payload

    def set(self, key: str, data: Dict[str, Any]) -> None:
        self._items[key] = (time.time(), data)


class ORSHttpClient:
    """Raw communication layer for OpenRouteService."""

    def __init__(self, config: ORSConfig) -> None:
        self.cfg = config
        self._cache = _MemoryCache(self.cfg.cache_ttl_s) if self.cfg.cache_enabled else None
        self._session = self._build_session()
        _log.debug("ORSHttpClient initialized. BaseURL=%s", self.cfg.base_url)

    def _build_session(self) -> requests.Session:
        sess = requests.Session()
        sess.headers.update(
            {
                "Authorization": self.cfg.api_key or "",
                "User-Agent": "CarbonFootprint/ORS-Client-v2",
                "Accept": "application/json",
            }
        )

        retries = Retry(
            total=self.cfg.retry_limit,
            backoff_factor=0.5,
            status_forcelist={500, 502, 503, 504},
            allowed_methods={"GET", "POST"},
        )
        sess.mount("https://", HTTPAdapter(max_retries=retries))
        return sess

    def _generate_cache_key(self, method: str, endpoint: str, payload: Dict[str, Any]) -> str:
        payload_str = json.dumps(payload, sort_keys=True)
        raw = f"{method.upper()}|{endpoint}|{payload_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        payload_for_key = params or json_body or {}

        if use_cache and self._cache:
            key = self._generate_cache_key(method, endpoint, payload_for_key)
            cached_data = self._cache.get(key)
            if cached_data is not None:
                _log.debug("CACHE HIT: %s %s (Key: %s)", method, endpoint, key[:8])
                return cached_data

        if not self.cfg.api_key:
            _log.error("Attempted API call without ORS_API_KEY.")
            raise ORSError("ORS API Key is missing. Set ORS_API_KEY in Streamlit secrets.")

        url = f"{self.cfg.base_url}{endpoint}"
        _log.info("API CALL: %s %s", method, endpoint)

        try:
            t0 = time.time()
            resp = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                timeout=self.cfg.timeout,
            )
            duration_ms = (time.time() - t0) * 1000

            if resp.status_code == 429:
                _log.warning("ORS Rate Limit Exceeded (429).")
                raise RateLimited(f"Quota exceeded: {resp.text}")

            resp.raise_for_status()

            data = resp.json()
            _log.debug("API SUCCESS: %.0fms, Size=%db", duration_ms, len(resp.content))

            if use_cache and self._cache:
                key = self._generate_cache_key(method, endpoint, payload_for_key)
                self._cache.set(key, data)

            return data

        except requests.RequestException as exc:
            _log.error("Network Error on %s: %s", endpoint, exc)
            raise ORSError(f"Communication failure: {exc}") from exc


if __name__ == "__main__":
    from modules.infra.log_manager import init_logging

    init_logging(level="DEBUG")

    print("--- ORS HTTP Engine Smoke Test ---")

    cfg = ORSConfig(api_key="TEST_KEY_INVALID", cache_enabled=False)
    client = ORSHttpClient(cfg)

    print("1. Testing connectivity (expecting 401/403)...")
    try:
        client.request("GET", "/v2/status", use_cache=False)
    except ORSError as exc:
        print(f"Request attempted and failed as expected: {exc}")

    print("--- Done ---")
