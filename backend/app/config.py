"""Configuration via env vars / .env file (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Mode
    mock: bool = Field(False, alias="MOCK")

    # Docker socket (mounted into the backend container)
    docker_sock: str = Field("/var/run/docker.sock", alias="DOCKER_SOCK")

    # Persistence
    config_db: str = Field(
        "data/config.db",
        alias="CONFIG_DB",
    )

    # Server
    host: str = Field("127.0.0.1")
    port: int = 8000

    @field_validator("config_db")
    @classmethod
    def _abs(cls, v: str) -> str:
        return str(Path(v).expanduser().resolve())


@lru_cache
def get_settings() -> "Settings":
    return Settings()


def reload_settings() -> "Settings":
    get_settings.cache_clear()
    return get_settings()
