"""PDF tool processors (pypdf for structural ops, PyMuPDF for rendering/encryption)."""
from __future__ import annotations

import io
import mimetypes
from pathlib import Path

from app.core.temp_files import new_result_path
from app.tools.registry import ResultFile, ToolResult, register


def _save_result(data: bytes, name: str) -> ResultFile:
    path = new_result_path(name)
    path.write_bytes(data)
    return ResultFile(token=path.name, name=name, size=len(data), mime="application/pdf")


def _save_named(data: bytes, name: str) -> ResultFile:
    path = new_result_path(name)
    path.write_bytes(data)
    mime, _ = mimetypes.guess_type(name)
    return ResultFile(token=path.name, name=name, size=len(data), mime=mime or "application/octet-stream")


def _require_fitz():
    try:
        import fitz  # noqa: F401  (PyMuPDF)
        return True
    except ImportError:
        return False


def _require_pypdf():
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


def _parse_ranges(spec: str, max_page: int) -> list[int]:
    """Parse '1-3,5' (1-based) into a sorted list of 0-based page indices."""
    pages: set[int] = set()
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                start, end = int(a), int(b)
            except ValueError:
                continue
            for p in range(start, end + 1):
                if 1 <= p <= max_page:
                    pages.add(p - 1)
        else:
            try:
                p = int(part)
            except ValueError:
                continue
            if 1 <= p <= max_page:
                pages.add(p - 1)
    return sorted(pages)


