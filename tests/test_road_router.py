import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.infra.db.core import db_session
from modules.infra.db.road_cache import get_run
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
    def test_get_or_create_leg_persists_provider_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "routes.sqlite"

            with patch(
                "modules.road.router.db_session",
                side_effect=lambda *_args, **_kwargs: db_session(db_path, backend="sqlite"),
            ):
                result = get_or_create_leg(
                    _StaticRouteClient(),
                    origin={"label": "Origin A", "lat": -23.55, "lon": -46.63},
                    destiny={"label": "Destiny B", "lat": -23.96, "lon": -46.33},
                    db_path=db_path,
                    overwrite=True,
                )

            with db_session(db_path, backend="sqlite") as conn:
                row = get_run(
                    conn,
                    origin="Origin A",
                    destiny="Destiny B",
                    profile_requested="driving-hgv",
                )

        self.assertEqual(result["source"], "locationiq")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["source"], "locationiq")
        self.assertEqual(row["profile_used"], "driving-car")


if __name__ == "__main__":
    unittest.main()
