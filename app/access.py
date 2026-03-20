from __future__ import annotations

import hmac
from dataclasses import dataclass
from html import escape
from typing import Any, Callable

import requests
import streamlit as st

from app.components.turnstile import render_turnstile_widget
from app.main.utils.constants import APP_NAME
from modules.core.secrets import get_secret

_AUTHENTICATED_KEY = "_app_access_authenticated"
_ERROR_KEY = "_app_access_error"
_PASSWORD_INPUT_KEY = "_app_access_password"
_CLEAR_SENSITIVE_NEXT_RUN_KEY = "_app_access_clear_sensitive_next_run"
_TURNSTILE_RESET_KEY = "_app_access_turnstile_reset"
_TURNSTILE_WIDGET_PREFIX = "_app_access_turnstile_"
_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

_ACCESS_CSS = """
<style>
    .access-shell {
        max-width: 28rem;
        margin: 8vh auto 0 auto;
        padding: 1.5rem;
        border-radius: 24px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(9, 14, 26, 0.92)),
            #0f172a;
        box-shadow: 0 18px 42px rgba(2, 6, 23, 0.26);
    }
    .access-shell__eyebrow {
        margin: 0 0 0.3rem 0;
        color: #38bdf8;
        font-size: 0.76rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }
    .access-shell h1 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.7rem;
        line-height: 1.2;
    }
    .access-shell p {
        margin: 0.7rem 0 0 0;
        color: #cbd5e1;
        line-height: 1.5;
        font-size: 0.95rem;
    }
</style>
"""


class AccessConfigurationError(RuntimeError):
    """Raised when the app access gate secrets are not configured safely."""


@dataclass(frozen=True)
class AccessConfig:
    password: str
    turnstile_site_key: str | None = None
    turnstile_secret_key: str | None = None

    @property
    def captcha_enabled(self) -> bool:
        return bool(self.turnstile_site_key and self.turnstile_secret_key)


