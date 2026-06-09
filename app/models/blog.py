"""Blog posts and blog categories."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BlogStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"


class BlogCategory(Base):
    __tablename__ = "blog_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)

    blogs: Mapped[list["Blog"]] = relationship(back_populates="category")


class Blog(Base):
    __tablename__ = "blogs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    featured_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # SEO
    seo_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    focus_keyword: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    og_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # comma-separated

    status: Mapped[BlogStatus] = mapped_column(Enum(BlogStatus), default=BlogStatus.draft)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("blog_categories.id"), nullable=True)
    category: Mapped[Optional["BlogCategory"]] = relationship(back_populates="blogs")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
