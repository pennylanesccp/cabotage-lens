# modules/road/ors/api.py
# -*- coding: utf-8 -*-

"""
ORS Client API.
===============

High-level interface for OpenRouteService.
Provides semantic methods for:
- Geocoding (Forward/Reverse/Structured)
- Routing (Directions)
- Matrix (Distance Tables) - *Placeholder for future implementation*
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

# Path Bootstrap for direct execution
if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[3]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from modules.infra.log_manager import get_logger
from modules.road.ors.structures import ORSConfig, GeocodeNotFound, NoRoute
from modules.road.ors.http import ORSHttpClient

_log = get_logger(__name__)


class ORSClient:
    """
    The main entry point for the application to use OpenRouteService.
    Wraps the generic HTTP client with domain-specific logic.
    """

    def __init__(self, config: Optional[ORSConfig] = None) -> None:
        self.cfg = config or ORSConfig()
        self._http = ORSHttpClient(self.cfg)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Geocoding Methods
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def geocode_text(
        self, 
        text: str, 
        size: int = 1, 
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform free-text geocoding (Pelias /geocode/search).

        Parameters
        ----------
        text : str
            The address or place name to search for.
        size : int
            Max number of results to return.
        country : str, optional
            ISO alpha-2 country code (e.g., 'BR') to bias results.

        Returns
        -------
        List[Dict]
            A list of GeoJSON feature dictionaries.
        """
        params = {
            "text": text,
            "size": size,
            "boundary.country": country or self.cfg.default_country
        }
        
        _log.debug(f"Geocoding text: '{text}' (size={size})")
        data = self._http.request("GET", "/geocode/search", params=params)
        features = data.get("features", [])
        
        if not features:
            _log.warning(f"Geocode returned 0 results for: '{text}'")
            raise GeocodeNotFound(f"No results found for '{text}'")
            
        return features # type: ignore

    def geocode_structured(
        self,
        address: Optional[str] = None,
        locality: Optional[str] = None,
        region: Optional[str] = None,
        postalcode: Optional[str] = None,
        country: Optional[str] = None,
        size: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Perform structured geocoding. Better for specific address components.
        """
        params = {
            "address": address,
            "locality": locality,
            "region": region,
            "postalcode": postalcode,
            "country": country or self.cfg.default_country,
            "size": size
        }
        # Clean None values
        params = {k: v for k, v in params.items() if v is not None}
        
        _log.debug(f"Geocoding structured: {params}")
        data = self._http.request("GET", "/geocode/search/structured", params=params)
        features = data.get("features", [])
        
        if not features:
            raise GeocodeNotFound(f"No structured results for {params}")
            
        return features # type: ignore

    def resolve_lat_lon(self, query: str) -> Tuple[float, float, str]:
        """
        Convenience helper: Get (lat, lon, label) for a single query string.
        Returns the top match.
        """
        features = self.geocode_text(query, size=1)
        top = features[0]
        
        props = top.get("properties", {})
        geom = top.get("geometry", {})
        coords = geom.get("coordinates", [0.0, 0.0]) # [lon, lat]
        
        # Return lat, lon, label
        return coords[1], coords[0], props.get("label", query)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Routing Methods
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def route_road(
        self,
        origin: Union[str, Dict[str, Any]],
        destiny: Union[str, Dict[str, Any]],
        profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get directions between two points (Origin -> Destiny).
        
        Inputs can be:
        - Strings: "Sao Paulo" (will be geocoded)
        - Dicts: {"lat": -23.5, "lon": -46.6} (used directly)
        
        Returns
        -------
        Dict containing:
            - distance_m (float)
            - duration_s (float)
            - geometry (encoded polyline, if requested)
        """
        prof = profile or self.cfg.default_profile
        
        # 1. Resolve Inputs to Coordinates [lon, lat]
        c_start = self._resolve_input(origin)
        c_end = self._resolve_input(destiny)
        
        _log.info(f"Routing ({prof}): {c_start} -> {c_end}")
        
        # 2. Build Payload
        payload = {
            "coordinates": [c_start, c_end], # ORS expects [[lon, lat], [lon, lat]]
            "units": "m",
            "preference": "fastest"
        }
        
        # 3. Execute
        try:
            data = self._http.request("POST", f"/v2/directions/{prof}", json_body=payload)
        except Exception as e:
            # Catch generic HTTP errors and check for 404/400 which mean "No Route"
            err_msg = str(e).lower()
            if "404" in err_msg or "400" in err_msg:
                _log.warning(f"ORS failed to find route: {err_msg}")
                raise NoRoute(f"No route found between {c_start} and {c_end}") from e
            raise

        # 4. Parse Response
        routes = data.get("routes", [])
        if not routes:
            raise NoRoute("API returned success but 'routes' list is empty.")
            
        summary = routes[0].get("summary", {})
        
        return {
            "distance_m": summary.get("distance"),
            "duration_s": summary.get("duration"),
            "profile_used": prof,
            # Pass back metadata if needed
            "origin_coords": c_start,
            "destiny_coords": c_end
        }

    def _resolve_input(self, point: Union[str, Dict[str, Any]]) -> List[float]:
        """
        Helper: Convert diverse inputs into [lon, lat] list.
        """
        # A) Dictionary with explicit coords (e.g., from Ports module)
        if isinstance(point, dict):
            # Support various keys: lat/lon, latitude/longitude
            lat = point.get("lat") or point.get("latitude")
            lon = point.get("lon") or point.get("longitude")
            
            if lat is not None and lon is not None:
                return [float(lon), float(lat)]
            
            # If dict lacks coords, maybe it has a 'label' or 'input' to geocode?
            query = point.get("label") or point.get("input")
            if query:
                _log.debug(f"Input dict missing coords, geocoding label: '{query}'")
                lat_g, lon_g, _ = self.resolve_lat_lon(str(query))
                return [lon_g, lat_g]
        
        # B) String Input -> Geocode it
        if isinstance(point, str):
            # Is it "lat,lon"?
            if "," in point:
                try:
                    parts = point.split(",")
                    # Try parsing as explicit coords first
                    lat_f = float(parts[0].strip())
                    lon_f = float(parts[1].strip())
                    return [lon_f, lat_f]
                except ValueError:
                    pass # Not numbers, treat as address
            
            # Treat as address
            lat_g, lon_g, _ = self.resolve_lat_lon(point)
            return [lon_g, lat_g]

        raise ValueError(f"Could not resolve point input: {point}")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Smoke Test
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    from modules.infra.log_manager import init_logging
    init_logging(level="INFO")

    print("--- ORS API Smoke Test ---")
    try:
        # Needs valid ORS_API_KEY in Streamlit secrets
        ors = ORSClient()
        
        print("\n1. Testing Geocode (SP)...")
        lat, lon, lbl = ors.resolve_lat_lon("SÃ£o Paulo, Brasil")
        print(f"âœ… Found: {lbl} ({lat:.4f}, {lon:.4f})")
        
        print("\n2. Testing Routing (SP -> Santos)...")
        # Use the explicit method with [lon, lat] logic inside
        # SP (-23.55, -46.63), Santos (-23.96, -46.33)
        sp_dict = {"lat": -23.55, "lon": -46.63}
        santos_dict = {"lat": -23.96, "lon": -46.33}
        
        res = ors.route_road(sp_dict, santos_dict)
        dist_km = (res['distance_m'] or 0) / 1000.0
        print(f"âœ… Route found: {dist_km:.2f} km")
        
    except Exception as e:
        print(f"âš ï¸ Test skipped/failed (check API key): {e}")
        
    print("\n--- Done ---")
