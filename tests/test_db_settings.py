import unittest
from unittest.mock import patch

from modules.infra.db.settings import build_postgres_dsn_from_parts, database_settings_from_dsn, load_database_settings


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

    def test_load_database_settings_builds_dsn_from_split_secrets(self) -> None:
        with patch("modules.infra.db.settings.get_secret", side_effect=lambda key: {
            "SUPABASE_DB_HOST": "aws-0-us-west-2.pooler.supabase.com",
            "SUPABASE_DB_PORT": 6543,
            "SUPABASE_DB_NAME": "postgres",
            "SUPABASE_DB_USER": "postgres.projectref",
            "SUPABASE_DB_PASSWORD": "secret-password",
            "SUPABASE_DB_SSLMODE": "require",
        }.get(key)):
            settings = load_database_settings()

        self.assertEqual(settings.host, "aws-0-us-west-2.pooler.supabase.com")
        self.assertEqual(settings.port, 6543)
        self.assertEqual(settings.name, "postgres")
        self.assertEqual(settings.user, "postgres.projectref")
        self.assertEqual(
            settings.display_target,
            "postgresql://postgres.projectref:***@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require",
        )

    def test_load_database_settings_derives_user_from_project_ref(self) -> None:
        with patch("modules.infra.db.settings.get_secret", side_effect=lambda key: {
            "SUPABASE_PROJECT_REF": "fgspotqnwmvstzctuxzn",
            "SUPABASE_DB_HOST": "aws-0-us-west-2.pooler.supabase.com",
            "SUPABASE_DB_PASSWORD": "secret-password",
        }.get(key)):
            settings = load_database_settings()

        self.assertEqual(settings.user, "postgres.fgspotqnwmvstzctuxzn")
        self.assertEqual(settings.port, 6543)
        self.assertEqual(settings.name, "postgres")

    def test_build_postgres_dsn_from_parts_url_encodes_credentials(self) -> None:
        dsn = build_postgres_dsn_from_parts(
            host="aws-0-us-west-2.pooler.supabase.com",
            port=6543,
            name="postgres",
            user="postgres.projectref",
            password="s*B 2023",
            sslmode="require",
        )
        self.assertEqual(
            dsn,
            "postgresql://postgres.projectref:s%2AB%202023@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require",
        )

    def test_load_database_settings_requires_url_or_split_secrets(self) -> None:
        with patch("modules.infra.db.settings.get_secret", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "SUPABASE_DB_URL or split secrets"):
                load_database_settings()


if __name__ == "__main__":
    unittest.main()
