# `backend/app/main.md`

The FastAPI application module. Entry point:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Single source of all `/api/*` routes, plus the proxied `/docs` (FastAPI
Swagger) and `/health` endpoints on port 8000.

## App setup

```python
app = FastAPI(
    title="Docker Dashboard Backend",
    version="0.1.0",
    description="Service-discovery REST API for Docker containers on the host.",
)
```

CORS is wide open (`allow_origins=["*"]`) — the frontend is reverse-proxied
through nginx on the same origin in production, so CORS is only relevant during
local dev (vite on :5173 → backend on :8000).

### Startup hook

`@app.on_event("startup")` calls `init_db(s.config_db)` to create the SQLite
config table if it doesn't exist, then logs the mock/docker_socket mode.

## Discovery

### `_gather_real_services() -> tuple[list[Service], str]`

Internal helper. Connects to the local Docker socket:

1. Runs `docker ps -a` to list all containers on the host.
2. Parses the output into `DockerRow` objects.
3. Converts each row into a `Service` with `kind=ContainerKind.CONTAINER`.
4. Returns `(services, "docker")`.

Raises generic exceptions (logged as docker discovery failures) up to the route
handlers, which map them to HTTP 502.

## Routes

### Services

| Method | Path | Handler | Response model | Errors |
|---|---|---|---|---|
| `GET` | `/api/services` | `get_services` | `ServicesResponse` | 502 (Docker error) |
| `GET` | `/api/services/{service_id}/health` | `get_service_health` | `HealthResponse` | 404 (unknown id), 502 |

`get_services`:
- `MOCK=true` → returns `MOCK_SERVICES` with `source="mock"`.
- Otherwise calls `_gather_real_services()`.

`get_service_health`:
- `MOCK=true` → looks up `MOCK_HEALTH[service_id]` (404 if not found).
- Real mode: gathers services, finds the one with `id == service_id` (404
  if missing), derives `healthy = status == RUNNING`, returns a
  `ServiceHealth` with `uptime_seconds=0`, `last_seen=None`, and a short
  message. Per-container Docker stats are not currently collected, so
  uptime is always 0 in real mode.

### Config

| Method | Path | Handler | Response model |
|---|---|---|---|
| `GET` | `/api/config` | `get_config` | `DashboardConfig` |
| `POST` | `/api/config` | `post_config` | `ConfigSaveResponse` |
| `PUT` | `/api/config` | `put_config` | `DashboardConfig` |
| `POST` | `/api/config/services` | `add_service` | `ServiceEntry` (201) |
| `PUT` | `/api/config/services/reorder` | `reorder_services` | 204 |
| `PUT` | `/api/config/services/{service_id}` | `update_service` | `ServiceEntry` |
| `DELETE` | `/api/config/services/{service_id}` | `delete_service` | 204 |
| `PUT` | `/api/config/background` | `patch_background` | `DashboardConfig` |
| `PUT` | `/api/config/theme` | `patch_theme` | `DashboardConfig` |

`get_config` returns `DashboardConfig()` (defaults) if nothing is saved.
`post_config` / `put_config` call `save(s.config_db, cfg)` to persist; `put`
also backfills `cfg.updated_at` from the save result and returns the updated
config.

`add_service` auto-generates an id via `_gen_service_id(name)` if none is
provided, deduplicates against existing ids (appends `secrets.token_hex(2)`),
defaults `display_order = len(services)`, sorts the list, persists, returns the
new entry.

`reorder_services` sets `display_order` on each id in `ordered_ids` order,
appends any services not mentioned in `ordered_ids` (defensive — never drops
tiles), persists, returns 204.

`update_service` 404s if the id is unknown; `patch.id` is forced to the
existing id (ids are stable across edits). Persists, returns the patched entry.

`delete_service` 404s if the id is unknown; otherwise removes it, reindexes
`display_order` for the survivors, persists, returns 204.

`patch_background` / `patch_theme` replace the whole `background` / `theme`
sub-object on the config row and persist.

### Wallpapers

| Method | Path | Handler | Response model |
|---|---|---|---|
| `POST` | `/api/config/wallpaper` | `upload_wallpaper` (async) | `WallpaperItem` |
| `GET` | `/api/config/wallpapers` | `list_wallpapers_route` | `list[WallpaperItem]` |
| `GET` | `/wallpapers/{filename}` | `serve_wallpaper` (not in schema) | file response |

`upload_wallpaper` accepts a multipart `file`, calls `save_upload(file)`. A
`ValueError` from `save_upload` (e.g. unsupported content type) maps to 400.

### Bookmarks

