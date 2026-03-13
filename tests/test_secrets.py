import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.core.secrets import get_secret, load_local_secrets


class StreamlitSecretsTests(unittest.TestCase):
    def test_load_local_secrets_reads_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            secrets_path = Path(tmp_dir) / "secrets.toml"
            secrets_path.write_text('ORS_API_KEY = "abc123"\nLOG_ARCHIVE_ENABLED = false\n', encoding="utf-8")

            loaded = load_local_secrets(secrets_path)

        self.assertEqual(loaded["ORS_API_KEY"], "abc123")
        self.assertFalse(loaded["LOG_ARCHIVE_ENABLED"])

    def test_load_local_secrets_reads_utf8_bom_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            secrets_path = Path(tmp_dir) / "secrets.toml"
            secrets_path.write_text('ORS_API_KEY = "abc123"\n', encoding="utf-8-sig")

            loaded = load_local_secrets(secrets_path)

        self.assertEqual(loaded["ORS_API_KEY"], "abc123")

    def test_get_secret_returns_default_for_blank_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            secrets_path = Path(tmp_dir) / "secrets.toml"
            secrets_path.write_text('ORS_API_KEY = "  "\n', encoding="utf-8")

            value = get_secret("ORS_API_KEY", "fallback", path=secrets_path, include_runtime=False)

        self.assertEqual(value, "fallback")

    def test_get_secret_preserves_boolean_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            secrets_path = Path(tmp_dir) / "secrets.toml"
            secrets_path.write_text("LOG_ARCHIVE_ENABLED = false\n", encoding="utf-8")

            value = get_secret("LOG_ARCHIVE_ENABLED", True, path=secrets_path, include_runtime=False)

        self.assertFalse(value)

    def test_get_secret_falls_back_to_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, patch.dict("os.environ", {"LOCATIONIQ_PAT": "env-token"}, clear=False):
            secrets_path = Path(tmp_dir) / "secrets.toml"

            value = get_secret("LOCATIONIQ_PAT", "fallback", path=secrets_path, include_runtime=False)

        self.assertEqual(value, "env-token")


if __name__ == "__main__":
    unittest.main()
