import contextlib
import unittest
from unittest.mock import patch

from modules.road.router import get_or_create_leg


class _StaticRouteClient:
    def route_road(self, origin, destiny, profile: str | None = None):
        return {
            "distance_m": 12345.0,
            "duration_s": 900.0,
            "profile_used": "driving-car",
            "source": "locationiq",
            "provider": "locationiq",
        }


class RoadRouterTests(unittest.TestCase):
    def test_get_or_create_leg_prefers_coordinate_cache_lookup_when_coords_are_available(self) -> None:
        fake_conn = object()
        cached_row = {
            "origin": "Origin A",
            "destiny": "Destiny B",
            "distance_km": 123.45,
            "is_hgv": True,
            "profile_requested": "driving-hgv",
            "profile_used": "driving-hgv",
            "source": "ors",
        }

        with patch(
            "modules.road.router.db_session",
            return_value=contextlib.nullcontext(fake_conn),
        ), patch(
            "modules.road.router.ensure_main_table",
        ), patch(
            "modules.road.router.get_run_by_coords",
            return_value=cached_row,
        ) as get_run_by_coords_mock, patch(
            "modules.road.router.get_run",
        ) as get_run_mock:
            result = get_or_create_leg(
                _StaticRouteClient(),
                origin={"label": "Origin A", "lat": -23.5505204, "lon": -46.6333089},
                destiny={"label": "Destiny B", "lat": -23.9608313, "lon": -46.3336192},
                overwrite=False,
            )

        self.assertTrue(result["cached"])
        self.assertEqual(result["distance_km"], 123.45)
        get_run_by_coords_mock.assert_called_once()
        get_run_mock.assert_not_called()

    def test_get_or_create_leg_persists_provider_source(self) -> None:
        fake_conn = object()

        with patch(
            "modules.road.router.db_session",
            return_value=contextlib.nullcontext(fake_conn),
        ), patch(
            "modules.road.router.ensure_main_table",
        ), patch(
            "modules.road.router.get_run",
            return_value=None,
        ), patch(
            "modules.road.router.get_run_by_coords",
            return_value=None,
        ), patch(
            "modules.road.router.upsert_run",
        ) as upsert_run_mock:
            result = get_or_create_leg(
                _StaticRouteClient(),
                origin={"label": "Origin A", "lat": -23.55, "lon": -46.63},
                destiny={"label": "Destiny B", "lat": -23.96, "lon": -46.33},
                overwrite=True,
            )

        self.assertEqual(result["source"], "locationiq")
        upsert_run_mock.assert_called_once()
        self.assertEqual(upsert_run_mock.call_args.kwargs["source"], "locationiq")
        self.assertEqual(upsert_run_mock.call_args.kwargs["profile_used"], "driving-car")


if __name__ == "__main__":
    unittest.main()
