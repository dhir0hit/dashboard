# Proxmox Dashboard Backend

FastAPI service that connects to a Proxmox VE host, lists LXC + QEMU guests,
discovers Docker containers running inside each, and exposes them as a
dashboard-friendly REST API. Includes a mock mode for development without a
Proxmox server.

## Endpoints

| Method | Path                         | Description                                              |
|--------|------------------------------|---------------------------------------------------------|
| GET    | `/api/services`              | All services (docker containers) across all guests      |
| GET    | `/api/services/{id}/health`  | Health for a single service                             |
| GET    | `/api/config`                | Latest persisted dashboard config                       |
| POST   | `/api/config`                | Persist dashboard config (JSON → SQLite)                |
| GET    | `/health`                    | Backend readiness + mode                                |
| GET    | `/docs`                      | OpenAPI / Swagger UI                                    |

Service object shape (see `app/schemas.py`):

```json
{
  "id": "pve-lxc-100-docker-grafana",
  "name": "grafana",
  "node": "pve",
  "vmid": 100,
  "kind": "lxc",
  "status": "running",
  "image": "grafana/grafana:10.4.2",
  "ports": [{"host": 3000, "container": 3000, "protocol": "tcp"}],
  "icon_hint": "grafana",
  "labels": {}
}
```

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# dev mode without Proxmox
cp .env.example .env
echo MOCK=true >> .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for the interactive API explorer.

## Real Proxmox setup

1. Create an API token in PVE (`Datacenter → API Tokens → Add`). Give it
   the right ACLs to read `/nodes/*` and exec on `/nodes/{node}/lxc/{vmid}` if
   you want Docker discovery via `pct exec`.
2. Set in `.env`:

   ```
   PROXMOX_API_URL=https://proxmox.example.com:8006/
   PROXMOX_API_TOKEN=root@pam!dashboard=<secret-from-pve>
   PROXMOX_VERIFY_TLS=false        # self-signed dev cert
   ```

3. For Docker discovery you have two options:

   **A. SSH to the PVE host** (recommended for LXC)
      Set `SSH_HOST`, `SSH_USER=root`, and either `SSH_KEY_FILE` or
      `SSH_PASSWORD`. The backend runs `pct exec <vmid> -- docker ps` over
      SSH for LXC guests, and a plain `docker ps` for QEMU VMs reachable by
      SSH.

   **B. Run the backend inside a container/VM** with `docker` CLI installed
      and `/var/run/docker.sock` mounted. Local `docker ps -a` is used as a
      fallback when SSH is not configured.

## Auth error handling

- `/api/services` returns **401** if PVE rejects the API token, and **502**
  for other PVE-side errors (network, malformed response).
- The `/health` endpoint always answers 200 — it's the readiness probe.
- A missing token in non-mock mode returns 401 with a message telling the
  developer to set `MOCK=true`.

## Files

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py          # pydantic-settings env loader
│   ├── schemas.py         # public API models
│   ├── proxmox.py         # PVE HTTP client (token auth, httpx)
│   ├── docker_discover.py # SSH / local docker ps → Service[]
│   ├── mock_data.py       # deterministic mock dataset
│   ├── config_store.py    # SQLite persistence for /api/config
│   └── main.py            # FastAPI app, endpoints, error handling
├── requirements.txt
├── .env.example
└── README.md
```

## Testing

Boot in mock mode and curl:

```bash
curl localhost:8000/api/services | jq '.count, .source, .services[0]'
curl localhost:8000/api/services/pve-lxc-100-docker-grafana/health | jq .
curl -XPOST localhost:8000/api/config \
     -H 'content-type: application/json' \
     -d '{"layout":{"cols":3,"rows":2},"hidden_services":["x"]}'
curl localhost:8000/api/config | jq .
```

## Notes / limitations

- `pct exec` via the REST `/lxc/{vmid}/exec` endpoint returns a task UPID —
  synchronous stdout isn't available without task-wait polling. The backend
  therefore prefers SSH to the PVE host and runs `pct exec ...` over SSH,
  which returns output directly. If SSH is not configured and the backend
  isn't running inside the guest itself, docker discovery silently returns
  an empty list (other guests still appear from PVE's own data when the
  frontend adds that view).
- Per-container uptime is not surfaced via `docker ps --format`; the health
  endpoint reports uptime_seconds=0 in real mode. Mock mode returns
  deterministic values.
- TLS verification defaults to `false` for dev convenience — flip
  `PROXMOX_VERIFY_TLS=true` for production.