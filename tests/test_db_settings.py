import unittest
from unittest.mock import patch

from modules.infra.db.settings import load_database_settings


class DatabaseSettingsTests(unittest.TestCase):
    def test_project_ref_builds_encoded_postgres_dsn(self) -> None:
        secrets = {
            "SUPABASE_PROJECT_REF": "fgspotqnwmvstzctuxzn",
            "SUPABASE_DB_PASSWORD": "s*B20230422Stt3f4ny",
            "SUPABASE_DB_PORT": "5432",
        }

        with patch("modules.infra.db.settings.get_secret", side_effect=lambda key: secrets.get(key)):
            settings = load_database_settings()

        self.assertTrue(settings.is_postgres)
        self.assertEqual(settings.host, "db.fgspotqnwmvstzctuxzn.supabase.co")
        self.assertEqual(settings.user, "postgres")
        self.assertEqual(settings.port, 5432)
        self.assertEqual(
            settings.postgres_dsn,
            "postgresql://postgres:s%2AB20230422Stt3f4ny@db.fgspotqnwmvstzctuxzn.supabase.co:5432/postgres?sslmode=require",
        )

    def test_pooler_port_requires_explicit_host_when_only_project_ref_is_set(self) -> None:
        secrets = {
            "SUPABASE_PROJECT_REF": "fgspotqnwmvstzctuxzn",
            "SUPABASE_DB_PASSWORD": "secret",
            "SUPABASE_DB_PORT": "6543",
        }

        with patch("modules.infra.db.settings.get_secret", side_effect=lambda key: secrets.get(key)):
            with self.assertRaisesRegex(RuntimeError, "SUPABASE_DB_PORT=6543"):
                load_database_settings()


if __name__ == "__main__":
    unittest.main()
