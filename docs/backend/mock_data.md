# `backend/app/mock_data.py`

Deterministic mock dataset so `/api/services` and
`/api/services/{id}/health` work without a real Proxmox host. Active when
`Settings.mock == True` (the compose default).

## Public constants

### `MOCK_SERVICES: list[Service]`

Three hardcoded `Service` objects representing a typical *arr stack, each
with a distinct status so the UI exercises every code path:

| id | name | node | vmid | kind | status | image | ports | icon_hint |
|---|---|---|---|---|---|---|---|---|
| `pve-lxc-100-docker-sonarr` | sonarr | pve | 100 | lxc | running | `lscr.io/linuxserver/sonarr:latest` | `:8989` | sonarr |
| `pve-lxc-100-docker-radarr` | radarr | pve | 100 | lxc | running | `lscr.io/linuxserver/radarr:latest` | `:7878` | radarr |
| `pve-lxc-101-docker-lidarr` | lidarr | pve | 101 | lxc | stopped | `lscr.io/linuxserver/lidarr:latest` | `:8686` | lidarr |

### `MOCK_HEALTH: dict[str, ServiceHealth]`

Built via a dict comprehension over every entry in `MOCK_SERVICES`, so
**all 3 services have health entries** (not 2 — the comprehension
includes every service regardless of status).

```python
MOCK_HEALTH = {
    s.id: ServiceHealth(
        id=s.id,
        status=s.status,
        healthy=(s.status == ServiceStatus.RUNNING),
        uptime_seconds=126345 if s.status == ServiceStatus.RUNNING else 0,
        last_seen="2026-07-19T16:45:00Z"
                   if s.status == ServiceStatus.RUNNING else None,
        message="ok" if s.status == ServiceStatus.RUNNING
                else "container stopped",
    )
    for s in MOCK_SERVICES
}
```

| id | healthy | uptime_seconds | last_seen | message |
|---|---|---|---|---|
| sonarr | true | 126345 | `2026-07-19T16:45:00Z` | `"ok"` |
| radarr | true | 126345 | `2026-07-19T16:45:00Z` | `"ok"` |
| lidarr | false | 0 | `None` | `"container stopped"` |

## Usage

`main.get_services` returns `ServicesResponse(services=MOCK_SERVICES,
source="mock", count=...)` when `Settings.mock` is true.

`main.get_service_health` looks up `MOCK_HEALTH[service_id]` and returns
404 if not found. Since `MOCK_HEALTH` is keyed on every service's id,
unknown ids always come from a typo or a stale client link — the frontend
treats 404 as "container not discovered" and shows the unlinked state.

## Conventions

- **Stable ids**: the ids are deliberately named
  `<node>-<kind>-<vmid>-docker-<name>` to match the shape real discovery
  produces. This means the frontend's Settings-page "container_id" linker
  dropdown works unchanged in mock mode.
- **No randomness**: the dataset is fixed at module load. Every
  `_gather_real_services` call in mock mode sees the same three services
  and the same health entries. `uptime_seconds` is `126_345` (~1.5 days)
  for running services — a stable value, not "seconds since boot".
- **`last_seen` is a constant timestamp**: `2026-07-19T16:45:00Z`. Any
  test asserting on "N seconds ago" formatting would need to mock or
  freeze time, since the timestamp doesn't age.
- **Not a fixture, a module constant**: mock data lives at module scope,
  so import-time cost is negligible. There is no way to inject a custom
  mock dataset — to swap it, edit this file or extend `config.py` with
  a `MockOverrides` setting.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
