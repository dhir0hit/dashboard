"""Docker container discovery via the local Docker socket.

The backend runs inside a Docker container with ``/var/run/docker.sock`` mounted.
We call the Docker Engine API directly over the Unix socket (no `docker` CLI
needed) and shape each container into a Service object.
icon_hint is inferred from the image name (sonarr, radarr, postgres, redis, ...).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from .schemas import PortMapping, Service, ServiceStatus

# --- config -----------------------------------------------------------------
DOCKER_SOCK = os.getenv("DOCKER_SOCK", "/var/run/docker.sock")
DOCKER_API_VERSION = "v1.43"  # widely supported; falls back gracefully

# --- icon inference --------------------------------------------------------
_ICON_MAP = {
    "sonarr": "sonarr", "radarr": "radarr", "lidarr": "lidarr",
    "bazarr": "bazarr", "readarr": "readarr", "prowlarr": "prowlarr",
    "grafana": "grafana", "prometheus": "prometheus", "nginx": "nginx",
    "portainer": "portainer", "postgres": "postgres", "pgsql": "postgres",
    "redis": "redis", "mysql": "mysql", "mariadb": "mariadb",
    "mongo": "mongodb", "mongodb": "mongodb", "elasticsearch": "elasticsearch",
    "kibana": "kibana", "vault": "vault", "traefik": "traefik",
    "caddy": "caddy", "node": "nodejs", "python": "python", "nginx-proxy": "nginx",
    "homeassistant": "home-assistant", "home-assistant": "home-assistant",
    "pihole": "pihole", "adguard": "adguard", "uptime-kuma": "uptime-kuma",
    "jellyfin": "jellyfin", "kavita": "kavita", "calibre": "calibre",
    "vaultwarden": "vaultwarden", "paperless": "paperless",
    "code-server": "code-server", "syncthing": "syncthing",
    "filebrowser": "filebrowser", "stirling": "stirling-pdf",
    "dozzle": "dozzle", "watchtower": "watchtower", "photoprism": "photoprism",
    "homepage": "homepage", "adguardhome": "adguard", "tailscale": "tailscale",
    "linkwarden": "linkwarden", "joplin": "joplin", "actualbudget": "actual",
}


def _icon_hint(image: str) -> str:
    if not image:
        return "docker"
    # strip registry/registry:port and tag
    name = image.split("/")[-1].split(":")[0].lower()
    for key, icon in _ICON_MAP.items():
        if name == key or name.startswith(key):
            return icon
    return "docker"


def _parse_ports(container: dict) -> list[PortMapping]:
    """Parse Docker API PortBindings from container.HostConfig.PortBindings."""
    out: list[PortMapping] = []
    seen: set[tuple[int, int, str]] = set()
    bindings = (container.get("HostConfig") or {}).get("PortBindings") or {}
    for cport_str, host_list in bindings.items():
        if not host_list:
            continue
        # cport_str like "3000/tcp" or "8080/udp"
        try:
            cp, proto = cport_str.split("/", 1)
        except ValueError:
            cp, proto = cport_str, "tcp"
        try:
            container_port = int(cp)
        except ValueError:
            continue
        for hb in host_list:
            try:
                host_port = int(hb.get("HostPort", 0))
            except (ValueError, TypeError):
                continue
            if host_port == 0:
                continue
            key = (host_port, container_port, proto)
            if key in seen:
                continue
            seen.add(key)
            out.append(PortMapping(host=host_port, container=container_port, protocol=proto))
    return out


def _status_from(state: dict) -> ServiceStatus:
    status = (state.get("Status") or "").lower()
    if status == "running":
        return ServiceStatus.RUNNING
    if status == "paused":
        return ServiceStatus.PAUSED
    if status in ("exited", "created", "dead", "restarting"):
        return ServiceStatus.STOPPED
    return ServiceStatus.UNKNOWN


# --- public entry point ----------------------------------------------------
def discover_docker_services() -> list[Service]:
    """Discover Docker containers via the local Docker socket (Engine API).

    Returns a list of Service objects, one per container. Returns an empty
    list if the socket is unavailable or the API call fails.
    """
    if not os.path.exists(DOCKER_SOCK):
        return []

    transport = httpx.HTTPTransport(uds=DOCKER_SOCK)
    base = f"http://localhost/{DOCKER_API_VERSION}"

    try:
        with httpx.Client(transport=transport, base_url=base, timeout=10) as client:
            # GET /containers/json?all=1
            r = client.get("/containers/json", params={"all": "true"})
            if r.status_code != 200:
                return []
            containers = r.json()
    except (httpx.HTTPError, OSError):
        return []

    services: list[Service] = []
    for c in containers:
        name = (c.get("Names") or [""])[0].lstrip("/")
        if not name:
            continue
        image = c.get("Image", "")
        # Docker API returns State as a string ("running", "exited", etc.)
        state_str = c.get("State", "")
        status = _status_from({"Status": state_str} if isinstance(state_str, str) else state_str)
        ports = _parse_ports(c)
        labels = c.get("Labels") or {}

        svc = Service(
            id=f"docker-{name}",
            name=name,
            status=status,
            image=image,
            ports=ports,
            icon_hint=_icon_hint(image),
            labels=labels if isinstance(labels, dict) else dict(labels),
        )
        services.append(svc)

    return services
