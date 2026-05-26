"""Application settings using pydantic-settings."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    quiz_data_dir: str = ""  # override via QUIZ_DATA_DIR env var

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # UI
    app_theme: Literal["light", "dark"] = "light"

    # Application metadata
    app_name: str = "Quiz Desktop App"
    app_version: str = "0.1.0"


# Module-level singleton – import and use `settings` directly
settings = AppSettings()
