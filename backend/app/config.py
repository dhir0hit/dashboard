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

    # Proxmox
    proxmox_api_url: str = Field("https://proxmox.local:8006/")
    proxmox_api_token: str = Field("")  # user!tokenid=secret
    proxmox_verify_tls: bool = Field(False)
    proxmox_node: str = Field("")

    # SSH for in-guest docker discovery
    ssh_host: str = Field("")
    ssh_port: int = Field(22)
    ssh_user: str = Field("root")
    ssh_key_file: str = Field("")
    ssh_password: str = Field("")

    # Mode
    mock: bool = Field(False, alias="MOCK")

    # Persistence
    config_db: str = Field(
        "data/config.db",
        alias="CONFIG_DB",
    )

    # Server
    host: str = Field("127.0.0.1")
    port: int = Field(8000)

    # --- Derived helpers ------------------------------------------------
    @property
    def auth_header(self) -> dict[str, str]:
        if not self.proxmox_api_token:
            return {}
        return {"Authorization": f"PVEAPIToken={self.proxmox_api_token}"}

    @property
    def token_user(self) -> str:
        return self.proxmox_api_token.split("!", 1)[0] if "!" in self.proxmox_api_token else ""

    @property
    def base_url(self) -> str:
        u = self.proxmox_api_url.rstrip("/")
        return u if u.endswith("/api2/json") else f"{u}/api2/json"

    @field_validator("proxmox_api_url")
    @classmethod
    def _ensure_trailing_slash(cls, v: str) -> str:
        v = v.strip()
        return v if v.endswith("/") else v + "/"

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