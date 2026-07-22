"""Deterministic mock dataset so the API can run without a real Docker host."""
from __future__ import annotations

from .schemas import ContainerKind, PortMapping, Service, ServiceHealth, ServiceStatus

MOCK_SERVICES: list[Service] = [
    Service(
        id="docker-sonarr",
        name="sonarr",
        kind=ContainerKind.CONTAINER,
        status=ServiceStatus.RUNNING,
        ports=[PortMapping(host=8989, container=8989, protocol="tcp")],
        icon_hint="sonarr",
        image="lscr.io/linuxserver/sonarr:latest",
    ),
    Service(
        id="docker-radarr",
        name="radarr",
        kind=ContainerKind.CONTAINER,
        status=ServiceStatus.RUNNING,
        ports=[PortMapping(host=7878, container=7878, protocol="tcp")],
        icon_hint="radarr",
        image="lscr.io/linuxserver/radarr:latest",
    ),
    Service(
        id="docker-lidarr",
        name="lidarr",
        kind=ContainerKind.CONTAINER,
        status=ServiceStatus.STOPPED,
        ports=[PortMapping(host=8686, container=8686, protocol="tcp")],
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
