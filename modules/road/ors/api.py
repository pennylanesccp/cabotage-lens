# modules/road/ors/api.py
# -*- coding: utf-8 -*-

"""
Road provider facade.
=====================

This module keeps the public `ORSClient` API stable for the rest of the
application while centralizing provider failover:

- primary provider: OpenRouteService
- fallback provider: LocationIQ

The rest of the app continues to call `ORSClient.geocode_*()` and
`ORSClient.route_road()` and receives normalized results regardless of which
provider actually answered.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, TypeVar, Union

if __name__ == "__main__":
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[3]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger
from modules.road.locationiq import LocationIQClient
from modules.road.ors.http import ORSHttpClient
from modules.road.ors.structures import (
    GeocodeNotFound,
    NoRoute,
    ORSConfig,
    ORSError,
    RateLimited,
)
from modules.road.provider_base import BaseRoadProvider

_log = get_logger(__name__)
_T = TypeVar("_T")


class _ProviderProtocol(Protocol):
    name: str

    def is_enabled(self) -> bool:
        ...

    def geocode_text(
        self,
        text: str,
        size: int = 1,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def geocode_structured(
        self,
        address: Optional[str] = None,
        locality: Optional[str] = None,
        region: Optional[str] = None,
        postalcode: Optional[str] = None,
        country: Optional[str] = None,
        size: int = 1,
    ) -> List[Dict[str, Any]]:
        ...

    def resolve_lat_lon(self, query: str) -> Tuple[float, float, str]:
        ...

    def route_road(
        self,
        origin: Union[str, Dict[str, Any]],
        destiny: Union[str, Dict[str, Any]],
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class OpenRouteServiceProvider(BaseRoadProvider):
    """Primary ORS-backed provider implementation."""

    name = "ors"

    def __init__(self, config: Optional[ORSConfig] = None) -> None:
        self.cfg = config or ORSConfig()
        self._http = ORSHttpClient(self.cfg)

    def is_enabled(self) -> bool:
        return bool(self.cfg.api_key)

    def geocode_text(
        self,
        text: str,
        size: int = 1,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params = {
            "text": text,
            "size": size,
            "boundary.country": country or self.cfg.default_country,
        }
        data = self._http.request("GET", "/geocode/search", params=params)
        return self._extract_features(data, query=text)

    def geocode_structured(
        self,
        address: Optional[str] = None,
        locality: Optional[str] = None,
        region: Optional[str] = None,
        postalcode: Optional[str] = None,
        country: Optional[str] = None,
        size: int = 1,
    ) -> List[Dict[str, Any]]:
        params = {
            "address": address,
            "locality": locality,
            "region": region,
            "postalcode": postalcode,
            "country": country or self.cfg.default_country,
            "size": size,
        }
        params = {key: value for key, value in params.items() if value is not None}
        data = self._http.request("GET", "/geocode/search/structured", params=params)
        return self._extract_features(data, query=str(params))

    def route_road(
        self,
        origin: Union[str, Dict[str, Any]],
        destiny: Union[str, Dict[str, Any]],
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        prof = profile or self.cfg.default_profile
        c_start = self._resolve_input(origin)
        c_end = self._resolve_input(destiny)

        payload = {
            "coordinates": [c_start, c_end],
            "units": "m",
            "preference": "fastest",
        }

        try:
            data = self._http.request("POST", f"/v2/directions/{prof}", json_body=payload)
        except RateLimited:
            raise
        except Exception as exc:
            err_msg = str(exc).lower()
            if "404" in err_msg or "400" in err_msg or "no route" in err_msg:
                raise NoRoute(f"No route found between {c_start} and {c_end}") from exc
            raise

        if not isinstance(data, dict):
            raise ORSError("ORS directions returned an invalid payload.")

        routes = data.get("routes", [])
        if not isinstance(routes, list) or not routes:
            raise NoRoute("ORS returned success but the routes list was empty.")

        summary = routes[0].get("summary", {}) if isinstance(routes[0], dict) else {}
        distance_m = summary.get("distance")
        duration_s = summary.get("duration")
        if distance_m is None:
            raise NoRoute("ORS route response did not contain a usable distance.")

        return {
            "distance_m": float(distance_m),
            "duration_s": (None if duration_s is None else float(duration_s)),
            "profile_used": prof,
            "provider": self.name,
            "source": self.name,
            "origin_coords": c_start,
            "destiny_coords": c_end,
        }

    def _extract_features(self, payload: Any, *, query: str) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ORSError(f"ORS geocode returned an invalid payload for '{query}'.")

        features = payload.get("features", [])
        if not isinstance(features, list):
            raise ORSError(f"ORS geocode returned a malformed feature list for '{query}'.")
        if not features:
            raise GeocodeNotFound(f"No results found for '{query}'")
        normalized: list[Dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            copied = dict(feature)
            props = dict(copied.get("properties") or {})
            props.setdefault("provider", self.name)
            copied["properties"] = props
            copied.setdefault("provider", self.name)
            normalized.append(copied)
        if not normalized:
            raise GeocodeNotFound(f"No results found for '{query}'")
        return normalized


class ORSClient:
    """
    Backward-compatible road client facade.

    All existing call sites keep using `ORSClient`, but the implementation now
    attempts ORS first and automatically falls back to LocationIQ when ORS
    fails, is unavailable, or returns no usable result.
    """

    def __init__(
        self,
        config: Optional[ORSConfig] = None,
        *,
        primary_provider: Optional[_ProviderProtocol] = None,
        fallback_provider: Optional[_ProviderProtocol] = None,
    ) -> None:
        self.cfg = config or ORSConfig()
        self._primary = primary_provider or OpenRouteServiceProvider(self.cfg)
        self._fallback = fallback_provider if fallback_provider is not None else LocationIQClient()
        self._metrics_lock = threading.Lock()
        self._provider_metrics: dict[str, dict[str, dict[str, float]]] = {}

    def has_geocoding_provider(self) -> bool:
        return self._primary.is_enabled() or self._fallback.is_enabled()

    def has_routing_provider(self) -> bool:
        return self.has_geocoding_provider()

    def available_providers(self) -> tuple[str, ...]:
        names: list[str] = []
        if self._primary.is_enabled():
            names.append(self._primary.name)
        if self._fallback.is_enabled():
            names.append(self._fallback.name)
        return tuple(names)

    def geocode_text(
        self,
        text: str,
        size: int = 1,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._call_with_fallback(
            operation="geocode_text",
            query=text,
            primary_call=lambda: self._primary.geocode_text(text, size=size, country=country),
            fallback_call=lambda: self._fallback.geocode_text(text, size=size, country=country),
        )

    def geocode_structured(
        self,
        address: Optional[str] = None,
        locality: Optional[str] = None,
        region: Optional[str] = None,
        postalcode: Optional[str] = None,
        country: Optional[str] = None,
        size: int = 1,
    ) -> List[Dict[str, Any]]:
        query_parts = [address, locality, region, postalcode, country]
        query = ", ".join(str(part).strip() for part in query_parts if str(part or "").strip()) or "<structured>"
        return self._call_with_fallback(
            operation="geocode_structured",
            query=query,
            primary_call=lambda: self._primary.geocode_structured(
                address=address,
                locality=locality,
                region=region,
                postalcode=postalcode,
                country=country,
                size=size,
            ),
            fallback_call=lambda: self._fallback.geocode_structured(
                address=address,
                locality=locality,
                region=region,
                postalcode=postalcode,
                country=country,
                size=size,
            ),
        )

    def resolve_lat_lon(self, query: str) -> Tuple[float, float, str]:
        features = self.geocode_text(query, size=1)
        top = features[0]
        props = top.get("properties", {})
        geom = top.get("geometry", {})
        coords = geom.get("coordinates", [0.0, 0.0])
        return float(coords[1]), float(coords[0]), str(props.get("label") or query)

    def route_road(
        self,
        origin: Union[str, Dict[str, Any]],
        destiny: Union[str, Dict[str, Any]],
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = f"{origin!r} -> {destiny!r}"
        return self._call_with_fallback(
            operation="route_road",
            query=query,
            primary_call=lambda: self._primary.route_road(origin, destiny, profile=profile),
            fallback_call=lambda: self._fallback.route_road(origin, destiny, profile=profile),
        )

    def metrics_snapshot(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        with self._metrics_lock:
            return {
                provider: {
                    operation: dict(stats)
                    for operation, stats in operations.items()
                }
                for provider, operations in self._provider_metrics.items()
            }

    def reset_metrics(self) -> None:
        with self._metrics_lock:
            self._provider_metrics.clear()

    def _call_with_fallback(
        self,
        *,
        operation: str,
        query: str,
        primary_call: Callable[[], _T],
        fallback_call: Callable[[], _T],
    ) -> _T:
        primary_enabled = self._primary.is_enabled()
        fallback_enabled = self._fallback.is_enabled()
        if not primary_enabled and not fallback_enabled:
            raise ORSError(
                f"No provider is configured for {operation}. Set ORS_API_KEY or LOCATIONIQ_PAT."
            )

        primary_exc: Exception | None = None
        fallback_exc: Exception | None = None

        if primary_enabled:
            try:
                t0 = time.perf_counter()
                self._record_metric(self._primary.name, operation, "attempts", 1.0)
                _log.info(
                    "Provider attempt operation=%s provider=%s query=%s",
                    operation,
                    self._primary.name,
                    query,
                )
                result = primary_call()
                duration_s = time.perf_counter() - t0
                self._record_metric(self._primary.name, operation, "successes", 1.0, duration_s=duration_s)
                _log.info(
                    "Provider success operation=%s provider=%s query=%s",
                    operation,
                    self._primary.name,
                    query,
                )
                return result
            except Exception as exc:
                duration_s = time.perf_counter() - t0
                self._record_metric(self._primary.name, operation, "failures", 1.0, duration_s=duration_s)
                primary_exc = exc
                _log.warning(
                    "Provider fallback triggered operation=%s provider=%s query=%s reason=%s",
                    operation,
                    self._primary.name,
                    query,
                    self._format_exception(exc),
                )
        else:
            primary_exc = ORSError("ORS_API_KEY is not configured.")
            _log.warning(
                "Primary provider unavailable operation=%s provider=%s query=%s reason=%s",
                operation,
                self._primary.name,
                query,
                self._format_exception(primary_exc),
            )

        if fallback_enabled:
            try:
                t0 = time.perf_counter()
                self._record_metric(self._fallback.name, operation, "attempts", 1.0)
                _log.info(
                    "Provider attempt operation=%s provider=%s query=%s",
                    operation,
                    self._fallback.name,
                    query,
                )
                result = fallback_call()
                duration_s = time.perf_counter() - t0
                self._record_metric(self._fallback.name, operation, "successes", 1.0, duration_s=duration_s)
                _log.info(
                    "Provider success operation=%s provider=%s query=%s fallback_from=%s",
                    operation,
                    self._fallback.name,
                    query,
                    self._primary.name,
                )
                return result
            except Exception as exc:
                duration_s = time.perf_counter() - t0
                self._record_metric(self._fallback.name, operation, "failures", 1.0, duration_s=duration_s)
                fallback_exc = exc
                _log.error(
                    "Provider fallback failed operation=%s provider=%s query=%s reason=%s",
                    operation,
                    self._fallback.name,
                    query,
                    self._format_exception(exc),
                )
        else:
            _log.warning(
                "Fallback provider unavailable operation=%s provider=%s query=%s reason=LOCATIONIQ_PAT is not configured",
                operation,
                self._fallback.name,
                query,
            )

        if primary_exc and fallback_exc:
            raise self._merge_failures(operation, primary_exc, fallback_exc)
        if primary_exc:
            raise primary_exc
        raise ORSError(f"{operation} failed without a usable provider result.")

    def _merge_failures(
        self,
        operation: str,
        primary_exc: Exception,
        fallback_exc: Exception,
    ) -> Exception:
        message = (
            f"{operation} failed for ORS and LocationIQ: "
            f"ors={self._format_exception(primary_exc)}; "
            f"locationiq={self._format_exception(fallback_exc)}"
        )
        if isinstance(primary_exc, RateLimited) or isinstance(fallback_exc, RateLimited):
            return RateLimited(message)
        if isinstance(primary_exc, GeocodeNotFound) and isinstance(fallback_exc, GeocodeNotFound):
            return GeocodeNotFound(message)
        if isinstance(primary_exc, NoRoute) and isinstance(fallback_exc, NoRoute):
            return NoRoute(message)
        return ORSError(message)

    def _format_exception(self, exc: Exception) -> str:
        text = str(exc).strip()
        return text or exc.__class__.__name__

    def _record_metric(
        self,
        provider: str,
        operation: str,
        field: str,
        value: float,
        *,
        duration_s: float = 0.0,
    ) -> None:
        with self._metrics_lock:
            provider_metrics = self._provider_metrics.setdefault(provider, {})
            operation_metrics = provider_metrics.setdefault(
                operation,
                {
                    "attempts": 0.0,
                    "successes": 0.0,
                    "failures": 0.0,
                    "duration_s": 0.0,
                },
            )
            operation_metrics[field] = float(operation_metrics.get(field, 0.0) + value)
            operation_metrics["duration_s"] = float(operation_metrics.get("duration_s", 0.0) + duration_s)


if __name__ == "__main__":
    from modules.infra.log_manager import init_logging

    init_logging(level="INFO")

    print("--- Road Provider Smoke Test ---")
    try:
        client = ORSClient()
        lat, lon, lbl = client.resolve_lat_lon("Sao Paulo, Brasil")
        print(f"Found: {lbl} ({lat:.4f}, {lon:.4f})")

        sp_dict = {"lat": -23.55, "lon": -46.63}
        santos_dict = {"lat": -23.96, "lon": -46.33}
        res = client.route_road(sp_dict, santos_dict)
        dist_km = (res["distance_m"] or 0) / 1000.0
        print(f"Route found: {dist_km:.2f} km via {res.get('source')}")
    except Exception as exc:
        print(f"Smoke test skipped/failed (check provider keys): {exc}")

    print("--- Done ---")
