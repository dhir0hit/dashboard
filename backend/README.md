# Docker Dashboard Backend

FastAPI service that connects to the local Docker socket, lists all containers,
and exposes them as a dashboard-friendly REST API. Includes a mock mode for
development without a real Docker host.

## Endpoints

| Method | Path                         | Description                                              |
|--------|------------------------------|---------------------------------------------------------|
| GET    | `/api/services`              | All services (Docker containers) on the host            |
| GET    | `/api/services/{id}/health`  | Health for a single service                             |
| GET    | `/api/config`                | Latest persisted dashboard config                       |
| POST   | `/api/config`                | Persist dashboard config (JSON → SQLite)                |
| GET    | `/health`                    | Backend readiness + mode                                |
| GET    | `/docs`                      | OpenAPI / Swagger UI                                    |

Service object shape (see `app/schemas.py`):

```json
{
  "id": "docker-grafana",
  "name": "grafana",
  "kind": "container",
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

# dev mode without Docker
cp .env.example .env
echo MOCK=true >> .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for the interactive API explorer.

## Real Docker setup

1. Ensure the Docker daemon is running and the user running the backend has
   access to `/var/run/docker.sock`.

2. For development, you can run the backend inside a container with the socket
   mounted:

   ```bash
   docker run -v /var/run/docker.sock:/var/run/docker.sock \
              -p 8000:8000 \
              my-dashboard-backend
   ```

3. Or run natively on the host where Docker is installed.

## Error handling

- `/api/services` returns **502** if Docker discovery fails (socket not
  accessible, daemon not running, etc.).
- The `/health` endpoint always answers 200 — it's the readiness probe.
- In mock mode, set `MOCK=true` to return deterministic test data.

## Files

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py          # pydantic-settings env loader
│   ├── schemas.py         # public API models
│   ├── docker_discover.py # Docker CLI discovery → Service[]
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
curl localhost:8000/api/services/docker-grafana/health | jq .
curl -XPOST localhost:8000/api/config \
     -H 'content-type: application/json' \
     -d '{"layout":{"cols":3,"rows":2},"hidden_services":["x"]}'
curl localhost:8000/api/config | jq .
```

## Notes / limitations

- Discovery uses `docker ps -a` via the CLI. Per-container uptime is not
  surfaced; the health endpoint reports uptime_seconds=0 in real mode. Mock
  mode returns deterministic values.
- The backend must run as a user with access to the Docker socket (typically
  `root` or a user in the `docker` group).
