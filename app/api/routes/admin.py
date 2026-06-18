"""Super Admin API — auth, blog CRUD, categories, settings.

Visitors never authenticate; only admins do. All write endpoints require a valid
admin bearer token.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import create_access_token, get_current_admin
from app.config import settings
from app.core.limiter import limiter
from app.core.security import (
    UploadValidationError,
    sanitize_text,
    validate_upload,
    verify_password,
)
from app.database import get_db
from app.models import Blog, BlogCategory, ToolCategory, User
from app.models.blog import BlogStatus
from app.schemas.blog import BlogCategoryIn, BlogCategoryOut, BlogIn, BlogOut
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
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = (file.filename or "").lower().rsplit(".", 1)[-1]
    name = f"{uuid.uuid4().hex}.{ext}"
    dest = Path(settings.blog_images_dir) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    base = settings.api_base_url.rstrip("/") if settings.api_base_url else str(request.base_url).rstrip("/")
    url = f"{base}/storage/blog-images/{name}"
    return {"url": url, "filename": name}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return {
        "total_blogs": db.scalar(select(func.count()).select_from(Blog)) or 0,
        "total_blog_categories": db.scalar(select(func.count()).select_from(BlogCategory)) or 0,
        "total_tool_categories": db.scalar(select(func.count()).select_from(ToolCategory)) or 0,
        "total_tools": len(list_tools()),
    }


# --- Blog CRUD --------------------------------------------------------------


@router.post("/blogs", response_model=BlogOut)
def create_blog(payload: BlogIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    if db.execute(select(Blog).where(Blog.slug == payload.slug)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A blog with this slug already exists")
    blog = Blog(**payload.model_dump())
    blog.title = sanitize_text(blog.title)
    if blog.status == BlogStatus.published and blog.published_at is None:
        blog.published_at = func.now()
    db.add(blog)
    db.commit()
    db.refresh(blog)
    return blog


@router.put("/blogs/{blog_id}", response_model=BlogOut)
def update_blog(blog_id: int, payload: BlogIn, db: Session = Depends(get_db),
                _: User = Depends(get_current_admin)):
    blog = db.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    for key, value in payload.model_dump().items():
        setattr(blog, key, value)
    db.commit()
    db.refresh(blog)
    return blog


@router.delete("/blogs/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    blog = db.get(Blog, blog_id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    db.delete(blog)
    db.commit()
    return {"deleted": blog_id}


@router.get("/blogs", response_model=list[BlogOut])
def admin_list_blogs(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return db.execute(select(Blog).order_by(Blog.created_at.desc())).scalars().all()


# --- Blog categories --------------------------------------------------------


@router.post("/blog-categories", response_model=BlogCategoryOut)
def create_blog_category(payload: BlogCategoryIn, db: Session = Depends(get_db),
                         _: User = Depends(get_current_admin)):
    cat = BlogCategory(**payload.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/blog-categories/{cat_id}")
def delete_blog_category(cat_id: int, db: Session = Depends(get_db),
                         _: User = Depends(get_current_admin)):
    cat = db.get(BlogCategory, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"deleted": cat_id}
