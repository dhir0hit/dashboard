# `backend/app/schemas.py`

Pydantic models backing the public REST API. These are the single source of
truth for request/response shapes on every `/api/*` route, and they mirror the
TypeScript types in `frontend/src/types.ts`.

## Enums

### `ServiceStatus(str, Enum)`

Container status reported by discovery or health polling.

| Value | Meaning |
|---|---|
| `RUNNING` | Container is up. |
| `STOPPED` | Container is not running. |
| `PAUSED` | Container paused (Docker `paused` state). |
| `UNKNOWN` | Status couldn't be determined. |

### `ContainerKind(str, Enum)`

| Value | Meaning |
|---|---|
| `LXC` | Proxmox Linux container. |
| `QEMU` | Proxmox virtual machine. |

## Discovery models

### `PortMapping`

A single published port on a discovered container.

| Field | Type | Alias | Notes |
|---|---|---|---|
| `host_port` | `int` | `host` | Published host port. |
| `container_port` | `int` | `container` | Port inside the container. |
| `protocol` | `str` | — | Default `"tcp"`. |

`model_config = {"populate_by_name": True}` — accepts either the alias
(`host`/`container`) or the snake-case field name on input.

### `Service`

A single discoverable Docker container on a PVE guest.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | required | Stable id, e.g. `<node>-<kind>-<vmid>-docker-<name>`. |
| `name` | `str` | required | Container name. |
| `node` | `str` | required | PVE node. |
| `vmid` | `int` | required | Guest VMID. |
| `kind` | `ContainerKind` | required | `lxc` or `qemu`. |
| `status` | `ServiceStatus` | `UNKNOWN` | Current status. |
| `image` | `str` | `""` | Docker image ref. |
| `ports` | `list[PortMapping]` | `[]` | Published ports. |
| `icon_hint` | `str` | `""` | Short hint (e.g. `"grafana"`) — frontend maps to emoji. |
| `labels` | `dict[str, str]` | `{}` | Docker container labels. |

### `ServiceHealth`

Per-service health snapshot returned by `/api/services/{id}/health`.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | required | Service id. |
| `status` | `ServiceStatus` | required | Live status. |
| `healthy` | `bool` | required | True iff `status == RUNNING`. |
| `uptime_seconds` | `int` | `0` | Best-effort uptime (0 when unavailable). |
| `last_seen` | `Optional[str]` | `None` | ISO timestamp or null. |
| `message` | `str` | `""` | Free-form status message. |

### `HealthResponse`

Wrapper: `{"health": ServiceHealth}`. The `/api/services/{id}/health` route
returns this shape.

### `ServicesResponse`

`/api/services` response.

| Field | Type | Default | Notes |
|---|---|---|---|
| `services` | `list[Service]` | required | All discovered services. |
| `source` | `str` | `"proxmox"` | `"mock"` or `"proxmox:<host_label>"`. |
| `count` | `int` | `0` | `len(services)`. |

## Bookmarks

### `Bookmark`

A user-saved link, persisted on the same config row as tiles/theme.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | `""` | POST auto-generates if empty. |
| `title` | `str` | required | Display label. |
| `url` | `str` | required | Target URL. |
| `category` | `str` | `"general"` | Free-form grouping string. |
| `icon` | `Optional[str]` | `None` | Emoji or short hint. |
| `display_order` | `int` | `0` | Sort key. |

### `BookmarkPatch`

Partial update shape for `PUT /api/config/bookmarks/{id}`. All fields optional;
`None` means "leave unchanged".

## Themes

### `ThemeDefinition`

A user-defined theme beyond the built-in set.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | `""` | POST auto-generates if empty. |
| `name` | `str` | required | Display name. |
| `dark` | `bool` | `True` | Drives the `theme-light` CSS class. |
| `accent` | `str` | `"#22d3ee"` | Accent hex. |
| `bg` | `str` | `"#0b1020"` | Page background. |
| `surface` | `str` | `"#111827"` | Card surface. |
| `text` | `str` | `"#e5e7eb"` | Body text. |
| `muted` | `str` | `"#94a3b8"` | Muted/secondary text. |
| `border` | `str` | `"#1f2937"` | Border color. |

## Settings-page overlay

### `ServiceEntry`

A dashboard tile the user added through the Settings page. Distinct from
`Service` (which is the *discovered* container). `container_id` optionally
links the tile to a `Service.id` so live status/health overlays it.

Widget integration fields (`widget_type`, `api_url`, `api_key`, `username`,
`password`) enable per-tile auto-login — see `widgets.py` and the
`POST /api/tiles/{id}/auth` route.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | `""` | Tile id (POST auto-generates). |
| `name` | `str` | required | Display label. |
| `url` | `Optional[str]` | `None` | Click-through URL (also used as `api_url` fallback). |
| `icon` | `Optional[str]` | `None` | Emoji or short hint. |
| `container_id` | `Optional[str]` | `None` | Linked `Service.id`. |
| `display_order` | `int` | `0` | Sort key. |
| `widget_type` | `Optional[str]` | `None` | One of `WIDGET_REGISTRY` ids (`"grafana"`, `"proxmox"`, etc.). |
| `api_url` | `Optional[str]` | `None` | Base URL of the service API/web UI. |
| `api_key` | `Optional[str]` | `None` | Bearer/token auth (Grafana, Proxmox, Portainer). |
| `username` | `Optional[str]` | `None` | Form-login / basic-auth username (qBittorrent, Sonarr). |
| `password` | `Optional[str]` | `None` | Paired with `username`. |

