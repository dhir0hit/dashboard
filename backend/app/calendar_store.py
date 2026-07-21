"""SQLite-backed persistence for calendar events + Google OAuth tokens.

Separate from dashboard_config — calendar events are their own table so
they can be queried by date range without loading the whole config blob.
Google tokens are stored in a single-row table (one user = one token).
"""
from __future__ import annotations

import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import CalendarEvent


_SCHEMA = """
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    date TEXT NOT NULL,
    time TEXT,
    duration_minutes INTEGER,
    source TEXT NOT NULL DEFAULT 'local',
    done INTEGER NOT NULL DEFAULT 0,
    google_event_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS google_token (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TEXT,
    email TEXT,
    scope TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_date ON calendar_events(date);
CREATE INDEX IF NOT EXISTS idx_events_source ON calendar_events(source);
"""


def _connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_calendar_db(path: str) -> None:
    with _connect(path) as c:
        c.executescript(_SCHEMA)
        c.commit()


def _gen_id() -> str:
    return f"evt-{secrets.token_hex(4)}"


def _row_to_event(row: sqlite3.Row) -> CalendarEvent:
    return CalendarEvent(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        date=row["date"],
        time=row["time"],
        duration_minutes=row["duration_minutes"],
        source=row["source"],
        done=bool(row["done"]),
        google_event_id=row["google_event_id"],
    )


def create_event(path: str, event: CalendarEvent) -> CalendarEvent:
    init_calendar_db(path)
    if not event.id:
        event.id = _gen_id()
    now = datetime.now(timezone.utc).isoformat()
    with _connect(path) as c:
        c.execute(
            """INSERT INTO calendar_events
               (id, title, description, date, time, duration_minutes,
                source, done, google_event_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event.id, event.title, event.description, event.date,
             event.time, event.duration_minutes, event.source, int(event.done),
             event.google_event_id, now, now),
        )
        c.commit()
    return event


def list_events(
    path: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source: Optional[str] = None,
) -> list[CalendarEvent]:
    if not Path(path).exists():
        return []
    sql = "SELECT * FROM calendar_events"
    conditions = []
    params: list = []
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    if source:
        conditions.append("source = ?")
        params.append(source)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY date, time IS NULL, time"
    with _connect(path) as c:
        rows = c.execute(sql, params).fetchall()
    return [_row_to_event(r) for r in rows]


def update_event(path: str, event_id: str, patch: dict) -> Optional[CalendarEvent]:
    if not Path(path).exists():
        return None
    allowed = {"title", "description", "date", "time",
               "duration_minutes", "done"}
    updates = {k: v for k, v in patch.items() if k in allowed}
    if not updates:
        return get_event(path, event_id)
    # Convert bool done to int
    if "done" in updates:
        updates["done"] = int(updates["done"])
    now = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [now, event_id]
    with _connect(path) as c:
        c.execute(
            f"UPDATE calendar_events SET {set_clause}, updated_at = ? WHERE id = ?",
            params,
        )
        c.commit()
    return get_event(path, event_id)


def delete_event(path: str, event_id: str) -> bool:
    if not Path(path).exists():
        return False
    with _connect(path) as c:
        cur = c.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        c.commit()
        return cur.rowcount > 0


def get_event(path: str, event_id: str) -> Optional[CalendarEvent]:
    if not Path(path).exists():
        return None
    with _connect(path) as c:
        row = c.execute(
            "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
        ).fetchone()
    return _row_to_event(row) if row else None


def upsert_google_event(path: str, event: CalendarEvent) -> CalendarEvent:
    """Insert or update a Google-sourced event (matched by google_event_id)."""
    init_calendar_db(path)
    if not event.google_event_id:
        return create_event(path, event)
    with _connect(path) as c:
        row = c.execute(
            "SELECT id FROM calendar_events WHERE google_event_id = ?",
            (event.google_event_id,),
        ).fetchone()
    if row:
        update_event(path, row["id"], {
            "title": event.title, "description": event.description,
            "date": event.date, "time": event.time,
            "duration_minutes": event.duration_minutes,
        })
        return get_event(path, row["id"])
    return create_event(path, event)


# --- Google token storage ----------------------------------------------


def save_google_token(
    path: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: str,
    email: Optional[str] = None,
    scope: Optional[str] = None,
) -> None:
    init_calendar_db(path)
    now = datetime.now(timezone.utc).isoformat()
    with _connect(path) as c:
        c.execute(
            """INSERT INTO google_token (id, access_token, refresh_token, expires_at,
               email, scope, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 access_token=excluded.access_token,
                 refresh_token=COALESCE(excluded.refresh_token, google_token.refresh_token),
                 expires_at=excluded.expires_at,
                 email=COALESCE(excluded.email, google_token.email),
                 scope=excluded.scope,
                 updated_at=excluded.updated_at""",
            (access_token, refresh_token, expires_at, email, scope, now),
        )
        c.commit()


def get_google_token(path: str) -> Optional[dict]:
    if not Path(path).exists():
        return None
    with _connect(path) as c:
        row = c.execute("SELECT * FROM google_token WHERE id = 1").fetchone()
    if not row:
        return None
    return {
        "access_token": row["access_token"],
        "refresh_token": row["refresh_token"],
        "expires_at": row["expires_at"],
        "email": row["email"],
        "scope": row["scope"],
    }


def clear_google_token(path: str) -> None:
    if not Path(path).exists():
        return
    with _connect(path) as c:
        c.execute("DELETE FROM google_token WHERE id = 1")
        c.commit()


def is_google_token_valid(path: str) -> bool:
    tok = get_google_token(path)
    if not tok or not tok.get("access_token") or not tok.get("expires_at"):
        return False
    try:
        exp = datetime.fromisoformat(tok["expires_at"].replace("Z", "+00:00"))
        return datetime.now(timezone.utc) < exp
    except (ValueError, TypeError):
        return False
