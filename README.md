# Server Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A full-stack dashboard for services on a NAS. The backend (FastAPI) discovers
containers/VMs via the Proxmox API and inspects each guest for running Docker
services. The frontend (React + Vite + Tailwind) renders the discovered services
as animated tiles with health polling, a settings page for managing dashboard
layout, and per-service background effects.

## Screenshots

### Dashboard — Tile Grid
![Dashboard Home](screenshots/dashboard-home.png)

### Settings — Tile Management, Background & Theme
![Settings](screenshots/settings.png)

### Search — Private Web Search
![Search](screenshots/search.png)

### Bookmarks
![Bookmarks](screenshots/bookmarks.png)

### Calendar
![Calendar](screenshots/calendar.png)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  docker compose up                                                  │
│                                                                     │
│  ┌───────────────────────┐         ┌──────────────────────────────┐ │
│  │  frontend (nginx:80)  │  :8888  │  backend (FastAPI :8000)     │ │
│  │  ─ React SPA          │ ◀────── │  ─ Proxmox API client         │ │
│  │  ─ nginx serves dist/  │ proxies │  ─ Docker socket / SSH        │ │
│  │  ─ /api proxy to      │  /api/  │  ─ SQLite config persistence  │ │
│  │    backend            │   /wppr │  ─ Wallpaper upload/storage    │ │
│  └───────────────────────┘         └──────────────────────────────┘ │
│         │                                       │                  │
│         │ exposed                                mounts             │
│         ▼                                       ▼                  │
│     :8888 (host)                  dashboard-config, dashboard-wppr  │
└─────────────────────────────────────────────────────────────────────┘
```

Only the frontend service is published to the host (port 8888 by default). It
reverse-proxies `/api/*` and `/wallpapers/*` to the backend, so the user
talks to exactly one origin and no CORS configuration is needed in production.

## Quick start (mock mode)

`docker compose up` defaults to `MOCK=true`, so the stack boots without a real
Proxmox host:

```bash
git clone <this repo> && cd Dashboard
docker compose up --build
```

Open http://localhost:8888 — you will see four mock services in the tile grid,
search/filter controls, and the Settings page. Edit `PROXMOX_API_TOKEN`,
`PROXMOX_API_URL`, and set `MOCK=false` to talk to a real host.

## Configuring for a real Proxmox host

1. Copy the env template and edit it:
   ```bash
   cp .env.example .env
   $EDITOR .env
   ```
2. Set, at minimum:
   - `PROXMOX_API_URL` — the PVE API endpoint (e.g. `https://proxmox.example.com:8006/`).
   - `PROXMOX_API_TOKEN` — `user!tokenid=secret`. Create one in the PVE web UI
     under *Datacenter → API Tokens*. Verify: the `!` and `=` are required.
   - `PROXMOX_VERIFY_TLS=false` for self-signed certs (default).
   - `MOCK=false` to stop returning mock data.
3. (Optional) SSH for in-guest Docker discovery. The backend can discover
   Docker containers inside LXC/QEMU guests one of three ways, in order:
   1. Direct Docker socket access (set `DOCKER_SOCK=/var/run/docker.sock` and
      mount it — the compose file already does this; comment out the line in
      `docker-compose.yml` to disable).
   2. SSH into each guest (`SSH_HOST`, `SSH_USER`, `SSH_KEY_FILE`).
   3. `pct exec` from the PVE host (needs token permissions on the host, no
      per-guest configuration).
4. Google Calendar setup (one-time):
   - Create a **Desktop app** OAuth client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
     - Enable the **Google Calendar API**
   - Add `VITE_GOOGLE_CLIENT_ID=<your-desktop-client-id>.apps.googleusercontent.com` to your `frontend/.env`
5. Bring the stack up:
   ```bash
   docker compose --env-file .env up --build
   ```

See `backend/.env.example` for the full list of environment variables.

## Volumes & persistence

The compose file declares two named volumes:

| Volume                  | Mount (in backend) | Purpose                               |
|-------------------------|--------------------|---------------------------------------|
| `dashboard-config`     | `/data`            | SQLite database backing `/api/config` |
| `dashboard-wallpapers` | `/app/wallpapers`  | Uploaded wallpaper images             |

Both survive container restarts and `docker compose down` (but are removed by
`docker compose down -v`).

## Single-port access

The frontend nginx config proxies all backend traffic:

| Route                  | Served by                |
|------------------------|--------------------------|
| `/`                    | React SPA (`index.html`) |
| `/assets/*`            | Vite-built static assets |
| `/api/*`               | `backend:8000`           |
| `/wallpapers/*`        | `backend:8000`           |

Change the published host port with `DASHBOARD_PORT` (default `8888`).

## Files

```
.
├── docker-compose.yml     # service definitions, env vars, volumes
├── .env.example           # copy to .env for real-Proxmox configuration
├── README.md              # this file
├── backend/
│   ├── Dockerfile         # FastAPI + uvicorn runtime
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── .env.example       # backend-specific vars (used in local dev)
│   └── app/               # FastAPI application code
└── frontend/
    ├── Dockerfile         # multi-stage: vite build + nginx runtime
    ├── .dockerignore
    ├── nginx.conf         # SPA serve + /api proxy
    ├── package.json
    ├── vite.config.ts
    └── src/               # React + Tailwind SPA
```

## Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
MOCK=true uvicorn app.main:app --reload --port 8000

# Frontend (in another shell)
cd frontend
npm install
npm run dev   # http://localhost:5173 — vite dev-proxies /api → :8000
```

## Troubleshooting

- **Backend container exits with `PROXMOX_API_TOKEN not set`**: that's a
  non-mock startup rejecting an auth-less request. Set `MOCK=true` or provide
  a real token.
- **Self-signed Proxmox cert errors from the backend**: confirm
  `PROXMOX_VERIFY_TLS=false` is set in the backend environment.
- **No services discovered**: check the backend logs
  (`docker compose logs backend`). Mock mode returns 4 canned services; real
  mode returns only guests that have Docker installed and reachable either via
  the Docker socket or SSH.
- **`port 8888 is already in use`**: set `DASHBOARD_PORT=8000` (or any free
  port) in your `.env` and restart.

## Verification checklist (acceptance)

- [x] `docker compose up --build` builds and starts both containers
- [x] Dashboard is reachable at http://localhost:8888 (single published port)
- [x] `/api/services` proxies through to the backend and returns mock services
- [x] Config edits persist across `docker compose down` / `up` ( SQLite
      volume)
- [x] Proxmox host URL, API token, and Docker socket are all configurable via
      environment variables