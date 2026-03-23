from __future__ import annotations

import logging
from typing import Any, Mapping

import streamlit as st
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:  # pragma: no cover - Streamlit internals may move between releases
    get_script_run_ctx = None

from modules.core.secrets import get_secret
from modules.infra.db.settings import load_database_settings
from modules.infra.log_manager import (
    detect_runtime_environment,
    get_current_archive_object_path,
    get_current_local_log_path,
    get_logger,
    init_logging,
    local_file_logging_enabled_by_default,
    storage_archival_enabled_by_default,
)

from app.main.utils.constants import DEFAULTS, ROOT

_log = get_logger("streamlit_app")


class StreamlitLogHandler(logging.Handler):
    """Push log lines into Streamlit session state."""

    def __init__(self, key: str = "ui_logs", max_lines: int = 1000) -> None:
        super().__init__()
        self.key = key
        self.max_lines = max_lines

    def emit(self, record: logging.LogRecord) -> None:
        if not self._has_script_context():
            return
        try:
            logs = st.session_state.setdefault(self.key, [])
            logs.append(self.format(record))
            if len(logs) > self.max_lines:
                del logs[:-self.max_lines]
        except Exception:
            pass

    @staticmethod
    def _has_script_context() -> bool:
        if get_script_run_ctx is None:
            return True
        try:
            return get_script_run_ctx() is not None
        except Exception:
            return False


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


def resolve_runtime_db_target() -> str:
    try:
        settings = load_database_settings()
        return settings.display_target
    except Exception as exc:
        _log.warning("Database target could not be resolved from Streamlit secrets: %s", exc)
        return str(DEFAULTS["db_target_str"])


def init_state(defaults: Mapping[str, Any] | None = None) -> None:
    runtime_defaults: dict[str, Any] = dict(defaults or DEFAULTS)
    runtime_environment = detect_runtime_environment(secret_value("APP_ENV", None))
    archive_default = (
        storage_archival_enabled_by_default(runtime_environment)
        if defaults is None
        else bool_from_any(runtime_defaults.get("archive_logs"), default=False)
    )
    local_logs_default = (
        local_file_logging_enabled_by_default(runtime_environment)
        if defaults is None
        else bool_from_any(
            runtime_defaults.get("write_local_logs"),
            default=local_file_logging_enabled_by_default(runtime_environment),
        )
    )
    runtime_defaults["db_target_str"] = str(resolve_runtime_db_target())
    runtime_defaults["runtime_environment"] = runtime_environment
    runtime_defaults["log_level"] = validated_log_level(
        runtime_defaults.get("log_level", "INFO"),
        default=str(runtime_defaults.get("log_level", "INFO")),
    )
    runtime_defaults["archive_logs"] = bool_from_any(
        secret_value("LOG_ARCHIVE_ENABLED", None),
        default=archive_default,
    )
    runtime_defaults["write_local_logs"] = bool_from_any(
        secret_value("LOG_LOCAL_ENABLED", None),
        default=local_logs_default,
    )

    for key, value in runtime_defaults.items():
        st.session_state.setdefault(key, value)

    st.session_state.setdefault("ui_logs", [])
    st.session_state.setdefault("last_geo", None)
    st.session_state.setdefault("last_results", None)
    st.session_state.setdefault("local_log_path", None)
    st.session_state.setdefault("archive_log_path", None)
    st.session_state.setdefault("effective_archive_logs", bool(st.session_state.get("archive_logs", False)))
    st.session_state.setdefault("logging_policy_message", None)


def attach_streamlit_logging(level: str, archive_to_storage: bool) -> None:
    safe_level = validated_log_level(level, default=str(DEFAULTS["log_level"]))
    runtime_environment = detect_runtime_environment(st.session_state.get("runtime_environment"))
    requested_archive_to_storage = bool_from_any(
        archive_to_storage,
        default=storage_archival_enabled_by_default(runtime_environment),
    )
    effective_archive_to_storage = bool(requested_archive_to_storage)
    effective_write_local_logs = local_file_logging_enabled_by_default(runtime_environment)
    policy_message: str | None = None
    try:
        init_logging(
            level=safe_level,
            archive_to_storage=effective_archive_to_storage,
            archive_to_local_file=effective_write_local_logs,
            environment=runtime_environment,
            local_logs_dir=ROOT / "logs",
            force_clean=True,
        )
    except Exception as exc:
        try:
            init_logging(
                level=safe_level,
                archive_to_storage=False,
                archive_to_local_file=effective_write_local_logs,
                environment=runtime_environment,
                local_logs_dir=ROOT / "logs",
                force_clean=True,
            )
            effective_archive_to_storage = False
            policy_message = f"Supabase log archival disabled for this session: {exc}"
            _log.warning(policy_message)
        except Exception as fallback_exc:
            init_logging(
                level=safe_level,
                archive_to_storage=False,
                archive_to_local_file=False,
                environment=runtime_environment,
                local_logs_dir=ROOT / "logs",
                force_clean=True,
            )
            effective_archive_to_storage = False
            effective_write_local_logs = False
            policy_message = (
                "File and Storage logging disabled for this session: "
                f"{exc} / {fallback_exc}"
            )
            _log.warning(
                policy_message,
            )

    st.session_state.runtime_environment = runtime_environment
    st.session_state.write_local_logs = effective_write_local_logs
    st.session_state.effective_archive_logs = effective_archive_to_storage
    st.session_state.local_log_path = get_current_local_log_path()
    st.session_state.archive_log_path = get_current_archive_object_path()
    st.session_state.logging_policy_message = policy_message

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
