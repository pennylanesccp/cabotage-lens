from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

_MISSING = object()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SECRETS_PATH = _REPO_ROOT / ".streamlit" / "secrets.toml"


def default_secrets_path() -> Path:
    """Return the repository-local Streamlit secrets file path."""
    return _DEFAULT_SECRETS_PATH


def load_local_secrets(path: Path | None = None) -> dict[str, Any]:
    """Load repo secrets from `.streamlit/secrets.toml` when present."""
    target = Path(path) if path is not None else default_secrets_path()
    if not target.exists():
        return {}

    # Accept UTF-8 BOM files because Windows editors commonly save TOML this way.
    text = target.read_text(encoding="utf-8-sig")
    data = tomllib.loads(text)

    if not isinstance(data, dict):
        return {}
    return data


def _runtime_secret_value(key: str) -> Any:
    try:
        import streamlit as st
    except Exception:
        return _MISSING

    try:
        secrets = st.secrets
    except Exception:
        return _MISSING

    try:
        if key in secrets:
            return secrets[key]
    except Exception:
        return _MISSING

    return _MISSING


def _normalize_secret_value(value: Any) -> Any:
    if value is _MISSING or value is None:
        return _MISSING
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return _MISSING
    return value


def _environment_secret_value(key: str) -> Any:
    return os.environ.get(str(key).strip(), _MISSING)


def get_secret(
    key: str,
    default: Any = None,
    *,
    path: Path | None = None,
    include_runtime: bool = True,
) -> Any:
    """Return a secret from local secrets.toml, Streamlit runtime, or the environment."""
    local_value = _normalize_secret_value(load_local_secrets(path).get(key, _MISSING))
    if local_value is not _MISSING:
        return local_value

    if include_runtime:
        runtime_value = _normalize_secret_value(_runtime_secret_value(key))
        if runtime_value is not _MISSING:
            return runtime_value

    env_value = _normalize_secret_value(_environment_secret_value(key))
    if env_value is not _MISSING:
        return env_value

    return default
