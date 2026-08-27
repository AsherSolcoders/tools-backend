"""Canonical site URLs.

SITE_URL is configured as the apex domain while the site serves from www, so
every URL we emit — sitemap entries, JSON-LD `@id`s, breadcrumbs — is built from
one normalized origin instead of the raw setting.
"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from app.config import settings

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def canonical_base() -> str:
    """Site origin, forced to https + www (localhost and IPs are left alone)."""
    raw = settings.site_url.rstrip("/")
    parts = urlsplit(raw if "//" in raw else f"https://{raw}")
    host = parts.netloc
    if host.split(":")[0] in _LOCAL_HOSTS:
        return urlunsplit((parts.scheme, host, "", "", ""))
    if not host.startswith("www."):
        host = f"www.{host}"
    return urlunsplit(("https", host, "", "", ""))


def canonical_url(path: str = "/") -> str:
    """Absolute URL for a path.

    The root keeps its slash; everything else is emitted without a trailing one,
    matching the canonical tags the frontend renders.
    """
    base = canonical_base()
    if not path or path == "/":
        return f"{base}/"
    return f"{base}/{path.strip('/')}"
