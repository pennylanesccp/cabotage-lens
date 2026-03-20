import tempfile
import unittest
from pathlib import Path

from modules.road.locationiq.api import LocationIQClient
from modules.road.locationiq.structures import LocationIQConfig
from modules.road.ors.api import ORSClient
from modules.road.ors.structures import (
    GeocodeNotFound,
    NoRoute,
    ORSError,
    RateLimited,
    get_configured_ors_api_keys,
)


class _FakeProvider:
    def __init__(
        self,
        name: str,
        *,
        enabled: bool = True,
        geocode_result=None,
        geocode_exc: Exception | None = None,
        route_result=None,
        route_exc: Exception | None = None,
    ) -> None:
        self.name = name
        self._enabled = enabled
        self._geocode_result = geocode_result
        self._geocode_exc = geocode_exc
        self._route_result = route_result
        self._route_exc = route_exc
        self.geocode_calls = 0
        self.route_calls = 0

    def is_enabled(self) -> bool:
        return self._enabled

    def geocode_text(self, text: str, size: int = 1, country: str | None = None):
        self.geocode_calls += 1
        if self._geocode_exc is not None:
            raise self._geocode_exc
        return list(self._geocode_result or [])

    def geocode_structured(self, **_kwargs):
        return self.geocode_text("<structured>")

    def resolve_lat_lon(self, query: str):
        features = self.geocode_text(query, size=1)
        top = features[0]
        coords = top["geometry"]["coordinates"]
        return float(coords[1]), float(coords[0]), str(top["properties"]["label"])

    def route_road(self, origin, destiny, profile: str | None = None):
        self.route_calls += 1
        if self._route_exc is not None:
            raise self._route_exc
        return dict(self._route_result or {})


class ORSClientFallbackTests(unittest.TestCase):
    def test_loads_ors_key_list_from_array_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            secrets_path = Path(tmp_dir) / "secrets.toml"
            secrets_path.write_text(
                'ORS_API_KEYS = ["key-1", " key-2 ", "key-1"]\n',
                encoding="utf-8",
            )

            keys = get_configured_ors_api_keys(path=secrets_path, include_runtime=False)

        self.assertEqual(keys, ["key-1", "key-2"])

    def test_falls_back_to_legacy_ors_keys_when_list_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            secrets_path = Path(tmp_dir) / "secrets.toml"
            secrets_path.write_text(
                'ORS_API_KEY = "key-1"\nORS_API_KEY_2 = "key-2"\n',
                encoding="utf-8",
            )

            keys = get_configured_ors_api_keys(path=secrets_path, include_runtime=False)

        self.assertEqual(keys, ["key-1", "key-2"])

    def test_prefers_ors_when_primary_succeeds(self) -> None:
        primary = _FakeProvider(
            "ors",
            geocode_result=[
                {
                    "geometry": {"coordinates": [-46.6333, -23.5505]},
                    "properties": {"label": "Sao Paulo, SP", "provider": "ors"},
                    "provider": "ors",
                }
            ],
        )
        fallback = _FakeProvider("locationiq", geocode_result=[])
        client = ORSClient(primary_provider=primary, fallback_provider=fallback)

        features = client.geocode_text("Sao Paulo")

        self.assertEqual(features[0]["properties"]["label"], "Sao Paulo, SP")
        self.assertEqual(primary.geocode_calls, 1)
        self.assertEqual(fallback.geocode_calls, 0)

    def test_falls_back_to_locationiq_for_geocode(self) -> None:
        primary = _FakeProvider("ors", geocode_exc=GeocodeNotFound("ORS empty"))
        fallback = _FakeProvider(
            "locationiq",
            geocode_result=[
                {
                    "geometry": {"coordinates": [-46.730357, -23.558808]},
                    "properties": {
                        "label": "Avenida Professor Luciano Gualberto, Sao Paulo",
                        "provider": "locationiq",
                    },
                    "provider": "locationiq",
                }
            ],
        )
        client = ORSClient(primary_provider=primary, fallback_provider=fallback)

        features = client.geocode_text("Avenida Professor Luciano Gualberto, Sao Paulo")

        self.assertEqual(features[0]["provider"], "locationiq")
        self.assertEqual(primary.geocode_calls, 1)
        self.assertEqual(fallback.geocode_calls, 1)

    def test_falls_back_to_secondary_ors_before_locationiq(self) -> None:
        primary = _FakeProvider("ors", geocode_exc=RateLimited("ORS quota"))
        secondary = _FakeProvider(
            "ors_2",
            geocode_result=[
                {
                    "geometry": {"coordinates": [-46.730357, -23.558808]},
                    "properties": {
                        "label": "Avenida Professor Luciano Gualberto, Sao Paulo",
                        "provider": "ors_2",
                    },
                    "provider": "ors_2",
                }
            ],
        )
        fallback = _FakeProvider("locationiq", geocode_result=[])
        client = ORSClient(
            primary_provider=primary,
            secondary_provider=secondary,
            fallback_provider=fallback,
        )

        features = client.geocode_text("Avenida Professor Luciano Gualberto, Sao Paulo")

        self.assertEqual(features[0]["provider"], "ors_2")
        self.assertEqual(primary.geocode_calls, 1)
        self.assertEqual(secondary.geocode_calls, 1)
        self.assertEqual(fallback.geocode_calls, 0)

    def test_falls_back_to_locationiq_for_routing(self) -> None:
        primary = _FakeProvider("ors", route_exc=ORSError("timeout"))
        fallback = _FakeProvider(
            "locationiq",
            route_result={
                "distance_m": 1200.0,
                "duration_s": 180.0,
                "profile_used": "driving-car",
                "source": "locationiq",
                "provider": "locationiq",
            },
        )
        client = ORSClient(primary_provider=primary, fallback_provider=fallback)

        route = client.route_road({"lat": -23.5, "lon": -46.6}, {"lat": -23.9, "lon": -46.3})

        self.assertEqual(route["source"], "locationiq")
        self.assertEqual(route["profile_used"], "driving-car")
        self.assertEqual(primary.route_calls, 1)
        self.assertEqual(fallback.route_calls, 1)

    def test_raises_clean_error_when_both_providers_fail(self) -> None:
        primary = _FakeProvider("ors", route_exc=NoRoute("ORS no route"))
        fallback = _FakeProvider("locationiq", route_exc=ORSError("LocationIQ unavailable"))
        client = ORSClient(primary_provider=primary, fallback_provider=fallback)

        with self.assertRaises(ORSError) as ctx:
            client.route_road({"lat": -23.5, "lon": -46.6}, {"lat": -23.9, "lon": -46.3})

        self.assertIn("ORS no route", str(ctx.exception))
        self.assertIn("LocationIQ unavailable", str(ctx.exception))

    def test_missing_locationiq_pat_keeps_primary_error(self) -> None:
        primary = _FakeProvider("ors", route_exc=ORSError("ORS timeout"))
        fallback = _FakeProvider("locationiq", enabled=False)
        client = ORSClient(primary_provider=primary, fallback_provider=fallback)

        with self.assertRaises(ORSError) as ctx:
            client.route_road({"lat": -23.5, "lon": -46.6}, {"lat": -23.9, "lon": -46.3})

        self.assertIn("ORS timeout", str(ctx.exception))
        self.assertEqual(fallback.route_calls, 0)


