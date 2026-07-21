"""Pydantic schemas for the public REST API."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class ContainerKind(str, Enum):
    LXC = "lxc"
    QEMU = "qemu"


class PortMapping(BaseModel):
    host_port: int = Field(..., alias="host", description="Published host port")
    container_port: int = Field(..., alias="container")
    protocol: str = Field("tcp")

    model_config = {"populate_by_name": True}


class Service(BaseModel):
    """A single discoverable service (docker container on a PVE guest)."""

    id: str = Field(..., description="Stable unique id, e.g. <node>-<kind>-<vmid>-docker-<name>")
    name: str
    node: str
    vmid: int
    kind: ContainerKind
    status: ServiceStatus = ServiceStatus.UNKNOWN
    image: str = ""
    ports: list[PortMapping] = Field(default_factory=list)
    icon_hint: str = ""
    labels: dict[str, str] = Field(default_factory=dict)


class ServiceHealth(BaseModel):
    id: str
    status: ServiceStatus
    healthy: bool
    uptime_seconds: int = 0
    last_seen: Optional[str] = None
    message: str = ""


class ServicesResponse(BaseModel):
    services: list[Service]
    source: str = "proxmox"  # or "mock"
    count: int = 0


class HealthResponse(BaseModel):
    health: ServiceHealth


# -------------------------------------------------------------- bookmarks
# User-saved bookmarks, managed via the Bookmarks page. Persisted on the same
# dashboard_config row, alongside services/theme/background.


class Bookmark(BaseModel):
    # `id` defaults to empty so the POST route can auto-generate it; subsequent
    # GET responses always carry a populated id.
    id: str = ""
    title: str
    url: str
    category: str = "general"
    icon: Optional[str] = None  # emoji or short hint
    display_order: int = 0


class BookmarkPatch(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None


# -------------------------------------------------------------- custom themes
# User-defined themes beyond the built-in set. Persisted on the config row so
# the "add more themes later via UI menu" acceptance is satisfied.


class ThemeDefinition(BaseModel):
    id: str = ""  # stable identifier e.g. "solarized-dark" (POST auto-generates)
    name: str  # display name
    dark: bool = True
    accent: str = "#22d3ee"
    bg: str = "#0b1020"
    surface: str = "#111827"
    text: str = "#e5e7eb"
    muted: str = "#94a3b8"
    border: str = "#1f2937"


# -------------------------------------------------------------- settings UI
# These models back the interactive Settings page. They are intentionally a
# richer overlay on top of the free-form bag-schema below — `extra` still
# carries anything the frontend may add in the future that the backend does
# not yet understand.


class ServiceEntry(BaseModel):
    """A dashboard tile the user added through the Settings page.

    `id` is the tile id (not the underlying Proxmox service id). `container_id`
    optionally links the tile to a discovered service so /api/services health
    can be overlaid on the rendered card.

    Widget integration: `widget_type` selects a known widget from the registry
    (`backend/app/widgets.py`). When set, `api_url` plus one of (`api_key` or
    `username`+`password`) provide the credentials the auto-login route uses to
    POST the service login form on the user behalf. All auth fields are optional
    and stored plaintext in the SQLite config row.
    """

    id: str = ""  # tile id (POST auto-generates)
    name: str
    url: Optional[str] = None  # click-through URL (also used as api_url fallback)
    icon: Optional[str] = None  # emoji or short hint like "sonarr"
    icon_url: Optional[str] = None  # custom icon URL (.svg/.png/.jpg) — overrides emoji
    container_id: Optional[str] = None
    display_order: int = 0
    # --- Widget integration -------------------------------------------------
    widget_type: Optional[str] = None  # one of WIDGET_REGISTRY keys, or None
    api_url: Optional[str] = None  # base URL of the service API/web UI
    api_key: Optional[str] = None  # bearer/token auth (Grafana, Proxmox, Portainer)
    username: Optional[str] = None  # form-login auth (qBittorrent, Sonarr, etc.)
    password: Optional[str] = None  # paired with username


class BackgroundSettings(BaseModel):
    mode: str = "gradient"  # none | gradient | particles | wallpaper
    effects_enabled: bool = True
    wallpaper_url: Optional[str] = None
    wallpaper_blend: float = 0.6
    gradient_colors: list[str] = Field(
        default_factory=lambda: ["#0ea5e9", "#7c3aed", "#ec4899"]
    )
    particle_density: int = 40
    particle_speed: int = 30


class ThemeSettings(BaseModel):
    active_theme: str = "midnight-neon"
    accent_color: str = "#22d3ee"
    density: str = "comfortable"  # compact | comfortable | spacious


class DashboardConfig(BaseModel):
    """Dashboard layout/config persisted via POST/PUT /api/config.

    The Settings page (t_c1b1badf) writes the overlay fields below; legacy
    consumers may still read/write the generic `layout`/`extra` bag.
    """

    version: int = 1
    layout: dict[str, Any] = Field(default_factory=dict)
    hidden_services: list[str] = Field(default_factory=list)
    custom_labels: dict[str, dict[str, str]] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)

    # Settings-page overlay (additive — older clients ignore these).
    services: list[ServiceEntry] = Field(default_factory=list)
    background: BackgroundSettings = Field(default_factory=BackgroundSettings)
    theme: ThemeSettings = Field(default_factory=ThemeSettings)
    # Root-task (t_c8aa6b03) additions: bookmarks page + custom themes.
    bookmarks: list[Bookmark] = Field(default_factory=list)
    custom_themes: list[ThemeDefinition] = Field(default_factory=list)
    updated_at: Optional[str] = None


class WallpaperItem(BaseModel):
    id: str
    url: str
    name: str


class ReorderRequest(BaseModel):
    ordered_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------- cron events
# Surfaced by /api/cron — mirrors the subset of the Hermes `cronjob list` schema
# that's useful on a calendar.


class CronEntry(BaseModel):
    id: str
    name: Optional[str] = None
    schedule: Optional[str] = None
    enabled: bool = True
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    description: Optional[str] = None


class CronListResponse(BaseModel):
    jobs: list[CronEntry]
    source: str  # "hermes-cli" | "stub"
    count: int = 0


# --------------------------------------------------------------- search proxy


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    favicon: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    engine: str
    results: list[SearchResult]


class ConfigSaveResponse(BaseModel):
    ok: bool = True
    id: int
    updated_at: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None