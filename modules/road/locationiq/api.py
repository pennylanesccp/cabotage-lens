from __future__ import annotations

import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union

from modules.road.locationiq.http import LocationIQHttpClient
from modules.road.locationiq.structures import LocationIQConfig
from modules.road.ors.structures import GeocodeNotFound, NoRoute, ORSError, RateLimited
from modules.road.provider_base import BaseRoadProvider

_BRAZIL_STATE_CODES = {
    "acre": "AC",
    "alagoas": "AL",
    "amapa": "AP",
    "amazonas": "AM",
    "bahia": "BA",
    "ceara": "CE",
    "distrito federal": "DF",
    "espirito santo": "ES",
    "goias": "GO",
    "maranhao": "MA",
    "mato grosso": "MT",
    "mato grosso do sul": "MS",
    "minas gerais": "MG",
    "para": "PA",
    "paraiba": "PB",
    "parana": "PR",
    "pernambuco": "PE",
    "piaui": "PI",
    "rio de janeiro": "RJ",
    "rio grande do norte": "RN",
    "rio grande do sul": "RS",
    "rondonia": "RO",
    "roraima": "RR",
    "santa catarina": "SC",
    "sao paulo": "SP",
    "sergipe": "SE",
    "tocantins": "TO",
}


def _ascii_lower(value: Any) -> str:
    text = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


