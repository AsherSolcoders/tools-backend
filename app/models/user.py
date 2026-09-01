"""Staff accounts. Visitors are never stored.

A user is both a login and a public byline: the profile fields below render the
/author/<slug> page and the credit under every post they write. There is no
separate authors table, so a writer never exists twice.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    editor = "editor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))  # hashed
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.admin)

    # --- Public author profile ---------------------------------------------
    # Every column here is nullable: existing accounts predate the profile, and a
    # user with nothing filled in simply has no public page.
    #
    # `slug` carries no UNIQUE constraint. It is added to a live table by
    # ALTER TABLE (see database.py), which cannot backfill a unique value for
    # rows that already exist — so uniqueness is enforced in the API instead.
    slug: Mapped[Optional[str]] = mapped_column(String(180), index=True, nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Wide banner behind the profile header. Separate from `image`, which is the
    # square portrait used for the avatar and for og:image.
    cover_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profession: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    # Comma-separated, like Blog.tags — a skill list needs no table of its own.
    skills: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    experience: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # Deliberately NOT the login `email`. Publishing the address someone signs in
    # with invites credential-stuffing and spam, so the public page shows only
    # what the user explicitly puts here.
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Socials as columns, not a JSON blob: the set is small and fixed, and each
    # renders as its own button with its own icon.
    facebook: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    twitter: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instagram: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    youtube: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    meta_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Retires a byline without deleting the account: the profile page 404s and the
    # credit stops linking, but the posts keep their author.
    profile_public: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
