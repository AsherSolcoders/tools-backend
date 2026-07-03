"""Public blog API (read-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Blog, BlogCategory
from app.models.blog import BlogStatus
from app.schemas.blog import BlogListItem, BlogOut

router = APIRouter(prefix="/api/blog", tags=["blog"])


def _visible():
    """A post is publicly live if it isn't a draft and its publish time has arrived.

    Scheduled posts carry a future `published_at`; they surface automatically once
    the database clock passes that time — no background job needed. Posts published
    without an explicit date (published_at IS NULL) stay visible.
    """
    return and_(
        Blog.status != BlogStatus.draft,
        or_(Blog.published_at.is_(None), Blog.published_at <= func.now()),
    )


@router.get("", response_model=list[BlogListItem])
def list_blogs(
    db: Session = Depends(get_db),
    category: str | None = None,
    featured: bool | None = None,
    popular: bool | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
):
    stmt = select(Blog).options(joinedload(Blog.category)).where(_visible())
    if category:
        stmt = stmt.join(BlogCategory, Blog.category_id == BlogCategory.id).where(BlogCategory.slug == category)
    if featured:
        stmt = stmt.where(Blog.is_featured.is_(True))
    if popular:
        stmt = stmt.where(Blog.is_popular.is_(True))
    stmt = stmt.order_by(Blog.published_at.desc().nullslast()).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()


@router.get("-count")
def count_blogs(
    db: Session = Depends(get_db),
    category: str | None = None,
    featured: bool | None = None,
    popular: bool | None = None,
):
    """Total published posts matching the filters (for numbered pagination)."""
    stmt = select(func.count(Blog.id)).where(_visible())
    if category:
        stmt = stmt.join(BlogCategory, Blog.category_id == BlogCategory.id).where(BlogCategory.slug == category)
    if featured:
        stmt = stmt.where(Blog.is_featured.is_(True))
    if popular:
        stmt = stmt.where(Blog.is_popular.is_(True))
    return {"count": db.execute(stmt).scalar_one()}


@router.get("/{slug}", response_model=BlogOut)
def get_blog(slug: str, db: Session = Depends(get_db)):
    blog = db.execute(
        select(Blog).where(Blog.slug == slug).where(_visible())
    ).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return blog


@router.get("-categories")
def blog_categories(db: Session = Depends(get_db)):
    """Categories with a count of published posts in each (for the blog sidebar)."""
    rows = db.execute(
        select(BlogCategory, func.count(Blog.id))
        .outerjoin(
            Blog,
            (Blog.category_id == BlogCategory.id) & (Blog.status == BlogStatus.published),
        )
        .group_by(BlogCategory.id)
        .order_by(BlogCategory.name)
    ).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug, "count": count} for c, count in rows]
