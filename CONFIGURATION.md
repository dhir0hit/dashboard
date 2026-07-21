# Configuration Guide

End-to-end guide for configuring the Proxmox Dashboard — from spinning up the
stack to wiring it to a real Proxmox host and tuning every through-the-website
setting (tiles, theme, background, bookmarks, search, calendar).

> **TL;DR**: `docker compose up --build` → open
> <http://localhost:8888> → click **Settings**. Everything below is for
> going beyond the defaults.

---

## 1. Prerequisites

| Requirement | Why |
|---|---|
| Docker 20.10+ & Docker Compose v2 | Runs the two-container stack |
| A Proxmox VE host (optional) | Only needed when `MOCK=false` |
| A PVE API token (optional) | Needed for real service discovery |
| `hermes` CLI on the backend host (optional) | Needed for the Calendar page to show real jobs |

Mock mode (`MOCK=true`, the default) needs **none** of the Proxmox/SSH/Hermes
prerequisites — it ships canned data so you can explore the UI immediately.

---

## 2. Quick start — zero-config (mock mode)

```bash
cd Dashboard
docker compose up --build
```

Open <http://localhost:8888>. You'll see four mock services in the tile grid
(grafana, prometheus, nginx, portainer), a working search page, an empty
bookmarks page, and an empty calendar.

To switch to a real Proxmox host later, keep reading.

---

## 3. Environment variables

Everything that is not editable through the website is configured via
environment variables — either in a `.env` file next to
`docker-compose.yml`, or exported in your shell before `docker compose up`.

Copy the template and edit:

```bash
cp .env.example .env
$EDITOR .env
docker compose --env-file .env up --build
```

### Full reference

| Variable | Default | Purpose |
|---|---|---|
| `DASHBOARD_PORT` | `8888` | Host port the dashboard is published on. Change if 8888 is taken. |
| `MOCK` | `true` | `true` → canned mock data, no Proxmox needed. `false` → query the real PVE host. |
| `PROXMOX_API_URL` | `https://proxmox.local:8006/` | PVE API endpoint (include the trailing slash). |
| `PROXMOX_API_TOKEN` | _(empty)_ | `user!tokenid=secret`. The `!` and `=` are mandatory. Create one in PVE under *Datacenter → API Tokens*. |
| `PROXMOX_VERIFY_TLS` | `false` | Set `false` for self-signed certs (typical for homelab PVE). |
| `PROXMOX_NODE` | _(empty)_ | Specific PVE node to query. Empty = auto-pick first reachable node. |
| `SSH_HOST` | _(empty)_ | For in-guest Docker discovery over SSH. Empty → fall back to `pct exec` for LXC. |
| `SSH_PORT` | `22` | SSH port for in-guest discovery. |
| `SSH_USER` | `root` | SSH user. |
| `SSH_KEY_FILE` | _(empty)_ | Path **inside the backend container** to a private key. Mount host keys via a compose volume override. |
| `SSH_PASSWORD` | _(empty)_ | Alternative to `SSH_KEY_FILE` for password auth. |
| `DOCKER_SOCK` | `/var/run/docker.sock` | Host Docker socket for discovering containers running directly on the host. Set to `/dev/null` to disable. |

### Minimal real-Proxmox `.env`

```env
DASHBOARD_PORT=8888
MOCK=false
PROXMOX_API_URL=https://proxmox.example.com:8006/
PROXMOX_API_TOKEN=root@pam!dashboard=00000000-0000-0000-0000-000000000000
PROXMOX_VERIFY_TLS=false
```

### Creating a PVE API token

1. Log into the Proxmox web UI → **Datacenter → API Tokens**.
2. Pick the user (e.g. `root@pam`), click **Add Token**.
3. Give it an ID (e.g. `dashboard`) — the full token identifier is
   `root@pam!dashboard`.
4. Copy the secret UUID shown once. Uncheck **Privilege Separation** if you
   want the token to inherit the user's full permissions.
5. Assemble the token string: `root@pam!dashboard=<secret>`.
6. Paste it into `PROXMOX_API_TOKEN` in your `.env`.

### In-guest Docker discovery — pick one method

The backend can enumerate Docker containers inside LXC/QEMU guests. It tries
the following strategies in order; the first that works wins.

