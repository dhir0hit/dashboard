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