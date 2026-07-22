# `backend/app/config.py`

Configuration via env vars / `.env`, using `pydantic-settings`. Loaded
once at startup via `get_settings()` (an `lru_cache`-backed accessor).
All other modules read settings through this single instance so callers
don't have to re-parse env or re-validate.

## Public symbols

### `class Settings(BaseSettings)`

Pydantic-settings auto-maps environment variables to fields by name.
Env var names are case-insensitive by default (pydantic-settings
convention); fields with an explicit `alias` arg read from that alias
instead.

#### Configuration

```python
model_config = SettingsConfigDict(
    env_file=".env", env_file_encoding="utf-8", extra="ignore"
)
```

- Reads `.env` if present at process CWD. (In the docker compose stack
  the pair `env_file:` / environment block is what populates `Settings`.)
- `extra="ignore"` — unknown env vars are not errors.
- No `env_prefix` — env var names map directly to field names.

#### Fields (env var in parens)

| Field (Python) | Env var | Type | Default | Purpose |
|---|---|---|---|---|
| `proxmox_api_url` | `PROXMOX_API_URL` | `str` | `"https://proxmox.local:8006/"` | PVE API endpoint URL. The `_ensure_trailing_slash` validator forces a trailing `/`. |
| `proxmox_api_token` | `PROXMOX_API_TOKEN` | `str` | `""` | Token string `user!tokenid=secret`. Used by `auth_header` below. |
| `proxmox_verify_tls` | `PROXMOX_VERIFY_TLS` | `bool` | `False` | Whether to verify PVE's TLS cert. Set false for self-signed homelab CA. |
| `proxmox_node` | `PROXMOX_NODE` | `str` | `""` | PVE node to query. Empty → `ProxmoxClient.pick_node()` auto-selects. |
| `ssh_host` | `SSH_HOST` | `str` | `""` | For in-guest Docker discovery over SSH. |
| `ssh_port` | `SSH_PORT` | `int` | `22` | SSH port. |
| `ssh_user` | `SSH_USER` | `str` | `"root"` | SSH user. |
| `ssh_key_file` | `SSH_KEY_FILE` | `str` | `""` | Path inside container to a private key. |
| `ssh_password` | `SSH_PASSWORD` | `str` | `""` | Alternative to `ssh_key_file`. |
| `mock` | `MOCK` (alias) | `bool` | `False` | If true, `/api/services` returns mock data instead of querying PVE. **The docker-compose file sets `MOCK=true` in the backend environment, so the running stack defaults to mock mode — but the `Settings` class itself defaults to `False`.** |
| `config_db` | `CONFIG_DB` (alias) | `str` | `"data/config.db"` | SQLite path. The `_abs` validator normalizes to an absolute, expanded, resolved path. **The docker-compose stack overrides this via `CONFIG_DB=/data/config.db` (the persistent volume mount); the class default is for local dev.** |
| `host` | `HOST` | `str` | `"127.0.0.1"` | uvicorn bind host (compose sets `HOST=0.0.0.0`). |
| `port` | `PORT` | `int` | `8000` | uvicorn bind port. |

#### Properties

##### `auth_header -> dict[str, str]`

Returns `{"Authorization": f"PVEAPIToken={proxmox_api_token}"}` when the
token is set, `{}` otherwise. `ProxmoxClient.__init__` reads this once and
reuses it for every request.

##### `token_user -> str`

Extracts the username portion (before `!`) from the token, or `""` when
the token has no `!`. Used for diagnostics; not load-bearing for actual
PVE auth.

##### `base_url -> str`

Computes the API root URL. Strips the trailing slash from
`proxmox_api_url`, then ensures it ends with `/api2/json` (PVE's REST
root). If the URL already ends with `/api2/json`, it's returned as-is.

#### Validators

- `@field_validator("proxmox_api_url")` `_ensure_trailing_slash` — strips
  whitespace and forces a trailing `/`. So `"https://pve:8006"` becomes
  `"https://pve:8006/"`.
- `@field_validator("config_db")` `_abs` — resolves the path to absolute
  via `Path(v).expanduser().resolve()`. So `~/config.db` becomes
  `/root/config.db`; relative paths are resolved against CWD.

### `get_settings() -> Settings`

```python
@lru_cache
def get_settings() -> "Settings":
    return Settings()
```

- First call constructs `Settings()` (which reads env + `.env`, runs the
  validators, and freezes the instance).
- Subsequent calls return the SAME instance (cached by `lru_cache`).
- Used everywhere in the app where settings are read (route handlers,
  background pollers, etc.) so all callers see the same env-derived
  config.

### `reload_settings() -> Settings`

```python
def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
```

- Clears the `lru_cache` and constructs a fresh `Settings` from the
  current env.
- Useful in tests; not currently wired into a runtime "reload env" feature
  in the app.

## Notable details

- **No reload mechanism in the running app**: `lru_cache` means env
  changes require a process restart. `reload_settings()` exists but isn't
  called from any route. Restart the container to pick up new env vars.
- **Secrets in the env**: `proxmox_api_token` and `ssh_password` are
  read from env vars. They are never written to the SQLite config
  database; only the deduplicated store of tiles/theme/etc. is persisted.
- **`mock` defaults to `False` in the class, `True` in compose** — the
  `docker-compose.yml` `environment:` block on the backend service
  explicitly sets `MOCK=true` so the stack boots out-of-the-box. Flip
  `MOCK=false` and provide a real token to talk to PVE.
- **`config_db` defaults to a project path, overridden in compose** —
  the docker compose stack mounts `dashboard-config:/data` and sets
  `CONFIG_DB=/data/config.db` so SQLite persists. In local dev without
  Docker, the default `data/config.db` works
  from the repo root.
- **`WALLPAPER_DIR` is not a pydantic field**: the wallpaper storage directory
  is read directly by `wallpapers.py` via `os.environ.get("WALLPAPER_DIR", ...)`,
  not through the `Settings` class. It defaults to `/app/wallpapers` in Docker
  (set in `docker-compose.yml`) or `<project>/backend/wallpapers` locally.
- **`base_url` adds `/api2/json`** — PVE's REST root path. Every
  `ProxmoxClient` request prepends `base_url`; if you point
  `PROXMOX_API_URL` at `https://pve.local:8006/api2/json/` directly,
  `base_url` returns it as-is (no double-suffix).

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
