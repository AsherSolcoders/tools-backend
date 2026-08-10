"""URL slug normalization.

The API is the authority on slug shape: the admin UI also tidies slugs as you
type, but a slug arriving from any client is normalized here so a stray space or
punctuation mark can never reach the database and produce a URL like
`/%20%20%20%20seo-ppc-marketing-solutions`.
"""
from __future__ import annotations

import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Turn arbitrary text into a lowercase, hyphen-separated ASCII slug."""
    if not value:
        return ""
    # Fold accents to ASCII ("café" -> "cafe") so they survive as readable text
    # instead of being dropped by the character filter below.
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return _NON_SLUG.sub("-", folded.lower()).strip("-")


def normalize_slug_list(value: str | None) -> str | None:
    """Normalize a comma-separated slug list (used for `old_slugs` redirects).

    Blank entries and duplicates are dropped; returns None for an empty result so
    the column stays NULL rather than holding an empty string.
    """
    if not value:
        return None
    seen: list[str] = []
    for part in value.split(","):
        slug = slugify(part)
        if slug and slug not in seen:
            seen.append(slug)
    return ",".join(seen) or None
