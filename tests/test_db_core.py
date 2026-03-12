import unittest
from unittest.mock import MagicMock, patch

from modules.infra.db.core import DBConnection, connect
from modules.infra.db.settings import DatabaseSettings


class _FakeCursor:
    def __init__(self) -> None:
        self.statement = None
        self.rows = None
        self.rowcount = 0
        self.closed = False

    def executemany(self, statement, rows) -> None:
        self.statement = statement
        self.rows = rows
        self.rowcount = len(rows)

    def close(self) -> None:
        self.closed = True


class _FakeRawConnection:
    def __init__(self) -> None:
        self.cursor_instance = _FakeCursor()

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance


class DBConnectionTests(unittest.TestCase):
    def test_executemany_uses_cursor_fallback_for_postgres_connections(self) -> None:
        raw = _FakeRawConnection()
        conn = DBConnection(raw, backend="postgres", target="postgres://test")

        cursor = conn.executemany(
            "UPDATE demo SET value = ? WHERE id = ?",
            [[1, "a"], [2, "b"]],
        )

        self.assertIs(cursor, raw.cursor_instance)
        self.assertEqual(cursor.statement, "UPDATE demo SET value = %s WHERE id = %s")
        self.assertEqual(cursor.rows, [(1, "a"), (2, "b")])
        self.assertEqual(cursor.rowcount, 2)
        self.assertFalse(cursor.closed)

    def test_connect_disables_prepared_statements_for_postgres(self) -> None:
        fake_raw = object()
        fake_psycopg = MagicMock()
        fake_psycopg.connect.return_value = fake_raw
        settings = DatabaseSettings(
            backend="postgres",
            sqlite_path=None,
            postgres_dsn="postgresql://postgres:secret@example.com:6543/postgres?sslmode=require",
            host="aws-0-sa-east-1.pooler.supabase.com",
            port=6543,
            name="postgres",
            user="postgres.projectref",
            password="secret",
            sslmode="require",
        )

        with patch("modules.infra.db.core.load_database_settings", return_value=settings), patch(
            "modules.infra.db.core.psycopg",
            fake_psycopg,
        ):
            conn = connect(backend="postgres")

        self.assertIsInstance(conn, DBConnection)
        self.assertIs(conn._raw, fake_raw)
        fake_psycopg.connect.assert_called_once_with(
            settings.postgres_dsn,
            connect_timeout=10,
            prepare_threshold=None,
        )


if __name__ == "__main__":
    unittest.main()