class LocationIQNormalizationTests(unittest.TestCase):
    def test_locationiq_geocode_normalizes_response_shape(self) -> None:
        client = LocationIQClient(LocationIQConfig(api_key="test-key", cache_enabled=False))
        client._http.request = lambda *_args, **_kwargs: [  # type: ignore[method-assign]
            {
                "lat": "-23.558808",
                "lon": "-46.730357",
                "display_name": "Avenida Professor Luciano Gualberto, Sao Paulo, Sao Paulo, Brasil",
                "type": "house",
                "address": {
                    "state": "Sao Paulo",
                    "country": "Brasil",
                    "country_code": "br",
                },
            }
        ]

        features = client.geocode_text("Avenida Professor Luciano Gualberto, Sao Paulo", size=1)
        feature = features[0]

        self.assertEqual(feature["geometry"]["coordinates"], [-46.730357, -23.558808])
        self.assertEqual(feature["properties"]["layer"], "address")
        self.assertEqual(feature["properties"]["region"], "Sao Paulo")
        self.assertEqual(feature["properties"]["provider"], "locationiq")

    def test_locationiq_route_normalizes_response_shape(self) -> None:
        client = LocationIQClient(LocationIQConfig(api_key="test-key", cache_enabled=False))
        client._http.request = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
            "routes": [
                {
                    "summary": {
                        "distance": 43210.0,
                        "duration": 3600.0,
                    }
                }
            ]
        }

        route = client.route_road(
            {"lat": -23.558808, "lon": -46.730357},
            {"lat": -23.9608, "lon": -46.3336},
            profile="driving-hgv",
        )

        self.assertEqual(route["distance_m"], 43210.0)
        self.assertEqual(route["duration_s"], 3600.0)
        self.assertEqual(route["profile_used"], "driving-car")
        self.assertEqual(route["source"], "locationiq")


if __name__ == "__main__":
    unittest.main()
