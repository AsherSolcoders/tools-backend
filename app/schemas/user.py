"""Pydantic schemas for staff users, who double as public blog authors."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.slug import slugify


class UserRef(BaseModel):
    """Lightweight user reference for audit fields (created_by / updated_by)."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class AuthorRef(BaseModel):
    """The byline attached to a post: just enough to render a link and an avatar."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str | None = None
    image: str | None = None
    profession: str | None = None
    # Read from the account but never serialized: it exists only to blank the slug
    # below, so a hidden profile can't hand the frontend a link that would 404.
    profile_public: bool = Field(default=True, exclude=True)

    @model_validator(mode="after")
    def _hide_private_profile(self) -> "AuthorRef":
        if not self.profile_public:
            self.slug = None
        return self


# Profile fields that end up in an href or a src. Anything else there is a
# stored-XSS vector: `javascript:alert(1)` in a social link executes the moment
# a visitor clicks it, and any staff account — an editor included — could plant
# one for an admin to hit.
_URL_FIELDS = frozenset({
    "image", "cover_image", "facebook", "twitter", "linkedin",
    "instagram", "youtube", "website",
})


def _safe_url(value: str) -> str | None:
    """Keep only URLs a browser can safely navigate to.

    http and https, or a site-relative path (our own uploads are stored as
    `/storage/...`). A bare domain gets https:// prepended, since that is what
    people type. Everything else — javascript:, data:, vbscript:, file: — is
    dropped rather than corrected, because there is no safe version of it.
    """
    url = value.strip()
    if not url:
        return None
    if url.startswith("//"):
        # Protocol-relative. Pin it to https rather than letting it inherit the
        # page's scheme, and so it does not fall through to the bare-domain
        # branch below, which would produce "https:////host".
        return "https://" + url.lstrip("/")
    if url.startswith("/"):
        return url  # site-relative, e.g. our own /storage/... uploads
    if url.lower().startswith(("http://", "https://")):
        return url
    # No scheme at all: treat "example.com/page" as the https URL they meant.
    if "://" not in url and not url.lower().startswith(("javascript:", "data:", "vbscript:")):
        return "https://" + url
    return None


class ProfileFields(BaseModel):
    """The public half of a staff account — shared by the read and write models."""
    slug: str | None = None
    image: str | None = None
    cover_image: str | None = None
    bio: str | None = None
    profession: str | None = None
    education: str | None = None
    skills: str | None = None
    experience: str | None = None
    address: str | None = None
    contact_email: str | None = None
    facebook: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    instagram: str | None = None
    youtube: str | None = None
    website: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    profile_public: bool = True


class UserOut(ProfileFields):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    created_at: datetime


class AuthorOut(BaseModel):
    """Public author profile.

    Built field-by-field rather than by inheriting UserOut, so `email`, `role` and
    `password` can never reach a public response by being added upstream later.
    The only address shown is `contact_email`, which the user opted into.
    """
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str | None = None
    image: str | None = None
    cover_image: str | None = None
    bio: str | None = None
    profession: str | None = None
    education: str | None = None
    skills: str | None = None
    experience: str | None = None
    address: str | None = None
    contact_email: str | None = None
    facebook: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    instagram: str | None = None
    youtube: str | None = None
    website: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "editor"  # "admin" or "editor"; super_admin cannot be created via API


class ProfileUpdate(ProfileFields):
    """Profile edits. Every field is optional; `slug` is normalized on the way in.

    Normalization is on the write model only — doing it on the read model would
    rewrite a stored slug on every GET and break the profile's indexed URL.
    """
    name: str | None = None
    profile_public: bool | None = None

    @model_validator(mode="after")
    def _blank_is_absent(self) -> "ProfileUpdate":
        """Treat a field the user emptied as unset, not as the string "".

        A cleared text box submits "" — and a box cleared imprecisely submits " ".
        Stored as-is, a lone space is truthy in JavaScript, so the profile kept
        rendering a social button whose link went nowhere. Blanking to None here
        means "removed" is stored as removed.
        """
        for name, value in list(self.__dict__.items()):
            if isinstance(value, str):
                # Trimmed too: a URL pasted with a trailing space is the same URL,
                # and `bio` keeps its internal line breaks either way.
                cleaned = value.strip() or None
                if cleaned is not None and name in _URL_FIELDS:
                    cleaned = _safe_url(cleaned)
                setattr(self, name, cleaned)
        return self

    @field_validator("slug")
    @classmethod
    def _norm_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        slug = slugify(value)
        if not slug:
            raise ValueError("Profile URL must contain at least one letter or number.")
        return slug


class UserUpdate(ProfileUpdate):
    """Admin-side edit of another account: profile fields plus credentials."""
    password: str | None = None
    role: str | None = None
