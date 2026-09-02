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

    wm_text = options.get("text", "© Toolsimpli") or "© Toolsimpli"
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


# ===========================================================================
# Shared helpers for the tools below
# ===========================================================================

def _int(options: dict, key: str, default: int) -> int:
    try:
        return int(float(str(options.get(key, default)).strip() or default))
    except (TypeError, ValueError):
        return default


def _float(options: dict, key: str, default: float) -> float:
    try:
        return float(str(options.get(key, default)).strip() or default)
    except (TypeError, ValueError):
        return default


def _flag(options: dict, key: str, default: bool = False) -> bool:
    value = options.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _stem(src: Path) -> str:
    """The visitor's own filename, with the upload's uuid prefix removed."""
    return Path(src.name).stem.split("__", 1)[-1]


def _open(src: Path):
    """Open an upload, honouring the EXIF orientation flag.

    Phone cameras store the picture sideways plus a rotation flag. Without
    exif_transpose every crop and resize below would work on the sideways
    version, and the result comes out rotated.
    """
    from PIL import Image, ImageOps

    img = Image.open(src)
    rotated = ImageOps.exif_transpose(img)
    if rotated is not img and rotated is not None:
        # exif_transpose returns a NEW image, which carries no `.format` — the
        # dimension checker reported "None" for every upload because of it.
        rotated.format = img.format
        rotated.info.setdefault("dpi", img.info.get("dpi", (72, 72)))
        return rotated
    return img


def _encode(img, fmt: str, quality: int = 90, **extra) -> bytes:
    """Encode to bytes, converting the mode when the format cannot hold alpha."""
    import io as _io

    fmt = fmt.upper()
    if fmt in ("JPG", "JPEG"):
        fmt = "JPEG"
        if img.mode in ("RGBA", "LA", "P"):
            # JPEG has no alpha channel; flatten onto white rather than failing.
            from PIL import Image

            background = Image.new("RGB", img.size, "white")
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        extra = {"quality": quality, "optimize": True, "progressive": True, **extra}
    elif fmt == "PNG":
        extra = {"optimize": True, **extra}
    elif fmt in ("WEBP", "AVIF"):
        extra = {"quality": quality, **extra}
    buf = _io.BytesIO()
    img.save(buf, format=fmt, **extra)
    return buf.getvalue()


def _no_files() -> ToolResult:
    return ToolResult(meta={"error": "Upload an image to start."})


# ===========================================================================
# Crop and shape
# ===========================================================================

@register("circle-crop")
def circle_crop(files: list[Path], text: str, options: dict) -> ToolResult:
    """Crops to a circle with a transparent outside — PNG only, by necessity."""
    from PIL import Image, ImageDraw

    if not files:
        return _no_files()
    results = []
    for src in files:
        img = _open(src).convert("RGBA")
        side = min(img.size)
        left, top = (img.width - side) // 2, (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side))
        size = _int(options, "size", 0)
        if size and size != side:
            img = img.resize((size, size), Image.LANCZOS)
            side = size
        # Drawn at 4x and downsampled: a circle drawn directly at final size has
        # visibly jagged edges, because the mask is 1-bit per pixel.
        scale = 4
        mask = Image.new("L", (side * scale, side * scale), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, side * scale - 1, side * scale - 1), fill=255)
        img.putalpha(mask.resize((side, side), Image.LANCZOS))
        results.append(_save_result(_encode(img, "PNG"), f"circle_{_stem(src)}.png"))
    return ToolResult(files=results, meta={
        "count": len(results),
        "note": "Saved as PNG — JPEG cannot store the transparent corners.",
    })


@register("round-corners")
def round_corners(files: list[Path], text: str, options: dict) -> ToolResult:
    from PIL import Image, ImageDraw

    if not files:
        return _no_files()
    percent = max(0.0, min(_float(options, "radius_percent", 15), 50))
    results = []
    for src in files:
        img = _open(src).convert("RGBA")
        radius = int(min(img.size) * percent / 100)
        scale = 4
        mask = Image.new("L", (img.width * scale, img.height * scale), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, img.width * scale - 1, img.height * scale - 1),
            radius=radius * scale, fill=255)
        img.putalpha(mask.resize(img.size, Image.LANCZOS))
        results.append(_save_result(_encode(img, "PNG"), f"rounded_{_stem(src)}.png"))
    return ToolResult(files=results, meta={"count": len(results), "corner_radius_percent": percent})


