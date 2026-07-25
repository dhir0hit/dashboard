# Dashboard Backend

FastAPI service that discovers Docker containers via the local Docker
socket, lists them as dashboard-friendly services, and exposes them as a
REST API. Includes a mock mode for development without a Docker host.

## Endpoints

| Method | Path                         | Description                                              |
|--------|------------------------------|---------------------------------------------------------|
| GET    | `/api/services`              | All discovered Docker containers                         |
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

# dev mode without Docker discovery
cp .env.example .env
echo MOCK=true >> .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for the interactive API explorer.

## Real Docker discovery setup

1. Ensure the Docker socket (`/var/run/docker.sock`) is accessible to the
   backend container. The compose file mounts
   `${DOCKER_SOCK:-/dev/null}:/var/run/docker.sock` by default.
2. Set in `.env`:

   ```env
   MOCK=false
   DOCKER_SOCK=/var/run/docker.sock
   ```

3. The backend runs `docker ps -a --format ...` against the local Docker
   socket to discover all running and stopped containers. No SSH, no remote
   API — just the local socket.

## Error handling

- `/api/services` returns an empty list if the Docker socket is unavailable
  or no containers are found.
- The `/health` endpoint always answers 200 — it's the readiness probe.
- A missing socket in non-mock mode returns an empty discovery list with
  a warning in the backend log.

## Files

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py          # pydantic-settings env loader
│   ├── schemas.py         # public API models
│   ├── docker_discover.py # local docker ps → Service[]
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

- The backend discovers containers by running `docker ps -a --format ...`
  against the local Docker socket. No SSH, no remote hosts, no per-guest
  discovery — just the containers visible to the socket the backend is
  configured to read.
- Per-container uptime is not surfaced via `docker ps --format`; the health
  endpoint reports `uptime_seconds=0` in real mode. Mock mode returns
  deterministic values.
- If the Docker socket is not mounted or Docker is not installed, discovery
  silently returns an empty list (logged as a warning in the backend log).
