# modules/core/env_loader.py
# -*- coding: utf-8 -*-

"""
Local .env loader.

Keeps runtime configuration simple for local development without requiring
external packages.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional


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


def load_repo_env(explicit_path: Optional[Path] = None, *, override: bool = False) -> Optional[Path]:
    """
    Load environment variables from the first .env file found.

    Format supported:
      - KEY=value
      - export KEY=value
      - Optional single/double quotes around value
    """
    env_path: Optional[Path] = None
    for candidate in _candidate_env_paths(explicit_path):
        if candidate.exists() and candidate.is_file():
            env_path = candidate
            break

    if env_path is None:
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
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

        if override or key not in os.environ:
            os.environ[key] = value

    return env_path
