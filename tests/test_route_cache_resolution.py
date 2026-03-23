import contextlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from modules.infra.db.road_cache import (
    delete_key,
    find_place_point,
    get_run,
    list_origin_names,
    list_runs_by_label_keys,
)
from modules.multimodal.builder import resolve_point_for_geometry


class _FakeCursor:
    def __init__(self, *, row=None, rows=None, rowcount=None) -> None:
        self._row = row
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, *, row=None, rows=None, rowcount=None) -> None:
        self._row = row
        self._rows = rows or []
        self._rowcount = rowcount
        self.last_sql = None
        self.last_params = None

    def execute(self, _sql, _params=None):
        self.last_sql = _sql
        self.last_params = _params
        return _FakeCursor(row=self._row, rows=self._rows, rowcount=self._rowcount)


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

    def test_resolve_point_for_geometry_persists_provider_result_in_place_cache(self) -> None:
        fake_conn = SimpleNamespace(commit=unittest.mock.MagicMock())
        resolved = SimpleNamespace(label="Sao Paulo, SP", lat=-23.5505, lon=-46.6333, uf="SP")

        with patch(
            "modules.multimodal.builder.db_session",
            return_value=contextlib.nullcontext(fake_conn),
        ), patch(
            "modules.multimodal.builder.find_place_point",
            return_value=None,
        ), patch(
            "modules.multimodal.builder.resolve_point_null_safe",
            return_value=resolved,
        ), patch(
            "modules.multimodal.builder.upsert_place_point",
            return_value={
                "label": "Sao Paulo, SP",
                "lat": -23.5505,
                "lon": -46.6333,
                "uf": "SP",
                "location_id": 55,
            },
        ) as upsert_mock:
            point = resolve_point_for_geometry("Sao Paulo - SP", ors=object())

        self.assertEqual(
            point,
            {
                "label": "Sao Paulo, SP",
                "lat": -23.5505,
                "lon": -46.6333,
                "uf": "SP",
                "location_id": 55,
            },
        )
        upsert_mock.assert_called_once()
        self.assertEqual(upsert_mock.call_args.kwargs["place"], "Sao Paulo, SP")
        fake_conn.commit.assert_called_once_with()

    def test_get_run_ignores_requested_profile_and_uses_latest_route_for_pair(self) -> None:
        conn = _FakeConnection(
            row=(
                91,
                10,
                20,
                "Pelotas, RS",
                -31.7654,
                -52.3376,
                "Manaus, AM",
                -3.119,
                -60.0217,
                False,
                None,
                "ors",
                3921.4,
                198765.0,
                "2026-03-18 09:00:00",
                "2026-03-19 08:00:00",
            )
        )

        with patch(
            "modules.infra.db.road_cache.find_point",
            side_effect=[{"location_id": 10}, {"location_id": 20}],
        ), patch("modules.infra.db.road_cache.ensure_main_table"):
            row = get_run(
                conn,
                origin="Pelotas, RS",
                destiny="Manaus, AM",
                profile_requested="driving-hgv",
            )

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["id"], 91)
        self.assertEqual(row["profile_requested"], "driving-car")
        self.assertEqual(row["distance_km"], 3921.4)
        self.assertIsNotNone(conn.last_sql)
        assert conn.last_sql is not None
        self.assertNotIn("rc.is_hgv = ?", conn.last_sql)
        self.assertIn("ORDER BY rc.updated_timestamp DESC", conn.last_sql)
        self.assertEqual(conn.last_params, (10, 20))

    def test_list_runs_by_label_keys_maps_latest_pair_row_to_any_requested_profile(self) -> None:
        conn = _FakeConnection(
            rows=[
                (
                    44,
                    10,
                    20,
                    "Pelotas, RS",
                    -31.7654,
                    -52.3376,
                    "Manaus, AM",
                    -3.119,
                    -60.0217,
                    False,
                    "driving-car",
                    "ors",
                    3921.4,
                    198765.0,
                    "2026-03-18 09:00:00",
                    "2026-03-19 08:00:00",
                )
            ]
        )
        points = {
            "pelotas, rs": {"location_id": 10},
            "manaus, am": {"location_id": 20},
        }

        with patch(
            "modules.infra.db.road_cache.list_points",
            return_value=points,
        ), patch("modules.infra.db.road_cache.ensure_main_table"):
            rows = list_runs_by_label_keys(
                conn,
                keys=[
                    ("Pelotas, RS", "Manaus, AM", "driving-hgv"),
                    ("Pelotas, RS", "Manaus, AM", "driving-car"),
                ],
            )

        self.assertEqual(len(rows), 2)
        self.assertIn(("pelotas, rs", "manaus, am", "driving-hgv"), rows)
        self.assertIn(("pelotas, rs", "manaus, am", "driving-car"), rows)
        self.assertEqual(rows[("pelotas, rs", "manaus, am", "driving-hgv")]["id"], 44)
        self.assertEqual(rows[("pelotas, rs", "manaus, am", "driving-car")]["id"], 44)
        self.assertIsNotNone(conn.last_sql)
        assert conn.last_sql is not None
        self.assertIn("DISTINCT ON (rc.origin_location_id, rc.destiny_location_id)", conn.last_sql)
        self.assertNotIn("rc.is_hgv", conn.last_sql)
        self.assertEqual(conn.last_params, [10, 20, 10, 20])

    def test_delete_key_removes_all_cached_variants_for_pair(self) -> None:
        conn = _FakeConnection(rowcount=2)

        with patch(
            "modules.infra.db.road_cache.get_location_by_coords",
            side_effect=[{"location_id": 10}, {"location_id": 20}],
        ), patch("modules.infra.db.road_cache.ensure_main_table"):
            deleted = delete_key(
                conn,
                origin="Pelotas, RS",
                destiny="Manaus, AM",
                origin_lat=-31.7654,
                origin_lon=-52.3376,
                destiny_lat=-3.119,
                destiny_lon=-60.0217,
                profile_requested="driving-hgv",
            )

        self.assertEqual(deleted, 2)
        self.assertIsNotNone(conn.last_sql)
        assert conn.last_sql is not None
        self.assertIn("DELETE FROM route_cache_entries", conn.last_sql)
        self.assertNotIn("is_hgv", conn.last_sql)
        self.assertEqual(conn.last_params, (10, 20))


if __name__ == "__main__":
    unittest.main()
