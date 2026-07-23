"""Widget registry — known service types the dashboard can display.

Each widget defines:
- id: stable identifier used in `ServiceEntry.widget_type`
- name: display name for the settings dropdown
- icon_hint: matches an entry in the frontend's ICON_HINT_TO_EMOJI map (best-effort)
- auth_schema: which credential fields this widget uses
    - "api_key"     → api_url + api_key (Bearer/Token header)
    - "basic"       → api_url + username + password (HTTP Basic)
    - "form"        → api_url + username + password (form-encoded POST)
    - "none"        → no credentials, just link out
- login_path: URL path appended to api_url where login is performed
- auth_header_format: optional template; {token} is replaced with api_key
- login_form_template: optional template; {username} and {password} are
  substituted for form-post widgets. Field names are widget-specific
  (e.g. Grafana uses `user`+`password`; qBittorrent uses `username`+`password`).

The registry is intentionally small and hackable — add a new widget by
appending to WIDGET_REGISTRY below. Frontend reads the list via
`GET /api/widgets` and switches its form fields based on `auth_schema`.
"""
from __future__ import annotations

from typing import Any


WIDGET_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "generic",
        "name": "Generic link",
        "icon_hint": "link",
        "auth_schema": "none",
        "login_path": None,
        "description": "Just a link; no credentials. Used for non-authenticated services.",
    },
    {
        "id": "grafana",
        "name": "Grafana",
        "icon_hint": "grafana",
        "auth_schema": "form",
        "login_path": "/login",
        "login_form_template": "user={username}&password={password}",
        "description": "Open-source analytics & monitoring. Uses form login with `user` + `password`.",
    },
    {
        "id": "prometheus",
        "name": "Prometheus",
        "icon_hint": "prometheus",
        "auth_schema": "none",
        "login_path": None,
        "description": "Time-series DB. Native UI has no auth (use a reverse proxy for that).",
    },
    {
        "id": "proxmox",
        "name": "Proxmox VE",
        "icon_hint": "proxmox",
        "auth_schema": "api_key",
        "login_path": "/api2/json/access",
        "auth_header_format": "PVEAPIToken={token}",
        "description": "PVE API token. The dashboard already uses this for discovery; set it here per-tile to deep-link with auth.",
    },
    {
        "id": "portainer",
        "name": "Portainer",
        "icon_hint": "portainer",
        "auth_schema": "api_key",
        "login_path": "/api/auth",
        "auth_header_format": "Bearer {token}",
        "description": "Container management UI. Generate a PAT in Portainer → User → My Account → Access tokens.",
    },
    {
        "id": "qbit_torrent",
        "name": "qBittorrent",
        "icon_hint": "qbittorrent",
        "auth_schema": "form",
        "login_path": "/api/v2/auth/login",
        "login_form_template": "username={username}&password={password}",
        "description": "BitTorrent client web UI. Form login with `username`+`password`.",
    },
    {
        "id": "sonarr",
        "name": "Sonarr",
        "icon_hint": "sonarr",
        "auth_schema": "api_key",
        "login_path": "/api/v3/login",
        "auth_header_format": "X-Api-Key: {token}",
        "description": "TV show manager. Use the API key from Settings → General → API Key.",
    },
    {
        "id": "radarr",
        "name": "Radarr",
        "icon_hint": "radarr",
        "auth_schema": "api_key",
        "login_path": "/api/v3/login",
        "auth_header_format": "X-Api-Key: {token}",
        "description": "Movie manager. Same API key flow as Sonarr.",
    },
    {
        "id": "transmission",
        "name": "Transmission",
        "icon_hint": "transmission",
        "auth_schema": "basic",
        "login_path": "/transmission/rpc",
        "description": "BitTorrent client. HTTP Basic auth.",
    },
    {
        "id": "pihole",
        "name": "Pi-hole",
        "icon_hint": "pihole",
        "auth_schema": "api_key",
        "login_path": "/admin/api.php",
        "auth_header_format": "Bearer {token}",
        "description": "DNS sinkhole. Use the web password from Settings → API.",
    },
    {
        "id": "homeassistant",
        "name": "Home Assistant",
        "icon_hint": "home-assistant",
        "auth_schema": "api_key",
        "login_path": "/api/",
        "auth_header_format": "Bearer {token}",
        "description": "Home automation. Long-lived access token from your profile page.",
    },
    {
        "id": "adguard",
        "name": "AdGuard Home",
        "icon_hint": "adguard",
        "auth_schema": "basic",
        "login_path": "/control/status",
        "description": "DNS sinkhole. HTTP Basic auth with your AdGuard credentials.",
    },
    {
        "id": "nginxproxymanager",
        "name": "Nginx Proxy Manager",
        "icon_hint": "nginx",
        "auth_schema": "form",
        "login_path": "/api/tokens",
        "login_form_template": "identity={username}&secret={password}",
        "description": "Reverse proxy UI. Form login with `identity`+`secret`.",
    },
    {
        "id": "uptimekuma",
        "name": "Uptime Kuma",
        "icon_hint": "uptime-kuma",
        "auth_schema": "none",
        "login_path": None,
        "description": "Self-hosted monitoring. No standard login API; click-through opens the UI.",
    },
    # ── NAS / media stack (lidarr + *arr family + download clients) ─────────
    {
        "id": "lidarr",
        "name": "Lidarr",
        "icon_hint": "lidarr",
        "auth_schema": "api_key",
        "login_path": "/api/v1/system/status",
        "auth_header_format": "X-Api-Key: {token}",
        "description": "Music manager. Use the API key from Settings → General → API Key.",
    },
    {
        "id": "prowlarr",
        "name": "Prowlarr",
        "icon_hint": "prowlarr",
        "auth_schema": "api_key",
        "login_path": "/api/v1/system/status",
        "auth_header_format": "X-Api-Key: {token}",
        "description": "Indexer manager for the *arr stack. API key from Settings → General → API Key.",
    },
    {
        "id": "readarr",
        "name": "Readarr",
        "icon_hint": "readarr",
        "auth_schema": "api_key",
        "login_path": "/api/v1/system/status",
        "auth_header_format": "X-Api-Key: {token}",
        "description": "eBook/audiobook manager. Same API key flow as Sonarr/Radarr.",
    },
    {
        "id": "overseerr",
        "name": "Overseerr",
        "icon_hint": "overseerr",
        "auth_schema": "api_key",
        "login_path": "/api/v1/auth/me",
        "auth_header_format": "X-Api-Key: {token}",
        "description": "Request management for Plex/Jellyfin. API key from Settings → General.",
    },
    {
        "id": "bazarr",
        "name": "Bazarr",
        "icon_hint": "bazarr",
        "auth_schema": "basic",
        "login_path": "/api/system/status",
        "description": "Subtitle manager (companion to Sonarr/Radarr). HTTP Basic auth.",
    },
    {
        "id": "sabnzbd",
        "name": "SABnzbd",
        "icon_hint": "sabnzbd",
        "auth_schema": "api_key",
        "login_path": "/api",
        "auth_header_format": "Authorization: {token}",
        "description": "Usenet downloader. Use the API key from Config → General → API Key.",
    },
    {
        "id": "deluge",
        "name": "Deluge",
        "icon_hint": "deluge",
        "auth_schema": "basic",
        "login_path": "/json",
        "description": "BitTorrent client. HTTP Basic auth with the Web UI credentials.",
    },
    {
        "id": "unraid",
        "name": "Unraid",
        "icon_hint": "unraid",
        "auth_schema": "basic",
        "login_path": "/api/v1/",
        "description": "Unraid NAS OS. HTTP Basic auth with your Unraid credentials.",
    },
    {
        "id": "truenas",
        "name": "TrueNAS",
        "icon_hint": "truenas",
        "auth_schema": "api_key",
        "login_path": "/api/v2.0/system/info",
        "auth_header_format": "Authorization: Bearer {token}",
        "description": "TrueNAS SCALE/Enterprise REST API. API token from System Settings → API Keys.",
    },
    {
        "id": "synology",
        "name": "Synology DSM",
        "icon_hint": "synology",
        "auth_schema": "form",
        "login_path": "/webapi/auth.cgi",
        "login_form_template": "account={username}&passwd={password}&api=SYNO.API.Auth&version=6&method=login",
        "description": "Synology NAS DSM. Form login with your DSM account + password.",
    },
    {
        "id": "jellyfin",
        "name": "Jellyfin",
        "icon_hint": "jellyfin",
        "auth_schema": "api_key",
        "login_path": "/Users/Me",
        "auth_header_format": "Authorization: {token}",
        "description": "Media server. Use a long-lived API token from your Jellyfin profile.",
    },
    {
        "id": "plex",
        "name": "Plex",
        "icon_hint": "plex",
        "auth_schema": "api_key",
        "login_path": "/api/v2/user",
        "auth_header_format": "X-Plex-Token: {token}",
        "description": "Media server. Use a Plex auth token from your account.",
    },
    {
        "id": "navidrome",
        "name": "Navidrome",
        "icon_hint": "navidrome",
        "auth_schema": "basic",
        "login_path": "/api",
        "description": "Music server (Subsonic-compatible). HTTP Basic auth with your ND credentials.",
    },
    {
        "id": "nextcloud",
        "name": "Nextcloud",
        "icon_hint": "nextcloud",
        "auth_schema": "basic",
        "login_path": "/ocs/v1.php/cloud/capabilities",
        "description": "Self-hosted cloud. HTTP Basic auth with your Nextcloud credentials.",
    },
    {
        "id": "vaultwarden",
        "name": "Vaultwarden",
        "icon_hint": "vaultwarden",
        "auth_schema": "form",
        "login_path": "/api/accounts/prelogin",
        "login_form_template": "email={username}",
        "description": "Bitwarden-compatible password manager. Pre-login probe (email only).",
    },
    {
        "id": "gitea",
        "name": "Gitea",
        "icon_hint": "gitea",
        "auth_schema": "basic",
        "login_path": "/api/v1/user",
        "description": "Lightweight Git server. HTTP Basic auth with username + token.",
    },
    {
        "id": "immich",
        "name": "Immich",
        "icon_hint": "immich",
        "auth_schema": "api_key",
        "login_path": "/api/users/me",
        "auth_header_format": "x-api-key: {token}",
        "description": "Self-hosted photo/video backup. API key from Settings → API Keys.",
    },
    {
        "id": "paperlessngx",
        "name": "Paperless-ngx",
        "icon_hint": "paperless",
        "auth_schema": "form",
        "login_path": "/api/token/",
        "login_form_template": "username={username}&password={password}",
        "description": "Document management. Form login returns a JWT token for API access.",
    },
]