### `BackgroundSettings`

| Field | Type | Default | Notes |
|---|---|---|---|
| `mode` | `str` | `"gradient"` | `none` / `gradient` / `particles` / `wallpaper`. |
| `effects_enabled` | `bool` | `True` | Master switch. |
| `wallpaper_url` | `Optional[str]` | `None` | URL of the uploaded wallpaper. |
| `wallpaper_blend` | `float` | `0.6` | 0..1 opacity. |
| `gradient_colors` | `list[str]` | `["#0ea5e9","#7c3aed","#ec4899"]` | Three gradient stops. |
| `particle_density` | `int` | `40` | Particle count scaling factor. |
| `particle_speed` | `int` | `30` | Particle drift speed. |

### `ThemeSettings`

| Field | Type | Default | Notes |
|---|---|---|---|
| `active_theme` | `str` | `"midnight-neon"` | Built-in or custom theme id. |
| `accent_color` | `str` | `"#22d3ee"` | Overrides the theme's accent. |
| `density` | `str` | `"comfortable"` | `compact` / `comfortable` / `spacious`. |

### `DashboardConfig`

The single persisted config row. Returned by `GET /api/config`, replaced by
`PUT /api/config`, and owned by the Settings page.

| Field | Type | Default | Notes |
|---|---|---|---|
| `version` | `int` | `1` | Schema version. |
| `layout` | `dict[str, Any]` | `{}` | Legacy freeform bag. |
| `hidden_services` | `list[str]` | `[]` | Legacy: ids to hide. |
| `custom_labels` | `dict[str, dict[str, str]]` | `{}` | Legacy: per-id labels. |
| `extra` | `dict[str, Any]` | `{}` | Forward-compat bag for unknown future fields. |
| `services` | `list[ServiceEntry]` | `[]` | User tiles. |
| `background` | `BackgroundSettings` | default | Background config. |
| `theme` | `ThemeSettings` | default | Theme config. |
| `bookmarks` | `list[Bookmark]` | `[]` | Saved bookmarks. |
| `custom_themes` | `list[ThemeDefinition]` | `[]` | User-defined themes. |
| `updated_at` | `Optional[str]` | `None` | ISO timestamp of last save. |

## Wallpapers

### `WallpaperItem`

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Generated file id. |
| `url` | `str` | `/wallpapers/<filename>` URL. |
| `name` | `str` | Original filename. |

## Reorder

### `ReorderRequest`

Body for `PUT /api/config/services/reorder`.

| Field | Type | Notes |
|---|---|---|
| `ordered_ids` | `list[str]` | Tile ids in the new order. |

## Cron

### `CronEntry`

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | `str` | required | Job id. |
| `name` | `Optional[str]` | `None` | Display name. |
| `schedule` | `Optional[str]` | `None` | Cron expression / human schedule. |
| `enabled` | `bool` | `True` | Whether the job is active. |
| `next_run` | `Optional[str]` | `None` | ISO timestamp or null. |
| `last_run` | `Optional[str]` | `None` | ISO timestamp or null. |
| `description` | `Optional[str]` | `None` | Freeform description. |

### `CronListResponse`

`/api/cron` response.

| Field | Type | Notes |
|---|---|---|
| `jobs` | `list[CronEntry]` | All jobs. |
| `source` | `str` | `"hermes-cli"` when real, `"stub"` when CLI not available. |
| `count` | `int` | `len(jobs)`. |

## Search

### `SearchResult`

| Field | Type | Default | Notes |
|---|---|---|---|
| `title` | `str` | required | Result title. |
| `url` | `str` | required | Result URL. |
| `snippet` | `str` | `""` | Short description (currently unused by the DuckDuckGo parser). |
| `favicon` | `Optional[str]` | `None` | `https://icons.duckduckgo.com/ip3/<host>.ico` or null. |

### `SearchResponse`

| Field | Type | Notes |
|---|---|---|
| `query` | `str` | Original query. |
| `engine` | `str` | `"duckduckgo-html"`. |
| `results` | `list[SearchResult]` | Up to 30 results. |

## Misc

### `ConfigSaveResponse`

`POST /api/config` response.

| Field | Type | Default | Notes |
|---|---|---|---|
| `ok` | `bool` | `True` | Always true on success. |
| `id` | `int` | required | The SQLite row id (always 1 — single-row config table). |
| `updated_at` | `str` | required | ISO timestamp. |

### `ErrorResponse`

Generic error body for non-2xx responses.

| Field | Type | Default | Notes |
|---|---|---|---|
| `error` | `str` | required | Short error code. |
| `detail` | `Optional[str]` | `None` | Longer explanation. |

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
