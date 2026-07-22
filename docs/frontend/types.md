# `frontend/src/types.ts`

Shared TypeScript types and default constants. Mirrors the backend pydantic
schemas in `backend/app/schemas.py` — when backend schemas change, update this
file to match.

## Status / kind

### `ServiceStatus`

`"running" | "stopped" | "paused" | "unknown"` — matches the backend enum.

### `DiscoveredService`

A single discovered container, mirrors backend `Service`.

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Stable id, e.g. `pve-lxc-100-docker-grafana`. |
| `name` | `string` | Container name. |
| `node` | `string` | PVE node. |
| `vmid` | `number` | Guest VMID. |
| `kind` | `"lxc" \| "qemu"` | Guest type. |
| `status` | `ServiceStatus` | Current status. |
| `image` | `string` | Docker image ref. |
| `ports` | `PortMapping[]` | Published ports. |
| `icon_hint` | `string` | Short hint mapped to emoji by `iconForHint`. |
| `labels` | `Record<string, string>` | Docker container labels. |

### `PortMapping`

| Field | Type |
|---|---|
| `host` | `number` |
| `container` | `number` |
| `protocol` | `string` |

### `ServicesResponse`

| Field | Type | Notes |
|---|---|---|
| `services` | `DiscoveredService[]` | All discovered. |
| `source` | `string` | `"mock"` or `"proxmox:<host>"`. |
| `count` | `number` | `services.length`. |

### `ServiceHealth`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Service id. |
| `status` | `ServiceStatus` | Live status. |
| `healthy` | `boolean` | true iff running. |
| `uptime_seconds` | `number` | Best-effort (0 in real mode). |
| `last_seen` | `string \| null` | ISO timestamp or null. |
| `message` | `string` | Freeform status message. |

### `HealthResponse`

`{ health: ServiceHealth }` — wrapper matching the backend route's
`response_model`.

## User tiles

### `ServiceEntry`

A user-added dashboard tile. Distinct from `DiscoveredService` — links to one
optionally via `container_id`.

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Tile id (not the underlying service id). |
| `name` | `string` | Display label. |
| `url?` | `string` | Click-through URL (also used as `api_url` fallback). |
| `icon?` | `string` | Emoji or short hint like `"grafana"`. |
| `container_id?` | `string` | Linked `DiscoveredService.id` for status overlay. |
| `category?` | `string` | User-defined grouping (e.g. "Media", "Monitoring"). |
| `display_order` | `number` | Sort key. |
| `status?` | `ServiceStatus` | Optional surfaced status (read-only). |
| `ports?` | `{ host; container; protocol }[]` | Optional surfaced ports. |
| `image?` | `string` | Optional surfaced image. |
| `widget_type?` | `string` | One of `WIDGET_REGISTRY` ids. Enables auto-login. |
| `api_url?` | `string` | Base URL of the service API/web UI. |
| `api_key?` | `string` | Bearer/token auth. |
| `username?` | `string` | Form-login / basic-auth username. |
| `password?` | `string` | Paired with `username`. |

### `WidgetAuthSchema`

`"none" | "api_key" | "basic" | "form"` — determines which credential fields
the Settings form shows and how the auto-login route authenticates.

### `WidgetDefinition`

A widget registry entry. Returned by `GET /api/widgets`. Fields mirror the
backend `WIDGET_REGISTRY` dict — see `docs/backend/widgets.md`.

### `TileLoginResponse`

Response from `POST /api/tiles/{id}/auth`. Contains `method` (the auth
schema used), optional `cookies` (Set-Cookie strings to plant on the
browser), `redirect_url` (where to navigate after setting cookies), and a
`message`.

## Background & theme

### `BackgroundSettings`

| Field | Type | Notes |
|---|---|---|
| `mode` | `"none" \| "gradient" \| "particles" \| "wallpaper"` | Render mode. |
| `effects_enabled` | `boolean` | Master switch. |
| `wallpaper_url?` | `string` | Set when mode=wallpaper. |
| `wallpaper_blend?` | `number` | 0..1 opacity. |
| `gradient_colors?` | `[string, string, string]` | Three gradient stops. |
| `particle_density?` | `number` | Particle count factor (default 40). |
| `particle_speed?` | `number` | Drift speed (default 30). |