1. **Direct Docker socket** (default): the compose file already mounts
   `${DOCKER_SOCK:-/dev/null}:/var/run/docker.sock`. This only discovers
   containers on the PVE host itself, not inside guests. Comment out that
   line in `docker-compose.yml` to disable.
2. **SSH into each guest**: set `SSH_HOST`, `SSH_USER`, and either
   `SSH_KEY_FILE` (path inside the container — mount a host key via a
   compose volume override) or `SSH_PASSWORD`. Works for any guest the
   backend can reach on `SSH_PORT`.
3. **`pct exec` fallback**: if `SSH_HOST` is empty, the backend uses the
   PVE API's `pct exec` to run `docker ps` inside LXC guests. Requires the
   API token to have `VM.Audit`/`VM.Console` permissions on the guest — no
   per-guest configuration needed.

---

## 4. Configuring everything through the website

Once the stack is running, open <http://localhost:8888>. All below sections
happen through the website itself — no file editing or restarts.

### 4.1 Dashboard tiles (Home page)

The Home page shows the tiles you've added, optionally linked to live
Proxmox-discovered services for status overlay and health polling.

- **Add a tile**: go to **Settings → Dashboard tiles → Add tile**. Provide:
  - **Name** — the label shown on the tile.
  - **URL** (optional) — clicking the tile opens this in a new tab.
  - **Icon** (optional) — an emoji or a short hint like `grafana`,
    `prometheus`, `nginx`, `portainer`. The app maps known hints to icons.
  - **Container ID** (optional) — link the tile to a discovered service id
    (e.g. `pve-lxc-100-docker-grafana`) so live status/health is overlaid.
- **Reorder**: drag the gripper handle on a tile in the Settings page.
- **Edit / delete**: use the pencil / trash buttons on each row.
- **Filter / search**: on the Home page, use the search box and status chips
  (All / Running / Stopped / Paused / Unlinked) to narrow the grid.

Changes persist immediately to the backend SQLite database — a toast/visual
update confirms each save.

### 4.2 Background

Settings page → **Background** section.

- **Effects toggle**: master switch for all background animations. Turn off
  to reduce motion / save CPU.
- **Mode**:
  - `None` — solid dark backdrop.
  - `Animated gradient` — smooth flowing gradient (default). Edit the three
    gradient color hex values below.
  - `Particles` — moving particles canvas. Tune density (count) and speed
    via `particle_density` and `particle_speed` on the config (or via the
    API — see §5).
  - `Wallpaper` — use an uploaded image. Choose a wallpaper from the ones
    you've uploaded (see next bullet) and adjust the blend (opacity) slider.
- **Uploading a wallpaper**: in the Background section, use the upload
  control to drop an image file. It's stored in the `dashboard-wallpapers`
  volume and immediately selectable. Previously uploaded wallpapers are
  listed via `/api/config/wallpapers` (UI picker populates from this).

### 4.3 Theme

Settings page → **Theme** section.

- **Active theme**: pick from built-ins (`Midnight Neon`, `Aurora`,
  `Solarized Dark`, `Paper`) or any custom theme you've added.
- **Accent color** — override the accent color regardless of theme.
- **Density**: `Compact` / `Comfortable` / `Spacious` — controls content
  padding and spacing throughout the UI.
- **New theme**: click **New theme** to define a fully custom theme:
  - `name` — display name.
  - `dark` — whether it's a dark theme (drives the light/dark CSS class).
  - `accent` — accent hex.
  - `bg`, `surface`, `text`, `muted`, `border` — color hex values for each
    surface role.
  - The saved theme appears in the **Active theme** dropdown immediately.
- Delete a custom theme from the same menu.

### 4.4 Bookmarks

Bookmarks page (🌐 icon, route `/bookmarks`).

- **Add**: click **+**, fill in **Title**, **URL**, **Category**
  (free-form text — used for grouping/filtering), and optional **Icon**
  (emoji or short hint).
- **Filter**: use the category dropdown at the top to narrow the list.
- **Edit / delete**: the pencil / trash buttons on each bookmark.
- Bookmarks persist to the same SQLite config row as everything else and
  survive restarts.

### 4.5 Web search

Search page (🔍 icon, route `/search`).

