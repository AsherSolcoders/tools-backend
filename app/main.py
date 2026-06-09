"""Toolkit Pro — FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import admin, blog, health, seo, tools
from app.config import settings
from app.core.security import SecureHeadersMiddleware
from app.core.temp_files import cleanup_loop, ensure_dirs
from app.database import init_db

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    init_db()
    _seed_admin()
    sweeper = asyncio.create_task(cleanup_loop(interval_seconds=60))
    try:
        yield
    finally:
        sweeper.cancel()


def _seed_admin() -> None:
    """Create a default super-admin in dev if none exists."""
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.database import SessionLocal
    from app.models import User
    from app.models.user import UserRole

    with SessionLocal() as db:
        if db.execute(select(User).limit(1)).scalar_one_or_none():
            return
        db.add(User(
            name="Super Admin",
            email="admin@toolkitpro.local",
            password=hash_password("admin12345"),
            role=UserRole.super_admin,
        ))
        db.commit()


app = FastAPI(
    title=settings.app_name,
    description="Config-driven SEO tools platform + blog + admin. No visitor data stored.",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecureHeadersMiddleware)
# In production, lock CORS to the explicit origin list. In development, also allow any
# localhost/127.0.0.1 or private LAN IP on any port, so the app works whether you open it
# at localhost:3000 or http://<your-lan-ip>:3000 (e.g. from a phone on the same network).
cors_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_origins": settings.cors_origin_list,
}
if settings.environment != "production":
    cors_kwargs["allow_origin_regex"] = (
        r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"(\d{1,3}\.){3}\d{1,3})(:\d+)?"
    )
app.add_middleware(CORSMiddleware, **cors_kwargs)

# Permanent storage for blog images / site assets (swap for Cloudflare R2 in prod).
Path(settings.blog_images_dir).mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")

app.include_router(health.router)
app.include_router(tools.router)
app.include_router(blog.router)
app.include_router(admin.router)
app.include_router(seo.router)


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs", "health": "/api/health"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
