"""Application configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings, overridable via env vars or a .env file."""

    model_config = SettingsConfigDict(
        env_prefix="SQLDLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://neondb_owner:npg_U5Onf0sLPegS@ep-rapid-salad-aq2s2gvs-pooler.c-8.us-east-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require"
    echo_sql: bool = False


settings = Settings()