- Type a query and hit **Enter**. The backend proxies DuckDuckGo's HTML
  endpoint server-side — no browser CORS, no tracking, no ads.
- Up to 30 results are returned with favicons and direct links.
- The search engine is fixed to DuckDuckGo; there is no plugin or
  selectable engine at this time. Changing it requires editing
  `backend/app/main.py::search` (see §5).

### 4.6 Calendar / cron

Calendar page (📅 icon, route `/calendar`).

- Renders a month grid. Days that have a Hermes cron job's
  `last_run` or `next_run` on them are pinned with an indicator.
## 4.6 Calendar / cron

Calendar page (📅 icon, route `/calendar`).

- Renders a month grid. Days that have a Hermes cron job's `last_run` or `next_run` on them are pinned with an indicator.
- Data source: the backend shells out to `hermes cronjob list --json` on the backend container's host. If `hermes` is not on PATH or the call fails, the page falls back to an empty stub (you'll see `source: "stub"` in the API response).
- **To enable real jobs**: install the `hermes` CLI on the Docker host AND make it reachable inside the `dashboard-backend` container. The easiest way is a bind-mount in a `docker-compose.override.yml`:

  ```yaml
  services:
    backend:
      volumes:
        - /usr/local/bin/hermes:/usr/local/bin/hermes:ro
        - /root/.hermes:/root/.hermes:ro
  ```

  Then `docker compose up -d` and the calendar will reflect your real Hermes cron jobs.

- **Google Calendar integration** (one-time setup):
  - Create a **Desktop app** OAuth client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
    - Enable the **Google Calendar API**
  - Add `VITE_GOOGLE_CLIENT_ID=<your-desktop-client-id>.apps.googleusercontent.com` to your `frontend/.env`
- **No manual "add an event" UI** — the calendar is a view onto Hermes cron, not a standalone calendar app. Create jobs via the Hermes CLI (`hermes cronjob ...`) and refresh the page.
- **No manual "add an event" UI** — the calendar is a view onto Hermes
  cron, not a standalone calendar app. Create jobs via the Hermes CLI
  (`hermes cronjob ...`) and refresh the page.

---

## 5. REST API (advanced / automation)

Everything the website can do, the API can do. Useful for scripting initial
setup, automating config across hosts, or integrating with other tools.

Base URL: `http://localhost:8888/api` (proxied through nginx to the backend).
All endpoints below are reachable via this single published port.

The backend also exposes FastAPI's auto-generated Swagger UI at `/docs` and a
liveness endpoint at `/health`, **but those are not reverse-proxied by the
frontend's nginx** — they're only reachable from inside the container network
(on `backend:8000`). If you need them from the host, either:

- temporarily publish the backend port by uncommenting the `ports:` block
  under `backend:` in `docker-compose.yml`, then visit
  <http://localhost:8000/docs>, or
- add `location /docs` / `location /health` blocks to
  `frontend/nginx.conf` and rebuild the frontend image.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/services` | List discovered services (mock or from Proxmox). |
| `GET` | `/api/services/{id}/health` | Per-service health (status, uptime, last seen). |
| `GET` | `/api/config` | Fetch the full dashboard config (tiles, theme, background, bookmarks, custom themes). |
| `PUT` | `/api/config` | Replace the full config (used by every settings mutation). |
| `POST` | `/api/config/services` | Add a tile. Body: `{name, url?, icon?, container_id?}`. Returns the created tile with its `id`. |
| `PUT` | `/api/config/services/{id}` | Edit a tile. |
| `DELETE` | `/api/config/services/{id}` | Delete a tile. |
| `PUT` | `/api/config/services/reorder` | Reorder tiles. Body: `{"ordered_ids": ["id1","id2",...]}`. |
| `PUT` | `/api/config/background` | Replace background settings. |
| `PUT` | `/api/config/theme` | Replace theme settings. |
| `POST` | `/api/config/wallpaper` | Upload a wallpaper (multipart `file`). Returns `{id, url, name}`. |
| `GET` | `/api/config/wallpapers` | List uploaded wallpapers. |
| `GET` | `/api/config/bookmarks` | List bookmarks. |
| `POST` | `/api/config/bookmarks` | Add a bookmark. Body: `{title, url, category, icon?}`. |
| `PUT` | `/api/config/bookmarks/{id}` | Patch a bookmark. |
| `DELETE` | `/api/config/bookmarks/{id}` | Delete a bookmark. |
| `GET` | `/api/config/themes` | List custom themes. |
| `POST` | `/api/config/themes` | Add a custom theme. Body: `{name, dark, accent, bg, surface, text, muted, border}`. |
| `DELETE` | `/api/config/themes/{id}` | Delete a custom theme. |
| `GET` | `/api/search?query=...` | DuckDuckGo HTML search proxy. |
| `GET` | `/api/cron` | Hermes cron jobs (`hermes cronjob list --json`, or a stub). |

> The backend also serves `/docs` (Swagger) and `/health` on port 8000, but
> nginx does not currently reverse-proxy those paths. See the note above the
> table for how to reach them.

### Example: seed a tile via curl

```bash
curl -X POST http://localhost:8888/api/config/services \
  -H 'Content-Type: application/json' \
  -d '{"name":"Sonarr","url":"http://sonarr.example.com:8989","icon":"sonarr","container_id":"pve-lxc-100-docker-sonarr"}'
