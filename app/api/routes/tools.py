"""Tool catalogue + processing API.

The whole platform runs through these endpoints. The frontend reads tool configs
and renders UIs dynamically — no per-tool endpoints exist.
"""

import io
import re
import zipfile
from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.limiter import limiter
from app.core.security import UploadValidationError, validate_upload
from app.core.temp_files import new_upload_path, resolve_result
from app.tools import get_processor, get_tool, list_categories, list_tools
from app.tools.content import enrich
from app.core.schema import category_schema, tool_schema
from app.tools.seo_meta import PAGE_META

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _ensure_free(text: str, *, subject: str) -> str:
    """Guarantee the word "Free" appears in a meta title/description.

    Most entries already say it, so this only fills the gaps — and it applies at
    response time, meaning a tool added later gets the treatment without anyone
    remembering to edit its copy.
    """
    if not text:
        return text
    if re.search(r"\bfree\b", text, re.I):
        return text
    return f"Free {text}" if subject == "title" else f"Free tool. {text}"


def _tool_meta(slug: str, name: str, description: str) -> dict:
    """Meta title/description for a tool, always mentioning that it's free.

    Falls back to the tool's own name/description when it has no hand-written
    entry, so every tool page gets a usable title instead of an empty one.
    """
    m = PAGE_META.get(slug) or {}
    title = m.get("meta_title") or f"{name} – Online Tool | ToolSimpli"
    desc = m.get("meta_description") or description
    out = {
        "meta_title": _ensure_free(title, subject="title"),
        "meta_description": _ensure_free(desc, subject="description"),
    }
    if m.get("keywords"):
        out["seo_keywords"] = m["keywords"]
    return out



@router.get("/categories")
def categories():
    out = []
    for c in list_categories():
        d = asdict(c)
        m = PAGE_META.get(c.slug)
        if m:
            d["meta_title"] = _ensure_free(m["meta_title"], subject="title")
            d["meta_description"] = _ensure_free(m["meta_description"], subject="description")
        d["schema"] = category_schema(c, list_tools(c.slug),
                                      meta_description=d.get("meta_description", ""))
        out.append(d)
    return out


@router.get("")
def all_tools(category: str | None = None):
    tools = list_tools(category)
    return {
        "count": len(tools),
        "tools": [
            {
                "name": t.name,
                "slug": t.slug,
                "category": t.category,
                "description": t.description,
                "implemented": get_processor(t.slug) is not None,
                "pro": t.pro,
                "custom_ui": t.custom_ui,
                "coming_soon": t.coming_soon,
            }
            for t in tools
        ],
    }


@router.get("/{slug}")
def tool_config(slug: str):
    tool = get_tool(slug)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    data = tool.public_dict()
    data["implemented"] = get_processor(slug) is not None
    data.update(enrich(tool))  # about, features, benefits, faqs
    data.update(_tool_meta(slug, tool.name, tool.description))
    # Structured data is derived from the tool config + its FAQs, so a new tool
    # gets valid JSON-LD without anyone writing it by hand.
    data["schema"] = tool_schema(tool, faqs=data.get("faqs"),
                                 meta_description=data["meta_description"])
    return data


@router.post("/{slug}/process")
@limiter.limit("60/minute")  # protect CPU-heavy processing from a single abuser
async def process_tool(
    request: Request,
    slug: str,
    files: list[UploadFile] = File(default=[]),
    text: str = Form(default=""),
    options: str = Form(default="{}"),
):
    """Run a tool. Uploaded files are written to /tmp/uploads, processed, and the
    result is written to /tmp/results (auto-deleted after the TTL). Nothing is
    persisted to the database."""
    import json

    tool = get_tool(slug)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    processor = get_processor(slug)
    if processor is None:
        raise HTTPException(status_code=501, detail=f"'{tool.name}' is coming soon.")

    try:
        parsed_options = json.loads(options or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid options JSON")

    # Persist uploads to temp dir with validation.
    from app.config import settings

    max_bytes = (tool.max_upload_mb or settings.max_upload_mb) * 1024 * 1024
    if tool.supports_single_upload and not tool.supports_multi_upload and len(files) > 1:
        raise HTTPException(status_code=400, detail="This tool accepts only one file.")
    saved_paths = []
    for upload in files:
        content = await upload.read()
        try:
            validate_upload(upload, tool.accepted_extensions, content, max_bytes)
        except UploadValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        dest = new_upload_path(upload.filename or "upload")
        dest.write_bytes(content)
        saved_paths.append(dest)

    try:
        result = processor(files=saved_paths, text=text, options=parsed_options)
    except Exception as e:  # surface processing errors cleanly
        raise HTTPException(status_code=422, detail=f"Processing failed: {e}")

    return result.public_dict()


@router.get("/download/{token}")
def download(token: str):
    path = resolve_result(token)
    if not path:
        raise HTTPException(status_code=404, detail="File not found or expired")
    # Strip the uuid prefix for a clean download name.
    display = path.name.split("__", 1)[-1]
    return FileResponse(path, filename=display)


@router.post("/download-zip")
def download_zip(tokens: list[str]):
    """Bundle multiple result files into a single ZIP for download."""
    buf = io.BytesIO()
    found = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for token in tokens:
            path = resolve_result(token)
            if path:
                zf.write(path, arcname=path.name.split("__", 1)[-1])
                found += 1
    if found == 0:
        raise HTTPException(status_code=404, detail="No valid files to zip")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="results.zip"'},
    )
