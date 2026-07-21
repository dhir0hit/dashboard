"""SQLite-backed persistence for POST /api/config.

Uses stdlib sqlite3 — no extra dependency. Schema is intentionally simple:
one row (id INTEGER PK AUTOINCREMENT) holding a JSON blob + updated_at.
GET returns the latest row.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import DashboardConfig


_SCHEMA = """
CREATE TABLE IF NOT EXISTS dashboard_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    with _connect(path) as c:
        c.executescript(_SCHEMA)
        c.commit()


def save(path: str, cfg: DashboardConfig) -> tuple[int, str]:
    init_db(path)
    payload = cfg.model_dump_json()
    updated_at = datetime.now(timezone.utc).isoformat()
    with _connect(path) as c:
        cur = c.execute(
            "INSERT INTO dashboard_config (payload, updated_at) VALUES (?, ?)",
            (payload, updated_at),
        )
        c.commit()
        return cur.lastrowid or 0, updated_at


def latest(path: str) -> Optional[DashboardConfig]:
    if not Path(path).exists():
        return None
    with _connect(path) as c:
        row = c.execute(
            "SELECT payload FROM dashboard_config ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    try:
        return DashboardConfig.model_validate_json(row["payload"])
    except Exception:
        return None