def _normalized_secret(secret_reader: Callable[[str], Any], key: str) -> str | None:
    value = secret_reader(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_access_config(secret_reader: Callable[[str], Any] = get_secret) -> AccessConfig:
    password = _normalized_secret(secret_reader, "APP_PASSWORD")
    if password is None:
        raise AccessConfigurationError(
            "Missing required Streamlit secret 'APP_PASSWORD'. Add it to .streamlit/secrets.toml for local runs or to the deployed app secrets."
        )

    turnstile_site_key = _normalized_secret(secret_reader, "TURNSTILE_SITE_KEY")
    turnstile_secret_key = _normalized_secret(secret_reader, "TURNSTILE_SECRET_KEY")
    if bool(turnstile_site_key) != bool(turnstile_secret_key):
        raise AccessConfigurationError(
            "Incomplete Turnstile configuration. Set both TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY, or leave both unset."
        )

    return AccessConfig(
        password=password,
        turnstile_site_key=turnstile_site_key,
        turnstile_secret_key=turnstile_secret_key,
    )


def _password_bytes(value: str) -> bytes:
    return str(value or "").encode("utf-8")


def password_matches(password_input: str, expected_password: str) -> bool:
    return hmac.compare_digest(_password_bytes(password_input), _password_bytes(expected_password))


def verify_turnstile_token(
    *,
    token: str,
    secret_key: str,
    remote_ip: str | None = None,
    request_post: Callable[..., Any] = requests.post,
) -> bool:
    token_text = str(token or "").strip()
    secret_text = str(secret_key or "").strip()
    if not token_text or not secret_text:
        return False

    payload = {
        "secret": secret_text,
        "response": token_text,
    }
    if remote_ip:
        payload["remoteip"] = str(remote_ip).strip()

    try:
        response = request_post(_TURNSTILE_VERIFY_URL, data=payload, timeout=10)
        response.raise_for_status()
        body = response.json()
    except Exception:
        return False

    return bool(isinstance(body, dict) and body.get("success") is True)


def authenticate_attempt(
    config: AccessConfig,
    *,
    password_input: str,
    turnstile_token: str | None = None,
    turnstile_verifier: Callable[..., bool] = verify_turnstile_token,
) -> bool:
    if not password_matches(password_input, config.password):
        return False
    if not config.captcha_enabled:
        return True
    return bool(
        turnstile_verifier(
            token=str(turnstile_token or ""),
            secret_key=str(config.turnstile_secret_key or ""),
        )
    )


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def require_app_access() -> None:
    _ensure_access_state()
    _apply_pending_sensitive_input_clear()
    st.markdown(_ACCESS_CSS, unsafe_allow_html=True)

    try:
        config = load_access_config()
    except AccessConfigurationError as exc:
        _render_access_shell()
        st.error(str(exc))
        st.stop()

    if bool(st.session_state.get(_AUTHENTICATED_KEY, False)):
        return

    _render_login_screen(config)
    st.stop()


def _ensure_access_state() -> None:
    st.session_state.setdefault(_AUTHENTICATED_KEY, False)
    st.session_state.setdefault(_ERROR_KEY, None)
    st.session_state.setdefault(_PASSWORD_INPUT_KEY, "")
    st.session_state.setdefault(_CLEAR_SENSITIVE_NEXT_RUN_KEY, False)
    st.session_state.setdefault(_TURNSTILE_RESET_KEY, 0)


def _render_access_shell() -> None:
    st.markdown(
        f"""
        <section class="access-shell">
            <p class="access-shell__eyebrow">{escape(APP_NAME)}</p>
            <h1>Restricted access</h1>
            <p>Enter the password to continue.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_login_screen(config: AccessConfig) -> None:
    _render_access_shell()

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        turnstile_token = ""
        with st.form("app_access_login", border=False, enter_to_submit=False):
            st.text_input(
                "Password",
                type="password",
                key=_PASSWORD_INPUT_KEY,
                placeholder="Password",
                help="Restricted access. Enter the shared password to continue.",
            )

            if config.captcha_enabled:
                turnstile_token = str(
                    render_turnstile_widget(
                        site_key=str(config.turnstile_site_key or ""),
                        reset_nonce=int(st.session_state.get(_TURNSTILE_RESET_KEY, 0)),
                        key=f"{_TURNSTILE_WIDGET_PREFIX}{int(st.session_state.get(_TURNSTILE_RESET_KEY, 0))}",
                    )
                    or ""
                ).strip()

            submitted = st.form_submit_button(
                "Continue",
                type="primary",
                width="stretch",
                key="_app_access_submit",
            )

        if submitted:
            authenticated = authenticate_attempt(
                config,
                password_input=str(st.session_state.get(_PASSWORD_INPUT_KEY, "")),
                turnstile_token=turnstile_token,
            )
            _schedule_sensitive_input_clear()
            if authenticated:
                st.session_state[_AUTHENTICATED_KEY] = True
                st.session_state[_ERROR_KEY] = None
                st.rerun()

            st.session_state[_ERROR_KEY] = "Access denied. Retry to continue."
            st.session_state[_TURNSTILE_RESET_KEY] = int(st.session_state.get(_TURNSTILE_RESET_KEY, 0)) + 1
            st.rerun()

        error_message = st.session_state.get(_ERROR_KEY)
        if error_message:
            st.error(str(error_message))


def _clear_sensitive_inputs() -> None:
    st.session_state.pop(_PASSWORD_INPUT_KEY, None)
    for key in [name for name in st.session_state.keys() if str(name).startswith(_TURNSTILE_WIDGET_PREFIX)]:
        del st.session_state[key]


def _schedule_sensitive_input_clear() -> None:
    st.session_state[_CLEAR_SENSITIVE_NEXT_RUN_KEY] = True


def _apply_pending_sensitive_input_clear() -> None:
    if not bool(st.session_state.get(_CLEAR_SENSITIVE_NEXT_RUN_KEY, False)):
        return
    _clear_sensitive_inputs()
    st.session_state[_CLEAR_SENSITIVE_NEXT_RUN_KEY] = False


def render_logout_control() -> None:
    with st.sidebar:
        st.divider()
        st.caption("Restricted session")
        if st.button("Logout", width="stretch", key="_app_access_logout"):
            logout()
