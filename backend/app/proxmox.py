"""Proxmox VE API client (token auth, httpx).

Query-only. Returns the raw JSON PVE returns (already dict-shaped via httpx).
Handles auth-error HTTP codes by raising clear, typed exceptions the FastAPI
layer turns into 502/401 responses.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Settings


class ProxmoxError(Exception):
    """Generic Proxmox client error (network, parse, unexpected)."""


class ProxmoxAuthError(ProxmoxError):
    """401/403 from PVE — bad token or insufficient privileges."""


class ProxmoxClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.headers = settings.auth_header

    # ------------------------------------------------------------------ core
    def _request(self, method: str, path: str, **kw: Any) -> Any:
        url = f"{self.s.base_url}{path.lstrip('/')}"
        verify = self.s.proxmox_verify_tls
        try:
            with httpx.Client(timeout=20.0, verify=verify) as c:
                r = c.request(method, url, headers=self.headers, **kw)
        except httpx.HTTPError as e:
            raise ProxmoxError(f"network error: {e}") from e

        if r.status_code in (401, 403):
            raise ProxmoxAuthError(f"PVE rejected auth ({r.status_code}): {r.text[:200]}")
        if r.status_code >= 400:
            raise ProxmoxError(f"PVE {r.status_code}: {r.text[:200]}")

        try:
            return r.json().get("data", {})
        except ValueError as e:
            raise ProxmoxError(f"bad JSON from PVE: {e}") from e

    # ----------------------------------------------------------------- nodes
    def list_nodes(self) -> list[dict]:
        return self._request("GET", "/nodes") or []

    def pick_node(self) -> str:
        if self.s.proxmox_node:
            return self.s.proxmox_node
        nodes = self.list_nodes()
        if not nodes:
            raise ProxmoxError("no PVE nodes discovered")
        online = [n for n in nodes if n.get("status") == "online"]
        return (online[0] if online else nodes[0])["node"]

    # ------------------------------------------------------------ lxc & qemu
    def list_lxc(self, node: str) -> list[dict]:
        return self._request("GET", f"/nodes/{node}/lxc") or []

    def list_qemu(self, node: str) -> list[dict]:
        return self._request("GET", f"/nodes/{node}/qemu") or []

    def guest_status(self, node: str, vmid: int, kind: str) -> dict:
        # kind == 'lxc' or 'qemu'
        return self._request("GET", f"/nodes/{node}/{kind}/{vmid}/status/current") or {}

    def pct_exec(self, node: str, vmid: int, command: list[str]) -> str:
        """Run a command inside an LXC container via PVE's /pct exec endpoint.

        Returns stdout. Raises ProxmoxError on non-zero exit or API failure.
        """
        if vmid <= 0:
            raise ProxmoxError("pct_exec requires a positive vmid")
        # PVE expects {command: ["bash","-lc","docker ps ..."]} via POST.
        payload = {"command": command}
        try:
            with httpx.Client(timeout=60.0, verify=self.s.proxmox_verify_tls) as c:
                url = f"{self.s.base_url.rstrip('/')}/nodes/{node}/lxc/{vmid}/exec"
                r = c.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=payload)
        except httpx.HTTPError as e:
            raise ProxmoxError(f"pct exec network error: {e}") from e
        if r.status_code in (401, 403):
            raise ProxmoxAuthError(f"PVE rejected exec auth ({r.status_code})")
        if r.status_code >= 400:
            raise ProxmoxError(f"pct exec HTTP {r.status_code}: {r.text[:200]}")
        # The exec endpoint returns a task upid; we cannot stream output via
        # the simple REST path. For this dashboard we fall back to SSH when
        # pct exec is required for fetching docker container data — handled
        # in docker_discover.py. If we get here, return what we have.
        return r.text

    # --------------------------------------------------------- reachability
    def ping(self) -> bool:
        try:
            self.list_nodes()
            return True
        except ProxmoxAuthError:
            return False  # reachable but unauthorized — still not a crash
        except ProxmoxError:
            return False

    def host_label(self) -> str:
        try:
            host = urlparse(self.s.proxmox_api_url).hostname or "pve"
            return host
        except Exception:
            return "pve"