def list_widgets() -> list[dict[str, Any]]:
    """Public accessor — returned by GET /api/widgets."""
    return [dict(w) for w in WIDGET_REGISTRY]


def get_widget(widget_type: str | None) -> dict[str, Any] | None:
    """Look up a single widget by id. Returns None if missing or input is None."""
    if not widget_type:
        return None
    return next((w for w in WIDGET_REGISTRY if w["id"] == widget_type), None)


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE INFO — live, action-oriented stats from each service's own API.
#
# Each parser returns a flat dict of {label_key: value} pairs that the
# frontend renders in the ServiceInfoBlock.  The keys map to human-readable
# labels via the INFO_LABELS dict on the frontend.
#
# Design principles:
#   - Show what matters to the user: download/upload speeds, queue depth,
#     active streams, requests, blocked ads, etc.
#   - NEVER show version, server name, IDs, or other metadata — those
#     aren't actionable.
#   - Keep it to ~4-6 fields so the tile card stays compact.
# ══════════════════════════════════════════════════════════════════════════════

import httpx as _httpx


# ── *arr stack (Sonarr, Radarr, Lidarr, Readarr) ─────────────────────────────

def _sonarr_info(resp: dict, widget: dict) -> dict:
    """Sonarr: show missing episodes + queue count + wanted episodes."""
    out: dict[str, Any] = {}
    # /api/v3/wanted/missing returns total records
    if "totalRecords" in resp:
        out["missing_episodes"] = resp["totalRecords"]
    return out


