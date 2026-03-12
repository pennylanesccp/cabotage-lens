from __future__ import annotations

import logging
from typing import Any, Mapping

import streamlit as st

from modules.core.secrets import get_secret
from modules.infra.db.settings import load_database_settings
from modules.infra.log_manager import get_logger, init_logging

from app.main.utils.constants import DEFAULTS

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


def secret_value(key: str, default: Any = None) -> Any:
    value = get_secret(key, default)
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


def resolve_runtime_db_path() -> str:
    try:
        settings = load_database_settings()
        return settings.display_target
    except Exception as exc:
        _log.warning("Database target could not be resolved from Streamlit secrets: %s", exc)
        return str(DEFAULTS["db_path_str"])


def init_state(defaults: Mapping[str, Any] | None = None) -> None:
    runtime_defaults: dict[str, Any] = dict(defaults or DEFAULTS)
    runtime_defaults["db_path_str"] = str(resolve_runtime_db_path())
    runtime_defaults["log_level"] = validated_log_level(
        runtime_defaults.get("log_level", "INFO"),
        default=str(runtime_defaults.get("log_level", "INFO")),
    )
    runtime_defaults["write_log_file"] = bool_from_any(
        secret_value("CARBON_WRITE_LOG_FILE", runtime_defaults.get("write_log_file", False)),
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
