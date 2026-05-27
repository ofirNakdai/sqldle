"""Application configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, overridable via env vars or a .env file."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file="app/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    pg_connection_string: str 
    echo_sql: bool



    


settings = Settings()