@register("shape-crop")
def shape_crop(files: list[Path], text: str, options: dict) -> ToolResult:
    """Crop to a fixed aspect ratio, or to a named shape."""
    from PIL import Image, ImageDraw, ImageOps

    if not files:
        return _no_files()
    shape = str(options.get("shape", "square"))
    ratios = {"square": (1, 1), "4:3": (4, 3), "3:4": (3, 4), "16:9": (16, 9),
              "9:16": (9, 16), "3:2": (3, 2), "2:3": (2, 3)}
    results = []
    for src in files:
        img = _open(src)
        if shape in ratios:
            w, h = ratios[shape]
            # ImageOps.fit crops from the centre to the exact ratio rather than
            # squashing, which is what "crop to 16:9" is expected to mean.
            target = (img.width, int(img.width * h / w)) if img.width / img.height > w / h \
                else (int(img.height * w / h), img.height)
            img = ImageOps.fit(img, target, Image.LANCZOS, centering=(0.5, 0.5))
            out, ext = _encode(img, "PNG"), "png"
        else:
            side = min(img.size)
            img = ImageOps.fit(img.convert("RGBA"), (side, side), Image.LANCZOS)
            scale = 4
            mask = Image.new("L", (side * scale, side * scale), 0)
            draw = ImageDraw.Draw(mask)
            box = (0, 0, side * scale - 1, side * scale - 1)
            if shape == "triangle":
                draw.polygon([(side * scale // 2, 0), (0, side * scale - 1),
                              (side * scale - 1, side * scale - 1)], fill=255)
            elif shape == "hexagon":
                draw.regular_polygon((side * scale // 2, side * scale // 2, side * scale // 2),
                                     6, rotation=90, fill=255)
            elif shape == "star":
                draw.regular_polygon((side * scale // 2, side * scale // 2, side * scale // 2),
                                     5, rotation=0, fill=255)
            else:
                draw.ellipse(box, fill=255)
            img.putalpha(mask.resize((side, side), Image.LANCZOS))
            out, ext = _encode(img, "PNG"), "png"
        results.append(_save_result(out, f"{shape.replace(':', 'x')}_{_stem(src)}.{ext}"))
    return ToolResult(files=results, meta={"count": len(results), "shape": shape})


@register("bulk-image-resizer")
def bulk_image_resizer(files: list[Path], text: str, options: dict) -> ToolResult:
    """Resize many images at once, by dimension or by percentage."""
    from PIL import Image

    if not files:
        return _no_files()
    mode = str(options.get("mode", "fit"))
    fmt = str(options.get("format", "keep")).lower()
    quality = _int(options, "quality", 88)
    results, report = [], []
    for src in files:
        img = _open(src)
        before = img.size
        if mode == "percent":
            factor = max(1, _int(options, "percent", 50)) / 100
            size = (max(1, int(img.width * factor)), max(1, int(img.height * factor)))
            img = img.resize(size, Image.LANCZOS)
        else:
            width = _int(options, "width", 1200)
            height = _int(options, "height", 0)
            if mode == "exact" and width and height:
                img = img.resize((width, height), Image.LANCZOS)
            else:
                # thumbnail keeps the aspect ratio and never enlarges, which is
                # what "fit within" means — upscaling only adds blur.
                img.thumbnail((width or 10 ** 6, height or 10 ** 6), Image.LANCZOS)
        out_fmt = (src.suffix.lstrip(".") if fmt == "keep" else fmt) or "png"
        if out_fmt.lower() in ("jpg", "jpeg"):
            out_fmt = "JPEG"
        data = _encode(img, out_fmt, quality)
        ext = "jpg" if out_fmt == "JPEG" else out_fmt.lower()
        results.append(_save_result(data, f"resized_{_stem(src)}.{ext}"))
        report.append({"file": _stem(src), "from": f"{before[0]}x{before[1]}",
                       "to": f"{img.width}x{img.height}", "bytes": len(data)})
    return ToolResult(files=results, meta={"count": len(results), "images": report})


@register("universal-image-converter")
def universal_image_converter(files: list[Path], text: str, options: dict) -> ToolResult:
    """Between every raster format Pillow can write here."""
    if not files:
        return _no_files()
    target = str(options.get("format", "png")).lower()
    allowed = {"png", "jpg", "jpeg", "webp", "avif", "bmp", "tiff", "gif", "ico"}
    if target not in allowed:
        return ToolResult(meta={"error": f"Choose one of: {', '.join(sorted(allowed))}"})
    quality = _int(options, "quality", 90)
    results, notes = [], []
    for src in files:
        img = _open(src)
        if target == "ico":
            from PIL import Image

            # ICO holds several sizes in one file; browsers pick what they need.
            sizes = [(s, s) for s in (16, 32, 48, 64) if s <= max(img.size)] or [(32, 32)]
            import io as _io
            buf = _io.BytesIO()
            img.convert("RGBA").save(buf, format="ICO", sizes=sizes)
            data, ext = buf.getvalue(), "ico"
        elif target == "gif":
            data, ext = _encode(img.convert("P", palette=1), "GIF"), "gif"
        else:
            fmt = "JPEG" if target in ("jpg", "jpeg") else target.upper()
            data = _encode(img, fmt, quality)
            ext = "jpg" if fmt == "JPEG" else target
        if target in ("jpg", "jpeg") and img.mode in ("RGBA", "LA", "P"):
            notes.append(f"{_stem(src)}: transparency flattened onto white — JPEG has no alpha.")
        results.append(_save_result(data, f"{_stem(src)}.{ext}"))
    return ToolResult(files=results, meta={"count": len(results), "format": target,
                                           "notes": notes or ["Converted cleanly."]})


@register("png-compressor")
def png_compressor(files: list[Path], text: str, options: dict) -> ToolResult:
    """Shrinks PNGs by reducing the palette — the only real lever PNG has.

    PNG is lossless, so there is no quality slider. The saving comes from
    storing fewer distinct colours, which is why the result can band on a
    gradient but is nearly invisible on flat graphics, logos and screenshots.
    """
    from PIL import Image

    if not files:
        return _no_files()
    colors = max(2, min(_int(options, "colors", 256), 256))
    results, report = [], []
    for src in files:
        img = _open(src)
        original = src.stat().st_size
        has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
        work = img.convert("RGBA") if has_alpha else img.convert("RGB")
        if _flag(options, "reduce_colors", True):
            quantised = work.quantize(colors=colors, method=Image.FASTOCTREE if has_alpha else Image.MEDIANCUT)
        else:
            quantised = work
        data = _encode(quantised, "PNG")
        # Never hand back something bigger than what was uploaded.
        if len(data) >= original:
            data = src.read_bytes()
            note = "already smaller than anything we could produce — returned unchanged"
        else:
            note = f"saved {round(100 - len(data) / original * 100, 1)}%"
        results.append(_save_result(data, f"compressed_{_stem(src)}.png"))
        report.append({"file": _stem(src), "before": original, "after": len(data), "result": note})
    return ToolResult(files=results, meta={"count": len(results), "images": report})


@register("webp-avif-compressor")
def webp_avif_compressor(files: list[Path], text: str, options: dict) -> ToolResult:
    """Re-encode to WebP or AVIF, the two formats that beat JPEG at the same quality."""
    if not files:
        return _no_files()
    target = str(options.get("format", "webp")).lower()
    if target not in ("webp", "avif"):
        return ToolResult(meta={"error": "Choose webp or avif."})
    quality = max(1, min(_int(options, "quality", 80), 100))
    lossless = _flag(options, "lossless")
    results, report = [], []
    for src in files:
        img = _open(src)
        original = src.stat().st_size
        extra = {"lossless": True} if lossless and target == "webp" else {}
        data = _encode(img, target.upper(), quality, **extra)
        results.append(_save_result(data, f"{_stem(src)}.{target}"))
        report.append({"file": _stem(src), "before": original, "after": len(data),
                       "saved_percent": round(100 - len(data) / max(1, original) * 100, 1)})
    return ToolResult(files=results, meta={
        "count": len(results), "format": target, "images": report,
        "note": "AVIF compresses harder but encodes slower and is unsupported on very old browsers.",
    })


@register("svg-to-png")
def svg_to_png(files: list[Path], text: str, options: dict) -> ToolResult:
    """Rasterise SVG at any scale, or trace a raster into a rough SVG wrapper."""
    import io as _io

    direction = str(options.get("direction", "svg_to_png"))
    if direction == "svg_to_png":
        source = (text or "").strip().encode() if (text or "").strip() else None
        if not source and files:
            source = files[0].read_bytes()
        if not source:
            return ToolResult(meta={"error": "Upload an .svg file, or paste the SVG markup."})
        if b"<svg" not in source.lower():
            return ToolResult(meta={"error": "That doesn't look like SVG."})
        import fitz

        scale = max(0.1, min(_float(options, "scale", 2), 10))
        try:
            # PyMuPDF renders SVG directly, so there is no cairo/librsvg to install.
            doc = fitz.open(stream=source, filetype="svg")
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=True)
        except Exception as exc:  # noqa: BLE001 — malformed SVG, not a bug
            return ToolResult(meta={"error": f"Could not render that SVG: {exc}"})
        data = pix.tobytes("png")
        name = f"{_stem(files[0])}.png" if files else "image.png"
        return ToolResult(files=[_save_result(data, name)],
                          meta={"width": pix.width, "height": pix.height, "scale": scale})

    if not files:
        return _no_files()
    # Raster -> SVG here means embedding, not tracing: turning a photo into real
    # vector paths needs a tracer, and a fake one would produce a huge file that
    # still looks like a photo.
    img = _open(files[0])
    data = _encode(img, "PNG")
    encoded = base64.b64encode(data).decode()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{img.width}" height="{img.height}" '
           f'viewBox="0 0 {img.width} {img.height}">'
           f'<image width="{img.width}" height="{img.height}" '
           f'href="data:image/png;base64,{encoded}"/></svg>')
    return ToolResult(files=[_save_result(svg.encode(), f"{_stem(files[0])}.svg")],
                      text=svg[:2000] + ("…" if len(svg) > 2000 else ""),
                      meta={"note": "The image is embedded, not traced into vector paths."})


# ===========================================================================
# Adjustments and effects
# ===========================================================================

def _apply_each(files, options, transform, prefix: str, fmt: str = "PNG", ext: str = "png"):
    """Run `transform(img, options)` over every upload and save the results."""
    results = []
    for src in files:
        img = transform(_open(src), options)
        quality = _int(options, "quality", 90)
        results.append(_save_result(_encode(img, fmt, quality), f"{prefix}_{_stem(src)}.{ext}"))
    return results


@register("image-adjuster")
def image_adjuster(files: list[Path], text: str, options: dict) -> ToolResult:
    """Brightness, contrast, saturation, sharpness and gamma in one pass."""
    from PIL import Image, ImageEnhance

    if not files:
        return _no_files()

    def transform(img, opts):
        img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
        # 100 means "leave it alone" on every slider, so the defaults are a no-op.
        for key, enhancer in (("brightness", ImageEnhance.Brightness),
                              ("contrast", ImageEnhance.Contrast),
                              ("saturation", ImageEnhance.Color),
                              ("sharpness", ImageEnhance.Sharpness)):
            factor = _float(opts, key, 100) / 100
            if abs(factor - 1.0) > 0.001:
                img = enhancer(img).enhance(factor)
        gamma = _float(opts, "gamma", 1.0)
        if abs(gamma - 1.0) > 0.001 and gamma > 0:
            table = [min(255, int((i / 255) ** (1 / gamma) * 255)) for i in range(256)]
            channels = img.split()
            corrected = [c.point(table) for c in channels[:3]]
            img = Image.merge(img.mode, corrected + list(channels[3:]))
        return img

    return ToolResult(files=_apply_each(files, options, transform, "adjusted"),
                      meta={"count": len(files), "note": "100 leaves a slider untouched."})


@register("image-filters")
def image_filters(files: list[Path], text: str, options: dict) -> ToolResult:
    """Named looks, built from real colour maths rather than a preset table."""
    from PIL import Image, ImageEnhance, ImageOps

    if not files:
        return _no_files()
    effect = str(options.get("effect", "grayscale"))

    def transform(img, opts):
        rgb = img.convert("RGB")
        if effect == "grayscale":
            return ImageOps.grayscale(rgb)
        if effect == "sepia":
            grey = ImageOps.grayscale(rgb)
            # A warm duotone: dark tones go brown, highlights go cream.
            return ImageOps.colorize(grey, black="#2e1a08", white="#ffe6bf")
        if effect == "invert":
            return ImageOps.invert(rgb)
        if effect == "posterize":
            return ImageOps.posterize(rgb, max(1, min(_int(opts, "levels", 4), 8)))
        if effect == "solarize":
            return ImageOps.solarize(rgb, threshold=_int(opts, "threshold", 128))
        if effect == "vintage":
            faded = ImageEnhance.Color(rgb).enhance(0.55)
            faded = ImageEnhance.Contrast(faded).enhance(0.9)
            return ImageOps.colorize(ImageOps.grayscale(faded), "#20130a", "#f5e6cf").blend(
                faded, 0.5) if hasattr(ImageOps, "blend") else Image.blend(
                ImageOps.colorize(ImageOps.grayscale(faded), "#20130a", "#f5e6cf"), faded, 0.5)
        if effect == "cool":
            r, g, b = rgb.split()
            return Image.merge("RGB", (r.point(lambda v: max(0, v - 15)), g,
                                       b.point(lambda v: min(255, v + 25))))
        if effect == "warm":
            r, g, b = rgb.split()
            return Image.merge("RGB", (r.point(lambda v: min(255, v + 25)), g,
                                       b.point(lambda v: max(0, v - 20))))
        if effect == "high contrast":
            return ImageOps.autocontrast(rgb, cutoff=2)
        if effect == "duotone":
            return ImageOps.colorize(ImageOps.grayscale(rgb),
                                     str(opts.get("dark", "#1e1b4b")),
                                     str(opts.get("light", "#a5b4fc")))
        return rgb

    return ToolResult(files=_apply_each(files, options, transform, effect.replace(" ", "-")),
                      meta={"count": len(files), "effect": effect})


@register("black-and-white-converter")
def black_and_white_converter(files: list[Path], text: str, options: dict) -> ToolResult:
    """Greyscale, or a true two-tone threshold."""
    from PIL import Image, ImageOps

    if not files:
        return _no_files()
    mode = str(options.get("mode", "grayscale"))

    def transform(img, opts):
        grey = ImageOps.grayscale(img.convert("RGB"))
        if mode == "grayscale":
            return ImageOps.autocontrast(grey, cutoff=1) if _flag(opts, "auto_contrast") else grey
        if mode == "dithered":
            # Ordered dithering keeps detail readable in pure black and white —
            # a hard threshold would lose every mid-tone.
            return grey.convert("1")
        return grey.point(lambda v: 255 if v > _int(opts, "threshold", 128) else 0, mode="1")

    return ToolResult(files=_apply_each(files, options, transform, "bw"),
                      meta={"count": len(files), "mode": mode})


@register("sharpen-image")
def sharpen_image(files: list[Path], text: str, options: dict) -> ToolResult:
    """Unsharp masking — the technique every photo editor calls "sharpen"."""
    from PIL import ImageFilter

    if not files:
        return _no_files()

    def transform(img, opts):
        return img.convert("RGB").filter(ImageFilter.UnsharpMask(
            radius=max(0.1, _float(opts, "radius", 2)),
            percent=max(1, _int(opts, "amount", 150)),
            # Pixels differing by less than this are left alone, which keeps
            # sharpening off flat areas where it only amplifies noise.
            threshold=max(0, _int(opts, "threshold", 3))))

    return ToolResult(files=_apply_each(files, options, transform, "sharpened", "JPEG", "jpg"),
                      meta={"count": len(files)})


@register("blur-pixelate")
def blur_pixelate(files: list[Path], text: str, options: dict) -> ToolResult:
    """Blur or pixelate the whole image, or just one rectangle of it."""
    from PIL import Image, ImageFilter

    if not files:
        return _no_files()
    style = str(options.get("style", "blur"))

    def obscure(region, opts):
        if style == "pixelate":
            block = max(2, _int(opts, "block_size", 16))
            small = region.resize((max(1, region.width // block), max(1, region.height // block)),
                                  Image.NEAREST)
            return small.resize(region.size, Image.NEAREST)
        radius = max(0.5, _float(opts, "radius", 8))
        return region.filter(ImageFilter.GaussianBlur(radius))

    def transform(img, opts):
        img = img.convert("RGB")
        x = _int(opts, "x", 0); y = _int(opts, "y", 0)
        w = _int(opts, "width", 0); h = _int(opts, "height", 0)
        if w > 0 and h > 0:
            box = (max(0, x), max(0, y), min(img.width, x + w), min(img.height, y + h))
            if box[2] <= box[0] or box[3] <= box[1]:
                return img
            # Only the chosen rectangle is obscured — this is how you hide a face
            # or a number plate without ruining the rest of the photo.
            img.paste(obscure(img.crop(box), opts), box)
            return img
        return obscure(img, opts)

    return ToolResult(files=_apply_each(files, options, transform, style, "JPEG", "jpg"),
                      meta={"count": len(files), "style": style,
                            "note": "Leave width and height at 0 to affect the whole image."})


@register("motion-blur")
def motion_blur(files: list[Path], text: str, options: dict) -> ToolResult:
    """Directional blur — the streak you get from panning a camera.

    Built by averaging the image against copies of itself, each shifted one more
    pixel along the direction of travel. Pillow's convolution filter only
    accepts 3x3 and 5x5 kernels, which is far too small for a visible streak.
    """
    import numpy as np

    if not files:
        return _no_files()

    def transform(img, opts):
        from PIL import Image

        rgb = img.convert("RGB")
        length = max(3, min(_int(opts, "length", 15), 60))
        direction = str(opts.get("direction", "horizontal"))
        steps = {"horizontal": (1, 0), "vertical": (0, 1),
                 "diagonal": (1, 1), "anti-diagonal": (1, -1)}.get(direction, (1, 0))
        base = np.asarray(rgb, dtype=np.float32)
        total = np.zeros_like(base)
        for offset in range(length):
            # Centre the streak on the subject rather than dragging it one way.
            dx = steps[0] * (offset - length // 2)
            dy = steps[1] * (offset - length // 2)
            total += np.roll(np.roll(base, dy, axis=0), dx, axis=1)
        return Image.fromarray(np.clip(total / length, 0, 255).astype("uint8"))

    return ToolResult(files=_apply_each(files, options, transform, "motion", "JPEG", "jpg"),
                      meta={"count": len(files)})


@register("pixel-art-converter")
def pixel_art_converter(files: list[Path], text: str, options: dict) -> ToolResult:
    """Downsample hard, cut the palette, then scale back with nearest neighbour."""
    from PIL import Image

    if not files:
        return _no_files()

    def transform(img, opts):
        rgb = img.convert("RGB")
        width = max(8, min(_int(opts, "pixel_width", 64), 512))
        height = max(1, round(width * rgb.height / rgb.width))
        small = rgb.resize((width, height), Image.LANCZOS)
        colors = max(2, min(_int(opts, "colors", 16), 256))
        small = small.quantize(colors=colors, method=Image.MEDIANCUT).convert("RGB")
        if _flag(opts, "scale_back", True):
            factor = max(1, min(_int(opts, "scale", 8), 32))
            # NEAREST on the way back is what keeps the blocks crisp; any
            # smoothing filter would blur the pixels back into a normal photo.
            return small.resize((width * factor, height * factor), Image.NEAREST)
        return small

    return ToolResult(files=_apply_each(files, options, transform, "pixelart"),
                      meta={"count": len(files)})


@register("glitch-effect")
def glitch_effect(files: list[Path], text: str, options: dict) -> ToolResult:
    """Channel shifting and scanline displacement — the RGB-split look."""
    import random

    from PIL import Image, ImageEnhance

    if not files:
        return _no_files()

    def transform(img, opts):
        rgb = img.convert("RGB")
        strength = max(1, min(_int(opts, "strength", 10), 100))
        if _flag(opts, "rgb_split", True):
            r, g, b = rgb.split()
            shift = max(1, rgb.width * strength // 400)
            out = Image.new("RGB", rgb.size)
            # Each channel offset a different way: that separation is the effect.
            out.paste(Image.merge("RGB", (
                r.transform(r.size, Image.AFFINE, (1, 0, -shift, 0, 1, 0)),
                g,
                b.transform(b.size, Image.AFFINE, (1, 0, shift, 0, 1, 0)))), (0, 0))
            rgb = out
        for _ in range(strength // 2):
            y = random.randint(0, max(0, rgb.height - 12))
            band = rgb.crop((0, y, rgb.width, min(rgb.height, y + random.randint(2, 12))))
            rgb.paste(band, (random.randint(-strength * 3, strength * 3), y))
        if _flag(opts, "deep_fry"):
            rgb = ImageEnhance.Contrast(rgb).enhance(2.2)
            rgb = ImageEnhance.Color(rgb).enhance(3.0)
            rgb = ImageEnhance.Sharpness(rgb).enhance(4.0)
        return rgb

    quality = 12 if _flag(options, "deep_fry") else 88
    results = []
    for src in files:
        img = transform(_open(src), options)
        results.append(_save_result(_encode(img, "JPEG", quality), f"glitch_{_stem(src)}.jpg"))
    return ToolResult(files=results, meta={
        "count": len(results),
        "note": "Deep fry also crushes the JPEG quality, which is half the look.",
    })


@register("cartoon-effect")
def cartoon_effect(files: list[Path], text: str, options: dict) -> ToolResult:
    """A cartoon look from edge detection plus flat colour.

    Filters and posterisation, not a style-transfer model — so it runs instantly
    and needs nothing installed, but it will not redraw a face the way an AI
    cartooniser does.
    """
    from PIL import Image, ImageFilter, ImageOps

    if not files:
        return _no_files()

    def transform(img, opts):
        rgb = img.convert("RGB")
        # Median filter flattens texture while keeping edges, which is what makes
        # the posterised colour read as "drawn" rather than "reduced".
        flat = rgb.filter(ImageFilter.MedianFilter(size=max(3, min(_int(opts, "smoothing", 5), 9) | 1)))
        flat = ImageOps.posterize(flat, max(2, min(_int(opts, "levels", 4), 8)))
        edges = ImageOps.grayscale(rgb).filter(ImageFilter.FIND_EDGES)
        threshold = max(1, min(_int(opts, "edge_strength", 40), 200))
        outline = edges.point(lambda v: 0 if v > threshold else 255, mode="L")
        if _flag(opts, "outline", True):
            return Image.composite(Image.new("RGB", rgb.size, "black"), flat,
                                   ImageOps.invert(outline))
        return flat

    return ToolResult(files=_apply_each(files, options, transform, "cartoon", "JPEG", "jpg"),
                      meta={"count": len(files),
                            "note": "Filter-based, not an AI model — instant, but not a redraw."})


@register("scan-cleanup")
def scan_cleanup(files: list[Path], text: str, options: dict) -> ToolResult:
    """Straighten and whiten a photographed or scanned document."""
    import math

    from PIL import Image, ImageFilter, ImageOps

    if not files:
        return _no_files()
    results, report = [], []
    for src in files:
        img = _open(src).convert("RGB")
        grey = ImageOps.grayscale(img)
        angle = 0.0
        if _flag(options, "deskew", True):
            # Find the rotation that makes rows of text line up: the projection
            # profile of a straight page has the sharpest peaks and troughs.
            import numpy as np

            small = grey.resize((min(600, grey.width), min(800, grey.height)))
            best, arr = -1.0, None
            for candidate in [a / 2 for a in range(-16, 17)]:
                rotated = np.asarray(small.rotate(candidate, resample=Image.BILINEAR,
                                                  fillcolor=255), dtype=float)
                profile = rotated.sum(axis=1)
                score = float(((profile[1:] - profile[:-1]) ** 2).sum())
                if score > best:
                    best, angle = score, candidate
            if abs(angle) > 0.25:
                img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=(255, 255, 255),
                                 expand=True)
                grey = ImageOps.grayscale(img)
        if _flag(options, "whiten", True):
            # Divide by a heavily blurred copy to remove the uneven lighting a
            # phone camera leaves across a page, then stretch what remains.
            import numpy as np

            background = grey.filter(ImageFilter.GaussianBlur(radius=max(5, grey.width // 40)))
            a = np.asarray(grey, dtype=float)
            b = np.asarray(background, dtype=float)
            flat = np.clip(a / np.maximum(b, 1) * 255, 0, 255).astype("uint8")
            grey = Image.fromarray(flat)
            grey = ImageOps.autocontrast(grey, cutoff=(1, 20))
            img = grey.convert("RGB")
        if _flag(options, "sharpen", True):
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
        results.append(_save_result(_encode(img, "JPEG", 88), f"cleaned_{_stem(src)}.jpg"))
        report.append({"file": _stem(src), "straightened_by_degrees": round(-angle, 2)})
    return ToolResult(files=results, meta={"count": len(results), "images": report})


# ===========================================================================
# Colour analysis
# ===========================================================================

def _hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(c) for c in rgb[:3]))


def _color_name(rgb) -> str:
    """Nearest name from a small reference set — a label, not a colour system."""
    import colorsys

    r, g, b = (c / 255 for c in rgb[:3])
    h, light, sat = colorsys.rgb_to_hls(r, g, b)
    if sat < 0.12:
        return "black" if light < 0.2 else "white" if light > 0.85 else "grey"
    hue = h * 360
    names = [(15, "red"), (45, "orange"), (65, "yellow"), (150, "green"), (185, "teal"),
             (250, "blue"), (290, "purple"), (330, "pink"), (360, "red")]
    base = next(name for edge, name in names if hue <= edge)
    if light < 0.25:
        return f"dark {base}"
    if light > 0.75:
        return f"light {base}"
    return base


@register("image-color-picker")
def image_color_picker(files: list[Path], text: str, options: dict) -> ToolResult:
    """Read the exact colour at one pixel, plus the average of the area around it."""
    if not files:
        return _no_files()
    img = _open(files[0]).convert("RGB")
    x = max(0, min(_int(options, "x", img.width // 2), img.width - 1))
    y = max(0, min(_int(options, "y", img.height // 2), img.height - 1))
    pixel = img.getpixel((x, y))
    radius = max(0, min(_int(options, "sample_radius", 2), 50))
    box = (max(0, x - radius), max(0, y - radius),
           min(img.width, x + radius + 1), min(img.height, y + radius + 1))
    patch = img.crop(box)
    count = patch.width * patch.height
    totals = [0, 0, 0]
    for px in patch.getdata():
        totals[0] += px[0]; totals[1] += px[1]; totals[2] += px[2]
    average = tuple(t // count for t in totals)
    return ToolResult(meta={
        "image_size": f"{img.width}x{img.height}",
        "sampled_at": f"{x}, {y}",
        "pixel_hex": _hex(pixel), "pixel_rgb": f"rgb{pixel}", "pixel_name": _color_name(pixel),
        "average_hex": _hex(average), "average_rgb": f"rgb{average}",
        "note": "Averaging a few pixels avoids picking up JPEG noise from a single one.",
    })


def _palette(img, count: int):
    """Dominant colours, by quantising and reading the resulting palette."""
    from PIL import Image

    rgb = img.convert("RGB")
    # Quantising to more colours than asked for, then taking the biggest buckets,
    # gives a better spread than asking for exactly N — the extra buckets absorb
    # near-duplicates that would otherwise take a slot each.
    reduced = rgb.quantize(colors=min(256, count * 4), method=Image.MEDIANCUT)
    palette = reduced.getpalette() or []
    counts = sorted(reduced.getcolors(1 << 20) or [], reverse=True)
    total = sum(n for n, _ in counts) or 1
    out = []
    for n, index in counts[:count]:
        colour = tuple(palette[index * 3: index * 3 + 3])
        if len(colour) < 3:
            continue
        out.append({"hex": _hex(colour), "rgb": f"rgb{colour}",
                    "share_percent": round(n / total * 100, 2),
                    "name": _color_name(colour)})
    return out


@register("color-palette-extractor")
def color_palette_extractor(files: list[Path], text: str, options: dict) -> ToolResult:
    if not files:
        return _no_files()
    count = max(2, min(_int(options, "colors", 8), 24))
    img = _open(files[0])
    colours = _palette(img, count)
    css = ":root {\n" + "\n".join(
        f"  --color-{i + 1}: {c['hex']};" for i, c in enumerate(colours)) + "\n}"
    return ToolResult(text=css, meta={
        "palette": colours,
        "hex_list": [c["hex"] for c in colours],
    })


@register("dominant-color-finder")
def dominant_color_finder(files: list[Path], text: str, options: dict) -> ToolResult:
    """The single colour a viewer would call the image's colour."""
    if not files:
        return _no_files()
    img = _open(files[0])
    colours = _palette(img, 6)
    if not colours:
        return ToolResult(meta={"error": "Could not read any colour from that image."})
    top = colours[0]
    if _flag(options, "ignore_neutrals", True):
        # A photo on a white background is not "white" — skip the near-greys
        # unless nothing else is left.
        vivid = [c for c in colours if "grey" not in c["name"]
                 and c["name"] not in ("white", "black")]
        if vivid:
            top = vivid[0]
    from PIL import Image

    swatch = Image.new("RGB", (240, 120), top["hex"])
    return ToolResult(
        files=[_save_result(_encode(swatch, "PNG"), "dominant_color.png")],
        meta={"dominant": top, "runners_up": colours[1:4],
              "note": "Neutral backgrounds are skipped by default."})


@register("color-histogram")
def color_histogram(files: list[Path], text: str, options: dict) -> ToolResult:
    """Tonal distribution per channel, drawn as a chart."""
    from PIL import Image, ImageDraw

    if not files:
        return _no_files()
    img = _open(files[0]).convert("RGB")
    r, g, b = (img.getchannel(c).histogram() for c in ("R", "G", "B"))
    width, height = 512, 200
    chart = Image.new("RGB", (width, height + 20), "white")
    draw = ImageDraw.Draw(chart)
    peak = max(max(r), max(g), max(b)) or 1
    for values, colour in ((r, (220, 60, 60)), (g, (60, 180, 90)), (b, (70, 110, 230))):
        points = [(i * width / 256, height - values[i] / peak * height) for i in range(256)]
        draw.line(points, fill=colour, width=2)
    draw.line([(0, height), (width, height)], fill=(180, 180, 180))
    grey = img.convert("L").histogram()
    pixels = img.width * img.height
    dark = sum(grey[:64]) / pixels * 100
    bright = sum(grey[192:]) / pixels * 100
    verdict = ("Underexposed — most of the image sits in the shadows." if dark > 60
               else "Overexposed — most of the image sits in the highlights." if bright > 60
               else "Reasonably balanced exposure.")
    return ToolResult(
        files=[_save_result(_encode(chart, "PNG"), "histogram.png")],
        meta={"pixels": pixels,
              "shadows_percent": round(dark, 1), "highlights_percent": round(bright, 1),
              "mean_brightness": round(sum(i * n for i, n in enumerate(grey)) / pixels, 1),
              "clipped_black_percent": round(grey[0] / pixels * 100, 2),
              "clipped_white_percent": round(grey[255] / pixels * 100, 2),
              "verdict": verdict})


# ===========================================================================
# Metadata and inspection
# ===========================================================================

@register("exif-remover")
def exif_remover(files: list[Path], text: str, options: dict) -> ToolResult:
    """Strip EXIF, including the GPS coordinates a phone writes into every photo."""
    if not files:
        return _no_files()
    results, report = [], []
    for src in files:
        img = _open(src)
        had = {}
        try:
            raw = img.getexif()
            if raw:
                from PIL.ExifTags import GPSTAGS, TAGS

                had = {TAGS.get(k, k): str(v)[:40] for k, v in raw.items()}
                gps = raw.get_ifd(0x8825)
                if gps:
                    had["GPS"] = ", ".join(str(GPSTAGS.get(k, k)) for k in gps)
        except Exception:  # noqa: BLE001 — unreadable EXIF is not a failure here
            pass
        # Re-encoding from the raw pixel data is what actually drops the metadata;
        # copying the file and deleting tags leaves fragments behind.
        from PIL import Image

        clean = Image.new(img.mode, img.size)
        clean.putdata(list(img.getdata()))
        fmt = "PNG" if img.mode in ("RGBA", "LA", "P") else "JPEG"
        ext = "png" if fmt == "PNG" else "jpg"
        results.append(_save_result(_encode(clean, fmt, _int(options, "quality", 92)),
                                    f"clean_{_stem(src)}.{ext}"))
        report.append({"file": _stem(src), "tags_removed": len(had),
                       "had_gps": "GPS" in had,
                       "removed": sorted(had)[:15]})
    return ToolResult(files=results, meta={
        "count": len(results), "images": report,
        "note": "GPS coordinates in a photo can pin down where you live. Strip before sharing.",
    })


@register("image-dimension-checker")
def image_dimension_checker(files: list[Path], text: str, options: dict) -> ToolResult:
    from math import gcd

    if not files:
        return _no_files()
    rows = []
    for src in files:
        img = _open(src)
        size = src.stat().st_size
        divisor = gcd(img.width, img.height) or 1
        megapixels = img.width * img.height / 1_000_000
        rows.append({
            "file": _stem(src),
            "width": img.width, "height": img.height,
            "aspect_ratio": f"{img.width // divisor}:{img.height // divisor}",
            "megapixels": round(megapixels, 2),
            "format": img.format, "mode": img.mode,
            "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info,
            "file_size_bytes": size,
            "file_size_readable": f"{size / 1024:.1f} KB" if size < 1024 ** 2 else f"{size / 1024 ** 2:.2f} MB",
            "bytes_per_pixel": round(size / max(1, img.width * img.height), 3),
        })
    return ToolResult(meta={"count": len(rows), "images": rows})


@register("dpi-checker")
def dpi_checker(files: list[Path], text: str, options: dict) -> ToolResult:
    """Read or set DPI, and work out the real printed size.

    DPI is only a number stored in the file — changing it does not add detail.
    It tells a printer how large to render the pixels you already have.
    """
    if not files:
        return _no_files()
    new_dpi = _int(options, "set_dpi", 0)
    results, rows = [], []
    for src in files:
        img = _open(src)
        current = img.info.get("dpi", (72, 72))
        try:
            dpi_x = float(current[0]) or 72
        except (TypeError, ValueError, IndexError):
            dpi_x = 72
        effective = new_dpi or dpi_x
        rows.append({
            "file": _stem(src),
            "pixels": f"{img.width}x{img.height}",
            "stored_dpi": round(dpi_x, 1),
            "print_size_inches": f"{img.width / effective:.2f} x {img.height / effective:.2f}",
            "print_size_cm": f"{img.width / effective * 2.54:.1f} x {img.height / effective * 2.54:.1f}",
            "print_quality": ("photo quality" if effective >= 300 else
                              "acceptable for large prints" if effective >= 150 else
                              "screen only — will look soft in print"),
        })
        if new_dpi:
            fmt = "PNG" if img.mode in ("RGBA", "LA", "P") else "JPEG"
            ext = "png" if fmt == "PNG" else "jpg"
            import io as _io
            buf = _io.BytesIO()
            save = img if fmt == "PNG" or img.mode == "RGB" else img.convert("RGB")
            save.save(buf, format=fmt, dpi=(new_dpi, new_dpi),
                      **({"quality": 95} if fmt == "JPEG" else {}))
            results.append(_save_result(buf.getvalue(), f"{new_dpi}dpi_{_stem(src)}.{ext}"))
    return ToolResult(files=results, meta={
        "images": rows,
        "note": "Setting DPI changes the printed size, never the amount of detail.",
    })


@register("reverse-image-search")
def reverse_image_search(files: list[Path], text: str, options: dict) -> ToolResult:
    """Builds the search links for an image URL, on every major engine."""
    from urllib.parse import quote

    url = (text or "").strip() or str(options.get("image_url", "")).strip()
    if not url:
        return ToolResult(meta={
            "error": "Paste the image's public URL. Right-click the image on any page "
                     "and choose 'Copy image address'."
        })
    if not url.lower().startswith(("http://", "https://")):
        return ToolResult(meta={"error": "That must be a full URL starting with https://"})
    encoded = quote(url, safe="")
    links = {
        "Google Lens": f"https://lens.google.com/uploadbyurl?url={encoded}",
        "Bing": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{encoded}",
        "Yandex": f"https://yandex.com/images/search?rpt=imageview&url={encoded}",
        "TinEye": f"https://tineye.com/search?url={encoded}",
    }
    return ToolResult(text="\n".join(f"{name}: {link}" for name, link in links.items()),
                      meta={"links": links,
                            "note": "The image must be publicly reachable — these engines "
                                    "fetch it themselves."})


# ===========================================================================
# Generators and composition
# ===========================================================================

def _font(size: int):
    """A TrueType face at the requested size, falling back to Pillow's bitmap font.

    No font is bundled, so this walks the usual system paths. The bitmap
    fallback ignores `size`, which is why the caller is told what it got.
    """
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size), True
            except OSError:
                continue
    return ImageFont.load_default(), False


def _wrap(draw, message: str, font, max_width: int) -> list[str]:
    lines, current = [], ""
    for word in message.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


@register("add-text-to-image")
def add_text_to_image(files: list[Path], text: str, options: dict) -> ToolResult:
    from PIL import Image, ImageDraw

    if not files:
        return _no_files()
    message = (text or "").strip() or str(options.get("message", "")).strip()
    if not message:
        return ToolResult(meta={"error": "Type the text to place on the image."})
    results = []
    scalable = True
    for src in files:
        img = _open(src).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        size = _int(options, "font_size", 0) or max(16, img.width // 16)
        font, scalable = _font(size)
        colour = str(options.get("color", "#ffffff"))
        lines = _wrap(draw, message, font, int(img.width * 0.9))
        spacing = int(size * 0.25)
        heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in lines]
        block = sum(heights) + spacing * (len(lines) - 1)
        position = str(options.get("position", "bottom"))
        top = {"top": int(img.height * 0.05),
               "middle": (img.height - block) // 2}.get(position, img.height - block - int(img.height * 0.05))
        for line, height in zip(lines, heights):
            width = draw.textlength(line, font=font)
            x = (img.width - width) / 2
            if _flag(options, "outline", True):
                stroke = max(1, size // 18)
                draw.text((x, top), line, font=font, fill=colour,
                          stroke_width=stroke, stroke_fill=str(options.get("outline_color", "#000000")))
            else:
                draw.text((x, top), line, font=font, fill=colour)
            top += height + spacing
        opacity = max(0, min(_int(options, "opacity", 100), 100))
        if opacity < 100:
            alpha = overlay.getchannel("A").point(lambda v: int(v * opacity / 100))
            overlay.putalpha(alpha)
        img = Image.alpha_composite(img, overlay)
        results.append(_save_result(_encode(img, "PNG"), f"text_{_stem(src)}.png"))
    meta = {"count": len(results)}
    if not scalable:
        meta["warning"] = "No scalable font found on the server, so the size setting was ignored."
    return ToolResult(files=results, meta=meta)


@register("add-border")
def add_border(files: list[Path], text: str, options: dict) -> ToolResult:
    from PIL import Image, ImageOps

    if not files:
        return _no_files()
    results = []
    for src in files:
        img = _open(src).convert("RGB")
        style = str(options.get("style", "solid"))
        width = max(1, _int(options, "width", max(8, img.width // 40)))
        colour = str(options.get("color", "#ffffff"))
        if style == "polaroid":
            # A polaroid frame is not uniform: the bottom edge is much deeper.
            img = ImageOps.expand(img, border=(width, width, width, width * 5), fill=colour)
        elif style == "double":
            inner = str(options.get("inner_color", "#111827"))
            img = ImageOps.expand(img, border=max(1, width // 3), fill=inner)
            img = ImageOps.expand(img, border=max(1, width // 6), fill=colour)
            img = ImageOps.expand(img, border=width, fill=inner)
        else:
            img = ImageOps.expand(img, border=width, fill=colour)
        results.append(_save_result(_encode(img, "JPEG", 92), f"framed_{_stem(src)}.jpg"))
    return ToolResult(files=results, meta={"count": len(results)})


@register("meme-generator")
def meme_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    """Classic top and bottom caption, in the usual heavy outlined style."""
    from PIL import Image, ImageDraw

    if not files:
        return _no_files()
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    top_text = str(options.get("top", "")).strip() or (lines[0] if lines else "")
    bottom_text = str(options.get("bottom", "")).strip() or (lines[1] if len(lines) > 1 else "")
    if not top_text and not bottom_text:
        return ToolResult(meta={"error": "Enter the top line, the bottom line, or both."})
    img = _open(files[0]).convert("RGB")
    draw = ImageDraw.Draw(img)
    size = _int(options, "font_size", 0) or max(20, img.width // 10)
    font, scalable = _font(size)
    stroke = max(2, size // 12)

    def place(message: str, at_top: bool) -> None:
        if not message:
            return
        caption = message.upper() if _flag(options, "uppercase", True) else message
        wrapped = _wrap(draw, caption, font, int(img.width * 0.92))
        heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in wrapped]
        block = sum(heights) + 6 * (len(wrapped) - 1)
        y = int(img.height * 0.03) if at_top else img.height - block - int(img.height * 0.03)
        for line, height in zip(wrapped, heights):
            x = (img.width - draw.textlength(line, font=font)) / 2
            draw.text((x, y), line, font=font, fill="white",
                      stroke_width=stroke, stroke_fill="black")
            y += height + 6

    place(top_text, True)
    place(bottom_text, False)
    meta = {"top": top_text, "bottom": bottom_text}
    if not scalable:
        meta["warning"] = "No scalable font on the server — the caption size setting was ignored."
    return ToolResult(files=[_save_result(_encode(img, "JPEG", 92), "meme.jpg")], meta=meta)


@register("collage-maker")
def collage_maker(files: list[Path], text: str, options: dict) -> ToolResult:
    """Arrange several images into a grid, all cells the same size."""
    from PIL import Image, ImageOps

    if len(files) < 2:
        return ToolResult(meta={"error": "Upload at least two images."})
    columns = _int(options, "columns", 0) or max(1, round(len(files) ** 0.5))
    columns = max(1, min(columns, len(files)))
    rows = -(-len(files) // columns)
    cell = max(80, min(_int(options, "cell_size", 400), 1600))
    gap = max(0, min(_int(options, "gap", 10), 100))
    background = str(options.get("background", "#ffffff"))
    canvas = Image.new("RGB",
                       (columns * cell + gap * (columns + 1), rows * cell + gap * (rows + 1)),
                       background)
    for index, src in enumerate(files):
        # fit() crops to the cell rather than squashing, so faces stay proportioned.
        tile = ImageOps.fit(_open(src).convert("RGB"), (cell, cell), Image.LANCZOS,
                            centering=(0.5, 0.5))
        x = gap + (index % columns) * (cell + gap)
        y = gap + (index // columns) * (cell + gap)
        canvas.paste(tile, (x, y))
    return ToolResult(files=[_save_result(_encode(canvas, "JPEG", 90), "collage.jpg")],
                      meta={"images": len(files), "grid": f"{columns} x {rows}",
                            "size": f"{canvas.width}x{canvas.height}"})


@register("image-splitter")
def image_splitter(files: list[Path], text: str, options: dict) -> ToolResult:
    """Cut one image into a grid — the Instagram carousel trick."""
    if not files:
        return _no_files()
    columns = max(1, min(_int(options, "columns", 3), 10))
    rows = max(1, min(_int(options, "rows", 1), 10))
    img = _open(files[0]).convert("RGB")
    piece_w, piece_h = img.width // columns, img.height // rows
    if piece_w < 1 or piece_h < 1:
        return ToolResult(meta={"error": "That grid is finer than the image has pixels."})
    results = []
    for row in range(rows):
        for col in range(columns):
            # The last row and column take the remainder, so no pixels are lost
            # to integer division.
            right = img.width if col == columns - 1 else (col + 1) * piece_w
            bottom = img.height if row == rows - 1 else (row + 1) * piece_h
            piece = img.crop((col * piece_w, row * piece_h, right, bottom))
            results.append(_save_result(_encode(piece, "JPEG", 92),
                                        f"{_stem(files[0])}_r{row + 1}c{col + 1}.jpg"))
    return ToolResult(files=results, meta={
        "pieces": len(results), "grid": f"{columns} x {rows}",
        "piece_size": f"{piece_w}x{piece_h}",
        "note": "Upload to a carousel in order, left to right, top row first.",
    })


@register("favicon-generator")
def favicon_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    """Every icon a site needs, plus the HTML to reference them."""
    import io as _io

    from PIL import Image, ImageOps

    if not files:
        return _no_files()
    img = _open(files[0]).convert("RGBA")
    square = ImageOps.fit(img, (512, 512), Image.LANCZOS)
    results = []
    # A multi-size .ico is what old browsers and Windows shortcuts still read.
    buf = _io.BytesIO()
    square.save(buf, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    results.append(_save_result(buf.getvalue(), "favicon.ico"))
    for size in (16, 32, 96, 180, 192, 512):
        resized = square.resize((size, size), Image.LANCZOS)
        if size == 180:
            # Apple touch icons are composited on a background by iOS, so give
            # them an opaque one rather than letting iOS pick black.
            background = Image.new("RGB", (size, size), str(options.get("apple_background", "#ffffff")))
            background.paste(resized, mask=resized.split()[-1])
            results.append(_save_result(_encode(background, "PNG"), "apple-touch-icon.png"))
            continue
        results.append(_save_result(_encode(resized, "PNG"), f"favicon-{size}x{size}.png"))
    html = "\n".join([
        '<link rel="icon" href="/favicon.ico" sizes="any">',
        '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">',
        '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">',
        '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
    ])
    return ToolResult(files=results, text=html,
                      meta={"files": len(results),
                            "note": "Put these in your site root and paste the HTML into <head>."})


@register("placeholder-image-generator")
def placeholder_image_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    from PIL import Image, ImageDraw

    width = max(16, min(_int(options, "width", 800), 4000))
    height = max(16, min(_int(options, "height", 600), 4000))
    background = str(options.get("background", "#e2e8f0"))
    foreground = str(options.get("color", "#475569"))
    label = (text or "").strip() or str(options.get("label", "")).strip() or f"{width} x {height}"
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)
    if _flag(options, "diagonals"):
        draw.line([(0, 0), (width, height)], fill=foreground, width=2)
        draw.line([(width, 0), (0, height)], fill=foreground, width=2)
    font, _ = _font(max(12, min(width, height) // 8))
    box = draw.textbbox((0, 0), label, font=font)
    draw.text(((width - (box[2] - box[0])) / 2, (height - (box[3] - box[1])) / 2 - box[1]),
              label, font=font, fill=foreground)
    fmt = str(options.get("format", "png")).upper()
    fmt = "JPEG" if fmt in ("JPG", "JPEG") else "PNG"
    ext = "jpg" if fmt == "JPEG" else "png"
    return ToolResult(files=[_save_result(_encode(img, fmt, 90), f"placeholder-{width}x{height}.{ext}")],
                      meta={"size": f"{width}x{height}"})


@register("gradient-generator")
def gradient_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    """A gradient image plus the CSS that reproduces it."""
    import math

    from PIL import Image

    width = max(16, min(_int(options, "width", 1200), 4000))
    height = max(16, min(_int(options, "height", 600), 4000))
    start = str(options.get("start_color", "#4f46e5"))
    end = str(options.get("end_color", "#ec4899"))

    def parse(value: str):
        v = value.strip().lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        try:
            return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return None

    a, b = parse(start), parse(end)
    if a is None or b is None:
        return ToolResult(meta={"error": "Colours must be hex, like #4f46e5."})
    style = str(options.get("style", "linear"))
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    centre = (width / 2, height / 2)
    longest = math.hypot(centre[0], centre[1]) or 1
    angle = math.radians(_int(options, "angle", 90))
    dx, dy = math.cos(angle), math.sin(angle)
    span = abs(width * dx) + abs(height * dy) or 1
    for y in range(height):
        for x in range(width):
            if style == "radial":
                t = math.hypot(x - centre[0], y - centre[1]) / longest
            else:
                t = ((x - (width / 2 if dx < 0 else 0)) * dx +
                     (y - (height / 2 if dy < 0 else 0)) * dy) / span + 0.5
            t = max(0.0, min(1.0, t))
            pixels[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    css = (f"background: radial-gradient(circle, {start}, {end});" if style == "radial"
           else f"background: linear-gradient({_int(options, 'angle', 90)}deg, {start}, {end});")
    return ToolResult(files=[_save_result(_encode(img, "PNG"), "gradient.png")],
                      text=css, meta={"size": f"{width}x{height}", "css": css})


@register("signature-maker")
def signature_maker(files: list[Path], text: str, options: dict) -> ToolResult:
    """Turns a photo of a signature into a clean transparent PNG.

    Everything lighter than the threshold becomes transparent, so the paper
    disappears and only the ink is left — which is what makes it usable on a
    contract without a white box around it.
    """
    import numpy as np
    from PIL import Image, ImageOps

    if not files:
        return _no_files()
    img = _open(files[0]).convert("RGB")
    grey = np.asarray(ImageOps.grayscale(img), dtype=np.int16)
    threshold = max(1, min(_int(options, "threshold", 160), 254))
    ink = grey < threshold
    if not ink.any():
        return ToolResult(meta={
            "error": "No dark strokes found. Raise the threshold, or photograph the "
                     "signature on plain white paper in good light."
        })
    # Alpha ramps with darkness instead of being on/off, which keeps the thin
    # tapered ends of a pen stroke from turning into jagged steps.
    alpha = np.clip((threshold - grey) * 255 // max(1, threshold), 0, 255).astype("uint8")
    colour = str(options.get("ink_color", "#000000")).lstrip("#")
    try:
        rgb = tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        rgb = (0, 0, 0)
    out = Image.new("RGBA", img.size, rgb + (0,))
    out.putalpha(Image.fromarray(alpha))
    if _flag(options, "trim", True):
        rows = np.any(ink, axis=1); cols = np.any(ink, axis=0)
        top, bottom = int(np.argmax(rows)), int(len(rows) - np.argmax(rows[::-1]))
        left, right = int(np.argmax(cols)), int(len(cols) - np.argmax(cols[::-1]))
        pad = 8
        out = out.crop((max(0, left - pad), max(0, top - pad),
                        min(img.width, right + pad), min(img.height, bottom + pad)))
    return ToolResult(files=[_save_result(_encode(out, "PNG"), "signature.png")],
                      meta={"size": f"{out.width}x{out.height}",
                            "ink_pixels": int(ink.sum()),
                            "note": "Transparent PNG — drop it straight onto a document."})


@register("passport-photo-maker")
def passport_photo_maker(files: list[Path], text: str, options: dict) -> ToolResult:
    """Crops to an official photo size and lays out a print sheet.

    The crop is centred, not face-detected: check the head position against your
    country's rules before submitting, since those requirements are exact.
    """
    from PIL import Image, ImageOps

    if not files:
        return _no_files()
    sizes_mm = {
        "US passport (2x2 in)": (51, 51), "UK / EU passport (35x45 mm)": (35, 45),
        "India passport (35x45 mm)": (35, 45), "Schengen visa (35x45 mm)": (35, 45),
        "China visa (33x48 mm)": (33, 48), "Canada passport (50x70 mm)": (50, 70),
        "Australia passport (35x45 mm)": (35, 45),
    }
    choice = str(options.get("size", "US passport (2x2 in)"))
    if choice not in sizes_mm:
        return ToolResult(meta={"error": f"Choose one of: {', '.join(sizes_mm)}"})
    dpi = max(150, min(_int(options, "dpi", 300), 1200))
    mm_w, mm_h = sizes_mm[choice]
    px = (round(mm_w / 25.4 * dpi), round(mm_h / 25.4 * dpi))
    photo = ImageOps.fit(_open(files[0]).convert("RGB"), px, Image.LANCZOS, centering=(0.5, 0.4))
    background = str(options.get("background", "")).strip()
    results = [_save_result(_encode(photo, "JPEG", 95), "passport-photo.jpg")]
    if _flag(options, "print_sheet", True):
        # A 6x4 inch print is the cheapest thing any shop will print, so the
        # sheet is sized to that rather than to A4.
        sheet_px = (round(6 * dpi), round(4 * dpi))
        sheet = Image.new("RGB", sheet_px, "white")
        gap = round(0.08 * dpi)
        cols = max(1, (sheet_px[0] - gap) // (px[0] + gap))
        rows = max(1, (sheet_px[1] - gap) // (px[1] + gap))
        for r in range(rows):
            for c in range(cols):
                sheet.paste(photo, (gap + c * (px[0] + gap), gap + r * (px[1] + gap)))
        import io as _io
        buf = _io.BytesIO(); sheet.save(buf, "JPEG", quality=95, dpi=(dpi, dpi))
        results.append(_save_result(buf.getvalue(), "print-sheet-6x4.jpg"))
    return ToolResult(files=results, meta={
        "size": choice, "pixels": f"{px[0]}x{px[1]}", "dpi": dpi,
        "copies_on_sheet": cols * rows if _flag(options, "print_sheet", True) else 0,
        "warning": "Centre crop, not face detection — check head size and position "
                   "against your country's rules before submitting.",
    })


_ASCII_RAMP = "@%#*+=-:. "


@register("image-to-ascii")
def image_to_ascii(files: list[Path], text: str, options: dict) -> ToolResult:
    from PIL import ImageOps

    if not files:
        return _no_files()
    width = max(20, min(_int(options, "width", 100), 400))
    img = _open(files[0])
    grey = ImageOps.grayscale(img)
    if _flag(options, "enhance_contrast", True):
        grey = ImageOps.autocontrast(grey, cutoff=2)
    # Terminal characters are about twice as tall as they are wide, so the
    # height is halved or the picture comes out stretched.
    height = max(1, round(width * grey.height / grey.width * 0.5))
    grey = grey.resize((width, height))
    ramp = _ASCII_RAMP[::-1] if _flag(options, "invert") else _ASCII_RAMP
    pixels = list(grey.getdata())
    rows = []
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        rows.append("".join(ramp[min(len(ramp) - 1, v * len(ramp) // 256)] for v in row))
    art = "\n".join(rows)
    return ToolResult(text=art, files=[_save_result(art.encode(), "ascii-art.txt")],
                      meta={"columns": width, "rows": height})


@register("sprite-sheet-generator")
def sprite_sheet_generator(files: list[Path], text: str, options: dict) -> ToolResult:
    """Pack images into one sheet, with the CSS to address each frame."""
    from PIL import Image

    if len(files) < 2:
        return ToolResult(meta={"error": "Upload at least two images."})
    layout = str(options.get("layout", "horizontal"))
    cell_w = max(_open(f).width for f in files)
    cell_h = max(_open(f).height for f in files)
    if layout == "grid":
        columns = _int(options, "columns", 0) or max(1, round(len(files) ** 0.5))
    elif layout == "vertical":
        columns = 1
    else:
        columns = len(files)
    columns = max(1, min(columns, len(files)))
    rows = -(-len(files) // columns)
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (0, 0, 0, 0))
    css = [f".sprite {{ width: {cell_w}px; height: {cell_h}px; "
           f"background-image: url('sprite-sheet.png'); }}"]
    for i, src in enumerate(files):
        frame = _open(src).convert("RGBA")
        x, y = (i % columns) * cell_w, (i // columns) * cell_h
        # Centred in its cell, so frames of different sizes still line up.
        sheet.paste(frame, (x + (cell_w - frame.width) // 2, y + (cell_h - frame.height) // 2),
                    frame)
        name = "".join(ch if ch.isalnum() else "-" for ch in _stem(src).lower()).strip("-")
        css.append(f".sprite-{name or i + 1} {{ background-position: -{x}px -{y}px; }}")
    return ToolResult(files=[_save_result(_encode(sheet, "PNG"), "sprite-sheet.png")],
                      text="\n".join(css),
                      meta={"frames": len(files), "grid": f"{columns} x {rows}",
                            "cell": f"{cell_w}x{cell_h}"})


@register("css-image-snippet")
def css_image_snippet(files: list[Path], text: str, options: dict) -> ToolResult:
    """Embed an image in CSS as a data URI, with a size warning that matters."""
    if not files:
        return _no_files()
    src = files[0]
    data = src.read_bytes()
    import mimetypes as _mt

    mime = _mt.guess_type(src.name)[0] or "image/png"
    encoded = base64.b64encode(data).decode()
    uri = f"data:{mime};base64,{encoded}"
    selector = str(options.get("selector", ".hero")) or ".hero"
    css = (f"{selector} {{\n"
           f"  background-image: url('{uri}');\n"
           f"  background-size: {options.get('size', 'cover')};\n"
           f"  background-position: {options.get('position', 'center')};\n"
           f"  background-repeat: no-repeat;\n}}")
    # Base64 is about a third larger than the file, and it cannot be cached
    # separately from the stylesheet — worth saying before someone inlines a photo.
    inflated = len(encoded)
    return ToolResult(text=css, files=[_save_result(css.encode(), "background.css")],
                      meta={"file_bytes": len(data), "encoded_bytes": inflated,
                            "growth_percent": round(inflated / max(1, len(data)) * 100 - 100, 1),
                            "advice": ("Small enough to inline." if len(data) < 8000 else
                                       "Over 8 KB — inlining this blocks your CSS from rendering. "
                                       "Link to the file instead.")})


# ===========================================================================
# Sizing presets and GIF
# ===========================================================================

# Width x height for the placements people actually export for. Kept as data so
# a platform changing its spec is a one-line edit.
_SOCIAL_SIZES: dict[str, tuple[int, int]] = {
    "Instagram post (square)": (1080, 1080),
    "Instagram portrait": (1080, 1350),
    "Instagram story / Reel": (1080, 1920),
    "Facebook post": (1200, 630),
    "Facebook cover": (1640, 856),
    "X / Twitter post": (1600, 900),
    "X / Twitter header": (1500, 500),
    "LinkedIn post": (1200, 627),
    "LinkedIn banner": (1584, 396),
    "YouTube thumbnail": (1280, 720),
    "YouTube channel art": (2560, 1440),
    "Pinterest pin": (1000, 1500),
    "TikTok video": (1080, 1920),
    "Open Graph / link preview": (1200, 630),
}


@register("social-media-resizer")
def social_media_resizer(files: list[Path], text: str, options: dict) -> ToolResult:
    """Export one image at the right size for each placement you tick."""
    from PIL import Image, ImageOps

    if not files:
        return _no_files()
    wanted = [p.strip() for p in str(options.get("platforms", "")).split(",") if p.strip()]
    if not wanted:
        wanted = ["Instagram post (square)", "Facebook post", "X / Twitter post",
                  "YouTube thumbnail", "Open Graph / link preview"]
    unknown = [p for p in wanted if p not in _SOCIAL_SIZES]
    if unknown:
        return ToolResult(meta={
            "error": f"Unknown: {', '.join(unknown)}. Available: {', '.join(_SOCIAL_SIZES)}"
        })
    img = _open(files[0]).convert("RGB")
    fill = str(options.get("mode", "crop"))
    results, rows = [], []
    for name in wanted:
        size = _SOCIAL_SIZES[name]
        if fill == "pad":
            # Nothing is cut off, but the shape differs from the image, so the
            # gap is filled rather than the subject being cropped away.
            copy = img.copy()
            copy.thumbnail(size, Image.LANCZOS)
            canvas = Image.new("RGB", size, str(options.get("background", "#ffffff")))
            canvas.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
            out = canvas
        else:
            out = ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.4))
        slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
        results.append(_save_result(_encode(out, "JPEG", 90), f"{slug}-{size[0]}x{size[1]}.jpg"))
        rows.append({"placement": name, "size": f"{size[0]}x{size[1]}"})
    return ToolResult(files=results, meta={"exports": rows, "mode": fill})


@register("profile-picture-maker")
def profile_picture_maker(files: list[Path], text: str, options: dict) -> ToolResult:
    """A square avatar, optionally circular, at the sizes profiles ask for."""
    from PIL import Image, ImageDraw, ImageOps

    if not files:
        return _no_files()
    size = max(64, min(_int(options, "size", 512), 2048))
    img = ImageOps.fit(_open(files[0]).convert("RGBA"), (size, size), Image.LANCZOS,
                       centering=(0.5, 0.4))
    ring = max(0, min(_int(options, "border_width", 0), size // 8))
    if ring:
        colour = str(options.get("border_color", "#ffffff"))
        framed = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        inner = img.resize((size - ring * 2, size - ring * 2), Image.LANCZOS)
        draw = ImageDraw.Draw(framed)
        if _flag(options, "circle", True):
            draw.ellipse((0, 0, size - 1, size - 1), fill=colour)
        else:
            draw.rectangle((0, 0, size - 1, size - 1), fill=colour)
        framed.paste(inner, (ring, ring), inner)
        img = framed
    if _flag(options, "circle", True):
        scale = 4
        mask = Image.new("L", (size * scale, size * scale), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
        img.putalpha(mask.resize((size, size), Image.LANCZOS))
    return ToolResult(files=[_save_result(_encode(img, "PNG"), f"avatar-{size}.png")],
                      meta={"size": f"{size}x{size}",
                            "note": "PNG, so a circular avatar keeps its transparent corners."})


@register("thumbnail-maker")
def thumbnail_maker(files: list[Path], text: str, options: dict) -> ToolResult:
    """Small, right-sized copies — with a caption if you want one."""
    from PIL import Image, ImageDraw, ImageOps

    if not files:
        return _no_files()
    width = max(32, min(_int(options, "width", 400), 2000))
    height = max(32, min(_int(options, "height", 300), 2000))
    caption = (text or "").strip()
    results = []
    for src in files:
        img = _open(src).convert("RGB")
        if _flag(options, "crop_to_fit", True):
            thumb = ImageOps.fit(img, (width, height), Image.LANCZOS, centering=(0.5, 0.4))
        else:
            thumb = img.copy()
            thumb.thumbnail((width, height), Image.LANCZOS)
        if caption:
            draw = ImageDraw.Draw(thumb, "RGBA")
            font, _ = _font(max(12, thumb.width // 14))
            box = draw.textbbox((0, 0), caption, font=font)
            bar = box[3] - box[1] + 16
            # A translucent bar behind the caption, so it stays readable whatever
            # the photo underneath happens to be.
            draw.rectangle((0, thumb.height - bar, thumb.width, thumb.height), fill=(0, 0, 0, 150))
            draw.text(((thumb.width - (box[2] - box[0])) / 2, thumb.height - bar + 8 - box[1]),
                      caption, font=font, fill="white")
        results.append(_save_result(_encode(thumb, "JPEG", 85), f"thumb_{_stem(src)}.jpg"))
    return ToolResult(files=results, meta={"count": len(results), "size": f"{width}x{height}"})


@register("background-changer")
def background_changer(files: list[Path], text: str, options: dict) -> ToolResult:
    """Replace the background behind a subject with a colour, or blur it.

    Works from a colour key, not a segmentation model: it removes pixels close
    to the corner colour, which is reliable on a plain studio background and
    unreliable on a busy one. Upload a cut-out PNG to skip the guessing.
    """
    import numpy as np
    from PIL import Image, ImageFilter

    if not files:
        return _no_files()
    img = _open(files[0]).convert("RGBA")
    arr = np.asarray(img).astype(np.int16)

    if arr[:, :, 3].min() < 250:
        # Already has transparency, so trust it rather than re-keying.
        alpha = np.asarray(img.getchannel("A"))
    else:
        corners = np.array([arr[0, 0, :3], arr[0, -1, :3], arr[-1, 0, :3], arr[-1, -1, :3]])
        key = corners.mean(axis=0)
        tolerance = max(5, min(_int(options, "tolerance", 60), 200))
        distance = np.sqrt(((arr[:, :, :3] - key) ** 2).sum(axis=2))
        # A soft ramp rather than a hard cut, or the subject gets a jagged halo.
        alpha = np.clip((distance - tolerance) / max(1, tolerance * 0.5) * 255, 0, 255).astype("uint8")
        alpha = np.asarray(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1)))

    coverage = float((alpha > 128).mean())
    subject = Image.fromarray(arr[:, :, :3].astype("uint8")).convert("RGBA")
    subject.putalpha(Image.fromarray(alpha))

    style = str(options.get("background", "color"))
    if style == "blur":
        canvas = Image.fromarray(arr[:, :, :3].astype("uint8")).filter(
            ImageFilter.GaussianBlur(max(2, _int(options, "blur_radius", 12)))).convert("RGBA")
    elif style == "transparent":
        canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
    elif style == "image" and len(files) > 1:
        from PIL import ImageOps
        canvas = ImageOps.fit(_open(files[1]).convert("RGBA"), img.size, Image.LANCZOS)
    else:
        canvas = Image.new("RGBA", img.size, str(options.get("color", "#ffffff")))
    out = Image.alpha_composite(canvas, subject)
    fmt = "PNG" if style == "transparent" else "PNG"
    return ToolResult(files=[_save_result(_encode(out, fmt), f"newbg_{_stem(files[0])}.png")],
                      meta={"subject_coverage_percent": round(coverage * 100, 1),
                            "background": style,
                            "note": "Colour-key removal — best on a plain, evenly lit background. "
                                    "Raise the tolerance if too much subject is cut, lower it if "
                                    "background remains."})


@register("gif-converter")
def gif_converter(files: list[Path], text: str, options: dict) -> ToolResult:
    """Build an animated GIF from images, or split one back into frames."""
    from PIL import Image, ImageSequence

    if not files:
        return _no_files()
    direction = str(options.get("direction", "images_to_gif"))

    if direction == "gif_to_frames":
        source = Image.open(files[0])
        if not getattr(source, "is_animated", False):
            return ToolResult(meta={"error": "That GIF has only one frame."})
        limit = max(1, min(_int(options, "max_frames", 60), 300))
        results = []
        for index, frame in enumerate(ImageSequence.Iterator(source)):
            if index >= limit:
                break
            results.append(_save_result(_encode(frame.convert("RGB"), "PNG"),
                                        f"frame_{index + 1:03d}.png"))
        return ToolResult(files=results, meta={
            "frames_extracted": len(results), "total_frames": source.n_frames,
            "truncated": source.n_frames > limit,
        })

    if len(files) < 2:
        return ToolResult(meta={"error": "Upload at least two images to animate."})
    frames = [_open(f).convert("RGB") for f in files]
    width = _int(options, "width", 0) or frames[0].width
    width = max(16, min(width, 1200))
    sized = []
    for frame in frames:
        height = max(1, round(width * frame.height / frame.width))
        sized.append(frame.resize((width, height), Image.LANCZOS))
    # Every frame must share one canvas size or the GIF jumps about.
    canvas_h = max(f.height for f in sized)
    normalised = []
    for frame in sized:
        if frame.height != canvas_h:
            pad = Image.new("RGB", (width, canvas_h), "white")
            pad.paste(frame, (0, (canvas_h - frame.height) // 2))
            frame = pad
        normalised.append(frame.convert("P", palette=Image.ADAPTIVE))
    import io as _io
    buf = _io.BytesIO()
    fps = max(1, min(_int(options, "fps", 5), 50))
    normalised[0].save(buf, format="GIF", save_all=True, append_images=normalised[1:],
                       duration=round(1000 / fps), loop=0 if _flag(options, "loop", True) else 1,
                       optimize=True, disposal=2)
    data = buf.getvalue()
    return ToolResult(files=[_save_result(data, "animation.gif")],
                      meta={"frames": len(normalised), "fps": fps,
                            "size": f"{width}x{canvas_h}", "bytes": len(data)})
