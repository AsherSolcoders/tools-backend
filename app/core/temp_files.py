"""Runtime temp-file lifecycle.

Workflow:  upload -> /tmp/uploads  ->  process  ->  /tmp/results  ->  download  ->  auto-delete.

Files older than TEMP_FILE_TTL_MINUTES (default 10) are swept by a background task.
NOTHING here is persisted to the database — this is the heart of the
"no visitor data storage" rule.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path

from app.config import settings

UPLOAD_DIR = Path(settings.tmp_upload_dir)
RESULT_DIR = Path(settings.tmp_result_dir)


def ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(filename: str) -> str:
    """Strip any path components; keep only a safe basename."""
    return os.path.basename(filename).replace("\\", "_").replace("/", "_") or "file"


def new_upload_path(original_name: str) -> Path:
    ensure_dirs()
    token = uuid.uuid4().hex
    return UPLOAD_DIR / f"{token}__{_safe_name(original_name)}"


def new_result_path(suffix_name: str) -> Path:
    ensure_dirs()
    token = uuid.uuid4().hex
    return RESULT_DIR / f"{token}__{_safe_name(suffix_name)}"


def resolve_result(token_name: str) -> Path | None:
    """Resolve a download request to a real file, guarding against traversal."""
    ensure_dirs()
    candidate = (RESULT_DIR / _safe_name(token_name)).resolve()
    if RESULT_DIR.resolve() in candidate.parents and candidate.is_file():
        return candidate
    return None


def cleanup_once() -> int:
    """Delete files older than the TTL. Returns the number removed."""
    ttl_seconds = settings.temp_file_ttl_minutes * 60
    cutoff = time.time() - ttl_seconds
    removed = 0
    for directory in (UPLOAD_DIR, RESULT_DIR):
        if not directory.exists():
            continue
        for entry in directory.iterdir():
            try:
                if entry.is_file() and entry.stat().st_mtime < cutoff:
                    entry.unlink()
                    removed += 1
            except OSError:
                # Best-effort; a file may be mid-write or already gone.
                continue
    return removed


async def cleanup_loop(interval_seconds: int = 60) -> None:
    """Background sweeper; runs for the lifetime of the app."""
    ensure_dirs()
    while True:
        try:
            cleanup_once()
        except Exception:  # never let the sweeper die
            pass
        await asyncio.sleep(interval_seconds)
