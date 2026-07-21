# `backend/app/docker_discover.py`

In-guest Docker container discovery for LXC/QEMU Proxmox guests. Returns a
list of `Service` objects per `(node, vmid, kind)` tuple.

## Strategy (in priority order)

The dispatcher `discover_docker_services(s, node, vmid, kind)`:

1. **SSH (preferred)** — when `s.ssh_host` is set:
   - For **LXC** guests, the SSH command is prefixed with
     `pct exec <vmid> --` so the remote `docker ps` runs inside the guest
     (PVE's `pct exec` over SSH — no guest-side SSH server needed).
   - For **QEMU** guests, the `docker ps` runs directly on the SSH host
     (assumes the VM host IS the Docker host).
   - SSH failures (auth, connection, timeout) are swallowed — the
     dispatcher falls through to strategy 2.
2. **Local Docker** — when SSH isn't configured OR SSH failed:
   - Checks `shutil.which("docker")` first; if `docker` is not on PATH,
     falls back to checking for `/var/run/docker.sock` (so the backend
     can still report "discovered but no containers" if the socket exists
     but the CLI isn't installed).
   - Runs `docker ps -a --format ...` as a local subprocess (30s timeout).
   - On non-zero exit, TimeoutExpired, or FileNotFoundError, returns `[]`.

There is no separate `pct_exec` strategy — the pct-exec-via-SSH path is
folded into strategy 1's LXC branch. PVE's REST `/pct exec` endpoint
(used by `ProxmoxClient.pct_exec`) returns a task UPID, not stdout, so
it's not useful for `docker ps` discovery here.

Both strategies feed stdout through the shared `_rows_to_services` row
parser, so the output shape is identical regardless of strategy.

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

### `discover_docker_services(s, node, vmid, kind) -> list[Service]`

Top-level dispatcher. See "Strategy" above. Returns a list of `Service`
objects (may be empty if the guest has Docker installed but no containers
running, or if docker isn't installed).

### `hostname_to_node(default="pve") -> str`

Returns the local hostname (or `default` on error). Used as a `node`
fallback in some call paths.

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

### `_ssh_client(s: Settings) -> paramiko.SSHClient`

- Creates a `paramiko.SSHClient`, accepts missing host keys
  (`AutoAddPolicy`), connects with `s.ssh_host`, `s.ssh_user`,
  `s.ssh_port`, 15s timeout.
- Auth priority: `ssh_key_file` (if exists) → `ssh_password` →
  `look_for_keys=True` (agent / default keys).

### `_exec_ssh_command(s, command) -> tuple[int, str, str]`

- Opens a fresh SSH client, runs `command` (60s timeout), reads stdout and
  stderr fully, returns `(exit_code, stdout, stderr)`.
- Always closes the client in a `finally`.

### `discover_via_ssh(s, node, vmid, kind) -> list[Service]`

- Early-return `[]` if `s.ssh_host` is unset (defensive — caller also
  guards).
- For `kind == LXC`, prefixes the `docker ps` command with
  `pct exec <vmid> --` so the remote call executes inside the LXC guest.
- Runs via `_exec_ssh_command`. Non-zero exit OR `not found` text in
  stderr/stdout → returns `[]` (treats missing docker as a no-error empty
  result). Auth / connect failures bubble up via exceptions — the
  dispatcher swallows them.
- On success: returns `_rows_to_services(stdout, node, vmid, kind)`.

### `discover_via_local(node, vmid, kind) -> list[Service]`

- If `shutil.which("docker")` is None and `/var/run/docker.sock` doesn't
  exist either, returns `[]` immediately.
- Otherwise runs `docker ps -a --format ...` locally via `subprocess.run`
  (30s timeout). Captures stdout, runs through `_rows_to_services`.
- Any `TimeoutExpired` / `FileNotFoundError` → `[]`.

### `_rows_to_services(stdout, node, vmid, kind) -> list[Service]`

The shared output-shaping function — both `discover_via_ssh` and
`discover_via_local` end here. Walks `_parse_ps(stdout)`, builds a
`Service` per row with:

```python
id=f"{node}-{kind.value}-{vmid}-docker-{row.name}"
```

This id format is the one mock_data mirrors (`pve-lxc-100-docker-grafana`)
and is what the frontend's Settings-page "container_id" linker matches
against.

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

- **No retries**: a single SSH attempt; on failure the dispatcher falls
  through to local Docker. Adding retries would compound latency on
  unreachable guests.
- **No caching**: every `/api/services` call re-runs discovery. The
  frontend polls every 10s (`HEALTH_POLL_MS`) — the backend simply runs
  discovery per request. If your PVE host is slow, cache results with a
  short TTL at the `main.get_services` level.
- **Image-name matching is best-effort**: `_icon_hint` works for common
  registries and canonical names; exotic image refs default to `"docker"`.
- **Errors are not propagated**: every strategy catches its own failures
  and returns `[]`. The caller (`main._gather_real_services` logs
  per-guest warnings but doesn't aggregate). Discovery can never throw
  from this module — it can only return a list (possibly empty).
- **SSH uses paramiko**: not stdlib. Required dependency (already in
  `backend/requirements.txt`).
- **Local docker requires either the CLI or the socket**: the local
  fallback will still try `subprocess.run(...)` even if `docker` isn't on
  PATH as long as the socket exists — `subprocess.run` returns
  non-zero/stderr quickly, and we convert to `[]`. This is benign but
  means the socket can produce noise in the backend log on every request.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
