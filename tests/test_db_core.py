import unittest
from unittest.mock import MagicMock, patch

from modules.infra.db.core import DBConnection, connect, db_session
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
        conn = DBConnection(raw, target="postgresql://postgres:***@example.supabase.co:5432/postgres")

        cursor = conn.executemany(
            "UPDATE demo SET value = ? WHERE id = ?",
            [[1, "a"], [2, "b"]],
        )

        self.assertIs(cursor, raw.cursor_instance)
        self.assertEqual(cursor.statement, "UPDATE demo SET value = %s WHERE id = %s")
        self.assertEqual(cursor.rows, [(1, "a"), (2, "b")])
        self.assertEqual(cursor.rowcount, 2)
        self.assertFalse(cursor.closed)

    def test_ping_executes_simple_query(self) -> None:
        cursor = MagicMock()
        raw = MagicMock()
        raw.execute.return_value = cursor
        conn = DBConnection(raw, target="postgresql://postgres:***@example.supabase.co:5432/postgres")

        conn.ping()

        raw.execute.assert_called_once_with("SELECT 1")
        cursor.fetchone.assert_called_once_with()

    def test_reconnect_reopens_raw_connection(self) -> None:
        old_raw = MagicMock()
        new_raw = MagicMock()
        conn = DBConnection(
            old_raw,
            target="postgresql://postgres:***@example.supabase.co:5432/postgres",
            reconnect_dsn="postgresql://postgres:secret@example.com:6543/postgres?sslmode=require",
        )

        with patch("modules.infra.db.core._open_raw_connection", return_value=new_raw) as open_mock:
            conn.reconnect()

        old_raw.close.assert_called_once_with()
        open_mock.assert_called_once_with("postgresql://postgres:secret@example.com:6543/postgres?sslmode=require")
        self.assertIs(conn._raw, new_raw)

    def test_connect_uses_supabase_postgres_only(self) -> None:
        fake_raw = object()
        settings = DatabaseSettings(
            postgres_dsn="postgresql://postgres:secret@example.com:6543/postgres?sslmode=require",
            display_target="postgresql://postgres:***@example.com:6543/postgres?sslmode=require",
            host="example.com",
            port=6543,
            name="postgres",
            user="postgres",
        )

        with patch("modules.infra.db.core.load_database_settings", return_value=settings), patch(
            "modules.infra.db.core._open_raw_connection",
            return_value=fake_raw,
        ):
            conn = connect()

        self.assertIsInstance(conn, DBConnection)
        self.assertIs(conn._raw, fake_raw)
        self.assertEqual(conn._reconnect_dsn, settings.postgres_dsn)


class DBSessionTests(unittest.TestCase):
    def test_db_session_preserves_original_exception_when_rollback_fails(self) -> None:
        conn = MagicMock()
        conn.commit.side_effect = RuntimeError("commit failed")
        conn.rollback.side_effect = RuntimeError("rollback failed")

        with patch("modules.infra.db.core.connect", return_value=conn):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                with db_session():
                    pass

        conn.rollback.assert_called_once_with()
        conn.close.assert_called_once_with()

    def test_db_session_ignores_close_failure_after_successful_commit(self) -> None:
        conn = MagicMock()
        conn.close.side_effect = RuntimeError("close failed")

        with patch("modules.infra.db.core.connect", return_value=conn):
            with db_session():
                pass

        conn.commit.assert_called_once_with()
        conn.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