def _radarr_info(resp: dict, widget: dict) -> dict:
    """Radarr: show missing movies + queue count."""
    out: dict[str, Any] = {}
    if "totalRecords" in resp:
        out["missing_movies"] = resp["totalRecords"]
    return out


def _lidarr_info(resp: dict, widget: dict) -> dict:
    """Lidarr: show missing albums + artist count + queue."""
    out: dict[str, Any] = {}
    if "totalRecords" in resp:
        out["missing_albums"] = resp["totalRecords"]
    return out


def _readarr_info(resp: dict, widget: dict) -> dict:
    """Readarr: show missing books + queue."""
    out: dict[str, Any] = {}
    if "totalRecords" in resp:
        out["missing_books"] = resp["totalRecords"]
    return out


def _prowlarr_info(resp: dict, widget: dict) -> dict:
    """Prowlarr: show indexer count + indexer health."""
    out: dict[str, Any] = {}
    if "totalRecords" in resp:
        out["indexers"] = resp["totalRecords"]
    return out


# ── Download clients ──────────────────────────────────────────────────────────

def _qbittorrent_info(resp: dict, _widget: dict) -> dict:
    """qBittorrent: show DL/UL speed + active torrents + leech/seeds."""
    out: dict[str, Any] = {}
    dl = resp.get("dl_info", {})
    up = resp.get("up_info", {})
    out["download_speed"] = dl.get("speed", 0)
    out["upload_speed"] = up.get("speed", 0)
    return out


