"""Pydantic schemas for staff user management."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRef(BaseModel):
    """Lightweight user reference for audit fields (created_by / updated_by)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "editor"  # "admin" or "editor"; super_admin cannot be created via API


class UserUpdate(BaseModel):
    name: str | None = None
    password: str | None = None
    role: str | None = None