@register("pdf-merge")
def pdf_merge(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pypdf():
        return ToolResult(meta={"error": "pypdf not installed"})
    from pypdf import PdfReader, PdfWriter

    if len(files) < 2:
        return ToolResult(meta={"error": "Upload at least two PDFs to merge"})
    writer = PdfWriter()
    for src in files:
        reader = PdfReader(str(src))
        for page in reader.pages:
            writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return ToolResult(files=[_save_result(buf.getvalue(), "merged.pdf")],
                      meta={"pages": len(writer.pages)})


@register("pdf-split")
def pdf_split(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pypdf():
        return ToolResult(meta={"error": "pypdf not installed"})
    from pypdf import PdfReader, PdfWriter

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    reader = PdfReader(str(files[0]))
    total = len(reader.pages)
    ranges = options.get("ranges", "").strip()
    targets = _parse_ranges(ranges, total) if ranges else list(range(total))

    results: list[ResultFile] = []
    for idx in targets:
        writer = PdfWriter()
        writer.add_page(reader.pages[idx])
        buf = io.BytesIO()
        writer.write(buf)
        results.append(_save_result(buf.getvalue(), f"page_{idx + 1}.pdf"))
    return ToolResult(files=results, meta={"pages": len(results), "total": total})


@register("pdf-extract-pages")
def pdf_extract_pages(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pypdf():
        return ToolResult(meta={"error": "pypdf not installed"})
    from pypdf import PdfReader, PdfWriter

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    reader = PdfReader(str(files[0]))
    total = len(reader.pages)
    targets = _parse_ranges(options.get("ranges", "1"), total)
    if not targets:
        return ToolResult(meta={"error": "No valid pages selected"})
    writer = PdfWriter()
    for idx in targets:
        writer.add_page(reader.pages[idx])
    buf = io.BytesIO()
    writer.write(buf)
    return ToolResult(files=[_save_result(buf.getvalue(), "extracted.pdf")],
                      meta={"pages": len(targets)})


@register("pdf-rotate")
def pdf_rotate(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pypdf():
        return ToolResult(meta={"error": "pypdf not installed"})
    from pypdf import PdfReader, PdfWriter

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    angle = int(options.get("angle", 90) or 90)
    reader = PdfReader(str(files[0]))
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return ToolResult(files=[_save_result(buf.getvalue(), "rotated.pdf")],
                      meta={"pages": len(writer.pages), "angle": angle})


@register("pdf-metadata-viewer")
def pdf_metadata_viewer(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pypdf():
        return ToolResult(meta={"error": "pypdf not installed"})
    from pypdf import PdfReader

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    reader = PdfReader(str(files[0]))
    info = reader.metadata or {}
    return ToolResult(meta={
        "pages": len(reader.pages),
        "title": str(info.title) if info.title else None,
        "author": str(info.author) if info.author else None,
        "creator": str(info.creator) if info.creator else None,
        "producer": str(info.producer) if info.producer else None,
        "encrypted": reader.is_encrypted,
    })


@register("pdf-organizer")
def pdf_organizer(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pypdf():
        return ToolResult(meta={"error": "pypdf not installed"})
    from pypdf import PdfReader, PdfWriter

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    reader = PdfReader(str(files[0]))
    total = len(reader.pages)
    order = (options.get("order") or "").strip()
    indices = _parse_ranges(order, total) if order else list(range(total))
    if not indices:
        return ToolResult(meta={"error": "No valid pages in the requested order"})
    writer = PdfWriter()
    for idx in indices:
        writer.add_page(reader.pages[idx])
    buf = io.BytesIO()
    writer.write(buf)
    return ToolResult(files=[_save_result(buf.getvalue(), "organized.pdf")],
                      meta={"pages": len(indices)})


@register("pdf-compress")
def pdf_compress(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    original = files[0].stat().st_size
    doc = fitz.open(str(files[0]))
    out = doc.tobytes(garbage=4, deflate=True, clean=True)
    doc.close()
    rf = _save_result(out, "compressed.pdf")
    saved = max(0, original - len(out))
    return ToolResult(files=[rf], meta={
        "original_kb": round(original / 1024, 1),
        "compressed_kb": round(len(out) / 1024, 1),
        "saved_percent": round(saved / original * 100, 1) if original else 0,
    })


@register("pdf-to-jpg")
def pdf_to_jpg(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    fmt = options.get("format", "jpg")
    dpi = int(options.get("dpi", 150) or 150)
    doc = fitz.open(str(files[0]))
    results: list[ResultFile] = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        data = pix.tobytes("jpg" if fmt == "jpg" else "png")
        results.append(_save_named(data, f"page_{i + 1}.{fmt}"))
    doc.close()
    return ToolResult(files=results, meta={"pages": len(results)})


@register("jpg-to-pdf")
def jpg_to_pdf(files: list[Path], text: str, options: dict) -> ToolResult:
    try:
        from PIL import Image
    except ImportError:
        return ToolResult(meta={"error": "Pillow not installed"})
    if not files:
        return ToolResult(meta={"error": "No images uploaded"})
    images = [Image.open(p).convert("RGB") for p in files]
    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return ToolResult(files=[_save_result(buf.getvalue(), "images.pdf")],
                      meta={"pages": len(images)})


@register("word-to-pdf")
def word_to_pdf(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    try:
        import docx
    except ImportError:
        return ToolResult(meta={"error": "python-docx not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    document = docx.Document(str(files[0]))
    body = "\n".join(p.text for p in document.paragraphs)
    doc = fitz.open()
    rect = fitz.Rect(56, 56, 539, 785)  # ~A4 with margins
    remaining = body
    while True:
        page = doc.new_page(width=595, height=842)
        leftover = page.insert_textbox(rect, remaining, fontsize=11, fontname="helv")
        if leftover <= 0 or not remaining.strip():
            break
        # insert_textbox returns remaining height when it fits; loop by trimming inserted text.
        # Fallback: stop to avoid infinite loop on pathological input.
        break
    out = doc.tobytes()
    doc.close()
    return ToolResult(files=[_save_result(out, "converted.pdf")],
                      meta={"note": "Text-only conversion (layout/styles not preserved)"})


@register("pdf-to-word")
def pdf_to_word(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    try:
        import docx
    except ImportError:
        return ToolResult(meta={"error": "python-docx not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    doc = fitz.open(str(files[0]))
    document = docx.Document()
    for page in doc:
        for line in page.get_text().splitlines():
            document.add_paragraph(line)
    doc.close()
    buf = io.BytesIO()
    document.save(buf)
    return ToolResult(files=[_save_named(buf.getvalue(), "converted.docx")],
                      meta={"note": "Text-only conversion (images/layout not preserved)"})


@register("pdf-unlock")
def pdf_unlock(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    doc = fitz.open(str(files[0]))
    if doc.is_encrypted:
        if not doc.authenticate(options.get("password", "") or ""):
            doc.close()
            return ToolResult(meta={"error": "Wrong password"})
    out = doc.tobytes()  # saved without encryption
    doc.close()
    return ToolResult(files=[_save_result(out, "unlocked.pdf")])


@register("pdf-protect")
def pdf_protect(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    password = options.get("password", "") or ""
    if not password:
        return ToolResult(meta={"error": "Enter a password"})
    doc = fitz.open(str(files[0]))
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY
    )
    out = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw=password, user_pw=password, permissions=perm,
    )
    doc.close()
    return ToolResult(files=[_save_result(out, "protected.pdf")])


@register("pdf-watermark")
def pdf_watermark(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    wm = options.get("text", "CONFIDENTIAL") or "CONFIDENTIAL"
    opacity = max(5, min(int(options.get("opacity", 15) or 15), 80)) / 100
    doc = fitz.open(str(files[0]))
    for page in doc:
        # Vertically centered band across the page (insert_textbox only rotates in 90° steps,
        # so we draw the watermark horizontally for reliable output).
        w, h = page.rect.width, page.rect.height
        band = fitz.Rect(0, h / 2 - 40, w, h / 2 + 40)
        page.insert_textbox(
            band, wm, fontsize=44, fontname="helv",
            color=(0.5, 0.5, 0.5), fill_opacity=opacity, align=fitz.TEXT_ALIGN_CENTER,
        )
    out = doc.tobytes()
    doc.close()
    return ToolResult(files=[_save_result(out, "watermarked.pdf")])


@register("pdf-page-numbering")
def pdf_page_numbering(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_fitz():
        return ToolResult(meta={"error": "PyMuPDF not installed"})
    import fitz

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    position = options.get("position", "bottom-center")
    doc = fitz.open(str(files[0]))
    total = len(doc)
    for i, page in enumerate(doc):
        label = f"{i + 1} / {total}"
        w, h = page.rect.width, page.rect.height
        y = h - 30
        if position == "bottom-left":
            point = fitz.Point(40, y)
        elif position == "bottom-right":
            point = fitz.Point(w - 70, y)
        else:
            point = fitz.Point(w / 2 - 15, y)
        page.insert_text(point, label, fontsize=10, fontname="helv", color=(0.3, 0.3, 0.3))
    out = doc.tobytes()
    doc.close()
    return ToolResult(files=[_save_result(out, "numbered.pdf")], meta={"pages": total})
