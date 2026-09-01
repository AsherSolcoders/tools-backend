"""Super Admin API — auth, blog CRUD, categories, settings.

Visitors never authenticate; only admins do. All write endpoints require a valid
admin bearer token.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import create_access_token, get_current_admin, require_admin
from app.config import settings
from app.core.images import shrink_for_web, strip_image_metadata
from app.core.slug import slugify
from app.core.limiter import limiter
from app.core.security import (
    UploadValidationError,
    hash_password,
    validate_svg,
    validate_upload,
    verify_password,
)
from app.database import get_db
from app.models import Blog, BlogCategory, ToolCategory, User
from app.models.blog import BlogStatus
from app.models.user import UserRole
from app.schemas.blog import AdminBlogOut, BlogCategoryIn, BlogCategoryOut, BlogIn, BlogOut
from app.schemas.user import AuthorRef, ProfileUpdate, UserCreate, UserOut, UserUpdate
from app.tools import list_tools

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login")
@limiter.limit("10/minute")  # brute-force protection (per IP)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == form.username)).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer",
            "user": {"name": user.name, "email": user.email, "role": user.role.value}}


_IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "gif", "svg"]


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(get_current_admin),
):
    """Upload a blog/featured image to permanent storage and return its public URL.

    Unlike tool uploads (which auto-delete), these persist under /storage/blog-images.
    Swap this for a Cloudflare R2 upload in production.
    """
    content = await file.read()
    try:
        validate_upload(file, _IMAGE_EXTS, content)
        # SVG has no magic bytes, so validate_upload's content check skips it
        # entirely — any file named .svg gets through. Check it explicitly.
        if (file.filename or "").lower().endswith(".svg"):
            validate_svg(content)
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = (file.filename or "").lower().rsplit(".", 1)[-1]

    # Downscale to a sane maximum and re-encode as WebP. Uploads were being stored
    # at full resolution (a 1731px screenshot ≈ 2.2 MB), which the blog listing then
    # downloaded twelve times over for 234px cards. Returns None for SVG/GIF and
    # animated images, which are stored as-is.
    shrunk = shrink_for_web(content)
    if shrunk is not None:
        content, ext = shrunk
    else:
        # Not re-encoded, so metadata is still in there — strip it. (A re-encode
        # already drops EXIF, so this is only needed on the untouched path.)
        content = strip_image_metadata(content)

    name = f"{uuid.uuid4().hex}.{ext}"
    dest = Path(settings.blog_images_dir) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    base = settings.api_base_url.rstrip("/") if settings.api_base_url else str(request.base_url).rstrip("/")
    url = f"{base}/storage/blog-images/{name}"
    return {"url": url, "filename": name}


# Downloadable attachments a writer can embed in a post (docs, sheets, archives…).
_FILE_EXTS = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "txt", "zip"]


@router.post("/upload-file")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(get_current_admin),
):
    """Upload an arbitrary downloadable file (PDF, Office doc, archive…) for embedding.

    Returns the public URL plus the original filename so the editor can render a
    labelled download link/button.
    """
    content = await file.read()
    try:
        validate_upload(file, _FILE_EXTS, content)
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    original = (file.filename or "file").rsplit("/", 1)[-1]
    ext = original.lower().rsplit(".", 1)[-1]
    name = f"{uuid.uuid4().hex}.{ext}"
    dest = Path(settings.blog_files_dir) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    base = settings.api_base_url.rstrip("/") if settings.api_base_url else str(request.base_url).rstrip("/")
    url = f"{base}/storage/blog-files/{name}"
    return {"url": url, "filename": original, "size": len(content)}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    # Counts the posts this account can actually open, so the number on the
    # dashboard matches the length of the list behind it.
    blogs = select(func.count()).select_from(Blog)
    if not _sees_everything(user):
        blogs = blogs.where(_own_blogs(user))
    return {
        "total_blogs": db.scalar(blogs) or 0,
        "total_blog_categories": db.scalar(select(func.count()).select_from(BlogCategory)) or 0,
        "total_tool_categories": db.scalar(select(func.count()).select_from(ToolCategory)) or 0,
        "total_tools": len(list_tools()),
    }


# --- Ownership scoping ------------------------------------------------------

# Only the super admin sees the whole site. Everyone else — admins included —
# sees their own work and nothing else.
#
# This is enforced on every read AND every write. Filtering the list alone would
# be cosmetic: the ids are sequential, so anyone could still open, edit or delete
# a post that simply wasn't shown to them.


def _sees_everything(user: User) -> bool:
    return user.role == UserRole.super_admin


def _own_blogs(user: User):
    """A post is yours if you are credited on it or you created it.

    Both halves matter. `author_id` alone would lose a post the moment an admin
    handed the byline to someone else; `created_by_id` alone would hide a post
    that was assigned to you by somebody else.
    """
    return or_(Blog.author_id == user.id, Blog.created_by_id == user.id)


def _own_blog_or_404(blog_id: int, db: Session, user: User) -> Blog:
    """Fetch a post the caller is allowed to touch.

    Deliberately 404, not 403: a post outside your scope does not exist as far as
    you are concerned, and a 403 would confirm which ids are real.
    """
    blog = db.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    if not _sees_everything(user) and not (
        blog.author_id == user.id or blog.created_by_id == user.id
    ):
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog


def _visible_users(actor: User, db: Session) -> list[User]:
    """Accounts `actor` may see — the same hierarchy /users already manages by.

    super_admin: everyone. admin: themselves and the editors they manage.
    editor: only themselves.
    """
    stmt = select(User).order_by(User.name)
    if _sees_everything(actor):
        return list(db.execute(stmt).scalars().all())
    if actor.role == UserRole.admin:
        return list(
            db.execute(
                stmt.where(or_(User.id == actor.id, User.role == UserRole.editor))
            ).scalars().all()
        )
    return [actor]


# --- Blog CRUD --------------------------------------------------------------


def _apply_relations(blog: Blog, data: dict, db: Session) -> None:
    """Pop the M2M id lists off `data` and resolve them into ORM relationships."""
    category_ids = data.pop("category_ids", []) or []
    related_ids = [rid for rid in (data.pop("related_ids", []) or []) if rid != blog.id]

    blog.categories = (
        db.execute(select(BlogCategory).where(BlogCategory.id.in_(category_ids))).scalars().all()
        if category_ids else []
    )
    blog.related = (
        db.execute(select(Blog).where(Blog.id.in_(related_ids))).scalars().all()
        if related_ids else []
    )
    # Keep the legacy single category_id in sync (used by list views / filtering).
    if category_ids and not data.get("category_id"):
        data["category_id"] = category_ids[0]


# --- Authorship -------------------------------------------------------------

# Who may hand a post to someone else. An editor writes under their own name and
# nobody else's, so the picker is theirs to read but not to set — the server
# ignores whatever `author_id` an editor submits rather than trusting the UI to
# have disabled it.
_MAY_CHOOSE_AUTHOR = {UserRole.super_admin, UserRole.admin}


def _assign_author(blog: Blog, data: dict, actor: User, db: Session, *, creating: bool) -> None:
    """Resolve the byline and keep the denormalized display name in step.

    `Blog.author` stays populated because every card, feed and JSON-LD builder
    already reads it; `author_id` is what makes that name link to a profile.
    """
    requested = data.pop("author_id", None)

    if actor.role in _MAY_CHOOSE_AUTHOR and requested:
        target = db.get(User, requested)
        if not target:
            raise HTTPException(status_code=400, detail="That author account no longer exists.")
        # The picker already hides accounts out of scope, but the id arrives from
        # the client — so re-check it here rather than trusting the form.
        if target.id not in {u.id for u in _visible_users(actor, db)}:
            raise HTTPException(
                status_code=403, detail="You cannot publish a post under that account."
            )
    elif creating:
        # No choice made, or an editor creating a post: it is theirs.
        target = actor
    else:
        # An editor saving an edit must not steal the byline from whoever wrote it.
        # Leave the existing credit exactly as it is.
        return

    blog.author_id = target.id
    blog.author = target.name


def _ensure_profile_slug(user: User, db: Session, requested: str | None = None) -> None:
    """Give the profile a unique URL slug, deriving one from the name if needed.

    The column has no UNIQUE constraint (it was added to a live table by ALTER
    TABLE, which cannot backfill existing rows), so collisions are resolved here.
    """
    base = slugify(requested or user.slug or user.name) or f"author-{user.id}"
    candidate, n = base, 2
    while True:
        clash = db.execute(
            select(User).where(User.slug == candidate, User.id != user.id)
        ).scalar_one_or_none()
        if not clash:
            break
        candidate, n = f"{base}-{n}", n + 1
    user.slug = candidate


def _apply_profile(user: User, payload: ProfileUpdate, db: Session) -> None:
    """Copy the public profile fields onto a user.

    `exclude_unset` matters: without it every field the caller left out would be
    written back as None, so editing one social link would wipe the rest.
    """
    fields = payload.model_dump(exclude_unset=True)
    fields.pop("password", None)
    fields.pop("role", None)
    slug = fields.pop("slug", None)
    name = fields.pop("name", None)
    if fields.get("profile_public") is None:
        # Non-nullable column: an explicit null in the payload would write NULL.
        fields.pop("profile_public", None)
    if name is not None:
        # Names render as text, so they are trimmed but never HTML-escaped —
        # escaping here is what once put a literal "&amp;" on a byline.
        user.name = name.strip()
    for key, value in fields.items():
        setattr(user, key, value)
    if slug is not None or not user.slug:
        _ensure_profile_slug(user, db, slug)


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_admin)):
    """The signed-in user's own account and public profile."""
    return user