def _transmission_info(resp: dict, _widget: dict) -> dict:
    """Transmission: DL/UL speed + torrent count."""
    args = resp.get("arguments", resp)
    out: dict[str, Any] = {}
    out["download_speed"] = args.get("downloadSpeed", 0)
    out["upload_speed"] = args.get("uploadSpeed", 0)
    out["torrents"] = args.get("torrentCount", 0)
    return out


def _sabnzbd_info(resp: dict, _widget: dict) -> dict:
    """SABnzbd: queue length + queue size + download speed."""
    out: dict[str, Any] = {}
    if "queue" in resp:
        q = resp["queue"]
        out["queue"] = int(q.get("noofslots", 0))
        out["queue_size_mb"] = float(q.get("size", "0").replace(" ", ""))
        out["download_speed"] = int(q.get("speed", "0").replace(" ", "").split(".")[0] if isinstance(q.get("speed"), str) else q.get("speed", 0))
    if "history" in resp:
        out["downloaded"] = int(resp["history"].get("noofslots", 0))
    return out


def _deluge_info(resp: dict, _widget: dict) -> dict:
    """Deluge: DL/UL speed + torrent count."""
    out: dict[str, Any] = {}
    stats = resp.get("stats", resp)
    out["download_speed"] = int(stats.get("download_rate", 0))
    out["upload_speed"] = int(stats.get("upload_rate", 0))
    out["torrents"] = int(stats.get("num_torrents", 0))
    return out


# ── DNS sinkholes ──────────────────────────────────────────────────────────────

def _pihole_info(resp: dict, _widget: dict) -> dict:
    """Pi-hole: queries today + ads blocked + block %."""
    out: dict[str, Any] = {}
    out["queries_today"] = resp.get("dns_queries_today", 0)
    out["ads_blocked"] = resp.get("ads_blocked_today", 0)
    out["block_pct"] = round(resp.get("ads_percentage_today", 0), 1)
    out["domains_blocked"] = resp.get("domains_being_blocked", 0)
    return out


def _adguard_info(resp: dict, _widget: dict) -> dict:
    """AdGuard: DNS queries + blocked + block %."""
    out: dict[str, Any] = {}
    out["queries"] = resp.get("numDnsQueries", 0)
    out["blocked"] = resp.get("numBlockedFiltering", 0)
    out["block_pct"] = round(resp.get("ratioFastFiltering", 0) * 100, 1)
    return out


# ── Monitoring ────────────────────────────────────────────────────────────────

def _grafana_info(resp: dict, _widget: dict) -> dict:
    """Grafana: dashboards + users + alerts."""
    out: dict[str, Any] = {}
    out["dashboards"] = resp.get("dashboards", 0)
    out["users"] = resp.get("users", 0)
    out["alerts"] = resp.get("alerts", 0)
    return out


def _prometheus_info(resp: dict, _widget: dict) -> dict:
    """Prometheus: active series + status."""
    out: dict[str, Any] = {}
    data = resp.get("data", {})
    out["active_series"] = data.get("activeSeries", 0)
    return out


def _uptimekuma_info(resp: dict, _widget: dict) -> dict:
    """Uptime Kuma: monitors up/down/paused."""
    out: dict[str, Any] = {}
    if "stats" in resp:
        stats = resp["stats"]
        out["up"] = stats.get("up", 0)
        out["down"] = stats.get("down", 0)
        out["paused"] = stats.get("paused", 0)
    return out


