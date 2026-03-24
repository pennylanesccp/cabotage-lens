from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from modules.core.secrets import get_secret

DEFAULT_BASE_URL = "https://us1.locationiq.com/v1"
SECRET_API_KEYS = "LOCATIONIQ_PATS"
SECRET_API_KEY = "LOCATIONIQ_PAT"


def _append_secret_values(target: list[str], raw: Any) -> None:
    if raw is None:
        return
    if isinstance(raw, (list, tuple)):
        for item in raw:
            _append_secret_values(target, item)
        return

    text = str(raw).strip()
    if not text:
        return

    for part in text.replace("\r", "\n").replace(";", ",").replace("\n", ",").split(","):
        value = part.strip()
        if value and value not in target:
            target.append(value)


def get_configured_locationiq_api_keys(
    *,
    explicit_api_key: Optional[str] = None,
    path: Path | None = None,
    include_runtime: bool = True,
) -> list[str]:
    keys: list[str] = []
    _append_secret_values(keys, explicit_api_key)

    configured_list = get_secret(
        SECRET_API_KEYS,
        None,
        path=path,
        include_runtime=include_runtime,
    )
    list_keys: list[str] = []
    _append_secret_values(list_keys, configured_list)
    if list_keys:
        for key in list_keys:
            if key not in keys:
                keys.append(key)
        return keys

    _append_secret_values(
        keys,
        get_secret(
            SECRET_API_KEY,
            None,
            path=path,
            include_runtime=include_runtime,
        ),
    )
    return keys


@dataclass
class LocationIQConfig:
    """Configuration for the optional LocationIQ fallback provider."""

    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    cache_enabled: bool = True
    cache_ttl_s: int = 2_592_000
    timeout: tuple[float, float] = (5.0, 5.0)
    retry_limit: int = 0
    default_country: str = "BR"
    default_profile: str = "driving-car"

    def __post_init__(self) -> None:
        if not self.api_key:
            keys = get_configured_locationiq_api_keys()
            self.api_key = keys[0] if keys else None
