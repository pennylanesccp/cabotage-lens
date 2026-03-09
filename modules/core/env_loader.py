# modules/core/env_loader.py
# -*- coding: utf-8 -*-

"""
Local runtime config loader.

Loads configuration from `.streamlit/secrets.toml` and `.env` without
requiring external services at import time.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


def _candidate_env_paths(explicit_path: Optional[Path] = None) -> Iterable[Path]:
    """Yield likely .env paths in priority order."""
    seen: set[Path] = set()

    def _push(p: Path) -> Iterable[Path]:
        rp = p.resolve()
        if rp in seen:
            return []
        seen.add(rp)
        return [rp]

    if explicit_path is not None:
        for item in _push(explicit_path):
            yield item

    cwd = Path.cwd().resolve()
    for item in _push(cwd / ".env"):
        yield item
    for parent in cwd.parents:
        for item in _push(parent / ".env"):
            yield item

    # Repository root inferred from this file location.
    repo_root = Path(__file__).resolve().parents[2]
    for item in _push(repo_root / ".env"):
        yield item


def _candidate_secrets_paths() -> Iterable[Path]:
    seen: set[Path] = set()

    def _push(p: Path) -> Iterable[Path]:
        rp = p.resolve()
        if rp in seen:
            return []
        seen.add(rp)
        return [rp]

    cwd = Path.cwd().resolve()
    for item in _push(cwd / ".streamlit" / "secrets.toml"):
        yield item
    for parent in cwd.parents:
        for item in _push(parent / ".streamlit" / "secrets.toml"):
            yield item

    repo_root = Path(__file__).resolve().parents[2]
    for item in _push(repo_root / ".streamlit" / "secrets.toml"):
        yield item


def _set_env_value(key: str, value: object, *, override: bool) -> None:
    if not key:
        return
    if not override and key in os.environ:
        return
    if isinstance(value, bool):
        os.environ[key] = "true" if value else "false"
        return
    if value is None:
        return
    os.environ[key] = str(value)


def _load_streamlit_secrets(path: Path, *, override: bool) -> Optional[Path]:
    if not path.exists() or not path.is_file():
        return None

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for key, value in data.items():
        if isinstance(value, dict):
            continue
        _set_env_value(str(key).strip(), value, override=override)
    return path


def _load_env_file(path: Path, *, override: bool) -> Optional[Path]:
    if not path.exists() or not path.is_file():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
            value = value[1:-1]

        _set_env_value(key, value, override=override)

    return path


def load_repo_env(explicit_path: Optional[Path] = None, *, override: bool = False) -> Optional[Path]:
    """
    Load runtime variables from local secrets files.

    Precedence:
      1. Existing process environment
      2. `.streamlit/secrets.toml`
      3. `.env`
    """
    first_loaded: Optional[Path] = None

    for candidate in _candidate_secrets_paths():
        loaded = _load_streamlit_secrets(candidate, override=override)
        if loaded is not None:
            first_loaded = first_loaded or loaded
            break

    for candidate in _candidate_env_paths(explicit_path):
        loaded = _load_env_file(candidate, override=override)
        if loaded is not None:
            first_loaded = first_loaded or loaded
            break

    return first_loaded
