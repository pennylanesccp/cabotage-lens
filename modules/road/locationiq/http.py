from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from modules.infra.log_manager import get_logger
from modules.road.locationiq.structures import LocationIQConfig
from modules.road.ors.structures import ORSError, RateLimited

_log = get_logger(__name__)

_QUOTA_ERROR_HINTS = (
    "quota",
    "rate limit",
    "limit exceeded",
    "daily",
    "too many requests",
    "request limit",
)


class _MemoryCache:
    def __init__(self, ttl_s: int) -> None:
        self.ttl_s = ttl_s
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        record = self._items.get(key)
        if record is None:
            return None

        inserted_at, payload = record
        if self.ttl_s > 0 and (time.time() - inserted_at) > self.ttl_s:
            self._items.pop(key, None)
            return None

        return payload

    def set(self, key: str, data: Any) -> None:
        self._items[key] = (time.time(), data)


class LocationIQHttpClient:
    """Raw communication layer for LocationIQ."""

    def __init__(self, config: LocationIQConfig) -> None:
        self.cfg = config
        self._cache = _MemoryCache(self.cfg.cache_ttl_s) if self.cfg.cache_enabled else None
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": "CarbonFootprint/LocationIQ-Client-v1",
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
    ) -> Any:
        payload_for_key = dict(params or json_body or {})

        if use_cache and self._cache:
            key = self._generate_cache_key(method, endpoint, payload_for_key)
            cached_data = self._cache.get(key)
            if cached_data is not None:
                _log.debug("CACHE HIT: %s %s provider=locationiq key=%s", method, endpoint, key[:8])
                return cached_data

        if not self.cfg.api_key:
            raise ORSError(
                "LocationIQ API key is missing. Set LOCATIONIQ_PATS (preferred) or LOCATIONIQ_PAT in Streamlit secrets or the environment."
            )

        merged_params = dict(params or {})
        merged_params["key"] = self.cfg.api_key

        url = f"{self.cfg.base_url}{endpoint}"
        _log.debug("API CALL: %s %s provider=locationiq", method, endpoint)

        try:
            t0 = time.time()
            resp = self._session.request(
                method=method,
                url=url,
                params=merged_params,
                json=json_body,
                timeout=self.cfg.timeout,
            )
            duration_ms = (time.time() - t0) * 1000

            response_text = resp.text or ""
            normalized_text = response_text.lower()
            if resp.status_code == 429 or (
                resp.status_code == 403
                and any(token in normalized_text for token in _QUOTA_ERROR_HINTS)
            ):
                raise RateLimited(f"LocationIQ quota exceeded ({resp.status_code}): {response_text}")

            resp.raise_for_status()
            data = resp.json()
            _log.debug(
                "API SUCCESS: %.0fms provider=locationiq endpoint=%s size=%db",
                duration_ms,
                endpoint,
                len(resp.content),
            )

            if use_cache and self._cache:
                key = self._generate_cache_key(method, endpoint, payload_for_key)
                self._cache.set(key, data)

            return data
        except requests.RequestException as exc:
            raise ORSError(f"LocationIQ communication failure: {exc}") from exc
