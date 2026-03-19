from __future__ import annotations

import gzip
import json
import logging
import os
import sys
import tempfile
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from modules.core.secrets import get_secret
from modules.infra.supabase_storage import (
    SupabaseStorageClient,
    build_log_archive_object_path,
)

_LOG_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})
_CONTEXT_FIELDS = ("run_id", "request_id", "correlation_id", "scenario_key")
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LOCAL_LOGS_DIR = _REPO_ROOT / "logs"
_current_archive_object_path: Optional[str] = None
_current_local_log_path: Optional[str] = None


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name if name else "root")


def get_current_archive_object_path() -> Optional[str]:
    return _current_archive_object_path


def get_current_local_log_path() -> Optional[str]:
    return _current_local_log_path


def _normalize_context(values: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        text = str(value).strip() if isinstance(value, str) else value
        if text in ("", None):
            continue
        normalized[str(key)] = text
    return normalized


def get_log_context() -> dict[str, Any]:
    return dict(_LOG_CONTEXT.get({}))


def set_log_context(**values: Any) -> dict[str, Any]:
    updated = {**get_log_context(), **_normalize_context(values)}
    _LOG_CONTEXT.set(updated)
    return updated


def clear_log_context(*keys: str) -> None:
    if not keys:
        _LOG_CONTEXT.set({})
        return
    updated = get_log_context()
    for key in keys:
        updated.pop(str(key), None)
    _LOG_CONTEXT.set(updated)


@contextmanager
def bind_log_context(**values: Any):
    token = _LOG_CONTEXT.set({**get_log_context(), **_normalize_context(values)})
    try:
        yield
    finally:
        _LOG_CONTEXT.reset(token)


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _configure_stdout_encoding() -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass


def _boolish(value: Any, default: bool = False) -> bool:
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


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = get_log_context()
        for key in _CONTEXT_FIELDS:
            if getattr(record, key, None) in (None, "") and context.get(key) not in (None, ""):
                setattr(record, key, context[key])
        return True


class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = int(max_level)

    def filter(self, record: logging.LogRecord) -> bool:
        return int(record.levelno) <= self._max_level


class _ContextConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        parts: list[str] = []
        for key in _CONTEXT_FIELDS:
            value = getattr(record, key, None)
            if value not in (None, ""):
                parts.append(f"{key}={value}")
        return f"{base} {' '.join(parts)}" if parts else base


class _SupabaseArchiveHandler(logging.Handler):
    def __init__(self, *, client: SupabaseStorageClient, object_path: str) -> None:
        super().__init__()
        self._client = client
        self._object_path = object_path
        self._spool = tempfile.SpooledTemporaryFile(max_size=1_048_576, mode="w+b")
        self._gzip = gzip.GzipFile(fileobj=self._spool, mode="wb")
        self._entry_count = 0
        self._closed = False
        self._exception_formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload: dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
                "run_id": getattr(record, "run_id", None),
                "request_id": getattr(record, "request_id", None),
                "correlation_id": getattr(record, "correlation_id", None),
                "scenario_key": getattr(record, "scenario_key", None),
            }
            if record.exc_info:
                payload["exception"] = self._exception_formatter.formatException(record.exc_info)
            line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
            self._gzip.write(line.encode("utf-8"))
            self._entry_count += 1
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        if self._closed:
            return
        try:
            self._gzip.flush()
            self._spool.flush()
        except Exception:
            pass

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.flush()
            self._gzip.close()
            if self._entry_count > 0:
                self._spool.seek(0)
                self._client.upload_bytes(
                    object_path=self._object_path,
                    payload=self._spool.read(),
                    content_type="application/gzip",
                    upsert=True,
                )
        except Exception as exc:
            try:
                sys.stderr.write(
                    f"[logging][warning] failed to archive logs to Supabase Storage ({self._object_path}): {exc}\n"
                )
            except Exception:
                pass
        finally:
            self._spool.close()
            self._closed = True
            super().close()


