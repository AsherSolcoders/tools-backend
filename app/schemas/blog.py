"""Pydantic schemas for blog + category API payloads."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.slug import normalize_slug_list, slugify
from app.schemas.user import AuthorRef, UserRef


def _clean_slug(value: str) -> str:
    """Shared slug validator: normalize, and reject input that leaves nothing."""
    slug = slugify(value)
    if not slug:
        raise ValueError("Slug must contain at least one letter or number.")
    return slug


class BlogCategoryBase(BaseModel):
    name: str
    slug: str
    meta_title: str | None = None
    meta_description: str | None = None


class BlogCategoryIn(BlogCategoryBase):
    # Slug normalization lives on the *input* model only. When BlogCategoryOut
    # inherited from this, reading a row whose slug wasn't already normalized
    # returned a rewritten slug (breaking links), and one that normalized to
    # nothing raised on read — turning a GET into a 500.
    _norm_slug = field_validator("slug")(_clean_slug)


class BlogCategoryOut(BlogCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RelatedBlog(BaseModel):
    """Lightweight reference used for the related-posts picker and public cards."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    excerpt: str | None = None
    featured_image: str | None = None


class BlogIn(BaseModel):
    title: str
    slug: str
    old_slugs: str | None = None
    content: str
    excerpt: str | None = None
    featured_image: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    focus_keyword: str | None = None
    og_image: str | None = None
    tags: str | None = None
    status: str = "draft"
    published_at: datetime | None = None
    display_date: datetime | None = None
    category_id: int | None = None
    # Who gets the byline. The display name is derived from this account on the
    # server (see admin._assign_author) rather than being typed in, so a post can
    # never credit a name that no profile page backs. Editors cannot set it.
    author_id: int | None = None
    is_featured: bool = False
    is_popular: bool = False
    category_ids: list[int] = []
    related_ids: list[int] = []

    _norm_slug = field_validator("slug")(_clean_slug)

    @field_validator("title")
    @classmethod
    def _trim_title(cls, value: str) -> str:
        # Trim only. The title is NOT HTML-escaped here: it is rendered as a React
        # text node (and via JSON.stringify in JSON-LD), both of which escape on
        # output. Escaping at storage too produced a literal "&amp;" in titles.
        return value.strip()

    @field_validator("old_slugs")
    @classmethod
    def _norm_old_slugs(cls, value: str | None) -> str | None:
        return normalize_slug_list(value)


class BlogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    old_slugs: str | None = None
    content: str
    excerpt: str | None
    featured_image: str | None
    seo_title: str | None
    seo_description: str | None
    focus_keyword: str | None
    og_image: str | None
    tags: str | None
    status: str
    category_id: int | None
    author: str | None = None
    author_user: AuthorRef | None = None
    is_featured: bool = False
    is_popular: bool = False
    categories: list[BlogCategoryOut] = []
    related: list[RelatedBlog] = []
    published_at: datetime | None
    display_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BlogListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    excerpt: str | None
    featured_image: str | None
    status: str
    author: str | None = None
    author_user: AuthorRef | None = None
    is_featured: bool = False
    is_popular: bool = False
    published_at: datetime | None
    display_date: datetime | None = None
    created_at: datetime
    category: BlogCategoryOut | None = None


class AdminBlogOut(BlogOut):
    """Admin-only view of a post, including who created and last edited it.

    Kept separate from the public `BlogOut` so staff names are never exposed on
    the public blog API.
    """
    created_by: UserRef | None = None
    updated_by: UserRef | None = None