| Method | Path | Handler | Response model |
|---|---|---|---|
| `GET` | `/api/config/bookmarks` | `list_bookmarks` | `list[Bookmark]` |
| `POST` | `/api/config/bookmarks` | `add_bookmark` | `Bookmark` (201) |
| `PUT` | `/api/config/bookmarks/{bookmark_id}` | `update_bookmark` | `Bookmark` |
| `DELETE` | `/api/config/bookmarks/{bookmark_id}` | `delete_bookmark` | 204 |

Same auto-id + dedupe + `display_order` pattern as services. `update_bookmark`
applies only the non-null fields from `BookmarkPatch` (true partial update),
404s on unknown id.

### Custom themes

| Method | Path | Handler | Response model |
|---|---|---|---|
| `GET` | `/api/config/themes` | `list_custom_themes` | `list[ThemeDefinition]` |
| `POST` | `/api/config/themes` | `add_custom_theme` | `ThemeDefinition` (201) |
| `DELETE` | `/api/config/themes/{theme_id}` | `delete_custom_theme` | 204 |

Same CRUD pattern. Delete 404s on unknown id.

### Search proxy

| Method | Path | Handler | Response model |
|---|---|---|---|
| `GET` | `/api/search?query=...` | `search` | `SearchResponse` |

Server-side DuckDuckGo HTML proxy. Empty query → 400. Fetches
`https://html.duckduckgo.com/html/?q=<query>` with a Chrome User-Agent
(10s timeout), then regex-extracts every `<a class="result__a" href=...>`
and decodes the `uddg=` redirect parameter to get the real result URL.
Favicons come from `https://icons.duckduckgo.com/ip3/<host>.ico`. Capped at
30 results. Network failure → 502.

### Cron

| Method | Path | Handler | Response model |
|---|---|---|---|
| `GET` | `/api/cron` | `list_cron` | `CronListResponse` |

Shells out to `hermes cronjob list --json` (8s timeout). If the binary is
missing, the call times out, or the JSON is unparseable, returns an empty
stub with `source="stub"`. Accepts either a top-level list, or an object with
`jobs`/`items`/`data` carrying the list. Normalizes each entry into
`CronEntry` (id falls back to `name`), sets `source="hermes-cli"`.

### Health & root

| Method | Path | Handler | Notes |
|---|---|---|---|
| `GET` | `/health` | `root_health` | `{"ok": true, "mock": bool, "docker_socket": "<path>"}` — liveness for the compose healthcheck. |
| `GET` | `/` | `root` | Manifest with `name`, `version`, `docs`, and `endpoints` list. Useful for sanity-checking the backend from inside the container network. |

### Widgets + auto-login

| Method | Path | Handler | Response model | Notes |
|---|---|---|---|---|
| `GET` | `/api/widgets` | `widgets_list` | `list[dict]` | Full widget registry. |
| `GET` | `/api/widgets/{widget_id}` | `widgets_get` | `dict` | Single widget. 404 on unknown id. |
| `POST` | `/api/tiles/{service_id}/auth` | `tile_login` | `dict` | Server-side login for a tile. |

`tile_login` loads the tile by `service_id` from the SQLite config, looks up
its `widget_type` in the registry, and performs the appropriate login call:

- `auth_schema == "none"` → returns `{"method": "none", "redirect_url": api_url}`
  immediately (no HTTP call).
- `auth_schema == "api_key"` → POST to `api_url + login_path` with the
  formatted auth header (`auth_header_format` template, `{token}` replaced).
- `auth_schema == "basic"` → POST with `auth=(username, password)`.
- `auth_schema == "form"` → POST with `application/x-www-form-urlencoded`
  body from `login_form_template` (`{username}` / `{password}` substituted).

On success: returns `{"method", "cookies" (Set-Cookie list), "redirect_url",
"message"}`. The frontend plants the cookies via `document.cookie` then
opens `redirect_url` in a new tab.

Errors: 404 (unknown tile id), 400 (no widget_type, no api_url, missing
credentials for the schema), 502 (upstream login failure or network error).

## Helpers

- `_gen_service_id(name) -> str` — `svc-<slug>-<3-byte-hex>`; slug is
  `re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")` falling back to
  `"svc"`.
- `_gen_bookmark_id(title) -> str` — same pattern with `bm-` prefix.

Both are used by the POST routes above to auto-assign ids when the client
omits one.

## Logging

`log = logging.getLogger("dashboard")` with `basicConfig(level=INFO)` at
module load. Every route logs meaningful events (config replaced, per-guest
discovery failures, etc.) at INFO or WARNING.

## Not exported

This module has no `__all__`. The public surface is the FastAPI `app` object
(named for `uvicorn app.main:app`) and the route functions. Everything
prefixed `_` is internal.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
