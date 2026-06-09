"""Admin users only — visitors are never stored."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