class LocationIQClient(BaseRoadProvider):
    """Optional LocationIQ fallback provider for geocoding and directions."""

    name = "locationiq"

    def __init__(self, config: Optional[LocationIQConfig] = None, *, provider_name: Optional[str] = None) -> None:
        self.cfg = config or LocationIQConfig()
        self.name = str(provider_name or self.name).strip() or "locationiq"
        self._http = LocationIQHttpClient(self.cfg)

    def is_enabled(self) -> bool:
        return bool(self.cfg.api_key)

    def geocode_text(
        self,
        text: str,
        size: int = 1,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "q": text,
            "format": "json",
            "limit": max(int(size), 1),
            "addressdetails": 1,
        }
        country_code = str(country or self.cfg.default_country or "").strip().lower()
        if country_code:
            params["countrycodes"] = country_code

        data = self._http.request("GET", "/search", params=params)
        if isinstance(data, dict) and any(key in data for key in ("error", "message")):
            raise ORSError(
                str(data.get("error") or data.get("message") or "LocationIQ geocode failed.")
            )
        hits = data if isinstance(data, list) else []
        features = [
            self._normalize_hit(hit, fallback_label=text)
            for hit in hits
            if isinstance(hit, dict)
        ]
        features = [feature for feature in features if feature is not None]
        if not features:
            raise GeocodeNotFound(f"No LocationIQ results found for '{text}'")
        return features[: max(int(size), 1)]

    def geocode_structured(
        self,
        address: Optional[str] = None,
        locality: Optional[str] = None,
        region: Optional[str] = None,
        postalcode: Optional[str] = None,
        country: Optional[str] = None,
        size: int = 1,
    ) -> List[Dict[str, Any]]:
        parts = [address, locality, region, postalcode, country or self.cfg.default_country]
        query = ", ".join(str(part).strip() for part in parts if str(part or "").strip())
        if not query:
            raise GeocodeNotFound("No LocationIQ structured query fields were provided.")
        return self.geocode_text(query, size=size, country=country)

    def route_road(
        self,
        origin: Union[str, Dict[str, Any]],
        destiny: Union[str, Dict[str, Any]],
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        requested_profile = str(profile or self.cfg.default_profile).strip().lower() or self.cfg.default_profile
        provider_profile = self._provider_profile(requested_profile)
        profile_used = "driving-car" if provider_profile == "driving" else requested_profile

        c_start = self._resolve_input(origin)
        c_end = self._resolve_input(destiny)
        coords = f"{c_start[0]},{c_start[1]};{c_end[0]},{c_end[1]}"
        params = {
            "overview": "false",
            "steps": "false",
            "alternatives": "false",
        }

        try:
            data = self._http.request("GET", f"/directions/{provider_profile}/{coords}", params=params)
        except RateLimited:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "404" in message or "400" in message or "no route" in message:
                raise NoRoute(f"No LocationIQ route found between {c_start} and {c_end}") from exc
            raise

        route_obj = self._extract_route(data)
        distance_m, duration_s = self._extract_summary(route_obj)
        if distance_m is None:
            raise NoRoute("LocationIQ route response did not contain a usable distance.")

        return {
            "distance_m": float(distance_m),
            "duration_s": (None if duration_s is None else float(duration_s)),
            "profile_used": profile_used,
            "provider_profile": provider_profile,
            "provider": self.name,
            "source": self.name,
            "origin_coords": c_start,
            "destiny_coords": c_end,
        }

    def _provider_profile(self, requested_profile: str) -> str:
        if requested_profile in {"driving-hgv", "driving-car", "driving"}:
            return "driving"
        return requested_profile

    def _extract_route(self, payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ORSError("LocationIQ directions returned an invalid payload.")

        routes = payload.get("routes")
        if isinstance(routes, list) and routes:
            route_obj = routes[0]
        elif isinstance(routes, dict):
            route_obj = routes
        else:
            route_obj = payload.get("route")

        if not isinstance(route_obj, dict):
            raise NoRoute("LocationIQ directions returned no routes.")
        return route_obj

    def _extract_summary(self, route_obj: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        summary = route_obj.get("summary")
        if isinstance(summary, dict):
            distance = summary.get("distance")
            duration = summary.get("duration")
        else:
            distance = route_obj.get("distance")
            duration = route_obj.get("duration")

        if distance is None or duration is None:
            legs = route_obj.get("legs")
            if isinstance(legs, list) and legs:
                distance = distance if distance is not None else 0.0
                duration = duration if duration is not None else 0.0
                for leg in legs:
                    if not isinstance(leg, dict):
                        continue
                    leg_summary = leg.get("summary") if isinstance(leg.get("summary"), dict) else {}
                    leg_distance = leg_summary.get("distance", leg.get("distance"))
                    leg_duration = leg_summary.get("duration", leg.get("duration"))
                    if leg_distance is not None:
                        distance = float(distance) + float(leg_distance)
                    if leg_duration is not None:
                        duration = float(duration) + float(leg_duration)

        return (
            None if distance is None else float(distance),
            None if duration is None else float(duration),
        )

    def _normalize_hit(self, raw: Dict[str, Any], *, fallback_label: str) -> Optional[Dict[str, Any]]:
        try:
            lat = float(raw["lat"])
            lon = float(raw["lon"])
        except (KeyError, TypeError, ValueError):
            return None

        address = raw.get("address") if isinstance(raw.get("address"), dict) else {}
        display_name = str(raw.get("display_name") or raw.get("name") or fallback_label)
        region = (
            address.get("state")
            or address.get("state_district")
            or address.get("county")
            or address.get("region")
        )
        region_code = address.get("state_code")
        if not region_code and region:
            region_code = _BRAZIL_STATE_CODES.get(_ascii_lower(region))

        layer = self._infer_layer(raw, address)
        properties = {
            "label": display_name,
            "name": str(raw.get("name") or display_name),
            "layer": layer,
            "region": region,
            "region_a": region_code,
            "country": address.get("country"),
            "country_a": str(address.get("country_code") or "").upper() or None,
            "provider": self.name,
        }
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": properties,
            "provider": self.name,
        }

    def _infer_layer(self, raw: Dict[str, Any], address: Dict[str, Any]) -> str:
        raw_type = str(raw.get("type") or "").strip().lower()
        raw_class = str(raw.get("class") or "").strip().lower()

        if "postcode" in raw_type or "postcode" in raw_class or address.get("postcode"):
            return "postalcode"
        if raw_type in {"city", "town", "village", "hamlet", "municipality"}:
            return "locality"
        if raw_type in {"road", "street"}:
            return "street"
        if raw_type in {"house", "building"}:
            return "address"
        if raw_type:
            return raw_type
        return "address"
