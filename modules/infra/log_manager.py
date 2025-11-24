# modules/infra/log_manager.py
# -*- coding: utf-8 -*-

"""
Central Log Manager.
====================

This module acts as the single source of truth for application observability.
It wraps the standard library `logging` module to provide:
    1. Consistent formatting (Time | Level | Logger | Message).
    2. Automatic file rotation and directory management.
    3. Environment variable overrides (CARBON_LOG_LEVEL).
    4. Utilities for visual separation in logs (banners).

Usage
-----
    from modules.infra.log_manager import init_logging, get_logger

    # In your main entry point:
    init_logging(level="DEBUG", write_to_file=True)

    # In any other module:
    _log = get_logger(__name__)
    _log.info("Calculation started.")

Environment Variables
---------------------
    CARBON_LOG_LEVEL : str
        Overrides the default logging level (e.g., set to "DEBUG" in CI/CD).
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ────────────────────────────────────────────────────────────────────────────────
# Constants & State
# ────────────────────────────────────────────────────────────────────────────────

# Default directory for log persistence
_DEFAULT_LOG_DIR = Path("logs")

# Track state for CLI reporting
_current_log_file: Optional[Path] = None


# ────────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────────

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Acquire a logger instance.

    This is a thin wrapper around `logging.getLogger`. Using this ensures
    that if we switch logging backends (e.g., to `loguru` or `structlog`)
    in the future, the change is isolated to this module.

    Parameters
    ----------
    name : str, optional
        The name of the logger, typically `__name__`.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """
    return logging.getLogger(name if name else "root")


def get_current_log_path() -> Optional[Path]:
    """
    Retrieve the filesystem path of the active log file.

    Returns
    -------
    Path or None
        The absolute path to the log file if file logging is enabled,
        otherwise None.
    """
    return _current_log_file


def init_logging(
      level: str = "INFO"
    , *
    , write_to_file: bool = False
    , log_file_path: Optional[Path] = None
    , silence_libs: Optional[List[str]] = None
    , force_clean: bool = True
) -> None:
    """
    Initialize the root logger with standard formatting and handlers.

    Parameters
    ----------
    level : str
        The desired logging verbosity ("DEBUG", "INFO", "WARNING", "ERROR").
        Can be overridden by the `CARBON_LOG_LEVEL` env var.
    write_to_file : bool
        If True, logs are also written to a timestamped file in `logs/`.
    log_file_path : Path, optional
        Specific path to write logs to. Overrides auto-generated names.
    silence_libs : List[str], optional
        List of library names (e.g., ["urllib3", "requests"]) to set to
        WARNING level, reducing noise when debugging your own code.
    force_clean : bool
        If True, removes all existing handlers from the root logger.
        Crucial for preventing duplicate logs during tests or re-runs.
    """
    global _current_log_file

    # 1. Environment Override
    #    Allows changing verbosity without changing code (great for Docker/CI).
    env_level = os.getenv("CARBON_LOG_LEVEL")
    if env_level:
        level = env_level.upper()

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 2. Clean Slate
    #    Remove pre-existing handlers to ensure our config is authoritative.
    if force_clean and root_logger.hasHandlers():
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

    # 3. Formatter Definition
    #    Format: [YYYY-MM-DD HH:MM:SS][LEVEL][LoggerName] Message
    log_fmt = logging.Formatter(
          fmt="[{asctime}][{levelname}][{name}] {message}"
        , datefmt="%Y-%m-%d %H:%M:%S"
        , style="{"
    )

    # 4. Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_fmt)
    root_logger.addHandler(console_handler)

    # 5. File Handler (Optional)
    if write_to_file or log_file_path:
        if log_file_path:
            target_path = Path(log_file_path)
        else:
            # Generate specific filename: app_YYYYMMDD-HHMMSS.log
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            script_name = Path(sys.argv[0]).stem if sys.argv[0] else "app"
            target_path = _DEFAULT_LOG_DIR / f"{script_name}__{timestamp}.log"

        # Ensure directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(target_path, encoding="utf-8")
        file_handler.setFormatter(log_fmt)
        root_logger.addHandler(file_handler)

        _current_log_file = target_path.resolve()

    # 6. Silence Noisy Libraries
    #    Sets chatty third-party libs to WARNING so they don't drown out app logs.
    default_silence = ["urllib3", "requests", "matplotlib", "geopy"]
    libs_to_silence = (silence_libs or []) + default_silence
    for lib_name in libs_to_silence:
        logging.getLogger(lib_name).setLevel(logging.WARNING)

    # 7. Self-Identification
    #    Log that we are ready.
    get_logger(__name__).debug(
        f"LogManager initialized. Level={level}, File={_current_log_file}"
    )


def log_banner(msg: str, level: str = "INFO", char: str = "═") -> None:
    """
    Log a visual separator to distinguish processing steps.

    Example
    -------
    ╔══════════════════════╗
    ║   Processing Route   ║
    ╚══════════════════════╝
    """
    logger = get_logger(__name__)
    log_method = getattr(logger, level.lower(), logger.info)

    width = 60
    # Center the message
    padded_msg = f" {msg} "
    fill_len = max(0, width - len(padded_msg) - 2)
    left_pad = fill_len // 2
    right_pad = fill_len - left_pad

    # Build box
    top = f"╔{char * (width - 2)}╗"
    middle = f"║{' ' * left_pad}{padded_msg}{' ' * right_pad}║"
    bottom = f"╚{char * (width - 2)}╝"

    log_method(top)
    log_method(middle)
    log_method(bottom)


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Init Logging (force DEBUG to see everything)
    print("--- Starting Log Manager Smoke Test ---")
    init_logging(level="DEBUG", write_to_file=True)

    # 2. Get a logger
    log = get_logger("smoke_test")

    # 3. Test Levels
    log.debug("This is a debug message (should appear).")
    log.info("This is an info message.")
    log.warning("This is a warning.")
    log.error("This is an error.")

    # 4. Test Banner
    log_banner("SECTION START")

    # 5. Verify File Creation
    log_path = get_current_log_path()
    if log_path and log_path.exists():
        log.info(f"SUCCESS: Log file confirmed at {log_path}")
    else:
        log.error("FAILURE: Log file was not created.")

    print("--- Smoke Test Complete ---")