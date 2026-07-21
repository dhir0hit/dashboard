# `backend/app/proxmox.py`

Thin httpx-based client for the Proxmox VE REST API. Token-auth, query-only,
returns the raw JSON PVE returns (already dict-shaped via httpx's
`.json()` -> extracted `data` field).

## Public classes

### `ProxmoxError(Exception)`

Generic Proxmox client error (network, parse, unexpected). The FastAPI
layer turns this into HTTP 502.

### `ProxmoxAuthError(ProxmoxError)`

Raised for HTTP 401/403 from PVE — bad token, revoked token, or
insufficient privileges. The FastAPI layer turns this into HTTP 401.

### `ProxmoxClient`

#### Constructor

```python
ProxmoxClient(settings: Settings)
```

Stores the settings and reads `settings.auth_header` (the prepared
`Authorization: PVEAPIToken=...` header). Does no token validation itself
— token format/error reporting is delegated to `Settings` (see
`config.md`). Any malformed token surfaces as a 401 from PVE on the first
request, which the client converts to `ProxmoxAuthError`.

#### Instance methods

##### `_request(method, path, **kw) -> Any`

Private HTTP core. Builds the URL from `settings.base_url`, opens an
`httpx.Client` with a **20s** timeout and `verify=settings.proxmox_verify_tls`,
sends the request with the token header, then:

- 401/403 → `ProxmoxAuthError(f"PVE rejected auth ({status}): {body[:200]}")`.
- >= 400 → `ProxmoxError(f"PVE {status}: {body[:200]}")`.
- Otherwise → `r.json().get("data", {})` (PVE wraps every response in
  `{"data": ...}`).
- Bad JSON → `ProxmoxError(f"bad JSON from PVE: {err}")`.

##### `list_nodes() -> list[dict]`

`GET /nodes` — returns the raw `data` array of node objects (each has
`node`, `status`, etc.) or `[]` if no nodes.

##### `pick_node() -> str`

- If `settings.proxmox_node` is set, returns it directly (no validation).
- Otherwise calls `list_nodes()` and returns the first online node
  (`status == "online"`); falls back to the first node if none are
  online. Raises `ProxmoxError("no PVE nodes discovered")` when the list
  is empty.

##### `list_lxc(node: str) -> list[dict]`

`GET /nodes/{node}/lxc` — raw guest dicts. Empty list when null.

##### `list_qemu(node: str) -> list[dict]`

`GET /nodes/{node}/qemu` — raw VM dicts. Empty list when null.

##### `guest_status(node, vmid, kind: str) -> dict`

`GET /nodes/{node}/{kind}/{vmid}/status/current`. `kind` is `"lxc"` or
`"qemu"`. Returns the live guest status object (or `{}` on null).

##### `pct_exec(node, vmid, command: list[str]) -> str`

Runs a command inside an LXC container via PVE's `/nodes/{node}/lxc/{vmid}/exec`
endpoint. POSTs `{"command": command}`. Uses an extended **60s** timeout
(docker ps can be slow on busy guests).

**Note**: PVE's REST `/exec` endpoint returns a task UPID, not stdout —
this method returns `r.text` (the UPID), and stdout streaming via the
simple REST path isn't implemented here. Real in-guest discovery uses SSH
or the local Docker socket via `docker_discover.py`; `pct_exec` is only
useful for one-shot probes, not discovery. If `vmid <= 0`, raises
`ProxmoxError("pct_exec requires a positive vmid")`.

##### `ping() -> bool`

Best-effort reachability check via `list_nodes()`. Returns `True` on
success, `False` on any `ProxmoxError` (including auth failures —
unauthorized is still "reachable"). Never raises.

##### `host_label() -> str`

Returns `urlparse(settings.proxmox_api_url).hostname` or `"pve"` on any
parsing exception. The returned string feeds into `ServicesResponse.source`
as `"proxmox:<host_label>"` (e.g. `"proxmox:pve-router.lan"`).

## Notable details

- **No token parsing in the client**: the client trusts `settings.auth_header`
  to be well-formed. Any malformed `PROXMOX_API_TOKEN` surfaces at the
  Settings layer (see `config.md`).
- **TLS verification defaults off** (`Settings.proxmox_verify_tls=False`)
  — typical for homelab PVE with a self-signed cert. Flip
  `PROXMOX_VERIFY_TLS=true` with a real CA cert in production.
- **`httpx.Client` opened per request** (no shared session). Each `_request`
  call constructs a client, sends, and closes it via `with`. Simpler than
  thread-local session management; acceptable for low request volume. If
  you scale beyond single-instance uvicorn workers, pool the client.
- **No retries**: every HTTP call is a single attempt. PVE is fast and
  local in typical deployments; retries on 5xx would mask real config
  errors.
- **Errors are typed**: the FastAPI layer in `main.py` catches
  `ProxmoxAuthError` and `ProxmoxError` separately so auth failures map
  to 401 and other PVE errors to 502 — the frontend can show
  "auth failed, check token" vs "PVE host unreachable" distinctly.
- **`pct_exec` is a stub for discovery**: PVE's REST exec endpoint
  returns a UPID, not stdout. `docker_discover._discover_via_pct_exec`
  (when it exists) uses SSH for actual stdout retrieval. The `pct_exec`
  method here is useful for status probes that return JSON, not for
  shell-out discovery.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
