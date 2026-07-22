"""Deterministic mock dataset so the API can run without a real Proxmox host.

NOTE: MOCK_SERVICES is intentionally empty — new deployments start with a blank
dashboard. Users add tiles via the Settings page (POST /api/config/services).
Mock health data is retained for testing the /api/services/{id}/health endpoint.
"""
from __future__ import annotations

from .schemas import Service, ServiceHealth, ServiceStatus

# Empty list — users start with a blank dashboard and add services via the UI.
MOCK_SERVICES: list[Service] = []

MOCK_HEALTH = {
    "test-service-1": ServiceHealth(
        id="test-service-1",
        status=ServiceStatus.RUNNING,
        healthy=True,
        uptime_seconds=126345,
        last_seen="2026-07-19T16:45:00Z",
        message="ok",
    ),
}
