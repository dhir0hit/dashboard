"""FastAPI application — Proxmox service discovery + dashboard config.

Run:
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Set MOCK=true for offline development (no real Proxmox host needed).
"""
from __future__ import annotations

import json
import logging
import re
import secrets
import subprocess
from typing import Optional
from urllib.parse import quote_plus, urlparse

import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .config_store import init_db, latest, save
from .docker_discover import discover_docker_services
from .mock_data import MOCK_HEALTH, MOCK_SERVICES
from .proxmox import ProxmoxAuthError, ProxmoxClient, ProxmoxError
from .schemas import (
    BackgroundSettings,
    Bookmark,
    BookmarkPatch,
    ConfigSaveResponse,
    CronEntry,
    CronListResponse,
    DashboardConfig,
    ErrorResponse,
    HealthResponse,
    ReorderRequest,
    SearchResponse,
    SearchResult,
    Service,
    ServiceEntry,
    ServiceHealth,
    ServiceStatus,
    ServicesResponse,
    ThemeDefinition,
    ThemeSettings,
    WallpaperItem,
)
from .wallpapers import list_all as list_wallpapers, respond as wallpaper_file, save_upload
from .widgets import get_widget, list_widgets

log = logging.getLogger("dashboard")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="Proxmox Dashboard Backend",
    version="0.1.0",
    description="Service-discovery REST API for an LXC/VM-heavy Proxmox host.",
)
# Allow a frontend on a different origin to hit this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    s = get_settings()
    init_db(s.config_db)
    log.info("Dashboard backend ready (mock=%s, pve=%s)", s.mock, s.proxmox_api_url)


# ---------------------------------------------------------------- discovery
def _gather_real_services() -> tuple[list[Service], str]:
    """Return services from a real PVE host. Raises ProxmoxError on failure."""
    s = get_settings()
    pve = ProxmoxClient(s)
    node = pve.pick_node()
    out: list[Service] = []
    for kind in ("lxc", "qemu"):
        try:
            if kind == "lxc":
                guests = pve.list_lxc(node)
            else:
                guests = pve.list_qemu(node)
        except ProxmoxError as e:
            log.warning("listing %s on node %s failed: %s", kind, node, e)
            continue
        for g in guests:
            vmid = int(g.get("vmid", 0))
            if vmid <= 0:
                continue
            guest_status = str(g.get("status", "")).lower()
            # only running guests can have docker containers
            if guest_status and guest_status not in ("running",):
                continue
            kind_enum = "lxc" if kind == "lxc" else "qemu"
            try:
                svcs = discover_docker_services(s, node, vmid, kind_enum)  # type: ignore[arg-type]
            except Exception as e:  # noqa: BLE001
                log.warning("docker discovery failed for %s %s: %s", kind, vmid, e)
                continue
            out.extend(svcs)
    return out, f"proxmox:{pve.host_label()}"


