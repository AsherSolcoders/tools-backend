"""Security helpers: upload validation, sanitization, secure headers, password hashing."""
from __future__ import annotations

import html
import re

import bcrypt
from fastapi import UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings


def hash_password(raw: str) -> str:
    # bcrypt operates on at most 72 bytes.
    return bcrypt.hashpw(raw.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8")[:72], hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def sanitize_text(value: str) -> str:
    """Escape HTML to neutralize stored/reflected XSS in user-supplied text."""
    return html.escape(value, quote=True)


class UploadValidationError(ValueError):
    pass


# Map a detected content type to the extensions that legitimately produce it.
_CONTENT_FAMILY: dict[str, set[str]] = {
    "jpg": {"jpg", "jpeg"},
    "zip": {"docx", "xlsx", "pptx", "zip"},  # Office Open XML files are ZIP containers
    "ole": {"doc", "xls", "ppt"},  # legacy Office binary formats
}


def _sniff_content(content: bytes) -> str | None:
    """Detect the true file type from its magic bytes, independent of filename."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "gif"
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.startswith(b"PK\x03\x04"):
        return "zip"
    if content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"  # legacy .doc/.xls/.ppt
    if content.startswith(b"BM"):
        return "bmp"
    if content[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return None


def validate_upload(
    file: UploadFile,
    allowed_exts: list[str] | None,
    content: bytes,
    max_bytes: int | None = None,
) -> None:
    """Validate an upload against size, extension, and real content type.

    `allowed_exts` is the tool's accepted extension list (e.g. ['png', 'jpg']).
    An empty/None list means the tool accepts any type.
    `max_bytes` overrides the global size cap (used for per-tool limits).

    Enforcement is two-layered: the filename extension must be allowed, AND the
    file's actual magic bytes must match an allowed type — so a PDF renamed to
    .png (or an image renamed to .pdf) is still rejected.
    """
    limit = max_bytes if max_bytes is not None else settings.max_upload_bytes
    if len(content) > limit:
        raise UploadValidationError(f"File exceeds the {limit // (1024 * 1024)} MB limit.")
    if not allowed_exts:
        return

    allowed = {e.lower().lstrip(".") for e in allowed_exts}
    allowed_label = ", ".join(sorted(allowed))

    name = (file.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in allowed:
        raise UploadValidationError(
            f"Unsupported file type '.{ext or '?'}'. This tool only accepts: {allowed_label}."
        )

    # Verify the real content type matches an allowed extension.
    detected = _sniff_content(content)
    if detected is not None:
        family = _CONTENT_FAMILY.get(detected, {detected})
        if not (family & allowed):
            raise UploadValidationError(
                f"This file's contents look like a .{detected} file, but this tool "
                f"only accepts: {allowed_label}."
            )


# An SVG is XML, not a bitmap, so it can carry script. Served from our own domain
# and opened directly in a tab, that script runs in our origin. These patterns are
# grounds for REJECTING the upload rather than trying to clean it: rejecting fails
# closed, whereas sanitizing SVG is notoriously easy to get subtly wrong.
_SVG_FORBIDDEN: tuple[tuple[re.Pattern[bytes], str], ...] = (
    (re.compile(rb"<\s*script", re.I), "a <script> block"),
    (re.compile(rb"<\s*foreignObject", re.I), "a <foreignObject> block"),
    (re.compile(rb"javascript\s*:", re.I), "a javascript: URL"),
    (re.compile(rb"<!\s*ENTITY", re.I), "an XML entity declaration"),
    # onload=, onclick=, onmouseover=… the classic scriptless-looking vector.
    (re.compile(rb"\son[a-z]+\s*=", re.I), "an inline event handler"),
)


def validate_svg(content: bytes) -> None:
    """Reject an SVG upload that could execute script when opened directly.

    Raises UploadValidationError with a message naming what was found, so the
    author knows how to fix their file instead of seeing a generic failure.
    """
    if b"<svg" not in content.lower():
        raise UploadValidationError("This .svg file doesn't look like an SVG image.")
    for pattern, what in _SVG_FORBIDDEN:
        if pattern.search(content):
            raise UploadValidationError(
                f"This SVG was rejected because it contains {what}. Re-export it as a "
                f"plain SVG (most editors offer 'no scripting'), or upload a PNG instead."
            )


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Uploaded files are user content served from our own origin. `sandbox` puts
        # any direct navigation to them in an opaque origin with scripting disabled,
        # so a script-bearing SVG can't run even if one is already on disk from
        # before validate_svg existed. Rendering via <img> is unaffected — browsers
        # never execute scripts in SVG loaded that way.
        if request.url.path.startswith("/storage"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
            )
            # Stored filenames are random UUIDs that are never rewritten (a changed
            # image gets a new name), so the bytes behind a URL can't change. That
            # makes `immutable` safe and lets repeat visits skip revalidation
            # entirely instead of spending a 304 round-trip per image.
            response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
