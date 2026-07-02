"""SEO endpoints: dynamic sitemap.xml and robots.txt."""
from __future__ import annotations

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


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    base = settings.site_url.rstrip("/")
    # Tools, categories, and posts all live flat at /<slug> (no /tools/ or /category/ prefix).
    urls: list[str] = [f"{base}/", f"{base}/tools", f"{base}/blog", f"{base}/faq", f"{base}/about"]
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


@router.get("/robots.txt")
def robots():
    base = settings.site_url.rstrip("/")
    body = f"User-agent: *\nAllow: /\nDisallow: /tool-admin\nSitemap: {base}/sitemap.xml\n"
    return Response(content=body, media_type="text/plain")
