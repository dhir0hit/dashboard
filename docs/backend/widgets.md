# `backend/app/widgets.py`

Widget registry — known service types the dashboard can auto-login to.
Defines the metadata for each widget type (Grafana, Proxmox, qBittorrent,
etc.) that `ServiceEntry.widget_type` references.

Each widget definition is a dict with:

| Key | Type | Purpose |
|---|---|---|
| `id` | `str` | Stable identifier used in `ServiceEntry.widget_type`. |
| `name` | `str` | Display name for the settings dropdown. |
| `icon_hint` | `str` | Maps to the frontend's `ICON_HINT_TO_EMOJI` table. |
| `auth_schema` | `str` | One of `"none"`, `"api_key"`, `"basic"`, `"form"`. Determines which credential fields the Settings form shows. |
| `login_path` | `str \| None` | URL path appended to `api_url` for the login API call. |
| `auth_header_format` | `str` (optional) | Template for `api_key` widgets. `{token}` is replaced with the stored `api_key`. |
| `login_form_template` | `str` (optional) | Template for `form` widgets. `{username}` and `{password}` are substituted. |
| `description` | `str` | Human-readable help text shown under the dropdown. |

## Auth schemas

| Schema | Fields used | How login works |
|---|---|---|
| `none` | (none) | No auto-login. Tile is just a click-through link. |
| `api_key` | `api_url` + `api_key` | POST to `api_url + login_path` with the formatted auth header. |
| `basic` | `api_url` + `username` + `password` | POST with HTTP Basic auth. |
| `form` | `api_url` + `username` + `password` | POST with `application/x-www-form-urlencoded` body. |

## Built-in widgets (14)

| id | name | auth_schema |
|---|---|---|
| `generic` | Generic link | none |
| `grafana` | Grafana | form |
| `prometheus` | Prometheus | none |
| `proxmox` | Proxmox VE | api_key |
| `portainer` | Portainer | api_key |
| `qbit_torrent` | qBittorrent | form |
| `sonarr` | Sonarr | api_key |
| `radarr` | Radarr | api_key |
| `transmission` | Transmission | basic |
| `pihole` | Pi-hole | api_key |
| `homeassistant` | Home Assistant | api_key |
| `adguard` | AdGuard Home | basic |
| `nginxproxymanager` | Nginx Proxy Manager | form |
| `uptimekuma` | Uptime Kuma | none |

## Public functions

### `list_widgets() -> list[dict]`

Returns a copy of every widget definition. Used by `GET /api/widgets`.

### `get_widget(widget_type: str | None) -> dict | None`

Looks up a single widget by id. Returns `None` if the id is missing or
`widget_type` is `None`. Used by `POST /api/tiles/{id}/auth` to determine
the login strategy.

## Adding a new widget

Append a dict to `WIDGET_REGISTRY` with the appropriate `auth_schema` and
field templates. The frontend picks it up automatically via
`GET /api/widgets` — no frontend code change needed (the Settings form
dynamically shows/hides credential fields based on `auth_schema`).

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
