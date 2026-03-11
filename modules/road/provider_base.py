from __future__ import annotations

from typing import Any, Dict, List, Tuple, Union

from modules.road.ors.structures import GeocodeNotFound


class BaseRoadProvider:
    """Shared coordinate-resolution helpers for road API providers."""

    name = "provider"

    def geocode_text(
        self,
        text: str,
        size: int = 1,
        country: str | None = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def resolve_lat_lon(self, query: str) -> Tuple[float, float, str]:
        features = self.geocode_text(query, size=1)
        if not features:
            raise GeocodeNotFound(f"No results found for '{query}'")

        top = features[0]
        props = top.get("properties", {}) if isinstance(top, dict) else {}
        geom = top.get("geometry", {}) if isinstance(top, dict) else {}
        coords = geom.get("coordinates", [0.0, 0.0])
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            raise GeocodeNotFound(f"Invalid coordinates returned for '{query}'")

        return float(coords[1]), float(coords[0]), str(props.get("label") or query)

    def _resolve_input(self, point: Union[str, Dict[str, Any]]) -> List[float]:
        if isinstance(point, dict):
            lat = point.get("lat")
            if lat is None:
                lat = point.get("latitude")
            lon = point.get("lon")
            if lon is None:
                lon = point.get("longitude")

            if lat is not None and lon is not None:
                return [float(lon), float(lat)]

            query = point.get("label") or point.get("input")
            if query:
                lat_g, lon_g, _ = self.resolve_lat_lon(str(query))
                return [lon_g, lat_g]

        if isinstance(point, str):
            if "," in point:
                parts = point.split(",")
                if len(parts) >= 2:
                    try:
                        lat_f = float(parts[0].strip())
                        lon_f = float(parts[1].strip())
                        return [lon_f, lat_f]
                    except ValueError:
                        pass

            lat_g, lon_g, _ = self.resolve_lat_lon(point)
            return [lon_g, lat_g]

        raise ValueError(f"Could not resolve point input: {point}")
