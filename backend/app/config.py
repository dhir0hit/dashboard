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

    # Docker
    docker_socket: str = Field("/var/run/docker.sock")

    # Mode
    mock: bool = Field(False, alias="MOCK")

    # Persistence
    config_db: str = Field(
        "data/config.db",
        alias="CONFIG_DB",
    )

    # Server
    host: str = Field("127.0.0.1")
    port: int = 8000

    # --- Derived helpers ------------------------------------------------
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

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