```

### Example: add a custom theme via curl

```bash
curl -X POST http://localhost:8888/api/config/themes \
  -H 'Content-Type: application/json' \
  -d '{"name":"Forest","dark":true,"accent":"#34d399","bg":"#0b1f17","surface":"#102a20","text":"#d1fae5","muted":"#6ee7b7","border":"#1c3a2b"}'
```

---

## 6. Volumes & persistence

Two named volumes survive container restarts and `docker compose down`:

| Volume | Mount (in backend) | Holds |
|---|---|---|
| `dashboard-config` | `/data` | SQLite config DB (`config.db`) — all website settings |
| `dashboard-wallpapers` | `/app/wallpapers` | Uploaded wallpaper images |

To wipe everything and start fresh: `docker compose down -v`.

To back up: snapshot the volumes

```bash
docker run --rm -v dashboard-config:/data -v "$PWD":/backup alpine \
  tar czf /backup/dashboard-config.tgz -C /data .
```

---

## 7. Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
MOCK=true uvicorn app.main:app --reload --port 8000

# Frontend (separate shell)
cd frontend
npm install
npm run dev   # http://localhost:5173 — vite dev-proxies /api → :8000
```

Variables override as usual (`MOCK=false PROXMOX_API_TOKEN=... uvicorn ...`).

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Blank page at `:8888` (empty `#root`) | Hard-refresh the browser (cache-bust). If still blank, check `docker compose logs frontend` for build errors and confirm the bundle hash in `/assets/index-*.js` matches the source build. |
| Backend container exits immediately with `PROXMOX_API_TOKEN not set` | Set `MOCK=true` (the default) or provide a real token in `.env`. |
| `502 Bad Gateway` from `/api/*` | Backend not healthy. Check `docker compose ps` and `docker compose logs backend`. Backend must be `Up (healthy)` before the frontend will proxy to it. |
| Self-signed Proxmox cert errors in backend logs | Set `PROXMOX_VERIFY_TLS=false` in `.env`. |
| No services discovered in real mode | Confirm the API token has `VM.Audit` on the guests. For in-guest Docker: verify the SSH path or that `pct exec` works from the PVE host. Check `docker compose logs backend` for per-guest errors. |
| Calendar shows `source: "stub"` | `hermes` CLI not reachable inside the backend container. Mount the binary + `~/.hermes` (see §4.6). |
| Port 8888 already in use | Set `DASHBOARD_PORT=<free port>` in `.env` and restart. |
| Settings edits don't persist | Verify the `dashboard-config` volume is healthy: `docker volume ls \| grep dashboard`. Don't run `docker compose down -v` unless you want a full reset. |

---

## 9. Verification checklist

- [ ] `docker compose up --build` starts both containers (`Up (healthy)`).
- [ ] <http://localhost:8888> loads the dashboard (not a blank page).
- [ ] `/api/services` returns services (4 mock services in mock mode).
- [ ] Settings edits to tiles/theme/background survive a
      `docker compose down && docker compose up -d` cycle (SQLite volume).
- [ ] `/health` returns `{"ok": true, "mock": bool, "pve": "<url>"}`.
- [ ] In real mode, `/api/services` reflects your actual PVE guests.