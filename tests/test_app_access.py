import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.access import (
    AccessConfigurationError,
    AccessConfig,
    authenticate_attempt,
    load_access_config,
    logout,
)


class AppAccessTests(unittest.TestCase):
    def test_correct_password_authenticates(self) -> None:
        config = AccessConfig(password="shared-secret")

        authenticated = authenticate_attempt(config, password_input="shared-secret")

        self.assertTrue(authenticated)

    def test_wrong_password_does_not_authenticate(self) -> None:
        config = AccessConfig(password="shared-secret")

        authenticated = authenticate_attempt(config, password_input="wrong-secret")

        self.assertFalse(authenticated)

    def test_missing_app_password_is_handled_safely(self) -> None:
        with self.assertRaises(AccessConfigurationError):
            load_access_config(lambda _key: None)

    def test_logout_clears_session_auth_state(self) -> None:
        fake_streamlit = SimpleNamespace(
            session_state={
                "_app_access_authenticated": True,
                "_app_access_password": "shared-secret",
                "heatmap_dataset": {"rows": 3},
            },
            rerun=Mock(),
        )

        with patch("app.access.st", fake_streamlit):
            logout()

        self.assertEqual(fake_streamlit.session_state, {})
        fake_streamlit.rerun.assert_called_once_with()

    def test_captcha_disabled_mode_works_without_turnstile_keys(self) -> None:
        verifier = Mock(side_effect=AssertionError("captcha verifier should not be called"))
        config = AccessConfig(password="shared-secret")

        authenticated = authenticate_attempt(
            config,
            password_input="shared-secret",
            turnstile_verifier=verifier,
        )

        self.assertTrue(authenticated)
        verifier.assert_not_called()

    def test_load_access_config_accepts_password_only_mode(self) -> None:
        config = load_access_config(
            lambda key: {
                "APP_PASSWORD": "shared-secret",
            }.get(key)
        )

        self.assertEqual(config.password, "shared-secret")
        self.assertFalse(config.captcha_enabled)

    def test_partial_turnstile_configuration_is_rejected(self) -> None:
        with self.assertRaises(AccessConfigurationError):
            load_access_config(
                lambda key: {
                    "APP_PASSWORD": "shared-secret",
                    "TURNSTILE_SITE_KEY": "site-key-only",
                }.get(key)
            )


if __name__ == "__main__":
    unittest.main()
