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
| `docker_sock` | `DOCKER_SOCK` | `str` | `"/var/run/docker.sock"` | Host Docker socket path for local container discovery. Mount into the backend container via a compose volume. |
| `mock` | `MOCK` (alias) | `bool` | `False` | If true, `/api/services` returns mock data instead of querying Docker. **The docker-compose file sets `MOCK=true` in the backend environment, so the running stack defaults to mock mode — but the `Settings` class itself defaults to `False`.** |
| `config_db` | `CONFIG_DB` (alias) | `str` | `"data/config.db"` | SQLite path. The `_abs` validator normalizes to an absolute, expanded, resolved path. **The docker-compose stack overrides this via `CONFIG_DB=/data/config.db` (the persistent volume mount); the class default is for local dev.** |
| `host` | `HOST` | `str` | `"127.0.0.1"` | uvicorn bind host (compose sets `HOST=0.0.0.0`). |
| `port` | `PORT` | `int` | `8000` | uvicorn bind port. |

#### Validators

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
- **No secrets in the env**: the only env vars are the Docker socket path
  and mock toggle — no tokens or passwords. All website settings (tiles,
  theme, etc.) are persisted in the SQLite config database.
- **`mock` defaults to `False` in the class, `True` in compose** — the
  `docker-compose.yml` `environment:` block on the backend service
  explicitly sets `MOCK=true` so the stack boots out-of-the-box. Flip
  `MOCK=false` to enable real Docker discovery.
- **`config_db` defaults to a project path, overridden in compose** —
  the docker compose stack mounts `dashboard-config:/data` and sets
  `CONFIG_DB=/data/config.db` so SQLite persists. In local dev without
  Docker, the default `data/config.db` works
  from the repo root.
- **`WALLPAPER_DIR` is not a pydantic field**: the wallpaper storage directory
  is read directly by `wallpapers.py` via `os.environ.get("WALLPAPER_DIR", ...)`,
  not through the `Settings` class. It defaults to `/app/wallpapers` in Docker
  (set in `docker-compose.yml`) or `<project>/backend/wallpapers` locally.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
