"""Public author profiles (read-only).

An author is a staff user with a profile filled in — see app/models/user.py.
Only the fields on `AuthorOut` are ever exposed; the login email, role and
password hash stay server-side.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.schema import author_schema
from app.database import get_db
from app.models import Blog, User
from app.schemas.blog import BlogListItem
from app.schemas.user import AuthorOut

# Profiles live under /author/<slug>, not the flat root namespace that tools,
# categories and posts share: adding a fifth lookup to every root request would
# cost a query on pages that can never be an author, and a writer whose slug
# matched a tool would silently shadow it.
router = APIRouter(prefix="/api/authors", tags=["authors"])


def _published(author_id: int):
    """Live posts credited to this author.

    Reuses the blog API's visibility rule so a draft — or a scheduled post whose
    time hasn't come — cannot surface here either. Those 404 on their own page,
    so a card linking to one would go nowhere.
    """
    from app.api.routes.blog import _visible

    return (
        select(Blog)
        .options(joinedload(Blog.category))
        .where(Blog.author_id == author_id, _visible())
    )


@router.get("", response_model=list[AuthorOut])
def list_authors(db: Session = Depends(get_db)):
    """Every author with a public profile, for listings and internal links."""
    return db.execute(
        select(User)
        .where(User.profile_public.is_(True), User.slug.isnot(None))
        .order_by(User.name)
    ).scalars().all()


# No response_model: the payload carries the author's posts and a generated
# `schema` block, both of which AuthorOut would strip out.
@router.get("/{slug}")
def get_author(
    slug: str,
    db: Session = Depends(get_db),
    limit: int = Query(12, le=50),
    offset: int = 0,
):
    author = db.execute(
        select(User).where(User.slug == slug, User.profile_public.is_(True))
    ).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    posts = db.execute(
        _published(author.id)
        .order_by(Blog.published_at.desc().nullslast(), Blog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    # Counted separately: `posts` is one page, and the profile header states the
    # author's full output, not how many happen to fit on this page.
    from sqlalchemy import func as sa_func

    total = db.execute(
        select(sa_func.count()).select_from(_published(author.id).subquery())
    ).scalar_one()

    payload = AuthorOut.model_validate(author).model_dump()
    payload["posts"] = [BlogListItem.model_validate(p).model_dump() for p in posts]
    payload["post_count"] = total
    payload["schema"] = author_schema(author, posts)
    return payload
