"""Wallpaper upload/storage for the Settings page.

Wallpapers are written to a directory on disk and served via FastAPI's
FileResponse at `/wallpapers/{filename}`. The directory is created lazily on
first use.

In Docker, the directory is `/app/wallpapers` (mounted as a named volume by
docker-compose). Locally, it defaults to `<project>/backend/wallpapers`.
Override either by setting the `WALLPAPER_DIR` environment variable.
"""
from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import UploadFile

# Storage directory. Priority:
#   1. WALLPAPER_DIR env var (explicit override — useful for Docker)
#   2. <project>/backend/wallpapers (sibling of the app package, i.e.
#      /app/wallpapers in the Docker container)
# Resolved once at import time so all calls agree on the same path.
_WALLPAPER_DIR = Path(
    os.environ.get("WALLPAPER_DIR", Path(__file__).resolve().parent.parent / "wallpapers")
)

# Allowed content types. Anything else is rejected with a ValueError that the
# FastAPI layer turns into a 400.
_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
    "image/avif",
    "image/svg+xml",
}

# File extension inferred from content type.
_EXT_BY_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
}

# Max upload size: 8 MiB. Keeps a stray multi-gigabyte upload from OOMing the
# backend in dev. Match the value in any future nginx/proxy limits.
_MAX_BYTES = 8 * 1024 * 1024

# filenames are `{random}.{ext}` — this regex validates what we serve back so
# an attacker can't path-traverse via `/wallpapers/../../etc/passwd`.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+\.(png|jpe?g|webp|gif|avif|svg)$")


def _wallpaper_dir() -> Path:
    d = _WALLPAPER_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _guess_ext(upload: UploadFile) -> str:
    ct = (upload.content_type or "").lower().split(";")[0].strip()
    if ct in _EXT_BY_TYPE:
        return _EXT_BY_TYPE[ct]
    # Fall back to filename suffix if the client lied about content-type.
    if upload.filename:
        suffix = Path(upload.filename).suffix.lower()
        if suffix in {ext for ext in _EXT_BY_TYPE.values()}:
            return suffix
    raise ValueError(f"unsupported wallpaper content type: {upload.content_type!r}")


async def save_upload(upload: UploadFile) -> tuple[str, str, str]:
    """Persist an uploaded image to disk.

    Returns ``(id, name, url)`` where ``id`` is the on-disk filename (incl. ext),
    ``name`` is the original client filename, and ``url`` is the path the
    frontend should use as the ``<img src>`` (served by the route in main.py).

    Raises ``ValueError`` for unsupported types or oversize uploads — the
    FastAPI handler turns those into HTTP 400.
    """
    ext = _guess_ext(upload)
    if upload.content_type and upload.content_type.lower() not in _ALLOWED_CONTENT_TYPES:
        # _guess_ext already rejected it, but be explicit for callers that
        # supplied only a filename.
        raise ValueError(f"unsupported wallpaper content type: {upload.content_type!r}")

    fid = f"{secrets.token_hex(8)}{ext}"
    target = _wallpaper_dir() / fid

    written = 0
    # Stream the upload in chunks to avoid loading the whole file into memory.
    # UploadFile.read() defaults to 1MB chunks; we cap total bytes manually.
    with target.open("wb") as fh:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > _MAX_BYTES:
                fh.close()
                target.unlink(missing_ok=True)
                raise ValueError(
                    f"wallpaper exceeds max size ({_MAX_BYTES // (1024 * 1024)} MiB)"
                )
            fh.write(chunk)

    name = upload.filename or fid
    url = f"/wallpapers/{fid}"
    return fid, name, url


def list_all() -> list[dict[str, Any]]:
    """Return every stored wallpaper as a list of dicts shaped for WallpaperItem."""
    out: list[dict[str, Any]] = []
    d = _wallpaper_dir()
    if not d.exists():
        return out
    for p in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file() and _SAFE_NAME.match(p.name):
            out.append({"id": p.name, "url": f"/wallpapers/{p.name}", "name": p.name})
    return out


def respond(filename: str):
    """Return a FileResponse for a wallpaper. Raises FileNotFoundError if missing.

    The caller (main.py) wraps this in a 404 handler. The filename must match
    ``_SAFE_NAME`` so path traversal via .. is impossible.
    """
    from fastapi.responses import FileResponse

    if not _SAFE_NAME.match(filename):
        # Sanitize — never let a bare path through. Treat as not-found so the
        # 404 handler responds cleanly instead of leaking validation internals.
        raise FileNotFoundError(filename)
    p = _wallpaper_dir() / filename
    if not p.is_file():
        raise FileNotFoundError(filename)
    return FileResponse(p)