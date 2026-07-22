"""Deterministic mock dataset so the API can run without a real Proxmox host.

The mock service list is intentionally empty — the dashboard starts with a
clean tile grid. Users add their own tiles via the Settings page. Mock mode
still exercises the discovery and health endpoints, just with zero services.
"""
from __future__ import annotations

from .schemas import Service, ServiceHealth, ServiceStatus

# Empty by default — the dashboard starts clean. Users add tiles via Settings.
MOCK_SERVICES: list[Service] = []

MOCK_HEALTH: dict[str, ServiceHealth] = {}