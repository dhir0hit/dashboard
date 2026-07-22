# `backend/app/mock_data.py`

Deterministic mock dataset so `/api/services` and
`/api/services/{id}/health` work without a real Proxmox host. Active when
`Settings.mock == True` (the compose default).

**NOTE**: `MOCK_SERVICES` is intentionally empty — new deployments start with a
blank dashboard. Users add tiles via the Settings page (`POST /api/config/services`).
Mock health data is retained for testing the `/api/services/{id}/health` endpoint.

## Public constants

### `MOCK_SERVICES: list[Service]`

Empty list. Users start with a blank dashboard and add services via the UI.

### `MOCK_HEALTH: dict[str, ServiceHealth]`

Contains a single test entry for demonstration purposes:

| id | healthy | uptime_seconds | last_seen | message |
|---|---|---|---|---|
| test-service-1 | true | 126345 | `2026-07-19T16:45:00Z` | `"ok"` |

## Usage

`main.get_services` returns `ServicesResponse(services=MOCK_SERVICES,
source="mock", count=...)` when `Settings.mock` is true. Since `MOCK_SERVICES`
is empty, mock mode returns an empty service list by default.

`main.get_service_health` looks up `MOCK_HEALTH[service_id]` and returns
404 if not found. Since `MOCK_HEALTH` only contains one test entry,
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
