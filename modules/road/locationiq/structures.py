from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from modules.core.secrets import get_secret

DEFAULT_BASE_URL = "https://us1.locationiq.com/v1"
SECRET_API_KEY = "LOCATIONIQ_PAT"


@dataclass
class LocationIQConfig:
    """Configuration for the optional LocationIQ fallback provider."""

    api_key: Optional[str] = None
    base_url: str = DEFAULT_BASE_URL
    cache_enabled: bool = True
    cache_ttl_s: int = 2_592_000
    timeout: tuple[float, float] = (10.0, 5.0)
    retry_limit: int = 1
    default_country: str = "BR"
    default_profile: str = "driving"

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = get_secret(SECRET_API_KEY)
