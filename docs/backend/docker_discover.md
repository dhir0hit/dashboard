# `backend/app/docker_discover.py`

Docker container discovery via the Docker socket. Returns a list of
`Service` objects for all containers on the host.

## Strategy

The dispatcher `discover_docker_services()` uses a single strategy:

**Local Docker socket** — runs `docker ps -a --format ...` against the
Docker socket mounted at `/var/run/docker.sock`. The backend container
must have the socket mounted (configured via `DOCKER_SOCK` in `.env`).

- Checks `shutil.which("docker")` first; if `docker` is not on PATH,
  falls back to checking for `/var/run/docker.sock` (so the backend
  can still report "discovered but no containers" if the socket exists
  but the CLI isn't installed).
- Runs `docker ps -a --format ...` as a local subprocess (30s timeout).
- On non-zero exit, TimeoutExpired, or FileNotFoundError, returns `[]`.

The function is a thin wrapper: `discover_via_local(node, vmid, kind)`.
The `node`, `vmid`, and `kind` parameters are accepted for API
compatibility but are no longer used (the old code supported multiple
nodes and VM types; now we just enumerate containers on the single host).

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

### `discover_docker_services() -> list[Service]`

Top-level dispatcher. Calls `discover_via_local("docker", "host", "container")`
and returns the result. The node/vmid/kind args are historical (kept for
call-site compatibility); they don't affect the output.

### `hostname_to_node(default="docker") -> str`

Returns the local hostname (or `default` on error). Not used in the
current discovery path but kept for potential future use.

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

### `discover_via_local(node, vmid, kind) -> list[Service]`

- If `shutil.which("docker")` is None and `/var/run/docker.sock` doesn't
  exist either, returns `[]` immediately.
- Otherwise runs `docker ps -a --format ...` locally via `subprocess.run`
  (30s timeout). Captures stdout, runs through `_rows_to_services`.
- Any `TimeoutExpired` / `FileNotFoundError` → `[]`.

### `_rows_to_services(stdout, node, vmid, kind) -> list[Service]`

The shared output-shaping function. Walks `_parse_ps(stdout)`, builds a
`Service` per row with:

```python
id=f"docker-{row.name}"
```

This id format is what the frontend's Settings-page "container_id" linker
matches against. The `node`, `vmid`, and `kind` parameters are accepted
but ignored (the id is now just `docker-<name>`).

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

- **No retries**: a single `subprocess.run` attempt. Adding retries would
  compound latency on an unreachable Docker daemon.
- **No caching**: every `/api/services` call re-runs discovery. The
  frontend polls every 10s (`HEALTH_POLL_MS`) — the backend simply runs
  discovery per request. If your Docker host is slow, cache results with a
  short TTL at the `main.get_services` level.
- **Image-name matching is best-effort**: `_icon_hint` works for common
  registries and canonical names; exotic image refs default to `"docker"`.
- **Errors are not propagated**: `discover_via_local` catches its own
  failures and returns `[]`. The caller (`main._gather_real_services`) logs
  warnings but doesn't aggregate. Discovery can never throw from this module
  — it can only return a list (possibly empty).
- **Docker socket required**: the backend container must have
  `/var/run/docker.sock` mounted (or `DOCKER_SOCK` set to the socket path
  on the host). Without it, discovery returns `[]`.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
