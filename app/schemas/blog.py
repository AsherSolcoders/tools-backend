"""Pydantic schemas for blog + category API payloads."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRef


class BlogCategoryIn(BaseModel):
    name: str
    slug: str
    meta_title: str | None = None
    meta_description: str | None = None


class BlogCategoryOut(BlogCategoryIn):
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
    category_id: int | None = None
    author_id: int | None = None
    author: str | None = None
    is_featured: bool = False
    is_popular: bool = False
    category_ids: list[int] = []
    related_ids: list[int] = []


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
    is_featured: bool = False
    is_popular: bool = False
    categories: list[BlogCategoryOut] = []
    related: list[RelatedBlog] = []
    published_at: datetime | None
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
    is_featured: bool = False
    is_popular: bool = False
    published_at: datetime | None
    category: BlogCategoryOut | None = None


class AdminBlogOut(BlogOut):
    """Admin-only view of a post, including who created and last edited it.

    Kept separate from the public `BlogOut` so staff names are never exposed on
    the public blog API.
    """
    created_by: UserRef | None = None
    updated_by: UserRef | None = None
