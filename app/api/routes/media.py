"""On-demand image thumbnails.

The blog listing displays a 234x176 card and a 48x48 sidebar icon, but was loading
the full-size upload for both — roughly 2 MB each, 21 MB for one page. This serves
a right-sized WebP instead.

Thumbnails are generated on first request and cached on disk, so images uploaded
before this existed get one automatically; no backfill is required for correctness
(though warming them is nice). If a thumbnail genuinely can't be produced — SVG,
animated GIF — the request redirects to the original file rather than 404ing, so a
card never renders broken.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse, RedirectResponse

from app.config import settings
from app.core.images import THUMB_BOXES, THUMB_WIDTHS, make_thumbnail

router = APIRouter(prefix="/media", tags=["media"])

# Stored uploads are always `<uuid4 hex>.<ext>`; anything else is not ours and is
# rejected before touching the filesystem (also blocks traversal via the name).
_NAME_RE = re.compile(r"^[a-f0-9]{32}\.[a-z0-9]{2,5}$", re.I)

# Filenames are content-addressed by a random UUID and never rewritten, so a URL's
# bytes can't change — safe to cache for a year and skip revalidation entirely.
_IMMUTABLE = "public, max-age=31536000, immutable"


# "480" keeps the source ratio; "560x360" crops to that exact box.
_SIZE_RE = re.compile(r"^(\d{2,4})(?:x(\d{2,4}))?$")


@router.get("/thumb/{size}/{name}")
def thumbnail(size: str, name: str):
    match = _SIZE_RE.match(size)
    if not match:
        raise HTTPException(status_code=404, detail="Unsupported thumbnail size")
    width = int(match.group(1))
    height = int(match.group(2)) if match.group(2) else None
    # Only sizes we actually render are allowed, so nobody can fill the disk by
    # requesting thousands of variants.
    if height is None:
        if width not in THUMB_WIDTHS:
            raise HTTPException(status_code=404, detail="Unsupported thumbnail size")
    elif (width, height) not in THUMB_BOXES:
        raise HTTPException(status_code=404, detail="Unsupported thumbnail size")
    if not _NAME_RE.match(name):
        raise HTTPException(status_code=404, detail="Not found")

    source = Path(settings.blog_images_dir) / name
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    # Keyed by the requested size string, so "480" and "560x360" cache apart.
    cached = Path(settings.blog_images_dir) / "thumbs" / size / f"{source.stem}.webp"
    if cached.is_file():
        return FileResponse(cached, media_type="image/webp", headers={"Cache-Control": _IMMUTABLE})

    data = make_thumbnail(source.read_bytes(), width, height)
    if data is None:
        # Not thumbnail-able (SVG, animated, or Pillow unavailable). Point at the
        # original so the caller still gets a usable image instead of a 404.
        return RedirectResponse(f"/storage/blog-images/{name}", status_code=307)

    try:
        cached.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp name then rename: two concurrent requests for the same
        # thumbnail can never leave a half-written file for the next reader.
        tmp = cached.with_suffix(f".{size}.part")
        tmp.write_bytes(data)
        tmp.replace(cached)
    except OSError:
        # Read-only or full disk — serve what we just generated from memory rather
        # than 500ing. Every request then regenerates, which is slow but not broken.
        pass

    return Response(content=data, media_type="image/webp", headers={"Cache-Control": _IMMUTABLE})