@app.get(
    "/api/services",
    response_model=ServicesResponse,
    responses={502: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    tags=["services"],
    summary="List all discoverable services across LXC/QEMU guests",
)
def get_services() -> ServicesResponse:
    s = get_settings()
    if s.mock:
        return ServicesResponse(services=MOCK_SERVICES, source="mock", count=len(MOCK_SERVICES))
    if not s.proxmox_api_token:
        raise HTTPException(
            status_code=401,
            detail="PROXMOX_API_TOKEN not set; set MOCK=true for local development",
        )
    try:
        services, source = _gather_real_services()
    except ProxmoxAuthError as e:
        raise HTTPException(status_code=401, detail=f"proxmox auth failed: {e}") from e
    except ProxmoxError as e:
        raise HTTPException(status_code=502, detail=f"proxmox error: {e}") from e
    return ServicesResponse(services=services, source=source, count=len(services))


@app.get(
    "/api/services/{service_id}/health",
    response_model=HealthResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["services"],
)
def get_service_health(service_id: str) -> HealthResponse:
    s = get_settings()
    if s.mock:
        if service_id in MOCK_HEALTH:
            return HealthResponse(health=MOCK_HEALTH[service_id])
        raise HTTPException(status_code=404, detail=f"unknown service id: {service_id}")

    # Real mode: fetch fresh service list and report health for the requested id.
    try:
        services, _ = _gather_real_services()
    except ProxmoxAuthError as e:
        raise HTTPException(status_code=401, detail=f"proxmox auth failed: {e}") from e
    except ProxmoxError as e:
        raise HTTPException(status_code=502, detail=f"proxmox error: {e}") from e

    match = next((x for x in services if x.id == service_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"unknown service id: {service_id}")
    healthy = match.status == ServiceStatus.RUNNING
    return HealthResponse(
        health=ServiceHealth(
            id=match.id,
            status=match.status,
            healthy=healthy,
            uptime_seconds=0,  # not available without per-container docker stats
            last_seen=None,
            message="ok" if healthy else f"container {match.status.value}",
        )
    )


# ----------------------------------------------------------------- config
@app.get("/api/config", response_model=DashboardConfig, tags=["config"])
def get_config() -> DashboardConfig:
    s = get_settings()
    cfg = latest(s.config_db)
    return cfg or DashboardConfig()


@app.post(
    "/api/config",
    response_model=ConfigSaveResponse,
    tags=["config"],
    summary="Persist dashboard layout/config to SQLite",
)
def post_config(cfg: DashboardConfig) -> ConfigSaveResponse:
    s = get_settings()
    rid, updated_at = save(s.config_db, cfg)
    return ConfigSaveResponse(ok=True, id=rid, updated_at=updated_at)


@app.put(
    "/api/config",
    response_model=DashboardConfig,
    tags=["config"],
    summary="Replace the full dashboard config (used by the Settings page)",
)
def put_config(cfg: DashboardConfig) -> DashboardConfig:
    s = get_settings()
    rid, updated_at = save(s.config_db, cfg)
    cfg.updated_at = updated_at
    log.info("config replaced (row %s)", rid)
    return cfg


def _gen_service_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "svc"
    return f"svc-{slug}-{secrets.token_hex(3)}"


@app.post(
    "/api/config/services",
    response_model=ServiceEntry,
    status_code=201,
    tags=["config"],
    summary="Add a dashboard tile (Settings page)",
)
def add_service(entry: ServiceEntry) -> ServiceEntry:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    if not entry.id:
        entry.id = _gen_service_id(entry.name)
    if any(svc.id == entry.id for svc in cfg.services):
        entry.id = f"{entry.id}-{secrets.token_hex(2)}"
    if entry.display_order == 0:
        entry.display_order = len(cfg.services)
    cfg.services.append(entry)
    cfg.services.sort(key=lambda x: x.display_order)
    save(s.config_db, cfg)
    return entry


@app.put(
    "/api/config/services/reorder",
    status_code=204,
    tags=["config"],
    summary="Reorder dashboard tiles (Settings page drag-and-drop)",
)
def reorder_services(req: ReorderRequest) -> None:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    by_id = {sv.id: sv for sv in cfg.services}
    reordered: list[ServiceEntry] = []
    for i, sid in enumerate(req.ordered_ids):
        sv = by_id.get(sid)
        if sv is not None:
            sv.display_order = i
            reordered.append(sv)
    # Append any that were not in ordered_ids (defensive — never drop services).
    seen = set(req.ordered_ids)
    for sv in cfg.services:
        if sv.id not in seen:
            sv.display_order = len(reordered)
            reordered.append(sv)
    cfg.services = reordered
    save(s.config_db, cfg)
    return None


@app.put(
    "/api/config/services/{service_id}",
    response_model=ServiceEntry,
    tags=["config"],
    summary="Edit a dashboard tile (Settings page)",
)
def update_service(service_id: str, patch: ServiceEntry) -> ServiceEntry:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    idx = next((i for i, sv in enumerate(cfg.services) if sv.id == service_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"unknown service id: {service_id}")
    existing = cfg.services[idx]
    patch.id = existing.id  # id is stable across edits
    cfg.services[idx] = patch
    save(s.config_db, cfg)
    return patch


@app.delete(
    "/api/config/services/{service_id}",
    status_code=204,
    tags=["config"],
    summary="Remove a dashboard tile (Settings page)",
)
def delete_service(service_id: str) -> None:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    before = len(cfg.services)
    cfg.services = [sv for sv in cfg.services if sv.id != service_id]
    if len(cfg.services) == before:
        raise HTTPException(status_code=404, detail=f"unknown service id: {service_id}")
    for i, sv in enumerate(cfg.services):
        sv.display_order = i
    save(s.config_db, cfg)
    return None


@app.put(
    "/api/config/background",
    response_model=DashboardConfig,
    tags=["config"],
    summary="Patch background settings (Settings page)",
)
def patch_background(patch: BackgroundSettings) -> DashboardConfig:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    cfg.background = patch
    save(s.config_db, cfg)
    return cfg


@app.put(
    "/api/config/theme",
    response_model=DashboardConfig,
    tags=["config"],
    summary="Patch theme settings (Settings page)",
)
def patch_theme(patch: ThemeSettings) -> DashboardConfig:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    cfg.theme = patch
    save(s.config_db, cfg)
    return cfg


# --------------------------------------------------------------- wallpapers
@app.post(
    "/api/config/wallpaper",
    response_model=WallpaperItem,
    tags=["config"],
    summary="Upload a wallpaper image and return its URL",
)
async def upload_wallpaper(file: UploadFile = File(...)) -> WallpaperItem:
    try:
        fid, name, url = await save_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WallpaperItem(id=fid, url=url, name=name)


@app.get(
    "/api/config/wallpapers",
    response_model=list[WallpaperItem],
    tags=["config"],
    summary="List previously uploaded wallpapers",
)
def list_wallpapers_route() -> list[WallpaperItem]:
    return [WallpaperItem(**w) for w in list_wallpapers()]


@app.get("/wallpapers/{filename}", tags=["config"], include_in_schema=False)
def serve_wallpaper(filename: str):
    try:
        return wallpaper_file(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"wallpaper not found: {filename}") from e


# --------------------------------------------------------------- bookmarks
# Root-task (t_c8aa6b03): bookmarks page — list/add/edit/remove via UI, persisted
# on the same dashboard_config row as services/theme/background.


def _gen_bookmark_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "bm").lower()).strip("-") or "bm"
    return f"bm-{slug}-{secrets.token_hex(3)}"


@app.get(
    "/api/config/bookmarks",
    response_model=list[Bookmark],
    tags=["bookmarks"],
    summary="List saved bookmarks",
)
def list_bookmarks() -> list[Bookmark]:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    return cfg.bookmarks


@app.post(
    "/api/config/bookmarks",
    response_model=Bookmark,
    status_code=201,
    tags=["bookmarks"],
    summary="Add a bookmark",
)
def add_bookmark(entry: Bookmark) -> Bookmark:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    if not entry.id:
        entry.id = _gen_bookmark_id(entry.title)
    if any(b.id == entry.id for b in cfg.bookmarks):
        entry.id = f"{entry.id}-{secrets.token_hex(2)}"
    if entry.display_order == 0:
        entry.display_order = len(cfg.bookmarks)
    cfg.bookmarks.append(entry)
    cfg.bookmarks.sort(key=lambda x: x.display_order)
    save(s.config_db, cfg)
    return entry


@app.put(
    "/api/config/bookmarks/{bookmark_id}",
    response_model=Bookmark,
    tags=["bookmarks"],
    summary="Edit a bookmark",
)
def update_bookmark(bookmark_id: str, patch: BookmarkPatch) -> Bookmark:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    idx = next((i for i, b in enumerate(cfg.bookmarks) if b.id == bookmark_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"unknown bookmark id: {bookmark_id}")
    existing = cfg.bookmarks[idx]
    data = existing.model_dump()
    for k, v in patch.model_dump(exclude_unset=True).items():
        if v is not None:
            data[k] = v
    cfg.bookmarks[idx] = Bookmark(**data)
    save(s.config_db, cfg)
    return cfg.bookmarks[idx]


@app.delete(
    "/api/config/bookmarks/{bookmark_id}",
    status_code=204,
    tags=["bookmarks"],
    summary="Remove a bookmark",
)
def delete_bookmark(bookmark_id: str) -> None:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    before = len(cfg.bookmarks)
    cfg.bookmarks = [b for b in cfg.bookmarks if b.id != bookmark_id]
    if len(cfg.bookmarks) == before:
        raise HTTPException(status_code=404, detail=f"unknown bookmark id: {bookmark_id}")
    for i, b in enumerate(cfg.bookmarks):
        b.display_order = i
    save(s.config_db, cfg)
    return None


# ------------------------------------------------------------- custom themes
# Root-task (t_c8aa6b03): "add more themes later via UI menu".


@app.get(
    "/api/config/themes",
    response_model=list[ThemeDefinition],
    tags=["themes"],
    summary="List custom user-defined themes",
)
def list_custom_themes() -> list[ThemeDefinition]:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    return cfg.custom_themes


@app.post(
    "/api/config/themes",
    response_model=ThemeDefinition,
    status_code=201,
    tags=["themes"],
    summary="Add a custom theme",
)
def add_custom_theme(theme: ThemeDefinition) -> ThemeDefinition:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    if not theme.id:
        slug = re.sub(r"[^a-z0-9]+", "-", theme.name.lower()).strip("-") or "theme"
        theme.id = f"{slug}-{secrets.token_hex(3)}"
    if any(t.id == theme.id for t in cfg.custom_themes):
        theme.id = f"{theme.id}-{secrets.token_hex(2)}"
    cfg.custom_themes.append(theme)
    save(s.config_db, cfg)
    return theme


@app.delete(
    "/api/config/themes/{theme_id}",
    status_code=204,
    tags=["themes"],
    summary="Remove a custom theme",
)
def delete_custom_theme(theme_id: str) -> None:
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    before = len(cfg.custom_themes)
    cfg.custom_themes = [t for t in cfg.custom_themes if t.id != theme_id]
    if len(cfg.custom_themes) == before:
        raise HTTPException(status_code=404, detail=f"unknown theme id: {theme_id}")
    save(s.config_db, cfg)
    return None


# --------------------------------------------------------------- search proxy
# Root-task (t_c8aa6b03): "search menu with duckduckgo and search web directly".
# Server-side proxy so we avoid browser CORS and can normalize results.


@app.get(
    "/api/search",
    response_model=SearchResponse,
    tags=["search"],
    summary="DuckDuckGo HTML search proxy (server-side, CORS-free)",
)
def search(query: str = Query(..., min_length=1)) -> SearchResponse:
    q = query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="empty query")
    ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
    results: list[SearchResult] = []
    try:
        resp = httpx.get(ddg_url, timeout=10.0, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        })
        text = resp.text
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"search proxy error: {e}") from e
    # Parse DuckDuckGo HTML results. Result anchors: result__a with uddg= redirect.
    snippets = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    from urllib.parse import unquote
    for href, raw_title in snippets:
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#x27;", "'"), ("&#39;", "'")):
            title = title.replace(ent, ch)
        href = href.replace("&amp;", "&")
        m = re.search(r"uddg=([^&]+)", href)
        if not m:
            continue
        u = unquote(m.group(1))
        try:
            host = urlparse(u).netloc
            favicon = f"https://icons.duckduckgo.com/ip3/{host}.ico" if host else None
        except Exception:
            favicon = None
        results.append(SearchResult(title=title or u, url=u, snippet="", favicon=favicon))
    return SearchResponse(query=q, engine="duckduckgo-html", results=results[:30])


