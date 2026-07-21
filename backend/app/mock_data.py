"""Deterministic mock dataset so the API can run without a real Proxmox host."""
from __future__ import annotations

from .schemas import Service, ServiceHealth, ServiceStatus

MOCK_SERVICES: list[Service] = [
    Service(
        id="pve-lxc-100-docker-sonarr",
        name="sonarr",
        node="pve",
        vmid=100,
        kind="lxc",
        status=ServiceStatus.RUNNING,
        ports=[{"host": 8989, "container": 8989, "protocol": "tcp"}],
        icon_hint="sonarr",
        image="lscr.io/linuxserver/sonarr:latest",
    ),
    Service(
        id="pve-lxc-100-docker-radarr",
        name="radarr",
        node="pve",
        vmid=100,
        kind="lxc",
        status=ServiceStatus.RUNNING,
        ports=[{"host": 7878, "container": 7878, "protocol": "tcp"}],
        icon_hint="radarr",
        image="lscr.io/linuxserver/radarr:latest",
    ),
    Service(
        id="pve-lxc-101-docker-lidarr",
        name="lidarr",
        node="pve",
        vmid=101,
        kind="lxc",
        status=ServiceStatus.STOPPED,
        ports=[{"host": 8686, "container": 8686, "protocol": "tcp"}],
        icon_hint="lidarr",
        image="lscr.io/linuxserver/lidarr:latest",
    ),
]

MOCK_HEALTH = {
    s.id: ServiceHealth(
        id=s.id,
        status=s.status,
        healthy=s.status == ServiceStatus.RUNNING,
        uptime_seconds=126345 if s.status == ServiceStatus.RUNNING else 0,
        last_seen="2026-07-19T16:45:00Z" if s.status == ServiceStatus.RUNNING else None,
        message="ok" if s.status == ServiceStatus.RUNNING else "container stopped",
    )
    for s in MOCK_SERVICES
}