@router.put("/me", response_model=UserOut)
def update_me(payload: ProfileUpdate, db: Session = Depends(get_db),
              user: User = Depends(get_current_admin)):
    """Every staff member may edit their own profile — including editors, who
    cannot reach /users at all. Role and password are not settable here: the
    schema drops them, so an editor cannot promote themselves."""
    _apply_profile(user, payload, db)
    db.commit()
    db.refresh(user)
    return user


@router.get("/authors", response_model=list[AuthorRef])
def list_authors_for_picker(db: Session = Depends(get_db),
                            actor: User = Depends(get_current_admin)):
    """Accounts that can be credited on a post, for the editor's author picker.

    Scoped like everything else: an admin can credit themselves or an editor,
    never the super admin.
    """
    return _visible_users(actor, db)


@router.post("/blogs", response_model=BlogOut)
def create_blog(payload: BlogIn, db: Session = Depends(get_db), actor: User = Depends(get_current_admin)):
    if db.execute(select(Blog).where(Blog.slug == payload.slug)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A blog with this slug already exists")
    data = payload.model_dump()
    blog = Blog()
    _apply_relations(blog, data, db)
    # Pops `author_id` before the loop below, so the byline is only ever set here.
    _assign_author(blog, data, actor, db, creating=True)
    for key, value in data.items():
        setattr(blog, key, value)
    # Title is stored verbatim (the schema only trims it). It used to be
    # HTML-escaped here, which stored "SEO &amp; PPC" and showed that literally on
    # the site — and because update_blog never escaped, the next save silently
    # "fixed" it. Titles are rendered as text, so output escaping is the right
    # layer and escaping here only ever double-escaped.
    blog.created_by_id = actor.id
    blog.updated_by_id = actor.id
    if blog.status == BlogStatus.published and blog.published_at is None:
        blog.published_at = func.now()
    db.add(blog)
    db.commit()
    db.refresh(blog)
    return blog


@router.put("/blogs/{blog_id}", response_model=BlogOut)
def update_blog(blog_id: int, payload: BlogIn, db: Session = Depends(get_db),
                actor: User = Depends(get_current_admin)):
    blog = _own_blog_or_404(blog_id, db, actor)
    data = payload.model_dump()
    prev_slug = blog.slug
    _apply_relations(blog, data, db)
    _assign_author(blog, data, actor, db, creating=False)
    for key, value in data.items():
        setattr(blog, key, value)
    blog.updated_by_id = actor.id
    # When the slug changes, remember the old one so its indexed URL can redirect.
    if prev_slug and prev_slug != blog.slug:
        olds = [s.strip() for s in (blog.old_slugs or "").split(",") if s.strip()]
        if prev_slug not in olds:
            olds.append(prev_slug)
        # never keep the current slug in the redirect list (avoids a self-redirect loop)
        blog.old_slugs = ",".join(s for s in olds if s != blog.slug) or None
    if blog.status == BlogStatus.published and blog.published_at is None:
        blog.published_at = func.now()
    db.commit()
    db.refresh(blog)
    return blog


@router.delete("/blogs/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    blog = _own_blog_or_404(blog_id, db, actor)
    db.delete(blog)
    db.commit()
    return {"deleted": blog_id}


@router.get("/blogs", response_model=list[AdminBlogOut])
def admin_list_blogs(db: Session = Depends(get_db), user: User = Depends(get_current_admin)):
    stmt = (
        select(Blog)
        # categories is a collection, so selectinload (one extra query) rather than
        # joinedload — the admin list renders a category column, and lazy loading
        # would fire a query per row.
        .options(
            joinedload(Blog.created_by),
            joinedload(Blog.updated_by),
            selectinload(Blog.categories),
        )
        .order_by(Blog.created_at.desc())
    )
    if not _sees_everything(user):
        stmt = stmt.where(_own_blogs(user))
    # unique(): the eager join on Blog.author_user can duplicate parent rows.
    return db.execute(stmt).unique().scalars().all()


# --- Blog categories --------------------------------------------------------


@router.post("/blog-categories", response_model=BlogCategoryOut)
def create_blog_category(payload: BlogCategoryIn, db: Session = Depends(get_db),
                         _: User = Depends(get_current_admin)):
    cat = BlogCategory(**payload.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/blog-categories/{cat_id}", response_model=BlogCategoryOut)
def update_blog_category(cat_id: int, payload: BlogCategoryIn, db: Session = Depends(get_db),
                         _: User = Depends(get_current_admin)):
    cat = db.get(BlogCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    clash = db.execute(
        select(BlogCategory).where(BlogCategory.slug == payload.slug, BlogCategory.id != cat_id)
    ).scalar_one_or_none()
    if clash:
        raise HTTPException(status_code=409, detail="Another category already uses this slug.")
    cat.name = payload.name
    cat.slug = payload.slug
    cat.meta_title = payload.meta_title
    cat.meta_description = payload.meta_description
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/blog-categories/{cat_id}")
def delete_blog_category(cat_id: int, db: Session = Depends(get_db),
                         _: User = Depends(require_admin)):
    cat = db.get(BlogCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"deleted": cat_id}


# --- Staff users ------------------------------------------------------------

_ASSIGNABLE_ROLES = {"admin", "editor"}


def _can_manage(actor: User, target_role: str) -> bool:
    """super_admin manages admin + editor; admin manages only editor."""
    if actor.role == UserRole.super_admin:
        return target_role in _ASSIGNABLE_ROLES
    if actor.role == UserRole.admin:
        return target_role == "editor"
    return False


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    """Staff accounts the caller may see.

    An admin sees themselves and the editors they manage — not the super admin,
    whom they could never act on anyway, so listing them only invited confusion.
    """
    users = _visible_users(actor, db)
    return sorted(users, key=lambda u: u.created_at, reverse=True)


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db),
                actor: User = Depends(require_admin)):
    role = (payload.role or "editor").strip().lower()
    if role not in _ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'editor'.")
    if not _can_manage(actor, role):
        raise HTTPException(status_code=403, detail="You can only create editors.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if db.execute(select(User).where(User.email == str(payload.email).lower())).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    user = User(
        # Same reasoning as the blog title: names render as text, so escaping here
        # would show "Smith &amp; Sons" on the author byline.
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        password=hash_password(payload.password),
        role=UserRole(role),
    )
    db.add(user)
    db.flush()  # need the id before deriving a slug that may need a numeric suffix
    _ensure_profile_slug(user, db)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(require_admin)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == UserRole.super_admin:
        raise HTTPException(status_code=403, detail="The super admin account cannot be modified here.")
    if not _can_manage(actor, target.role.value):
        raise HTTPException(status_code=403, detail="You do not have permission to edit this user.")
    _apply_profile(target, payload, db)
    if payload.password:
        if len(payload.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
        target.password = hash_password(payload.password)
    if payload.role is not None:
        new_role = payload.role.strip().lower()
        if new_role not in _ASSIGNABLE_ROLES:
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'editor'.")
        if not _can_manage(actor, new_role):
            raise HTTPException(status_code=403, detail="You cannot assign that role.")
        target.role = UserRole(new_role)
    db.commit()
    db.refresh(target)
    return target


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == actor.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    if target.role == UserRole.super_admin:
        raise HTTPException(status_code=403, detail="The super admin account cannot be deleted.")
    if not _can_manage(actor, target.role.value):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this user.")
    db.delete(target)
    db.commit()
    return {"deleted": user_id}