# ── Container / infrastructure ────────────────────────────────────────────────

def _portainer_info(resp: dict, _widget: dict) -> dict:
    """Portainer: endpoint count + running/stopped containers."""
    if isinstance(resp, list):
        return {
            "endpoints": len(resp),
            "running": sum(1 for e in resp if e.get("Status", 0) == 1),
            "stopped": sum(1 for e in resp if e.get("Status", 0) == 0),
        }
    return {}


def _nginxproxymanager_info(resp: dict, _widget: dict) -> dict:
    """NPM: proxy host count."""
    if isinstance(resp, list):
        return {"proxy_hosts": len(resp)}
    return {}


def _truenas_info(resp: dict, _widget: dict) -> dict:
    """TrueNAS: pool/dataset usage + uptime."""
    out: dict[str, Any] = {}
    out["uptime"] = resp.get("uptime_seconds", 0)
    load = resp.get("load_average", [])
    if load and isinstance(load, list) and len(load) > 0:
        out["load"] = round(load[0], 2)
    return out


def _unraid_info(resp: dict, _widget: dict) -> dict:
    """Unraid: CPU + memory + array state."""
    out: dict[str, Any] = {}
    if isinstance(resp, dict):
        out["cpu"] = resp.get("cpuUsage", "—")
        out["mem"] = resp.get("memUsage", "—")
        out["array"] = resp.get("mdState", "unknown")
    return out


def _synology_info(resp: dict, _widget: dict) -> dict:
    """Synology: CPU + memory + temp + uptime."""
    out: dict[str, Any] = {}
    data = resp.get("data", {})
    out["cpu"] = data.get("cpu_utilization", "—")
    out["mem"] = data.get("memory_utilization", "—")
    out["temp"] = data.get("temperature", "—")
    out["uptime"] = data.get("up_time", "—")
    return out


# ── Media servers ──────────────────────────────────────────────────────────────

def _jellyfin_info(resp: dict, _widget: dict) -> dict:
    """Jellyfin: currently playing sessions + active users + library size."""
    # If we got a list → these are sessions (from /Sessions endpoint)
    if isinstance(resp, list):
        active = [s for s in resp if s.get("IsActive", False) and s.get("NowPlayingItem")]
        out: dict[str, Any] = {}
        out["playing"] = len(active)
        out["sessions"] = len(resp)
        return out
    # Otherwise it's system info from /System/Info — return nothing useful
    return {}


def _plex_info(resp: dict, _widget: dict) -> dict:
    """Plex: active streams + bandwidth."""
    out: dict[str, Any] = {}
    # /status/sessions returns { MediaContainer: { size: N, ... } }
    mc = resp.get("MediaContainer", resp)
    out["streams"] = int(mc.get("size", 0))
    return out


def _navidrome_info(resp: dict, _widget: dict) -> dict:
    """Navidrome: artist + album + song count."""
    out: dict[str, Any] = {}
    subsonic = resp.get("subsonic-response", resp)
    if "artists" in subsonic:
        out["artists"] = subsonic["artists"].get("count", 0)
    if "albums" in subsonic:
        out["albums"] = subsonic["albums"].get("count", 0)
    if "songs" in subsonic:
        out["songs"] = subsonic["songs"].get("count", 0)
    return out


# ── Home automation ────────────────────────────────────────────────────────────

def _homeassistant_info(resp: dict, _widget: dict) -> dict:
    """Home Assistant: entity count + lights/switches on + sensors."""
    out: dict[str, Any] = {}
    if isinstance(resp, list):
        out["entities"] = len(resp)
        out["lights_on"] = sum(
            1 for e in resp
            if e.get("entity_id", "").startswith("light.") and e.get("state") == "on"
        )
        out["switches_on"] = sum(
            1 for e in resp
            if e.get("entity_id", "").startswith("switch.") and e.get("state") == "on"
        )
        out["sensors"] = sum(
            1 for e in resp
            if e.get("entity_id", "").startswith("sensor.")
        )
    return out


# ── Request management ─────────────────────────────────────────────────────────

def _overseerr_info(resp: dict, _widget: dict) -> dict:
    """Overseerr: pending/approved/declined requests."""
    out: dict[str, Any] = {}
    out["pending"] = resp.get("pending", 0)
    out["approved"] = resp.get("approved", 0)
    out["declined"] = resp.get("declined", 0)
    return out


