"""Health + meta endpoints."""
from fastapi import APIRouter

from app.config import settings
from app.tools import get_processor, list_categories, list_tools

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    tools = list_tools()
    implemented = sum(1 for t in tools if get_processor(t.slug))
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "tools_total": len(tools),
        "tools_implemented": implemented,
        "categories": len(list_categories()),
    }