# ---------------------------------------------------------------------- cron
# Root-task (t_c8aa6b03): "add a calendar and sync it with hermes agent cron jobs".
# Shells out to `hermes cronjob list --json` when available; otherwise returns
# a stub list so the UI demoes cleanly.


@app.get(
    "/api/cron",
    response_model=CronListResponse,
    tags=["cron"],
    summary="List Hermes cron jobs for the calendar",
)
def list_cron() -> CronListResponse:
    try:
        proc = subprocess.run(
            ["hermes", "cronjob", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=8.0,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CronListResponse(jobs=[], source="stub", count=0)
    if proc.returncode != 0 or not proc.stdout.strip():
        return CronListResponse(jobs=[], source="stub", count=0)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return CronListResponse(jobs=[], source="stub", count=0)
    # Accept either a list or an object with jobs/items/data.
    items: list[dict] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for k in ("jobs", "items", "data"):
            if isinstance(data.get(k), list):
                items = data[k]
                break
    jobs: list[CronEntry] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        jobs.append(
            CronEntry(
                id=str(it.get("id") or it.get("job_id") or it.get("name") or ""),
                name=it.get("name"),
                schedule=it.get("schedule") or it.get("cron"),
                enabled=bool(it.get("enabled", True)),
                next_run=it.get("next_run") or it.get("next_fire"),
                last_run=it.get("last_run") or it.get("last_fire") or it.get("last_output"),
                description=it.get("description") or it.get("prompt"),
            )
        )
    return CronListResponse(jobs=jobs, source="hermes-cli", count=len(jobs))


# ------------------------------------------------------------- widgets
# Widget registry + auto-login. POST /api/tiles/{id}/auth performs the service's
# login API call server-side using the credentials stored on the tile, then
# returns the cookies/token the user's browser needs so the click-through tile
# link opens an already-authenticated session.

@app.get(
    "/api/widgets",
    response_model=list[dict],
    tags=["widgets"],
    summary="List all known widget types in the registry",
)
def widgets_list() -> list[dict]:
    return list_widgets()


@app.get(
    "/api/widgets/{widget_id}",
    response_model=dict,
    tags=["widgets"],
    summary="Fetch a single widget definition",
)
def widgets_get(widget_id: str) -> dict:
    w = get_widget(widget_id)
    if not w:
        raise HTTPException(status_code=404, detail=f"unknown widget id: {widget_id}")
    return w


def _normalize_base(url: str) -> str:
    u = url.rstrip("/")
    return u if u else url


@app.post(
    "/api/tiles/{service_id}/auth",
    tags=["tiles"],
    summary="Perform the underlying service's login on behalf of the user",
)
def tile_login(service_id: str):
    """Server-side login for a tile.

    Loads the tile by id from the SQLite config, looks up its widget_type in the
    registry, and performs the appropriate login call against api_url using the
    stored credentials. Returns either a list of cookie strings that the
    frontend should set via `document.cookie` before redirecting, or a custom
    authorization header the frontend should pass when opening the tile URL.

    Responses:
        200 — `{method, cookies?, header?, redirect_url, message}` on success.
        400 — widget_type missing, no api_url, or unsupported auth_schema.
        404 — tile id unknown.
        502 — upstream service unreachable or non-2xx login response.
    """
    s = get_settings()
    cfg = latest(s.config_db) or DashboardConfig()
    entry = next((e for e in cfg.services if e.id == service_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"unknown tile id: {service_id}")
    if not entry.widget_type:
        raise HTTPException(
            status_code=400,
            detail="tile has no widget_type; nothing to auto-login to",
        )
    widget = get_widget(entry.widget_type)
    if widget is None:
        raise HTTPException(
            status_code=400,
            detail=f"unknown widget_type: {entry.widget_type}",
        )
    base_url = _normalize_base(entry.api_url or entry.url or "")
    if not base_url:
        raise HTTPException(status_code=400, detail="tile has no api_url or url to log in to")
    schema = widget.get("auth_schema", "none")
    if schema == "none":
        return {"method": "none", "redirect_url": base_url, "message": "no auth needed"}

    login_path = widget.get("login_path") or ""
    target = f"{base_url}{login_path}"

    try:
        if schema == "api_key":
            if not entry.api_key:
                raise HTTPException(status_code=400, detail="api_key required for this widget")
            header_fmt = widget.get("auth_header_format") or "Bearer {token}"
            header_value = header_fmt.replace("{token}", entry.api_key)
            # Split into header name/value if the template includes a colon
            # (e.g. "X-Api-Key: abc"), else synthesize Authorization.
            if ":" in header_fmt and not header_fmt.startswith("Bearer"):
                name, _, value = header_value.partition(":")
                headers = {name.strip(): value.strip()}
            else:
                headers = {"Authorization": header_value}
            resp = httpx.post(target, headers=headers, timeout=10.0)
        elif schema == "basic":
            if not entry.username or entry.password is None:
                raise HTTPException(
                    status_code=400,
                    detail="username + password required for this widget",
                )
            resp = httpx.post(
                target,
                auth=(entry.username, entry.password),
                timeout=10.0,
            )
        elif schema == "form":
            if not entry.username or entry.password is None:
                raise HTTPException(
                    status_code=400,
                    detail="username + password required for this widget",
                )
            template = widget.get("login_form_template") or "username={username}&password={password}"
            body = template.format(username=entry.username, password=entry.password)
            resp = httpx.post(
                target,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        else:
            raise HTTPException(status_code=400, detail=f"unsupported auth_schema: {schema}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"login upstream error: {e}") from e

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"login failed: upstream returned {resp.status_code}: {resp.text[:200]}",
        )

    # Pull Set-Cookie headers (may be multiple). The browser will set these
    # via document.cookie on the response handler.
    cookies = resp.headers.get_list("Set-Cookie") if hasattr(resp.headers, "get_list") else []
    return {
        "method": schema,
        "cookies": cookies,
        "redirect_url": base_url,
        "message": f"logged in via {schema}",
    }


# ------------------------------------------------------------- health root
@app.get("/health", tags=["meta"])
def root_health() -> dict:
    s = get_settings()
    return {"ok": True, "mock": s.mock, "pve": s.proxmox_api_url}


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "Proxmox Dashboard Backend",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": [
            "/api/services",
            "/api/services/{id}/health",
            "/api/config",
            "/api/config/bookmarks",
            "/api/config/themes",
            "/api/search",
            "/api/cron",
            "/health",
        ],
    }