# ── Other services ────────────────────────────────────────────────────────────

def _bazarr_info(resp: dict, _widget: dict) -> dict:
    """Bazarr: subtitle stats — total episodes/movies with subtitles."""
    out: dict[str, Any] = {}
    data = resp.get("data", resp)
    if isinstance(data, dict):
        out["episodes"] = data.get("totalEpisodes", 0)
        out["movies"] = data.get("totalMovies", 0)
    return out


def _nextcloud_info(resp: dict, _widget: dict) -> dict:
    """Nextcloud: storage usage + active users."""
    out: dict[str, Any] = {}
    ocs = resp.get("ocs", {})
    data = ocs.get("data", {})
    # storage stats
    storage = data.get("storage", {})
    if storage:
        out["storage_used"] = storage.get("used", 0)
        out["storage_free"] = storage.get("free", 0)
    out["users"] = len(data.get("users", {})) if isinstance(data.get("users"), dict) else data.get("activeUsers", 0)
    return out


def _gitea_info(resp: dict, _widget: dict) -> dict:
    """Gitea: repo count + open issues + pull requests."""
    out: dict[str, Any] = {}
    # /api/v1/repos/search returns {"data": [...], "ok": true}
    if isinstance(resp, dict) and "data" in resp:
        repos = resp["data"]
        out["repos"] = len(repos)
        out["open_issues"] = sum(r.get("open_issues_count", 0) for r in repos if isinstance(r, dict))
    return out


def _immich_info(resp: dict, _widget: dict) -> dict:
    """Immich: photo + video count + storage used."""
    out: dict[str, Any] = {}
    if isinstance(resp, dict):
        out["photos"] = resp.get("photos", 0)
        out["videos"] = resp.get("videos", 0)
        out["storage"] = resp.get("usage", 0)
    return out


def _paperless_info(resp: dict, _widget: dict) -> dict:
    """Paperless-ngx: document count + inbox count."""
    out: dict[str, Any] = {}
    out["documents"] = resp.get("count", resp.get("total", 0))
    out["inbox"] = resp.get("inbox_count", 0)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# INFO_REGISTRY maps widget_id → {info_endpoint, info_parser}
