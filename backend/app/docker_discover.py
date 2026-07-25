"""Docker container discovery via the local Docker socket.

The backend runs inside a Docker container with ``/var/run/docker.sock`` mounted.
We call ``docker ps`` locally and shape each container into a Service object.
icon_hint is inferred from the image name (sonarr, radarr, postgres, redis, ...).
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .schemas import PortMapping, Service, ServiceStatus

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


def _parse_ports(raw: str) -> list[PortMapping]:
    """Parse docker's Ports column, e.g. '0.0.0.0:3000->3000/tcp, :::3000->3000/tcp'."""
    if not raw or raw == "0":
        return []
    out: list[PortMapping] = []
    seen: set[tuple[int, int, str]] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if "->" not in chunk:
            continue
        try:
            left, right = chunk.split("->", 1)
            host_port = int(left.rsplit(":", 1)[-1])
            container_port_part = right.split("/", 1)[0]
            container_port = int(container_port_part)
            proto = right.split("/", 1)[1] if "/" in right else "tcp"
            key = (host_port, container_port, proto)
            if key in seen:
                continue
            seen.add(key)
            out.append(PortMapping(host=host_port, container=container_port, protocol=proto))
        except (ValueError, IndexError):
            continue
    return out


# --- docker ps output row --------------------------------------------------
@dataclass
class DockerRow:
    name: str
    image: str
    status: str  # "Up 2 hours", "Exited (0) 3 days ago", etc.
    ports: str
    labels: str = ""


def _status_from(status_str: str) -> ServiceStatus:
    s = status_str.lower()
    if s.startswith("up"):
        return ServiceStatus.RUNNING
    if s.startswith("paused"):
        return ServiceStatus.PAUSED
    if s.startswith("exited") or s.startswith("restarting"):
        return ServiceStatus.STOPPED
    return ServiceStatus.UNKNOWN


# --- docker ps invocation --------------------------------------------------
_DOCKER_PS_FORMAT = (
    "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Labels}}"
)


def _build_docker_ps_cmd() -> str:
    return f"docker ps -a --format '{_DOCKER_PS_FORMAT}'"


def _parse_ps(stdout: str) -> list[DockerRow]:
    rows: list[DockerRow] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("error"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name = parts[0].lstrip("/")
        image = parts[1]
        status = parts[2]
        ports = parts[3] if len(parts) > 3 else ""
        labels = parts[4] if len(parts) > 4 else ""
        rows.append(DockerRow(name, image, status, ports, labels))
    return rows


def _labels_to_dict(labels: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not labels:
        return out
    # docker emits labels as "key1=val1,key2=val2,..." when multiple.
    for kv in labels.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# --- shared row → Service --------------------------------------------------
def _rows_to_services(stdout: str) -> list[Service]:
    services: list[Service] = []
    for row in _parse_ps(stdout):
        status = _status_from(row.status)
        svc = Service(
            id=f"docker-{row.name}",
            name=row.name,
            status=status,
            image=row.image,
            ports=_parse_ports(row.ports),
            icon_hint=_icon_hint(row.image),
            labels=_labels_to_dict(row.labels),
        )
        services.append(svc)
    return services


# --- public entry point ----------------------------------------------------
def discover_docker_services() -> list[Service]:
    """Discover Docker containers via the local Docker socket.

    Returns a list of Service objects, one per container. Returns an empty
    list if Docker is not available (no CLI, no socket).
    """
    if not shutil.which("docker"):
        if not Path("/var/run/docker.sock").exists():
            return []
    cmd = _build_docker_ps_cmd()
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if r.returncode != 0:
        return []
    return _rows_to_services(r.stdout)
