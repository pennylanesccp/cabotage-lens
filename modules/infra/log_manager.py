# modules/infra/log_manager.py
# -*- coding: utf-8 -*-

"""
Centralized logging utilities for the project.

This module provides a single logging initialization path with a stable API,
including backward-compatible keyword aliases used by older modules.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from modules.core.secrets import get_secret

_DEFAULT_LOG_DIR = Path("logs")
_current_log_file: Optional[Path] = None


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger by name (or root logger when name is missing)."""
    return logging.getLogger(name if name else "root")


def get_current_log_path() -> Optional[Path]:
    """Return the active log file path when file logging is enabled."""
    return _current_log_file


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
    """
    Prevent UnicodeEncodeError on terminals with legacy encodings.

    We keep this best-effort and silent because stdout can be replaced by tools
    that do not implement `reconfigure`.
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass


def init_logging(
    level: str = "INFO",
    *,
    write_to_file: bool = False,
    log_file_path: Optional[Path] = None,
    silence_libs: Optional[List[str]] = None,
    force_clean: bool = True,
    # Backward-compatible aliases used by older call sites:
    force: Optional[bool] = None,
    write_output: Optional[bool] = None,
) -> None:
    """
    Initialize root logging handlers and format.

    Backward compatibility:
    - `force` is treated as alias for `force_clean`.
    - `write_output` is treated as alias for `write_to_file`.
    """
    global _current_log_file

    if force is not None:
        force_clean = bool(force)
    if write_output is not None:
        write_to_file = bool(write_output)

    secret_level = get_secret("CARBON_LOG_LEVEL")
    if secret_level:
        level = str(secret_level).upper()

    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    if force_clean and root_logger.hasHandlers():
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

    _configure_stdout_encoding()

    formatter = logging.Formatter(
        fmt="[{asctime}][{levelname}][{name}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    _current_log_file = None
    if write_to_file or log_file_path:
        target_path = Path(log_file_path) if log_file_path else (
            _DEFAULT_LOG_DIR
            / f"{Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else 'app'}__{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(target_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        _current_log_file = target_path.resolve()

    libs = _dedupe_keep_order((silence_libs or []) + ["urllib3", "requests", "matplotlib", "geopy"])
    for lib_name in libs:
        logging.getLogger(lib_name).setLevel(logging.WARNING)

    get_logger(__name__).debug(
        "LogManager initialized. Level=%s, File=%s",
        level,
        _current_log_file,
    )


def log_banner(msg: str, level: str = "INFO", char: str = "=") -> None:
    """Log a simple ASCII banner for visual separation in logs."""
    logger = get_logger(__name__)
    log_method = getattr(logger, str(level).lower(), logger.info)

    width = 60
    inner = f" {msg.strip()} "
    top_bottom = char * width
    middle = inner.center(width)

    log_method(top_bottom)
    log_method(middle)
    log_method(top_bottom)


if __name__ == "__main__":
    print("--- Starting Log Manager Smoke Test ---")
    init_logging(level="DEBUG", write_to_file=True)

    log = get_logger("smoke_test")
    log.debug("This is a debug message (should appear).")
    log.info("This is an info message.")
    log.warning("This is a warning.")
    log.error("This is an error.")

    log_banner("SECTION START")

    log_path = get_current_log_path()
    if log_path and log_path.exists():
        log.info("SUCCESS: Log file confirmed at %s", log_path)
    else:
        log.error("FAILURE: Log file was not created.")

    print("--- Smoke Test Complete ---")
