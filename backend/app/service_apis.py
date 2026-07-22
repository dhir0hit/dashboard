"""Service API integrations — ping websites and fetch data from Jellyfin/Radarr/qBittorrent.

This module provides:
- Website ping/health checks (t_22200dea)
- API integrations for Jellyfin, Radarr, qBittorrent (t_86528492)

Each service type has a dedicated fetcher that returns structured data the
frontend can display on dashboard tiles.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

log = logging.getLogger("dashboard.service_apis")


async def ping_website(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Ping a website and return status info.
    
    Returns dict with:
    - online: bool
    - status_code: int | None
    - response_time_ms: float | None
    - error: str | None
    """
    start = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
            return {
                "online": resp.status_code < 400,
                "status_code": resp.status_code,
                "response_time_ms": round(elapsed_ms, 2),
                "error": None,
            }
    except httpx.TimeoutException:
        return {
            "online": False,
            "status_code": None,
            "response_time_ms": None,
            "error": "timeout",
        }
    except httpx.RequestError as e:
        return {
            "online": False,
            "status_code": None,
            "response_time_ms": None,
            "error": str(e),
        }
    except Exception as e:  # noqa: BLE001
        log.warning("ping failed for %s: %s", url, e)
        return {
            "online": False,
            "status_code": None,
            "response_time_ms": None,
            "error": str(e),
        }


async def fetch_jellyfin_info(base_url: str, api_key: str) -> dict[str, Any]:
    """Fetch Jellyfin server info and library stats.
    
    Returns dict with:
    - server_name: str
    - version: str
    - total_movies: int
    - total_series: int
    - total_episodes: int
    - error: str | None
    """
    try:
        headers = {"X-Emby-Token": api_key}
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get server info
            server_resp = await client.get(
                urljoin(base_url, "/System/Info/Public"),
                headers=headers,
            )
            server_resp.raise_for_status()
            server_info = server_resp.json()
            
            # Get library stats
            items_resp = await client.get(
                urljoin(base_url, "/Items/Counts"),
                headers=headers,
            )
            items_resp.raise_for_status()
            counts = items_resp.json()
            
            return {
                "server_name": server_info.get("ServerName", "Jellyfin"),
                "version": server_info.get("Version", "unknown"),
                "total_movies": counts.get("MovieCount", 0),
                "total_series": counts.get("SeriesCount", 0),
                "total_episodes": counts.get("EpisodeCount", 0),
                "error": None,
            }
    except Exception as e:  # noqa: BLE001
        log.warning("jellyfin fetch failed: %s", e)
        return {
            "server_name": None,
            "version": None,
            "total_movies": 0,
            "total_series": 0,
            "total_episodes": 0,
            "error": str(e),
        }


async def fetch_radarr_info(base_url: str, api_key: str) -> dict[str, Any]:
    """Fetch Radarr movie stats and queue.
    
    Returns dict with:
    - total_movies: int
    - wanted_movies: int
    - queue_size: int
    - disk_space_free_gb: float
    - error: str | None
    """
    try:
        headers = {"X-Api-Key": api_key}
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get movie count
            movies_resp = await client.get(
                urljoin(base_url, "/api/v3/movie"),
                headers=headers,
            )
            movies_resp.raise_for_status()
            movies = movies_resp.json()
            total_movies = len(movies)
            
            # Get wanted/missing
            wanted_resp = await client.get(
                urljoin(base_url, "/api/v3/wanted/missing"),
                headers=headers,
                params={"pageSize": 1},  # just get totalRecords
            )
            wanted_resp.raise_for_status()
            wanted_data = wanted_resp.json()
            wanted_movies = wanted_data.get("totalRecords", 0)
            
            # Get queue
            queue_resp = await client.get(
                urljoin(base_url, "/api/v3/queue"),
                headers=headers,
            )
            queue_resp.raise_for_status()
            queue_data = queue_resp.json()
            queue_size = len(queue_data)
            
            # Get disk space
            disk_resp = await client.get(
                urljoin(base_url, "/api/v3/diskspace"),
                headers=headers,
            )
            disk_resp.raise_for_status()
            disks = disk_resp.json()
            free_gb = sum(d.get("freeSpace", 0) for d in disks) / (1024**3)
            
            return {
                "total_movies": total_movies,
                "wanted_movies": wanted_movies,
                "queue_size": queue_size,
                "disk_space_free_gb": round(free_gb, 2),
                "error": None,
            }
    except Exception as e:  # noqa: BLE001
        log.warning("radarr fetch failed: %s", e)
        return {
            "total_movies": 0,
            "wanted_movies": 0,
            "queue_size": 0,
            "disk_space_free_gb": 0,
            "error": str(e),
        }


async def fetch_qbittorrent_info(base_url: str, username: str, password: str) -> dict[str, Any]:
    """Fetch qBittorrent torrent stats.
    
    Returns dict with:
    - total_torrents: int
    - downloading: int
    - seeding: int
    - paused: int
    - total_speed_down_mbps: float
    - total_speed_up_mbps: float
    - error: str | None
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Login
            login_resp = await client.post(
                urljoin(base_url, "/api/v2/auth/login"),
                data={"username": username, "password": password},
            )
            login_resp.raise_for_status()
            
            # Get all torrents
            torrents_resp = await client.get(
                urljoin(base_url, "/api/v2/torrents/info"),
            )
            torrents_resp.raise_for_status()
            torrents = torrents_resp.json()
            
            # Count by state
            total = len(torrents)
            downloading = sum(1 for t in torrents if t.get("state") in ["downloading", "metaDL"])
            seeding = sum(1 for t in torrents if t.get("state") in ["uploading", "stalledUP"])
            paused = sum(1 for t in torrents if t.get("state") in ["pausedDL", "pausedUP"])
            
            # Sum speeds
            total_down = sum(t.get("dlspeed", 0) for t in torrents) / (1024**2)  # MB/s
            total_up = sum(t.get("upspeed", 0) for t in torrents) / (1024**2)
            
            return {
                "total_torrents": total,
                "downloading": downloading,
                "seeding": seeding,
                "paused": paused,
                "total_speed_down_mbps": round(total_down, 2),
                "total_speed_up_mbps": round(total_up, 2),
                "error": None,
            }
    except Exception as e:  # noqa: BLE001
        log.warning("qbittorrent fetch failed: %s", e)
        return {
            "total_torrents": 0,
            "downloading": 0,
            "seeding": 0,
            "paused": 0,
            "total_speed_down_mbps": 0,
            "total_speed_up_mbps": 0,
            "error": str(e),
        }
