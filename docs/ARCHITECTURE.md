# Architecture

The Proxmox Dashboard is a two-container stack: a FastAPI backend that talks
to Proxmox VE and does all persistence, and a React + Vite + Tailwind
frontend served by nginx that reverse-proxies API calls to the backend so
the user talks to exactly one origin.

This doc is the 30k-foot view — for per-module detail, follow the links
into `docs/backend/` and `docs/frontend/`.

## Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│ Host                                                                    │
│                                                                         │
│   Browser ──HTTP──► :8888 ─► nginx (frontend container)                 │
│                              │                                          │
│                              ├── /            ─► SPA index.html + JS     │
│                              ├── /assets/*    ─► static hashed bundles  │
│                              ├── /api/*       ─► backend:8000           │
│                              └── /wallpapers/* ─► backend:8000          │
│                              │                                          │
│                              ▼                                          │
│                          FastAPI                                         │
│                              │                                          │
│                              ├── /api/services    ─► discovery          │
│                              ├── /api/config       ─► SQLite (config.db) │
│                              ├── /api/search      ─► DuckDuckGo HTML    │
│                              ├── /api/cron        ─► `hermes` CLI       │
│                              └── /api/config/theme │bg│wppr ─► SQLite    │
│                                                                         │
│                              ▼                                          │
│                    Proxmox VE REST API (https://pve:8006)              │
│                              │                                          │
│                              ▼                                          │
│                    LXC/QEMU guests → Docker containers                 │
└────────────────────────────────────────────────────────────────────────┘
```

Either container can fail and the other still serves a degraded experience
(e.g. if the backend is down, the frontend loads but every fetch fails —
the UI surfaces error banners and falls back to defaults).

## Containers

### Frontend (`dashboard-frontend`)

- Built from `frontend/Dockerfile` (multi-stage: `node` for the Vite build,
  `nginx` for runtime).
- nginx serves the built `dist/` and proxies `/api` + `/wallpapers` to
  `backend:8000` via the config in `frontend/nginx.conf`.
- Single published port (`8888` by default, override with `DASHBOARD_PORT`).
- Healthcheck: `wget -qO- http://127.0.0.1/` — succeeds as long as
  `index.html` is reachable.

### Backend (`dashboard-backend`)

- Built from `backend/Dockerfile` (`python:3.11-slim` + `uvicorn`).
- Internal port `8000` only — never published externally in the compose
  default. Flip the `ports:` block in `docker-compose.yml` if you want
  direct API access (and Swagger UI at `/docs`) during debugging.
- Healthcheck: `curl -fsS http://127.0.0.1:8000/health` — fails fast on
  import or DB init errors.

The frontend container's `depends_on: backend (condition: service_healthy)`
means the frontend won't start until the backend's healthcheck passes — so
the user never sees a frontend that proxies to a missing backend.

## Data flow

### Discovery → tile render

```
1. Browser loads /                  (SPA bootstrap)
2. App.AppContent mounts            → useSettings.load() fires once
3. Store.load()                     → api.getConfig() → GET /api/config
4. HomePage mounts                  → api.getServices() → GET /api/services
5. If MOCK=true                     → backend returns MOCK_SERVICES
   If MOCK=false                    → ProxmoxClient.list_lxc/list_qemu()
                                    → discover_docker_services() per guest
6. HomePage builds Tile[]           → user tiles + discovery overlay
7. If no user tiles                 → unlinked discovered services render
8. For each linked tile             → api.getServiceHealth(id) (poll 10s)
9. Polling writes to healthById     → effect recomputes tiles + stats
```

### Settings mutation → persistence

```
User edits a tile in SettingsPage
  → useSettings.updateService(id, patch)
    → store set: {config.services: merged}  (optimistic)
    → api.updateService(id, patch)            → PUT /api/config/services/{id}
      → backend latest() reads SQLite row
      → patch applies, save() inserts new row
      → returns ServiceEntry
    → store persist returns, status: "idle"
  → Component re-renders with new tile
```

Every mutation goes through the store → api. Pages never `fetch` directly.
The Settings page can also call `api.*` for actions that aren't part of
the tile store (custom theme CRUD, wallpaper upload).

## Persistence model

- **SQLite, single table, single live row** — `backend/app/config_store.py`.
  Every save INSERTs a new row; `latest()` reads `max(id)`. The table
  grows by one row per save — older rows are an audit trail, not surfaced.
- **JSON blob, not column-per-field** — the schema stores the entire
  `DashboardConfig` as JSON so the model evolves without migrations.
  Pydantic validates on read; pydantic-settings handles env-var loading
  separately.
- **Two named volumes**: `dashboard-config` (the SQLite DB) and
  `dashboard-wallpapers` (uploaded wallpaper files). Survive
  `docker compose down`; wiped by `docker compose down -v`.

## Module dependency graph

```
                                  backend
                                    │
                  ┌─────────────────┼───────────────────┐
                  │                 │                   │
                config         config_store     docker_discover
                  │                 │                   │
                  └──► proxmox ◄──┘  └──► schemas ◄──┘
                                              ▲
                                              │
                                            main ◄── mock_data, widgets
                                              │
                                            wallpapers

                                  frontend
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                types             store ◄── api      App.tsx
                  ▲                 │ └───► types      │
                  │                 ▼                 ▼
                  └── pages (HomePage, SettingsPage, BookmarksPage,
                                     SearchPage, CalendarPage)
```

- **Types are the contract**: `frontend/types.ts` mirrors
  `backend/schemas.py`. Every add/remove on either side needs a matching
  change on the other. A separate contributor can change the backend, run
  the app, and see TypeScript errors flag the drift.
- **The store is the gate**: every UI mutation of `DashboardConfig` funnels
  through `useSettings`. Pages can call `api.*` directly for ad-hoc reads
  (cron, search, bookmarks) but never for the persisted config.

## External dependencies

| Dependency | Used by | Purpose |
|---|---|---|
| Proxmox VE API | backend `proxmox.py` | Guest + node discovery. |
| Docker socket | backend `docker_discover.py` | Local-container discovery when mounted. |
| SSH (optional) | backend `docker_discover.py` | In-guest Docker discovery. |
| DuckDuckGo HTML search | backend `main.search` | Search proxy. |
| `hermes` CLI (optional) | backend `main.list_cron` | Cron job list for the calendar. |

The frontend has zero external runtime deps beyond CDN-bundled React /
Vite-runtime. All API access is same-origin through nginx; no CORS in
production.

## Configuring the stack

See [`../CONFIGURATION.md`](../CONFIGURATION.md) for env vars, the PVE API
token creation flow, in-guest Docker discovery modes, deploying with real
Proxmox, and the through-the-website configuration story (tiles, theme,
background, bookmarks, search, calendar).

## Failure modes (graceful degradations)

| Failure | Visible behavior |
|---|---|
| Backend down (frontend up) | SPA loads; every GET fails; Home shows "Couldn't reach /api/services"; Settings shows error pill. Tiles already in the user's store persist via the zustand default config until reload. |
| Discovery returns empty | Home shows the empty CTA ("No dashboard tiles configured yet") only if BOTH user tiles and unlinked discovered services are zero — otherwise shows the unlinked section. |
| DuckDuckGo unreachable | `/api/search` returns 502; SearchPage shows an `AlertTriangle` banner. |
| `hermes` not on PATH | `/api/cron` returns `source: "stub"`; CalendarPage shows a normal month grid with no pins, footer says "Data source: stub". |
| Self-signed PVE cert + `PROXMOX_VERIFY_TLS=true` | Backend logs `proxmox error`; `/api/services` returns 502. Fix: `PROXMOX_VERIFY_TLS=false`. |
| SQLite DB corrupt / unreadable path | `init_db` fails; container marked unhealthy; frontend refuses to start (depends_on healthcheck). |

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
