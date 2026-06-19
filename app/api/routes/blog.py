"""Public blog API (read-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Blog, BlogCategory
from app.models.blog import BlogStatus
from app.schemas.blog import BlogListItem, BlogOut

router = APIRouter(prefix="/api/blog", tags=["blog"])


@router.get("", response_model=list[BlogListItem])
def list_blogs(
    db: Session = Depends(get_db),
    category: str | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
):
    stmt = select(Blog).options(joinedload(Blog.category)).where(Blog.status == BlogStatus.published)
    if category:
        stmt = stmt.join(BlogCategory).where(BlogCategory.slug == category)
    stmt = stmt.order_by(Blog.published_at.desc().nullslast()).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()


@router.get("/{slug}", response_model=BlogOut)
def get_blog(slug: str, db: Session = Depends(get_db)):
    blog = db.execute(select(Blog).where(Blog.slug == slug)).scalar_one_or_none()
    if not blog or blog.status != BlogStatus.published:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return blog


@router.get("-categories")
def blog_categories(db: Session = Depends(get_db)):
    cats = db.execute(select(BlogCategory)).scalars().all()
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in cats]
