"""Exercises every implemented tool with a real input and reports pass/fail.

Run:  python test_all_tools.py
"""
import base64
import io

from PIL import Image
from pypdf import PdfWriter
from fastapi.testclient import TestClient

from app.main import app
from app.tools import get_processor, list_tools


def png_bytes(color=(120, 60, 200), size=(240, 160)):
    b = io.BytesIO(); Image.new("RGB", size, color).save(b, "PNG"); return b.getvalue()

def jpg_bytes(color=(200, 120, 60), size=(240, 160)):
    b = io.BytesIO(); Image.new("RGB", size, color).save(b, "JPEG"); return b.getvalue()

def webp_bytes(color=(60, 200, 120), size=(240, 160)):
    b = io.BytesIO(); Image.new("RGB", size, color).save(b, "WEBP"); return b.getvalue()

def pdf_bytes(pages=3):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=300, height=300)
    b = io.BytesIO(); w.write(b); return b.getvalue()

def docx_bytes():
    import docx
    d = docx.Document(); d.add_paragraph("Hello world from a docx file. " * 10)
    b = io.BytesIO(); d.save(b); return b.getvalue()

EXT_BYTES = {
    "pdf": ("doc.pdf", "application/pdf", pdf_bytes),
    "png": ("img.png", "image/png", png_bytes),
    "jpg": ("img.jpg", "image/jpeg", jpg_bytes),
    "jpeg": ("img.jpg", "image/jpeg", jpg_bytes),
    "webp": ("img.webp", "image/webp", webp_bytes),
    "docx": ("doc.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx_bytes),
}

JSON_TEXT = '{"name":"toolkit","items":[1,2,3],"ok":true}'
B64_TEXT = base64.b64encode(b"hello world").decode()
DATA_URI = "data:image/png;base64," + base64.b64encode(png_bytes()).decode()

# Per-slug overrides for text/options. Files are auto-derived from accepted_extensions.
TEXT_INPUTS = {
    "word-counter": "The quick brown fox. Jumps over!", "character-counter": "abc def",
    "case-converter": "hello world", "duplicate-line-remover": "a\na\nb",
    "text-sorter": "banana\napple\ncherry", "text-reverser": "hello world",
    "url-encoder": "a b&c=d", "url-decoder": "a%20b%26c",
    "json-formatter": JSON_TEXT, "json-validator": JSON_TEXT, "json-minifier": JSON_TEXT,
    "base64-encoder": "hello", "base64-decoder": B64_TEXT,
    "css-minifier": "a {  color : red ; }", "js-minifier": "var x = 1; // c\nvar y=2;",
    "html-formatter": "<div><p>hi</p></div>",
    "qr-code-generator": "https://example.com", "barcode-generator": "12345678",
    "base64-to-image": DATA_URI,
}
OPTION_INPUTS = {
    "pdf-protect": {"password": "secret123"},
    "image-resize": {"width": 120, "height": 80},
    "image-crop": {"x": 5, "y": 5, "width": 80, "height": 60},
    "lorem-ipsum-generator": {"paragraphs": 2}, "random-text-generator": {"length": 16},
    "uuid-generator": {"count": 2}, "password-generator": {"length": 12},
}
MULTI = {"pdf-merge", "jpg-to-pdf"}  # need >= 2 files


def build_files(tool):
    if not tool.accepted_extensions:
        return []
    ext = tool.accepted_extensions[0]
    name, mime, gen = EXT_BYTES[ext]
    count = 2 if tool.slug in MULTI else 1
    out = []
    for i in range(count):
        out.append(("files", (f"{i}_{name}", gen(), mime)))
    return out


def main():
    c = TestClient(app)
    tools = [t for t in list_tools() if get_processor(t.slug)]
    passed, failed = [], []
    with c:
        for t in tools:
            files = build_files(t)
            data = {"text": TEXT_INPUTS.get(t.slug, ""),
                    "options": __import__("json").dumps(OPTION_INPUTS.get(t.slug, {}))}
            kw = {"data": data}
            if files:
                kw["files"] = files
            r = c.post(f"/api/tools/{t.slug}/process", **kw)
            ok, why = True, ""
            if r.status_code != 200:
                ok, why = False, f"HTTP {r.status_code}: {r.json().get('detail','')[:60]}"
            else:
                j = r.json()
                err = (j.get("meta") or {}).get("error")
                has_output = bool(j.get("files")) or j.get("text") is not None or (j.get("meta") and not err)
                if err:
                    ok, why = False, f"meta.error: {err[:60]}"
                elif not has_output:
                    ok, why = False, "empty result"
            (passed if ok else failed).append((t.slug, why))
            print(f"{'PASS' if ok else 'FAIL'}  {t.slug:24} {why}")
    print(f"\n{len(passed)}/{len(tools)} passed; {len(failed)} failed")
    if failed:
        print("FAILED:", ", ".join(s for s, _ in failed))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