### `ThemeSettings`

| Field | Type | Notes |
|---|---|---|
| `active_theme` | `string` | `"midnight-neon"` / `"aurora"` / custom id. |
| `accent_color` | `string` | Hex, overrides theme accent. |
| `density` | `"compact" \| "comfortable" \| "spacious"` | UI density. |

## Bookmarks

### `Bookmark`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Stable id. |
| `title` | `string` | Display label. |
| `url` | `string` | Target URL. |
| `category` | `string` | Freeform grouping. |
| `icon?` | `string \| null` | Emoji or hint. |
| `display_order` | `number` | Sort key. |

### `BookmarkPatch`

Partial-update shape for `api.updateBookmark`. Every field optional.

## Themes

### `ThemeDefinition`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Stable id. |
| `name` | `string` | Display name. |
| `dark` | `boolean` | Whether it's a dark theme (CSS class). |
| `accent` | `string` | Hex. |
| `bg` | `string` | Hex. |
| `surface` | `string` | Hex. |
| `text` | `string` | Hex. |
| `muted` | `string` | Hex. |
| `border` | `string` | Hex. |

### `BuiltTheme`

`ThemeDefinition & { builtin: true }` — used by `BUILTIN_THEMES` below.

## Cron / search

### `CronEntry`

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | Job id. |
| `name?` | `string \| null` | Display name. |
| `schedule?` | `string \| null` | Cron expression / human schedule. |
| `enabled` | `boolean` | Active flag. |
| `next_run?` | `string \| null` | ISO timestamp. |
| `last_run?` | `string \| null` | ISO timestamp. |
| `description?` | `string \| null` | Freeform. |

### `CronListResponse`

| Field | Type | Notes |
|---|---|---|
| `jobs` | `CronEntry[]` | All jobs. |
| `source` | `string` | `"hermes-cli"` or `"stub"`. |
| `count` | `number` | `jobs.length`. |

### `SearchResult`

| Field | Type | Notes |
|---|---|---|
| `title` | `string` | Result title. |
| `url` | `string` | Result URL. |
| `snippet` | `string` | Short description (currently unused). |
| `favicon?` | `string \| null` | Icon URL or null. |

### `SearchResponse`

| Field | Type |
|---|---|
| `query` | `string` |
| `engine` | `string` |
| `results` | `SearchResult[]` |

## Config

### `DashboardConfig`

The single persisted config object.

| Field | Type | Notes |
|---|---|---|
| `services` | `ServiceEntry[]` | User tiles. |
| `background` | `BackgroundSettings` | Background config. |
| `theme` | `ThemeSettings` | Theme config. |
| `bookmarks` | `Bookmark[]` | Saved bookmarks. |
| `custom_themes` | `ThemeDefinition[]` | User themes. |
| `updated_at?` | `string` | ISO timestamp of last save. |

## Constants

### `DEFAULT_CONFIG`

A `DashboardConfig` seeded with safe defaults (gradient background with the
cyan/violet/pink gradient, `midnight-neon` theme, empty `services`/`bookmarks`/
`custom_themes`). Used as the store's initial `config` and as the fallback
in `api.getConfig` when the backend omits fields.

### `BUILTIN_THEMES`

Array of 4 `BuiltTheme`:

| id | name | dark | accent |
|---|---|---|---|
| `midnight-neon` | Midnight Neon | yes | `#22d3ee` |
| `aurora` | Aurora | yes | `#a78bfa` |
| `solarized-dark` | Solarized Dark | yes | `#268bd2` |
| `paper` | Paper | no | `#1d4ed8` |

`ThemeApplier` in `App.tsx` picks the active theme from
`[...BUILTIN_THEMES, ...customThemes]` by `theme.active_theme`, falling back
to `BUILTIN_THEMES[0]`.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
