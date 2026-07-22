"""Widget registry — known service types the dashboard can auto-login to.

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

# ── Service info endpoints ─────────────────────────────────────────────
# Each widget that supports live data fetching has an `info_endpoint` (path
# appended to api_url) and an `info_parser` (a function that extracts stats
# from the JSON response).  The backend's GET /api/tiles/{id}/info route
# calls the appropriate endpoint with stored credentials and returns the
# parsed fields to the frontend.

import httpx as _httpx  # type: ignore  # already imported in main

# ── Info parsers ───────────────────────────────────────────────────────

def _arr_stats(resp: dict, _widget: dict) -> dict:
    """Parse *arr (Sonarr/Radarr/Lidarr/Readarr/Prowlarr) status response."""
    from datetime import datetime
    out = {}
    if "version" in resp:
        out["version"] = resp["version"]
    out["startTime"] = resp.get("startTime", "")
    # compute uptime
    try:
        start = datetime.fromisoformat(resp["startTime"].replace("Z", "+00:00"))
        uptime_s = int((datetime.now(start.tzinfo) - start).total_seconds())
        out["uptime"] = uptime_s
    except Exception:
        pass
    return out


def _qbittorrent_info(resp: dict, _widget: dict) -> dict:
    """Parse qBittorrent /api/v2/transfer/info response."""
    out = {}
    # resp is { "dl_info": { speed, ... }, "up_info": { ... }, ... }
    dl = resp.get("dl_info", {})
    up = resp.get("up_info", {})
    out["download_speed"] = dl.get("speed", 0)
    out["upload_speed"] = up.get("speed", 0)
    # Convert to human-readable in the frontend; here we return raw bytes/s
    return out


def _transmission_info(resp: dict, _widget: dict) -> dict:
    """Parse Transmission torrent-session-get response."""
    # resp shape: {"arguments": {"torrentCount": N, "downloadSpeed": N, "uploadSpeed": N}}
    args = resp.get("arguments", resp)
    out = {}
    out["download_speed"] = args.get("downloadSpeed", 0)
    out["upload_speed"] = args.get("uploadSpeed", 0)
    out["torrent_count"] = args.get("torrentCount", 0)
    return out


def _sabnzbd_info(resp: dict, _widget: dict) -> dict:
    """Parse SABnzbd queue + history summary."""
    out = {}
    if "queue" in resp:
        q = resp["queue"]
        out["queue_length"] = int(q.get("noofslots", 0))
        out["queue_size_mb"] = float(q.get("size", "0").replace(" ", ""))
    if "history" in resp:
        h = resp["history"]
        out["total_downloaded"] = int(h.get("noofslots", 0))
    return out


def _deluge_info(resp: dict, _widget: dict) -> dict:
    """Parse Deluge web UI stats response."""
    out = {}
    stats = resp.get("stats", resp)
    out["download_speed"] = int(stats.get("download_rate", 0))
    out["upload_speed"] = int(stats.get("upload_rate", 0))
    out["torrent_count"] = int(stats.get("num_torrents", 0))
    return out


def _pihole_info(resp: dict, _widget: dict) -> dict:
    """Parse Pi-hole API stats."""
    out = {}
    if "domains_being_blocked" in resp:
        out["domains_blocked"] = resp["domains_being_blocked"]
        out["dns_queries_today"] = resp.get("dns_queries_today", 0)
        out["ads_blocked_today"] = resp.get("ads_blocked_today", 0)
        out["ads_percentage_today"] = round(resp.get("ads_percentage_today", 0), 2)
    return out


def _adguard_info(resp: dict, _widget: dict) -> dict:
    """Parse AdGuard Home status response."""
    out = {}
    out["dns_queries"] = resp.get("numDnsQueries", 0)
    out["blocked_filtering"] = resp.get("numBlockedFiltering", 0)
    out["percent_blocked"] = round(resp.get("ratioFastFiltering", 0) * 100, 2)
    return out


def _traefik_npm_info(resp: dict, _widget: dict) -> dict:
    """Parse Nginx Proxy Manager users count."""
    # /api/nginx/proxy-hosts returns a list
    if isinstance(resp, list):
        return {"proxy_hosts": len(resp)}
    return {}


def _uptimekuma_info(resp: dict, _widget: dict) -> dict:
    """Parse Uptime Kuma status page metrics from /api/status-page/."""
    out = {}
    if "stats" in resp:
        stats = resp["stats"]
        out["up"] = stats.get("up", 0)
        out["down"] = stats.get("down", 0)
        out["paused"] = stats.get("paused", 0)
    return out


def _homeassistant_info(resp: dict, _widget: dict) -> dict:
    """Parse Home Assistant /api/states response."""
    out = {}
    if isinstance(resp, list):
        out["entities"] = len(resp)
        # Count entities by domain
        domains = {}
        for entity in resp:
            eid = entity.get("entity_id", "")
            domain = eid.split(".")[0] if "." in eid else "other"
            domains[domain] = domains.get(domain, 0) + 1
        out["domains"] = domains
        out["lights_on"] = sum(
            1 for e in resp
            if e.get("entity_id", "").startswith("light.")
            and e.get("state") == "on"
        )
        out["switches_on"] = sum(
            1 for e in resp
            if e.get("entity_id", "").startswith("switch.")
            and e.get("state") == "on"
        )
    elif isinstance(resp, dict):
        out["state"] = resp.get("state", "unknown")
        out["entity_id"] = resp.get("entity_id", "")
    return out


def _grafana_info(resp: dict, _widget: dict) -> dict:
    """Parse Grafana stats response."""
    out = {}
    out["dashboards"] = resp.get("dashboards", 0)
    out["users"] = resp.get("users", 0)
    out["orgs"] = resp.get("orgs", 0)
    return out


def _prometheus_info(resp: dict, _widget: dict) -> dict:
    """Parse Prometheus /api/v1/status/config response."""
    out = {}
    data = resp.get("data", {})
    out["active_series"] = data.get("activeSeries", 0)
    out["config_yaml"] = "loaded" if data.get("yamlConfig", "") else "none"
    return out


def _portainer_info(resp: dict, _widget: dict) -> dict:
    """Parse Portainer /api/endpoints response (list of endpoints)."""
    if isinstance(resp, list):
        return {
            "endpoints": len(resp),
            "running": sum(1 for e in resp if e.get("Status", 0) == 1),
            "stopped": sum(1 for e in resp if e.get("Status", 0) == 0),
        }
    return {}


def _overseerr_info(resp: dict, _widget: dict) -> dict:
    """Parse Overseerr /api/v1/request/count response."""
    out = {}
    out["pending"] = resp.get("pending", 0)
    out["approved"] = resp.get("approved", 0)
    out["declined"] = resp.get("declined", 0)
    return out


def _bazarr_info(resp: dict, _widget: dict) -> dict:
    """Parse Bazarr system status."""
    out = {}
    out["version"] = resp.get("data", {}).get("version", "") if isinstance(resp, dict) else ""
    return out


def _truenas_info(resp: dict, _widget: dict) -> dict:
    """Parse TrueNAS system info."""
    out = {}
    out["version"] = resp.get("version", "")
    out["hostname"] = resp.get("hostname", "")
    out["uptime"] = resp.get("uptime_seconds", 0)
    out["load_average"] = resp.get("load_average", [])
    return out


def _jellyfin_info(resp: dict, _widget: dict) -> dict:
    """Parse Jellyfin /GetSystemInfo response."""
    out = {}
    info = resp.get("SystemInfo", resp)
    out["version"] = info.get("Version", "")
    out["server_name"] = info.get("ServerName", "")
    out["id"] = info.get("Id", "")
    return out


def _plex_info(resp: dict, _widget: dict) -> dict:
    """Parse Plex /api/v2/user response."""
    out = {}
    out["username"] = resp.get("username", "")
    out["email"] = resp.get("email", "")
    out["friendly_name"] = resp.get("friendlyName", "")
    return out


def _navidrome_info(resp: dict, _widget: dict) -> dict:
    """Parse Navidrome /api/ping response."""
    out = {}
    out["version"] = resp.get("version", "")
    out["server"] = resp.get("server", "")
    return out


def _nextcloud_info(resp: dict, _widget: dict) -> dict:
    """Parse Nextcloud /ocs/v1.php/cloud/capabilities response."""
    out = {}
    ocs = resp.get("ocs", {})
    data = ocs.get("data", {})
    version_data = data.get("version", {})
    out["version"] = version_data.get("version", "")
    out["users"] = len(data.get("users", {})) if isinstance(data.get("users"), dict) else 0
    return out


def _gitea_info(resp: dict, _widget: dict) -> dict:
    """Parse Gitea /api/v1/version response."""
    out = {}
    out["version"] = resp.get("version", "")
    out["commit"] = resp.get("commit", {}).get("id", "") if isinstance(resp.get("commit"), dict) else ""
    return out


def _immich_info(resp: dict, _widget: dict) -> dict:
    """Parse Immich /api/server-info/server-version response."""
    out = {}
    out["version"] = ".".join(str(v) for v in resp.values()) if isinstance(resp, dict) else ""
    return out


def _paperless_info(resp: dict, _widget: dict) -> dict:
    """Parse Paperless-ngx /api/documents/total response."""
    out = {}
    total = resp.get("count", resp.get("total", 0))
    out["documents"] = total
    return out


def _unraid_info(resp: dict, _widget: dict) -> dict:
    """Parse Unraid /api/v1/var response (system stats)."""
    out = {}
    if isinstance(resp, dict):
        out["cpu_usage"] = resp.get("cpuUsage", "—")
        out["mem_usage"] = resp.get("memUsage", "—")
        out["array_state"] = resp.get("mdState", "unknown")
    return out


def _synology_info(resp: dict, _widget: dict) -> dict:
    """Parse Synology DSM system info response."""
    out = {}
    data = resp.get("data", {})
    out["model"] = data.get("model", "")
    out["ram"] = data.get("ram_size", 0)
    out["serial"] = data.get("serial", "")
    out["uptime"] = data.get("up_time", "")
    out["temperature"] = data.get("temperature", 0)
    return out


# ════════════════════════════════════════════════════════════════════════
# INFO_REGISTRY maps widget_id → (info_endpoint, info_parser_function)
# Only widgets that support live data fetching are listed here.
# The frontend only calls /api/tiles/{id}/info for tiles with a matching
# widget_type. Others just show the basic tile (name, url, link).
# ════════════════════════════════════════════════════════════════════════
INFO_REGISTRY: dict[str, dict[str, Any]] = {
    "sonarr": {
        "info_endpoint": "/api/v3/system/status",
        "info_parser": _arr_stats,
    },
    "radarr": {
        "info_endpoint": "/api/v3/system/status",
        "info_parser": _arr_stats,
    },
    "lidarr": {
        "info_endpoint": "/api/v1/system/status",
        "info_parser": _arr_stats,
    },
    "readarr": {
        "info_endpoint": "/api/v1/system/status",
        "info_parser": _arr_stats,
    },
    "prowlarr": {
        "info_endpoint": "/api/v1/system/status",
        "info_parser": _arr_stats,
    },
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
    "pihole": {
        "info_endpoint": "/admin/api.php?stats&summaryRaw",
        "info_parser": _pihole_info,
    },
    "adguard": {
        "info_endpoint": "/control/stats",
        "info_parser": _adguard_info,
    },
    "nginxproxymanager": {
        "info_endpoint": "/api/nginx/proxy-hosts",
        "info_parser": _traefik_npm_info,
    },
    "uptimekuma": {
        "info_endpoint": "/api/status-page/heart",
        "info_parser": _uptimekuma_info,
    },
    "homeassistant": {
        "info_endpoint": "/api/states",
        "info_parser": _homeassistant_info,
    },
    "grafana": {
        "info_endpoint": "/api/admin/stats",
        "info_parser": _grafana_info,
    },
    "prometheus": {
        "info_endpoint": "/api/v1/status/config",
        "info_parser": _prometheus_info,
    },
    "portainer": {
        "info_endpoint": "/api/endpoints",
        "info_parser": _portainer_info,
    },
    "overseerr": {
        "info_endpoint": "/api/v1/request/count",
        "info_parser": _overseerr_info,
    },
    "bazarr": {
        "info_endpoint": "/api/system/status",
        "info_parser": _bazarr_info,
    },
    "truenas": {
        "info_endpoint": "/api/v2.0/system/info",
        "info_parser": _truenas_info,
    },
    "jellyfin": {
        "info_endpoint": "/System/Info/public",
        "info_parser": _jellyfin_info,
    },
    "plex": {
        "info_endpoint": "/api/v2/user",
        "info_parser": _plex_info,
    },
    "navidrome": {
        "info_endpoint": "/rest/ping",
        "info_parser": _navidrome_info,
    },
    "nextcloud": {
        "info_endpoint": "/ocs/v1.php/cloud/capabilities?format=json",
        "info_parser": _nextcloud_info,
    },
    "gitea": {
        "info_endpoint": "/api/v1/version",
        "info_parser": _gitea_info,
    },
    "immich": {
        "info_endpoint": "/api/server-info/server-version",
        "info_parser": _immich_info,
    },
    "paperlessngx": {
        "info_endpoint": "/api/documents/total",
        "info_parser": _paperless_info,
    },
    "unraid": {
        "info_endpoint": "/api/v1/var",
        "info_parser": _unraid_info,
    },
    "synology": {
        "info_endpoint": "/webapi/query.cgi?api=SYNO.SystemInfo&version=2&method=get",
        "info_parser": _synology_info,
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
