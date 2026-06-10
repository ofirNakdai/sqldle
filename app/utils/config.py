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

    # --- AI challenge generation (optional) ---------------------------------
    # Uses the OpenAI Python SDK, which also targets Azure OpenAI / Foundry and
    # any OpenAI-compatible endpoint. Leave the key empty to disable the
    # `POST /api/challenges/generate` endpoint.
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"



    


settings = Settings()
