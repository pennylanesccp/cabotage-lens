import unittest
from unittest.mock import patch

from modules.infra.db.settings import database_settings_from_dsn, load_database_settings


class DatabaseSettingsTests(unittest.TestCase):
    def test_load_database_settings_reads_supabase_db_url(self) -> None:
        with patch("modules.infra.db.settings.get_secret", side_effect=lambda key: {
            "SUPABASE_DB_URL": "postgresql://postgres:secret@example.supabase.co:5432/postgres?sslmode=require",
        }.get(key)):
            settings = load_database_settings()

        self.assertTrue(settings.is_postgres)
        self.assertEqual(settings.host, "example.supabase.co")
        self.assertEqual(settings.port, 5432)
        self.assertEqual(settings.name, "postgres")
        self.assertEqual(settings.user, "postgres")
        self.assertEqual(
            settings.display_target,
            "postgresql://postgres:***@example.supabase.co:5432/postgres?sslmode=require",
        )

    def test_database_settings_from_dsn_rejects_non_postgres_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a postgres connection string"):
            database_settings_from_dsn("mysql://user:secret@example.invalid:3306/carbon")

    def test_load_database_settings_requires_supabase_db_url(self) -> None:
        with patch("modules.infra.db.settings.get_secret", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "SUPABASE_DB_URL"):
                load_database_settings()


if __name__ == "__main__":
    unittest.main()
