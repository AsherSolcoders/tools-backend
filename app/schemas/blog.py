"""Pydantic schemas for blog + category API payloads."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BlogCategoryIn(BaseModel):
    name: str
    slug: str


class BlogCategoryOut(BlogCategoryIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BlogIn(BaseModel):
    title: str
    slug: str
    content: str
    excerpt: str | None = None
    featured_image: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    focus_keyword: str | None = None
    og_image: str | None = None
    tags: str | None = None
    status: str = "draft"
    category_id: int | None = None
    author_id: int | None = None


class BlogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
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
    published_at: datetime | None