def _close_root_handlers(root_logger: logging.Logger) -> None:
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.flush()
        except Exception:
            pass
        try:
            handler.close()
        except Exception:
            pass


def _safe_log_file_stem(value: Optional[str]) -> str:
    text = str(value or "").strip()
    if not text:
        return "streamlit"
    normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in text)
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "streamlit"


def _resolve_local_log_path(
    *,
    local_logs_dir: Optional[Path | str] = None,
    archive_run_id: Optional[str] = None,
) -> Path:
    target_dir = Path(local_logs_dir) if local_logs_dir is not None else _DEFAULT_LOCAL_LOGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    existing = _current_local_log_path
    if existing:
        existing_path = Path(existing)
        if existing_path.parent == target_dir:
            return existing_path

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = _safe_log_file_stem(archive_run_id)
    return target_dir / f"{stem}__{timestamp}.log"


def init_logging(
    level: str = "INFO",
    *,
    archive_to_storage: Optional[bool] = None,
    archive_to_local_file: Optional[bool] = None,
    archive_run_id: Optional[str] = None,
    environment: Optional[str] = None,
    local_logs_dir: Optional[Path | str] = None,
    silence_libs: Optional[list[str]] = None,
    force_clean: bool = True,
) -> None:
    global _current_archive_object_path, _current_local_log_path

    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    if force_clean:
        _close_root_handlers(root_logger)

    _configure_stdout_encoding()
    _current_archive_object_path = None

    formatter = _ContextConsoleFormatter(
        fmt="[{asctime}][{levelname}][{name}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )
    context_filter = _ContextFilter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(_MaxLevelFilter(logging.WARNING))
    stdout_handler.addFilter(context_filter)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.addFilter(context_filter)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    if archive_to_storage is None:
        archive_to_storage = _boolish(get_secret("LOG_ARCHIVE_ENABLED"), default=False)
    if archive_to_local_file is None:
        archive_to_local_file = False
    if not archive_to_local_file:
        _current_local_log_path = None

    if archive_to_local_file:
        try:
            local_log_path = _resolve_local_log_path(
                local_logs_dir=local_logs_dir,
                archive_run_id=archive_run_id,
            )
            file_handler = logging.FileHandler(local_log_path, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.addFilter(context_filter)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            _current_local_log_path = str(local_log_path)
        except Exception as exc:
            _current_local_log_path = None
            root_logger.warning("Local file logging disabled: %s", exc)

    if archive_to_storage:
        archive_environment = (
            str(environment or os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "local").strip().lower()
            or "local"
        )
        archive_id = (
            str(archive_run_id).strip()
            if archive_run_id not in (None, "")
            else str(get_log_context().get("run_id") or uuid.uuid4().hex)
        )
        try:
            archive_client = SupabaseStorageClient()
            object_path = build_log_archive_object_path(
                environment=archive_environment,
                run_id=archive_id,
            )
            archive_handler = _SupabaseArchiveHandler(
                client=archive_client,
                object_path=object_path,
            )
            archive_handler.setLevel(logging.DEBUG)
            archive_handler.addFilter(context_filter)
            root_logger.addHandler(archive_handler)
            _current_archive_object_path = object_path
        except Exception as exc:
            root_logger.warning("Supabase log archival disabled: %s", exc)

    libs = _dedupe_keep_order((silence_libs or []) + ["urllib3", "requests", "matplotlib", "geopy"])
    for lib_name in libs:
        logging.getLogger(lib_name).setLevel(logging.WARNING)

    get_logger(__name__).debug(
        "LogManager initialized. level=%s archive=%s object=%s local=%s",
        level,
        bool(archive_to_storage),
        _current_archive_object_path,
        _current_local_log_path,
    )


def log_banner(msg: str, level: str = "INFO", char: str = "=") -> None:
    logger = get_logger(__name__)
    log_method = getattr(logger, str(level).lower(), logger.info)

    width = 60
    inner = f" {msg.strip()} "
    top_bottom = char * width
    middle = inner.center(width)

    log_method(top_bottom)
    log_method(middle)
    log_method(top_bottom)
