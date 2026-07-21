# `backend/app/config_store.py`

SQLite-backed persistence for `/api/config`. Stdlib `sqlite3` only — no
extra dependency.

## Schema

A single table `dashboard_config` with one row holding the JSON-serialized
`DashboardConfig` plus an `updated_at` timestamp:

```sql
CREATE TABLE IF NOT EXISTS dashboard_config (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    payload     TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
```

Only the latest row (max `id`) is ever read; older rows are kept for
post-mortem but never returned. In practice the app writes and re-reads
row 1 for the entire lifetime of the database — `save()` always inserts
a new row and `latest()` returns the highest-id row via
`ORDER BY id DESC LIMIT 1`.

## Public functions

### `init_db(path: str) -> None`

- Persists the chosen path on the module so subsequent `latest()` / `save()`
  calls don't need to pass it.
- Connects (creates the file if missing) and runs the `CREATE TABLE IF NOT
  EXISTS` above.
- Called once at app startup from `main._startup()`.

### `latest(path: str | None = None) -> Optional[DashboardConfig]`

- Reads the highest-id row via `SELECT payload FROM dashboard_config
  ORDER BY id DESC LIMIT 1`.
- `json.loads` the payload, constructs `DashboardConfig(**data)`.
- Returns `None` if the table is empty (caller in `main.get_config` returns
  `DashboardConfig()` defaults in that case).
- `path` optional — falls back to the path captured by `init_db`.

### `save(path: str | None, cfg: DashboardConfig) -> tuple[int, str]`

- Sets `cfg.updated_at = datetime.now(timezone.utc).isoformat()`.
- Serializes via `cfg.model_dump_json()` (pydantic's native JSON encoder —
  handles enums, datetimes, etc. correctly).
- INSERTs a new row (id auto-increments). `cur.lastrowid or 0` is returned
  in case INSERT somehow failed.
- Returns `(new_row_id, updated_at_string)` — the caller in
  `main.put_config` / `post_config` backfills these onto the response.

## Notable details

- **Single-row convention**: the implementation always inserts; `latest`
  always reads `max(id)`. Practical effect is "row 1" stays the live
  config. There is no UPDATE path — every save is an insert, which gives
  a cheap audit trail (older config revisions stay in the table, just not
  surfaced).
- **No concurrency control**: SQLite's default serialized access is
  sufficient given the single-process uvicorn deployment. If you scale
  horizontally, switch to a real DB or wrap writes in a transaction.
- **JSON not column-per-field**: the schema intentionally stores a JSON
  blob so the model can evolve (add new config keys) without migrations.
  The pydantic `DashboardConfig` validates the shape on read.
- **UTC timestamps**: `datetime.now(timezone.utc).isoformat()` — parsed
  correctly by JS `new Date()` on the frontend.
- **No vacuum / cleanup**: the table grows by one row per save. For
  long-running deployments with frequent saves, add a periodic
  `DELETE FROM dashboard_config WHERE id < (SELECT MAX(id) FROM dashboard_config)`
  task.
- **`model_dump_json` not `model_dump` + `json.dumps`**: pydantic v2's
  native JSON serializer handles enums correctly; an `model_dump()` then
  `json.dumps` round-trip would turn enums into plain strings (which is
  usually fine but less type-safe). The repo uses the native path.

## Errors

- `sqlite3.OperationalError` on a corrupted or unreadable path propagates
  to the caller — the FastAPI layer turns it into a 500. Cheap to make
  the path read-only for testing; the table will simply be empty.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
