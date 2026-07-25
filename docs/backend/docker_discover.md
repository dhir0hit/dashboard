# `backend/app/docker_discover.py`

Local Docker container discovery via the Docker socket. Returns a
list of `Service` objects per container found by `docker ps -a`.

## Strategy

The dispatcher `discover_docker_services(s)` uses a single strategy:

1. **Local Docker socket** — the backend talks to the local Docker daemon
   via the Docker socket (default `/var/run/docker.sock`, override with
   the `DOCKER_SOCK` env var / compose volume mount).
   - Checks `shutil.which("docker")` first; if `docker` is not on PATH,
     falls back to checking for the socket directly (so the backend can
     still report "discovered but no containers" if the socket exists
     but the CLI isn't installed).
   - Runs `docker ps -a --format ...` as a local subprocess (30s timeout).
   - On non-zero exit, TimeoutExpired, or FileNotFoundError, returns `[]`.

There is no SSH-based discovery, no remote API client, and no per-guest
execution — discovery is limited to the containers visible to the local
Docker socket.

## Constants

### `_ICON_MAP`

A dict mapping normalized image-name fragments to the `icon_hint` strings
the frontend recognizes. Keys are lowercase image-name fragments; the
check is `name == key or name.startswith(key)` — so `"nginx"` matches
both the `nginx` image and `nginx-proxy`. Covers grafana, prometheus,
nginx, portainer, postgres/pgsql, redis, mysql, mariadb, mongo/mongodb,
elasticsearch, kibana, vault, traefik, caddy, node, python,
homeassistant/home-assistant, pihole, adguard, uptime-kuma.

### `_DOCKER_PS_FORMAT`

The `--format` template passed to `docker ps`:
`"{{.Name}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Labels}}"` —
tab-delimited so `_parse_ps` can split reliably.

## Public functions

### `discover_docker_services(s) -> list[Service]`

Top-level dispatcher. See "Strategy" above. Returns a list of `Service`
objects (may be empty if Docker is installed but no containers are
running, or if Docker isn't installed / socket not mounted).

### `hostname_to_node(default="local") -> str`

Returns the local hostname (or `default` on error). Used as a fallback
label in some call paths.

## Private helpers

### `_icon_hint(image: str) -> str`

- Strips registry / tag from the image ref via
  `image.split("/")[-1].split(":")[0].lower()`.
- Iterates `_ICON_MAP` keys; returns the first matching value
  (`name == key or name.startswith(key)`).
- Defaults to `"docker"` if no match (or empty image).

### `_parse_ports(raw: str) -> list[PortMapping]`

- Parses Docker's `Ports` column, e.g.
  `"0.0.0.0:3000->3000/tcp, :::3000->3000/tcp"`.
- Skips chunks without `->`. For each: extracts `host_port` (right of
  last `:`), `container_port` and `proto` (split on `/`), dedups by
  `(host, container, proto)`.
- Returns `[]` when `raw` is empty or `"0"`.

### `_status_from(status_str: str) -> ServiceStatus`

- `status_str.lower().startswith("up")` → `RUNNING`
- `"paused"` prefix → `PAUSED`
- `"exited"` or `"restarting"` prefix → `STOPPED`
- else → `UNKNOWN`

### `_build_docker_ps_cmd() -> str`

Returns `f"docker ps -a --format '{_DOCKER_PS_FORMAT}'"`. Pinned format
so `_parse_ps` can rely on the field order.

### `_parse_ps(stdout: str) -> list[DockerRow]`

- Splits on newlines, skips blank lines and lines starting with `error`.
- Splits on `\t`; requires at least 4 columns (`Name`, `Image`, `Status`,
  `Ports`); `Labels` is optional (defaults to empty string).
- Strips leading `/` from container names (Docker prints `/name`).
- Returns a list of `DockerRow` dataclasses the shared
  `_rows_to_services` converts to `Service` objects.

### `_labels_to_dict(labels: str) -> dict[str, str]`

Parses Docker's Labels column (`"key1=val1,key2=val2,..."`) into a dict.
Empty/missing labels return `{}`.

### `_rows_to_services(stdout) -> list[Service]`

The shared output-shaping function. Walks `_parse_ps(stdout)`, builds a
`Service` per row with:

```python
id=f"docker-{row.name}"
```

This id format is the one mock_data mirrors (`docker-grafana`) and is
what the frontend's Settings-page "container_id" linker matches against.

## Data shapes

### `DockerRow` (dataclass)

Columns from the `docker ps --format` template:

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Container name (leading `/` stripped by `_parse_ps`). |
| `image` | `str` | Image ref. |
| `status` | `str` | Raw Docker status string, e.g. `"Up 2 hours"`, `"Exited (0) 3 days ago"`. |
| `ports` | `str` | Raw ports string from Docker. |
| `labels` | `str` | Defaults to `""`. `_labels_to_dict` parses it. |

## Conventions

- **No retries**: a single `docker ps` attempt; on failure returns `[]`.
- **No caching**: every `/api/services` call re-runs discovery. The
  frontend polls every 10s (`HEALTH_POLL_MS`) — the backend simply runs
  discovery per request. If your Docker host is slow, cache results with
  a short TTL at the `main.get_services` level.
- **Image-name matching is best-effort**: `_icon_hint` works for common
  registries and canonical names; exotic image refs default to `"docker"`.
- **Errors are not propagated**: discovery catches its own failures
  and returns `[]`. The caller (`main._gather_real_services`) logs
  warnings but doesn't aggregate. Discovery can never throw from this
  module — it can only return a list (possibly empty).
- **Local docker requires either the CLI or the socket**: the local
  fallback will still try `subprocess.run(...)` even if `docker` isn't on
  PATH as long as the socket exists — `subprocess.run` returns
  non-zero/stderr quickly, and we convert to `[]`. This is benign but
  means the socket can produce noise in the backend log on every request.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
