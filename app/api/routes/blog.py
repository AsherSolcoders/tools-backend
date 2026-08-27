"""Public blog API (read-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Blog, BlogCategory
from app.models.blog import BlogStatus
from app.core.schema import blog_schema
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


@router.get("-canonical/{slug}")
def blog_canonical(slug: str, db: Session = Depends(get_db)):
    """If `slug` is a previous slug of a live post, return its current slug (for a 301 redirect)."""
    rows = db.execute(
        select(Blog).where(Blog.old_slugs.isnot(None)).where(_visible())
    ).scalars().all()
    for b in rows:
        olds = [s.strip() for s in (b.old_slugs or "").split(",") if s.strip()]
        if slug in olds and b.slug != slug:
            return {"slug": b.slug}
    raise HTTPException(status_code=404, detail="Not found")


# No response_model: the payload adds a generated `schema` block that BlogOut
# would strip out.
@router.get("/{slug}")
def get_blog(slug: str, db: Session = Depends(get_db)):
    blog = db.execute(
        select(Blog).where(Blog.slug == slug).where(_visible())
    ).scalar_one_or_none()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog post not found")

    out = BlogOut.model_validate(blog)
    # `Blog.related` is an unfiltered relationship holding whatever an editor
    # picked, so a draft or a scheduled post whose time hasn't come can sit in it.
    # Those must not surface publicly: this same endpoint 404s them, so the card
    # would link nowhere. Re-check visibility in SQL rather than in Python so the
    # `published_at <= now()` comparison stays on the database clock.
    if out.related:
        visible_ids = set(
            db.execute(
                select(Blog.id).where(Blog.id.in_([r.id for r in out.related]), _visible())
            ).scalars().all()
        )
        out.related = [r for r in out.related if r.id in visible_ids]

    # Structured data generated from the stored post — no hand-written JSON-LD.
    payload = out.model_dump()
    payload["schema"] = blog_schema(blog)
    return payload


@router.get("-categories")
def blog_categories(db: Session = Depends(get_db)):
    """Categories with a count of published posts in each (for the blog sidebar)."""
    rows = db.execute(
        select(BlogCategory, func.count(Blog.id))
        .outerjoin(
            Blog,
            # `_visible()`, not `status == published`: a due scheduled post is live
            # but keeps the `scheduled` status, so every category undercounted.
            and_(Blog.category_id == BlogCategory.id, _visible()),
        )
        .group_by(BlogCategory.id)
        .order_by(BlogCategory.name)
    ).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "count": count,
            "meta_title": c.meta_title,
            "meta_description": c.meta_description,
        }
        for c, count in rows
    ]
