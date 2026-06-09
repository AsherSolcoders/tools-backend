"""Tool catalogue + processing API.

The whole platform runs through these endpoints. The frontend reads tool configs
and renders UIs dynamically — no per-tool endpoints exist.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.security import UploadValidationError, validate_upload
from app.core.temp_files import new_upload_path, resolve_result
from app.tools import get_processor, get_tool, list_categories, list_tools
from app.tools.content import enrich

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/categories")
def categories():
    return [asdict(c) for c in list_categories()]


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
    return data


@router.post("/{slug}/process")
async def process_tool(
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
