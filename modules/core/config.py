# modules/core/config.py
# -*- coding: utf-8 -*-

"""
Core Configuration.
===================

Centralizes project-wide settings, constants, and default paths.
Acts as the single source of truth for "static" configuration (as opposed to
dynamic runtime variables).

Exports:
    - Config: Main configuration object (use this for new code).
    - ProjectConfig, RoutingDefaults: Legacy compatibility wrappers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from modules.core.secrets import get_secret

# ────────────────────────────────────────────────────────────────────────────────
# Main Configuration Class
# ────────────────────────────────────────────────────────────────────────────────

def _first_configured_ors_key() -> Optional[str]:
    configured = get_secret("ORS_API_KEYS", [])
    if isinstance(configured, (list, tuple)):
        for value in configured:
            text = str(value).strip()
            if text:
                return text
    elif isinstance(configured, str):
        text = configured.strip()
        if text:
            return text.split(",", 1)[0].strip()
    return get_secret("ORS_API_KEY")


@dataclass
class Config:
    """
    Global application configuration.
    
    Aggregates defaults for:
    - Infrastructure (Paths to DB, JSONs)
    - Routing behavior (Profiles)
    - Context (Country, Language)
    """

    # --- Infrastructure Paths ---
    # These defaults assume the code runs from the repository root.
    # The main runtime persists through Supabase Postgres rather than a local DB path.
    db_target: str = "postgres"
    ports_path: Path = field(
        default_factory=lambda: Path("data/processed/cabotage_data/ports_br.json")
    )
    sea_matrix_path: Path = field(
        default_factory=lambda: Path("data/sea_matrix.json")
    )
    hotel_prices_path: Path = field(
        default_factory=lambda: Path("data/processed/cabotage_data/hotel.json")
    )

    # --- Routing Defaults ---
    ors_profile: str = "driving-car"
    ors_fallback_profile: str = "driving-car"
    
    # --- Project Context ---
    default_country: str = "BR"
    default_locale: str = "pt-BR"

    # --- Streamlit secrets ---
    # Auto-loads API key from Streamlit secrets if available
    ors_api_key: Optional[str] = field(
        default_factory=_first_configured_ors_key
    )

    def __post_init__(self) -> None:
        """Ensure paths are proper Path objects if strings were passed."""
        if isinstance(self.ports_path, str):
            self.ports_path = Path(self.ports_path)
        if isinstance(self.sea_matrix_path, str):
            self.sea_matrix_path = Path(self.sea_matrix_path)
        if isinstance(self.hotel_prices_path, str):
            self.hotel_prices_path = Path(self.hotel_prices_path)


# ────────────────────────────────────────────────────────────────────────────────
# Legacy Wrappers (Backward Compatibility)
# ────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProjectConfig:
    """Legacy: Global project configuration."""
    default_country: str = "BR"
    default_language: str = "pt-BR"

@dataclass(frozen=True)
class RoutingDefaults:
    """Legacy: Generic routing-related defaults."""
    primary_profile: str = "driving-car"
    fallback_profile: str = "driving-car"
    enable_fallback: bool = False

# Global instances for modules that haven't migrated to 'Config' yet
PROJECT_CONFIG = ProjectConfig()
ROUTING_DEFAULTS = RoutingDefaults()


def get_project_config() -> ProjectConfig:
    return PROJECT_CONFIG

def get_routing_defaults() -> RoutingDefaults:
    return ROUTING_DEFAULTS


# ────────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("--- Config Module Smoke Test ---")
    
    # 1. Test Main Config
    cfg = Config()
    print(f"Defaults loaded:")
    print(f"  - DB Target: {cfg.db_target}")
    print(f"  - ORS Profile: {cfg.ors_profile}")
    print(f"  - API Key Present: {bool(cfg.ors_api_key)}")

    # 2. Test Legacy
    print(f"Legacy Defaults: {get_routing_defaults().primary_profile}")
    
    print("--- Done ---")