# Only widgets that support live data fetching are listed here.
# ══════════════════════════════════════════════════════════════════════════════
INFO_REGISTRY: dict[str, dict[str, Any]] = {
    # ── *arr stack — use the "wanted/missing" endpoints for actionable counts ──
    "sonarr": {
        "info_endpoint": "/api/v3/wanted/missing?pageSize=1&page=1",
        "info_parser": _sonarr_info,
    },
    "radarr": {
        "info_endpoint": "/api/v3/wanted/missing?pageSize=1&page=1",
        "info_parser": _radarr_info,
    },
    "lidarr": {
        "info_endpoint": "/api/v1/wanted/missing?pageSize=1&page=1",
        "info_parser": _lidarr_info,
    },
    "readarr": {
        "info_endpoint": "/api/v1/wanted/missing?pageSize=1&page=1",
        "info_parser": _readarr_info,
    },
    "prowlarr": {
        "info_endpoint": "/api/v1/indexer?pageSize=1&page=1",
        "info_parser": _prowlarr_info,
    },
    # ── Download clients ──
    "qbit_torrent": {
        "info_endpoint": "/api/v2/transfer/info",
        "info_parser": _qbittorrent_info,
    },
    "transmission": {
        "info_endpoint": "/transmission/rpc",
        "info_parser": _transmission_info,
    },
    "sabnzbd": {
        "info_endpoint": "/api?mode=queue&output=json",
        "info_parser": _sabnzbd_info,
    },
    "deluge": {
        "info_endpoint": "/json",
        "info_parser": _deluge_info,
    },
    # ── DNS sinkholes ──
    "pihole": {
        "info_endpoint": "/admin/api.php?stats&summaryRaw",
        "info_parser": _pihole_info,
    },
    "adguard": {
        "info_endpoint": "/control/stats",
        "info_parser": _adguard_info,
    },
    # ── Monitoring ──
    "grafana": {
        "info_endpoint": "/api/admin/stats",
        "info_parser": _grafana_info,
    },
    "prometheus": {
        "info_endpoint": "/api/v1/status/tsdb",
        "info_parser": _prometheus_info,
    },
    "uptimekuma": {
        "info_endpoint": "/api/status-page/heart",
        "info_parser": _uptimekuma_info,
    },
    # ── Container / infrastructure ──
    "portainer": {
        "info_endpoint": "/api/endpoints",
        "info_parser": _portainer_info,
    },
    "nginxproxymanager": {
        "info_endpoint": "/api/nginx/proxy-hosts",
        "info_parser": _nginxproxymanager_info,
    },
    "truenas": {
        "info_endpoint": "/api/v2.0/system/info",
        "info_parser": _truenas_info,
    },
    "unraid": {
        "info_endpoint": "/api/v1/var",
        "info_parser": _unraid_info,
    },
    "synology": {
        "info_endpoint": "/webapi/query.cgi?api=SYNO.Core.System.Status&version=1&method=get",
        "info_parser": _synology_info,
    },
    # ── Media servers ──
    "jellyfin": {
        "info_endpoint": "/Sessions",
        "info_parser": _jellyfin_info,
    },
    "plex": {
        "info_endpoint": "/status/sessions",
        "info_parser": _plex_info,
    },
    "navidrome": {
        "info_endpoint": "/rest/getScanStatus",
        "info_parser": _navidrome_info,
    },
    # ── Home automation ──
    "homeassistant": {
        "info_endpoint": "/api/states",
        "info_parser": _homeassistant_info,
    },
    # ── Request management ──
    "overseerr": {
        "info_endpoint": "/api/v1/request/count",
        "info_parser": _overseerr_info,
    },
    # ── Other ──
    "bazarr": {
        "info_endpoint": "/api/system/status",
        "info_parser": _bazarr_info,
    },
    "nextcloud": {
        "info_endpoint": "/ocs/v1.php/cloud/capabilities?format=json",
        "info_parser": _nextcloud_info,
    },
    "gitea": {
        "info_endpoint": "/api/v1/repos/search?limit=5",
        "info_parser": _gitea_info,
    },
    "immich": {
        "info_endpoint": "/api/server-info/stats",
        "info_parser": _immich_info,
    },
    "paperlessngx": {
        "info_endpoint": "/api/documents/total",
        "info_parser": _paperless_info,
    },
}


def fetch_tile_info(entry: "ServiceEntry") -> dict:
    """Call the tile's service API and return parsed stats.

    If the widget_type doesn't support info fetching (not in INFO_REGISTRY),
    returns an empty dict.  On any network/parse error returns
    ``{"error": "...", "widget_type": "..."}``.
    """
    from .schemas import ServiceEntry  # type: ignore

    widget_id = entry.widget_type
    if not widget_id or widget_id not in INFO_REGISTRY:
        return {}

    cfg = INFO_REGISTRY[widget_id]
    endpoint = cfg["info_endpoint"]
    parser = cfg["info_parser"]
    widget = get_widget(widget_id) or {}

    base_url = (entry.api_url or entry.url or "").rstrip("/")
    if not base_url:
        return {"error": "no api_url or url configured", "widget_type": widget_id}

    url = f"{base_url}{endpoint}"
    headers: dict[str, str] = {}
    auth: tuple[str, str] | None = None

    schema = widget.get("auth_schema", "none")
    if schema == "api_key" and entry.api_key:
        fmt = widget.get("auth_header_format") or "Bearer {token}"
        val = fmt.replace("{token}", entry.api_key)
        if ":" in fmt and not fmt.startswith("Bearer"):
            name, _, value = val.partition(":")
            headers[name.strip()] = value.strip()
        else:
            headers["Authorization"] = val
    elif schema in ("basic", "form") and entry.username:
        auth = (entry.username, entry.password or "")

    try:
        resp = _httpx.get(url, headers=headers, auth=auth, timeout=10.0, verify=False)
    except _httpx.HTTPError as e:
        return {"error": f"network error: {e}", "widget_type": widget_id}

    if resp.status_code >= 400:
        return {"error": f"upstream {resp.status_code}", "widget_type": widget_id}

    try:
        body = resp.json()
    except ValueError:
        return {"error": "non-JSON response", "widget_type": widget_id}

    try:
        parsed = parser(body, widget)
        parsed["widget_type"] = widget_id
        return parsed
    except Exception as e:
        return {"error": f"parse error: {e}", "widget_type": widget_id}
