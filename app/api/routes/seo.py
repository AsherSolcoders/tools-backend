"""SEO endpoints: dynamic sitemap.xml and robots.txt."""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Blog
from app.models.blog import BlogStatus
from app.tools import list_categories, list_tools

router = APIRouter(tags=["seo"])


def _canonical_base() -> str:
    """Site origin with https and the www host.

    SITE_URL is configured as the apex domain, but the site serves from www — so
    without this the sitemap advertised a different host than every canonical tag,
    which splits ranking signals between two URLs.
    """
    base = settings.site_url.rstrip("/")
    parts = urlsplit(base if "//" in base else f"https://{base}")
    host = parts.netloc
    is_local = host.split(":")[0] in {"localhost", "127.0.0.1", "0.0.0.0"}
    if not is_local:
        if not host.startswith("www."):
            host = f"www.{host}"
        return urlunsplit(("https", host, "", "", ""))
    return urlunsplit((parts.scheme, host, "", "", ""))


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    base = _canonical_base()
    # Tools, categories, and posts all live flat at /<slug> (no /tools/ or /category/ prefix).
    # Only canonical URLs belong in a sitemap. /faq and /about were listed here but
    # both 307 to /faqs and /about-us, so search engines were being pointed at
    # redirects instead of the real pages.
    urls: list[str] = [
        f"{base}/",
        f"{base}/tools",
        f"{base}/blog",
        f"{base}/faqs",
        f"{base}/about-us",
        f"{base}/privacy-policy",
        f"{base}/terms-condition",
        f"{base}/disclaimer",
    ]
    urls += [f"{base}/{c.slug}" for c in list_categories()]
    urls += [f"{base}/{t.slug}" for t in list_tools()]
    blogs = db.execute(select(Blog).where(Blog.status == BlogStatus.published)).scalars().all()
    urls += [f"{base}/{b.slug}" for b in blogs]

    items = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{items}\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


# AI crawlers/assistants we explicitly welcome. `User-agent: *` already allows
# them, but naming them makes the intent unambiguous to each vendor's parser.
AI_USER_AGENTS = (
    "GPTBot",           # OpenAI — training
    "OAI-SearchBot",    # OpenAI — ChatGPT search index
    "ChatGPT-User",     # OpenAI — user-initiated browsing
    "Google-Extended",  # Google — Gemini / AI answers
    "ClaudeBot",        # Anthropic — training
    "Claude-User",      # Anthropic — user-initiated browsing
    "Claude-SearchBot", # Anthropic — search index
    "PerplexityBot",    # Perplexity
)


@router.get("/robots.txt")
def robots():
    base = _canonical_base()
    # NOTE: /tool-admin is deliberately NOT listed here. A Disallow line would
    # publish the admin URL to anyone reading robots.txt; the route is kept out
    # of search results with `noindex, nofollow` (see app/tool-admin/layout.tsx)
    # plus an X-Robots-Tag header, which robots.txt cannot do anyway.
    groups = ["User-agent: *\nAllow: /"]
    groups += [f"User-agent: {ua}\nAllow: /" for ua in AI_USER_AGENTS]
    body = "\n\n".join(groups) + f"\n\nSitemap: {base}/sitemap.xml\n"
    return Response(content=body, media_type="text/plain")
