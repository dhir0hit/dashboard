"""Docker container discovery for LXC guests and QEMU VMs.

Strategy (in order):
1. SSH into the host/guest and run `docker ps --format ...`. Works for VMs
   with an SSH server, and for LXC if SSH_HOST points at the PVE host (in
   which case we run `pct exec <vmid> -- docker ...` remotely).
2. Local fallback: if running inside the container/VM itself, use the local
   docker socket via docker CLI or /var/run/docker.sock.

The output is shaped into Service objects. Each docker container becomes one
Service. icon_hint is inferred from the image name (sonarr, radarr, lidarr,
postgres, redis, ...).
"""
from __future__ import annotations

import json
import shlex
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import paramiko

from .config import Settings
from .schemas import ContainerKind, PortMapping, Service, ServiceStatus

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


# --- exec backends ---------------------------------------------------------
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


# --- SSH implementation ----------------------------------------------------
def _ssh_client(s: Settings) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs: dict = {"port": s.ssh_port, "timeout": 15}
    if s.ssh_key_file and Path(s.ssh_key_file).exists():
        kwargs["key_filename"] = s.ssh_key_file
    elif s.ssh_password:
        kwargs["password"] = s.ssh_password
    else:
        kwargs["look_for_keys"] = True
    client.connect(s.ssh_host, username=s.ssh_user, **kwargs)
    return client


def _exec_ssh_command(s: Settings, command: str) -> tuple[int, str, str]:
    """Run `command` over SSH. Returns (exit_code, stdout, stderr)."""
    client = _ssh_client(s)
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=60)
        code = stdout.channel.recv_exit_status()
        return code, stdout.read().decode("utf-8", "replace"), stderr.read().decode("utf-8", "replace")
    finally:
        client.close()


def discover_via_ssh(s: Settings, node: str, vmid: int, kind: ContainerKind) -> list[Service]:
    """Run docker ps on the gamit, embedding vmid/kind into Service IDs."""
    if not s.ssh_host:
        return []
    cmd = _build_docker_ps_cmd()
    # For LXC, prefer the PVE host using pct exec so we don't need guest SSH.
    if kind == ContainerKind.LXC:
        cmd = f"pct exec {vmid} -- " + cmd
    code, stdout, stderr = _exec_ssh_command(s, cmd)
    if code != 0:
        # docker not installed — not an error, just no services.
        if "not found" in stderr.lower() or "not found" in stdout.lower():
            return []
        # auth / connect failures bubble up
        return []
    return _rows_to_services(stdout, node, vmid, kind)


# --- Local implementation (running inside the guest itself) ---------------
def discover_via_local(node: str, vmid: int, kind: ContainerKind) -> list[Service]:
    if not shutil.which("docker"):
        # try a raw socket query as a graceful no-op path
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
    return _rows_to_services(r.stdout, node, vmid, kind)


# --- shared row → Service --------------------------------------------------
def _rows_to_services(
    stdout: str, node: str, vmid: int, kind: ContainerKind
) -> list[Service]:
    services: list[Service] = []
    for row in _parse_ps(stdout):
        status = _status_from(row.status)
        kind_str = kind.value if hasattr(kind, "value") else kind
        svc = Service(
            id=f"{node}-{kind_str}-{vmid}-docker-{row.name}",
            name=row.name,
            node=node,
            vmid=vmid,
            kind=ContainerKind(kind) if isinstance(kind, str) else kind,
            status=status,
            image=row.image,
            ports=_parse_ports(row.ports),
            icon_hint=_icon_hint(row.image),
            labels=_labels_to_dict(row.labels),
        )
        services.append(svc)
    return services


# --- public dispatcher -----------------------------------------------------
def discover_docker_services(
    s: Settings, node: str, vmid: int, kind: ContainerKind
) -> list[Service]:
    """Try SSH first (covers VMs and LXC-via-pct), fall back to local docker."""
    if s.ssh_host:
        try:
            return discover_via_ssh(s, node, vmid, kind)
        except Exception:
            # fall through to local
            pass
    return discover_via_local(node, vmid, kind)


def hostname_to_node(default: str = "pve") -> str:
    """Best-effort node name for local Docker discovery.

    When the backend runs inside a Docker container, the hostname is a
    random 12-char hex (e.g. ``ea533efc469b``). That's useless as a node
    label, so fall back to ``default`` ("pve") in that case.
    """
    try:
        h = socket.gethostname()
        if not h:
            return default
        # Docker container hostnames are 12 hex chars — not human-friendly.
        if len(h) == 12 and all(c in "0123456789abcdef" for c in h.lower()):
            return default
        return h
    except Exception:
        return default