# `backend/app/wallpapers.py`

Wallpaper upload/storage for the Settings page. Minimal, dependency-free
implementation sufficient for the frontend-visuals task. Wallpapers land on
disk under `backend/wallpapers/` and are served via FastAPI's `FileResponse`
at `/wallpapers/{filename}` in `main.py`.

## Module-private constants

| Name | Value | Purpose |
|---|---|---|
| `_WALLPAPER_DIR` | `Path(__file__).resolve().parent.parent / "wallpapers"` | Resolved once at import — the on-disk storage directory. |
| `_ALLOWED_CONTENT_TYPES` | `{image/png, image/jpeg, image/jpg, image/webp, image/gif, image/avif, image/svg+xml}` | Allowed upload MIME types. |
| `_EXT_BY_TYPE` | content-type → extension mapping (e.g. `"image/png": ".png"`, `"image/svg+xml": ".svg"`) | Used to filename generated ids. Note `image/jpeg` and `image/jpg` both map to `.jpg`. |
| `_MAX_BYTES` | `8 * 1024 * 1024` (8 MiB) | Hard upload size cap. |
| `_SAFE_NAME` | `re.compile(r"^[A-Za-z0-9_-]+\.(png|jpe?g|webp|gif|avif|svg)$")` | Path-traversal guard — validates every served and listed filename. |

## Module-private functions

### `_wallpaper_dir() -> Path`

- Lazily `mkdir(parents=True, exist_ok=True)` on `_WALLPAPER_DIR` and
  returns the path. Idempotent — safe to call on every operation.

### `_guess_ext(upload: UploadFile) -> str`

- Looks up `upload.content_type` (lowercased, params stripped) in
  `_EXT_BY_TYPE`. If found, returns the extension.
- Falls back to the suffix of `upload.filename` if the client lied about
  content-type. Tolerates any extension in `_EXT_BY_TYPE.values()`.
- Raises `ValueError("unsupported wallpaper content type: ...")` if
  neither path matches. The route handler maps this to HTTP 400.

## Public functions

### `save_upload(upload: UploadFile) -> tuple[str, str, str]` (async)

Entry point for `POST /api/config/wallpaper` (the route handler
`main.upload_wallpaper` awaits this).

Returns `(id, name, url)` where:
- `id` is the on-disk filename: `<16-hex><ext>`, where the hex comes from
  `secrets.token_hex(8)` (16 char hex string).
- `name` is the original upload filename (kept for display in the UI)
  or the generated `id` if the upload omitted a filename.
- `url` is `/wallpapers/<id>` — the URL the frontend uses in `<img src>`.

Streaming behavior:
- The upload is read in **1 MiB chunks** (`await upload.read(1024 * 1024)`),
  written directly to disk. Memory usage stays roughly constant regardless
  of upload size — no whole-file read into memory.
- A running byte counter (`written`) accumulates chunk sizes; if any
  chunk pushes it past `_MAX_BYTES`, the partial file is closed and
  `unlink`'d, then `ValueError("wallpaper exceeds max size (8 MiB)")`
  is raised. The client sees HTTP 400.

Validation order: `_guess_ext` first (which raises on bad content type),
then an explicit allowlist re-check, then size enforcement during the
streaming write.

### `list_all() -> list[dict[str, Any]]`

Returns `[{"id": ..., "url": ..., "name": ...}, ...]` for every file in
`_WALLPAPER_DIR` (lazily creating the directory first).

- **Sorted by mtime descending** — most recently uploaded wallpapers appear
  first in the frontend picker.
- Files are filtered by `_SAFE_NAME.match(p.name)` — anything that doesn't
  match the safe-name regex is skipped. Combined with `p.is_file()`, this
  excludes directories, hidden files, and any stray non-wallpaper content.
- The `name` field in each entry is the on-disk filename (the generated
  `<hex>.<ext>`), NOT the original upload filename — there's no
  metadata sidecar for that. The frontend stores the original name in
  the SQLite config when the user picks a wallpaper.

### `respond(filename: str)`

Used by `GET /wallpapers/{filename}` in `main.py`.

- Validates `filename` against `_SAFE_NAME` first — anything that doesn't
  match raises `FileNotFoundError` → mapped to 404 by the route. This is
  path-traversal defense; an attacker can't escape the wallpapers
  directory via `..`.
- Returns `FileResponse(_WALLPAPER_DIR / filename)`. `FileResponse` is
  imported locally (inside the function) to keep the import graph lean
  for non-route callers.
- A missing file also raises `FileNotFoundError` (is_file() check) → 404.

## Notable details

- **No metadata database**: the wallpaper "name" is preserved only in the
  response URL (and, when picked, in the SQLite config). The wallpapers
  directory itself is flat — files are pure ids, no sidecar JSON.
- **No thumbnails**: the frontend `<img>` tag renders the full-resolution
  file. For very large uploads, consider generating a thumbnail in
  `save_upload` and serving it via `/wallpapers/thumb_<id>`.
- **Lazy directory creation**: `_WALLPAPER_DIR.mkdir(parents=True,
  exist_ok=True)` runs inside `_wallpaper_dir()` on every call, so the
  directory only exists after the first successful operation. This avoids
  import-time side effects and keeps the repo stateless until the user
  actually uses the feature.
- **`FileResponse` is lazy**: FastAPI streams the file in chunks, so memory
  usage stays flat regardless of wallpaper size. The directory is read
  fresh on each `GET` — no caching of file existence.
- **No auth on `/wallpapers/*`**: the route is `include_in_schema=False`
  but unauthenticated. The compose stack doesn't publish the backend
  port externally (only nginx on :8888 proxies it), so wallpapers are only
  reachable through the dashboard origin in production. If you publish
  the backend directly, anyone with the URL can fetch any wallpaper.
- **Streaming upload matters in dev**: the chunked write means a 50 MiB
  upload won't OOM the container before hitting the 8 MiB cap — the
  validator fires after ~8 chunks, not after buffering the whole file.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
