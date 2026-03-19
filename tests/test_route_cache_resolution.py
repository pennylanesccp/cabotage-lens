import contextlib
import unittest
from unittest.mock import patch

from modules.infra.db.road_cache import find_place_point, list_origin_names
from modules.multimodal.builder import resolve_point_for_geometry


class _FakeCursor:
    def __init__(self, *, row=None, rows=None) -> None:
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, *, row=None, rows=None) -> None:
        self._row = row
        self._rows = rows or []
        self.last_sql = None
        self.last_params = None

    def execute(self, _sql, _params=None):
        self.last_sql = _sql
        self.last_params = _params
        return _FakeCursor(row=self._row, rows=self._rows)


class RouteCacheResolutionTests(unittest.TestCase):
    def test_list_origin_names_returns_distinct_sorted_origins_only(self) -> None:
        conn = _FakeConnection(rows=[("Aracaju, SE",), ("Manaus, AM",)])

        with patch("modules.infra.db.road_cache.ensure_main_table"):
            origins = list_origin_names(conn)

        self.assertEqual(origins, ["Aracaju, SE", "Manaus, AM"])
        self.assertIsNotNone(conn.last_sql)
        assert conn.last_sql is not None
        self.assertIn("FROM (", conn.last_sql)
        self.assertIn("AS origin_labels", conn.last_sql)
        self.assertEqual(conn.last_params, (10_000,))

    def test_find_place_point_uses_latest_cached_origin_or_destiny_coordinates(self) -> None:
        conn = _FakeConnection(
            row=(
                17,
                "avenida professor luciano gualberto, sao paulo",
                "Avenida Professor Luciano Gualberto, Sao Paulo",
                -23.5599,
                -46.7311,
                "SP",
                "ors",
                "route_cache",
                "2026-03-11 16:00:00",
                "2026-03-11 16:00:00",
            )
        )

        with patch("modules.infra.db.locations.ensure_aliases_table"):
            point = find_place_point(conn, place="Avenida Professor Luciano Gualberto, Sao Paulo")

        self.assertIsNotNone(point)
        assert point is not None
        self.assertEqual(point["role"], "alias")
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
