from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

import streamlit as st

from modules.infra.db.settings import load_database_settings
from modules.infra.log_manager import get_logger, init_logging

from app.main.utils.constants import DEFAULTS, ROOT

_log = get_logger("streamlit_app")


class StreamlitLogHandler(logging.Handler):
    """Push log lines into Streamlit session state."""

    def __init__(self, key: str = "ui_logs", max_lines: int = 1000) -> None:
        super().__init__()
        self.key = key
        self.max_lines = max_lines

    def emit(self, record: logging.LogRecord) -> None:
        try:
            logs = st.session_state.setdefault(self.key, [])
            logs.append(self.format(record))
            if len(logs) > self.max_lines:
                del logs[:-self.max_lines]
        except Exception:
            pass


def secret_or_env(key: str, default: Any = None) -> Any:
    value = st.secrets.get(key, os.getenv(key))
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
    return value


def bool_from_any(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def validated_log_level(value: Any, default: str = "INFO") -> str:
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    candidate = str(value or default).strip().upper()
    return candidate if candidate in allowed else default


def resolve_runtime_db_path(configured_path: Any = None) -> str:
    settings = load_database_settings()
    if settings.is_postgres:
        return settings.display_target

    configured = configured_path if configured_path is not None else secret_or_env("CARBON_DB_PATH", DEFAULTS["db_path_str"])
    candidate = Path(str(configured)).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate

    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        with candidate.open("a", encoding="utf-8"):
            pass
        return str(candidate.resolve())
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "carbon-footprint" / "carbon_footprint.sqlite"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return str(fallback.resolve())


def bootstrap_runtime_env() -> None:
    for key in (
        "ORS_API_KEY",
        "CARBON_LOG_LEVEL",
        "CARBON_DB_BACKEND",
        "CARBON_DB_PATH",
        "DATABASE_URL",
        "SUPABASE_DB_URL",
        "SUPABASE_DB_HOST",
        "SUPABASE_DB_PORT",
        "SUPABASE_DB_NAME",
        "SUPABASE_DB_USER",
        "SUPABASE_DB_PASSWORD",
        "SUPABASE_DB_SSLMODE",
    ):
        value = secret_or_env(key)
        if value is not None:
            normalized = str(value).strip()
            if normalized:
                os.environ[key] = normalized


def init_state(defaults: Mapping[str, Any] | None = None) -> None:
    bootstrap_runtime_env()

    runtime_defaults: dict[str, Any] = dict(defaults or DEFAULTS)
    runtime_defaults["db_path_str"] = str(resolve_runtime_db_path())
    runtime_defaults["log_level"] = validated_log_level(
        secret_or_env("CARBON_LOG_LEVEL", runtime_defaults.get("log_level", "INFO")),
        default=str(runtime_defaults.get("log_level", "INFO")),
    )
    runtime_defaults["write_log_file"] = bool_from_any(
        secret_or_env("CARBON_WRITE_LOG_FILE", runtime_defaults.get("write_log_file", False)),
        default=bool(runtime_defaults.get("write_log_file", False)),
    )

    for key, value in runtime_defaults.items():
        st.session_state.setdefault(key, value)

    st.session_state.setdefault("ui_logs", [])
    st.session_state.setdefault("last_geo", None)
    st.session_state.setdefault("last_results", None)


def attach_streamlit_logging(level: str, write_to_file: bool) -> None:
    safe_level = validated_log_level(level, default=str(DEFAULTS["log_level"]))
    try:
        init_logging(level=safe_level, write_to_file=write_to_file, force_clean=True)
    except Exception as exc:
        init_logging(level=safe_level, write_to_file=False, force_clean=True)
        st.session_state.write_log_file = False
        _log.warning("File logging disabled due to runtime filesystem limits: %s", exc)

    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, StreamlitLogHandler):
            root.removeHandler(handler)

    ui_handler = StreamlitLogHandler()
    ui_handler.setLevel(logging.DEBUG)
    ui_handler.setFormatter(
        logging.Formatter(
            fmt="[{asctime}][{levelname}][{name}] {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )
    )
    root.addHandler(ui_handler)
