"""Image tool processors (Pillow + qrcode)."""
from __future__ import annotations

import base64
import io
import mimetypes
from pathlib import Path

from app.core.temp_files import new_result_path
from app.tools.registry import ResultFile, ToolResult, register


def _save_result(data: bytes, name: str) -> ResultFile:
    path = new_result_path(name)
    path.write_bytes(data)
    mime, _ = mimetypes.guess_type(name)
    return ResultFile(token=path.name, name=name, size=len(data), mime=mime or "application/octet-stream")


def _require_pil():
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


@register("image-compressor")
def image_compressor(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    quality = int(options.get("quality", 70) or 70)
    results: list[ResultFile] = []
    for src in files:
        img = Image.open(src)
        buf = io.BytesIO()
        fmt = "JPEG" if img.mode in ("RGB", "L") else "PNG"
        if fmt == "JPEG" and img.mode != "RGB":
            img = img.convert("RGB")
        save_kwargs = {"quality": quality, "optimize": True} if fmt == "JPEG" else {"optimize": True}
        img.save(buf, format=fmt, **save_kwargs)
        ext = "jpg" if fmt == "JPEG" else "png"
        stem = Path(src.name).stem.split("__", 1)[-1]
        results.append(_save_result(buf.getvalue(), f"compressed_{stem}.{ext}"))
    return ToolResult(files=results, meta={"count": len(results)})


@register("image-resize")
def image_resize(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    width = int(options.get("width", 800) or 800)
    height = int(options.get("height", 600) or 600)
    keep = bool(options.get("keep_aspect", True))
    results: list[ResultFile] = []
    for src in files:
        img = Image.open(src)
        if keep:
            img.thumbnail((width, height))
        else:
            img = img.resize((width, height))
        buf = io.BytesIO()
        fmt = img.format or "PNG"
        img.save(buf, format=fmt)
        stem = Path(src.name).stem.split("__", 1)[-1]
        results.append(_save_result(buf.getvalue(), f"resized_{stem}.{fmt.lower()}"))
    return ToolResult(files=results, meta={"count": len(results)})


@register("image-rotate")
def image_rotate(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    angle = int(options.get("angle", 90) or 90)
    results: list[ResultFile] = []
    for src in files:
        img = Image.open(src)
        out = img.rotate(-angle, expand=True)  # negative = clockwise
        buf = io.BytesIO()
        fmt = img.format or "PNG"
        out.save(buf, format=fmt)
        stem = Path(src.name).stem.split("__", 1)[-1]
        results.append(_save_result(buf.getvalue(), f"rotated_{stem}.{fmt.lower()}"))
    return ToolResult(files=results, meta={"count": len(results)})


def _convert(files: list[Path], target_fmt: str, target_ext: str, force_rgb: bool = False) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    results: list[ResultFile] = []
    for src in files:
        img = Image.open(src)
        if force_rgb and img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format=target_fmt)
        stem = Path(src.name).stem.split("__", 1)[-1]
        results.append(_save_result(buf.getvalue(), f"{stem}.{target_ext}"))
    return ToolResult(files=results, meta={"count": len(results)})


@register("jpg-to-png")
def jpg_to_png(files, text, options):
    return _convert(files, "PNG", "png")


@register("png-to-jpg")
def png_to_jpg(files, text, options):
    return _convert(files, "JPEG", "jpg", force_rgb=True)


@register("png-to-webp")
def png_to_webp(files, text, options):
    return _convert(files, "WEBP", "webp")


@register("webp-to-png")
def webp_to_png(files, text, options):
    return _convert(files, "PNG", "png")


@register("image-metadata-viewer")
def image_metadata_viewer(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    img = Image.open(files[0])
    meta = {
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
    }
    exif = getattr(img, "_getexif", lambda: None)()
    if exif:
        from PIL.ExifTags import TAGS
        meta["exif"] = {TAGS.get(k, str(k)): str(v) for k, v in exif.items() if isinstance(v, (str, int, float))}
    return ToolResult(meta=meta)


@register("image-to-base64")
def image_to_base64(files: list[Path], text: str, options: dict) -> ToolResult:
    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    data = files[0].read_bytes()
    mime, _ = mimetypes.guess_type(files[0].name)
    encoded = base64.b64encode(data).decode("ascii")
    return ToolResult(text=f"data:{mime or 'image/png'};base64,{encoded}",
                      meta={"bytes": len(data)})


@register("image-crop")
def image_crop(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    if not files:
        return ToolResult(meta={"error": "No file uploaded"})
    x = int(options.get("x", 0) or 0)
    y = int(options.get("y", 0) or 0)
    w = int(options.get("width", 400) or 400)
    h = int(options.get("height", 400) or 400)
    img = Image.open(files[0])
    box = (x, y, min(x + w, img.width), min(y + h, img.height))
    if box[0] >= box[2] or box[1] >= box[3]:
        return ToolResult(meta={"error": "Crop box is outside the image bounds"})
    out = img.crop(box)
    buf = io.BytesIO()
    fmt = img.format or "PNG"
    out.save(buf, format=fmt)
    stem = Path(files[0].name).stem.split("__", 1)[-1]
    return ToolResult(files=[_save_result(buf.getvalue(), f"cropped_{stem}.{fmt.lower()}")])


_POS = {
    "bottom-right": ("r", "b"), "bottom-left": ("l", "b"),
    "top-right": ("r", "t"), "top-left": ("l", "t"), "center": ("c", "c"),
}


@register("image-watermark")
def image_watermark(files: list[Path], text: str, options: dict) -> ToolResult:
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image, ImageDraw, ImageFont

    wm_text = options.get("text", "© Toolkit Pro") or "© Toolkit Pro"
    opacity = int(255 * max(10, min(int(options.get("opacity", 50) or 50), 100)) / 100)
    hpos, vpos = _POS.get(options.get("position", "bottom-right"), ("r", "b"))

    results: list[ResultFile] = []
    for src in files:
        base = Image.open(src).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font_size = max(14, base.width // 20)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        tb = draw.textbbox((0, 0), wm_text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        margin = max(10, base.width // 50)
        x = {"l": margin, "c": (base.width - tw) // 2, "r": base.width - tw - margin}[hpos]
        y = {"t": margin, "c": (base.height - th) // 2, "b": base.height - th - margin * 2}[vpos]
        draw.text((x, y), wm_text, fill=(255, 255, 255, opacity), font=font,
                  stroke_width=1, stroke_fill=(0, 0, 0, opacity))
        out = Image.alpha_composite(base, overlay).convert("RGB")
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        stem = Path(src.name).stem.split("__", 1)[-1]
        results.append(_save_result(buf.getvalue(), f"watermarked_{stem}.png"))
    return ToolResult(files=results, meta={"count": len(results)})


def _bg_remove_colorkey(img, tolerance: int):
    """Fast, vectorized background removal by color-keying the border color.

    Estimates the background from the median of the border pixels, then makes
    matching pixels transparent with a feathered (anti-aliased) edge. Works well
    on solid / near-solid backgrounds. Requires numpy.
    """
    import numpy as np
    from PIL import Image

    arr = np.asarray(img.convert("RGBA")).astype(np.float32)
    rgb = arr[..., :3]
    # Estimate background colour from the border ring (robust to a non-uniform subject).
    border = np.concatenate(
        [rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0
    )
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))  # Euclidean distance per pixel
    lo = float(tolerance)
    hi = lo * 2.0 + 1.0
    # frac=0 (transparent) when close to bg, ramps to 1 (opaque) past the threshold.
    frac = np.clip((dist - lo) / (hi - lo), 0.0, 1.0)
    arr[..., 3] = arr[..., 3] * frac
    return Image.fromarray(arr.clip(0, 255).astype("uint8"), "RGBA")


@register("background-remover")
def background_remover(files: list[Path], text: str, options: dict) -> ToolResult:
    """Remove an image background, returning a transparent PNG.

    Uses the `rembg` ML model when it is installed (best quality on real photos),
    and otherwise falls back to a fast vectorized color-key — ideal for solid or
    near-solid backgrounds (product shots, logos, icons)."""
    if not _require_pil():
        return ToolResult(meta={"error": "Pillow not installed"})
    from PIL import Image

    try:
        import numpy  # noqa: F401
    except ImportError:
        return ToolResult(meta={"error": "numpy is required for background removal"})

    tolerance = int(options.get("tolerance", 30) or 30)

    # Prefer rembg (U2Net) if available for studio-grade cutouts on any background.
    # NOTE: rembg calls sys.exit() (raising SystemExit, a BaseException — NOT an
    # Exception) when onnxruntime is missing, so we must catch BaseException here.
    try:
        from rembg import remove as rembg_remove
    except BaseException:
        rembg_remove = None

    results: list[ResultFile] = []
    engine = "colorkey"
    for src in files:
        img = Image.open(src).convert("RGBA")
        out = None
        if rembg_remove is not None:
            try:
                out = rembg_remove(img)
                if not isinstance(out, Image.Image):  # some versions return bytes
                    out = Image.open(io.BytesIO(out)).convert("RGBA")
                engine = "rembg"
            except Exception:
                # Model download/inference failed (e.g. offline) — fall back gracefully.
                out = None
        if out is None:
            out = _bg_remove_colorkey(img, tolerance)
            engine = "colorkey"

        buf = io.BytesIO()
        out.save(buf, format="PNG")
        stem = Path(src.name).stem.split("__", 1)[-1]
        results.append(_save_result(buf.getvalue(), f"nobg_{stem}.png"))
    return ToolResult(files=results, meta={"count": len(results), "engine": engine})


@register("base64-to-image")
def base64_to_image(files: list[Path], text: str, options: dict) -> ToolResult:
    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={"error": "Paste a Base64 string or data URI"})
    ext = "png"
    if raw.startswith("data:"):
        header, _, raw = raw.partition(",")
        if "image/" in header:
            ext = header.split("image/")[1].split(";")[0] or "png"
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception:
        return ToolResult(meta={"error": "Invalid Base64 data"})
    return ToolResult(files=[_save_result(data, f"image.{ext}")])


@register("barcode-generator")
def barcode_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError:
        return ToolResult(meta={"error": "python-barcode not installed"})
    value = (text or "").strip()
    if not value:
        return ToolResult(meta={"error": "Enter a value to encode"})
    kind = options.get("type", "code128")
    try:
        cls = barcode.get_barcode_class(kind)
        obj = cls(value, writer=ImageWriter())
        buf = io.BytesIO()
        obj.write(buf)
    except Exception as e:
        return ToolResult(meta={"error": f"Could not generate barcode: {e}"})
    data = buf.getvalue()
    preview = base64.b64encode(data).decode("ascii")
    return ToolResult(files=[_save_result(data, f"barcode_{kind}.png")],
                      meta={"preview_data_uri": f"data:image/png;base64,{preview}"})


@register("qr-code-generator")
def qr_code_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    try:
        import qrcode
    except ImportError:
        return ToolResult(meta={"error": "qrcode not installed"})
    if not (text or "").strip():
        return ToolResult(meta={"error": "Enter text or a URL to encode"})

    qr = qrcode.QRCode(box_size=int(options.get("box_size", 10) or 10), border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(
        fill_color=options.get("fill_color", "#000000"),
        back_color=options.get("back_color", "#ffffff"),
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    rf = _save_result(buf.getvalue(), "qrcode.png")
    preview = base64.b64encode(buf.getvalue()).decode("ascii")
    return ToolResult(files=[rf], meta={"preview_data_uri": f"data:image/png;base64,{preview}"})
