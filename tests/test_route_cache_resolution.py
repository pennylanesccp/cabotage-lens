import contextlib
import unittest
from unittest.mock import patch

from modules.infra.db.core import db_session
from modules.infra.db.road_cache import find_place_point, list_origin_names, upsert_run
from modules.multimodal.builder import resolve_point_for_geometry


class RouteCacheResolutionTests(unittest.TestCase):
    def test_list_origin_names_returns_distinct_sorted_origins_only(self) -> None:
        with db_session(":memory:", backend="sqlite") as conn:
            upsert_run(
                conn,
                origin="Manaus, AM",
                destiny="Belem, PA",
                distance_km=10.0,
                profile_requested="driving-hgv",
            )
            upsert_run(
                conn,
                origin="Aracaju, SE",
                destiny="Manaus, AM",
                distance_km=20.0,
                profile_requested="driving-hgv",
            )
            upsert_run(
                conn,
                origin="Manaus, AM",
                destiny="Curitiba, PR",
                distance_km=30.0,
                profile_requested="driving-hgv",
            )

            origins = list_origin_names(conn)

        self.assertEqual(origins, ["Aracaju, SE", "Manaus, AM"])

    def test_find_place_point_uses_latest_cached_origin_or_destiny_coordinates(self) -> None:
        with db_session(":memory:", backend="sqlite") as conn:
            upsert_run(
                conn,
                origin="Avenida Professor Luciano Gualberto, Sao Paulo",
                origin_lat=-23.5588,
                origin_lon=-46.7303,
                destiny="Manaus, AM",
                destiny_lat=-3.1190,
                destiny_lon=-60.0217,
                distance_km=3900.0,
                profile_requested="driving-hgv",
            )
            upsert_run(
                conn,
                origin="Rio de Janeiro, RJ",
                origin_lat=-22.9068,
                origin_lon=-43.1729,
                destiny="Avenida Professor Luciano Gualberto, Sao Paulo",
                destiny_lat=-23.5599,
                destiny_lon=-46.7311,
                distance_km=430.0,
                profile_requested="driving-hgv",
            )
            conn.execute(
                """
                UPDATE routes
                   SET updated_timestamp = '2026-03-11 16:00:00'
                 WHERE destiny_name = ?
                """,
                ("Avenida Professor Luciano Gualberto, Sao Paulo",),
            )
            conn.execute(
                """
                UPDATE routes
                   SET updated_timestamp = '2026-03-11 15:00:00'
                 WHERE origin_name = ?
                """,
                ("Avenida Professor Luciano Gualberto, Sao Paulo",),
            )

            point = find_place_point(conn, place="Avenida Professor Luciano Gualberto, Sao Paulo")

        self.assertIsNotNone(point)
        assert point is not None
        self.assertEqual(point["role"], "destiny")
        self.assertAlmostEqual(float(point["lat"]), -23.5599)
        self.assertAlmostEqual(float(point["lon"]), -46.7311)

    def test_resolve_point_for_geometry_prefers_cached_routes_coordinates(self) -> None:
        cached_point = {
            "label": "Avenida Professor Luciano Gualberto, Sao Paulo",
            "lat": -23.558808,
            "lon": -46.730357,
            "role": "origin",
        }

        with patch(
            "modules.multimodal.builder.db_session",
            return_value=contextlib.nullcontext(object()),
        ), patch(
            "modules.multimodal.builder.find_place_point",
            return_value=cached_point,
        ), patch(
            "modules.multimodal.builder.resolve_point_null_safe",
        ) as resolve_mock:
            point = resolve_point_for_geometry(
                "Avenida Professor Luciano Gualberto, Sao Paulo",
                ors=object(),
                db_path=":memory:",
            )

        self.assertEqual(
            point,
            {
                "label": "Avenida Professor Luciano Gualberto, Sao Paulo",
                "lat": -23.558808,
                "lon": -46.730357,
                "uf": None,
            },
        )
        resolve_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
