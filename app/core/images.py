"""Strip identifying metadata from uploaded images before they are published.

Uploads used to be written to disk byte-for-byte, so a photo straight off a phone
kept its EXIF block — GPS coordinates of where it was taken, device make/model,
capture timestamp, and any embedded photographer name. All of that is readable by
anyone who opens the public image URL, so it is removed on upload.
"""
from __future__ import annotations

import io

# Formats that can carry EXIF/metadata and that Pillow can safely round-trip.
# GIF and SVG are deliberately absent: GIF re-encoding risks palette/transparency
# artefacts for no real benefit, and SVG is XML that Pillow cannot open at all.
_STRIPPABLE = {"JPEG", "PNG", "WEBP"}

# Re-encode settings. JPEG/WEBP are lossy, so a small quality cost is accepted in
# exchange for dropping metadata; PNG stays lossless.
_SAVE_PARAMS: dict[str, dict[str, object]] = {
    "JPEG": {"quality": 88, "optimize": True, "progressive": True},
    "WEBP": {"quality": 90, "method": 4},
    "PNG": {"optimize": True},
}


# Widths the thumbnail endpoint will produce. A fixed set (rather than an
# arbitrary ?w=) keeps the on-disk cache bounded and stops anyone filling the
# disk by requesting thousands of sizes.
THUMB_WIDTHS = (96, 480, 960)

# Originals are downscaled to this on upload. A 1731px-wide PNG straight from a
# screenshot tool was ~2.2 MB; capped and re-encoded it is ~175 KB, and no layout
# on the site displays an image wider than this.
MAX_UPLOAD_WIDTH = 1600


def _encode_webp(image, quality: int = 82) -> bytes:
    import io as _io

    buf = _io.BytesIO()
    # WebP keeps alpha, so RGBA images don't need flattening. P/LA are converted
    # because the WebP encoder rejects palette modes.
    if image.mode in ("P", "LA"):
        image = image.convert("RGBA")
    elif image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    image.save(buf, "WEBP", quality=quality, method=5)
    return buf.getvalue()


def make_thumbnail(content: bytes, width: int) -> bytes | None:
    """Downscale `content` to `width` px wide and return it as WebP.

    Returns None when a thumbnail can't be produced — animated images, SVG, or
    anything Pillow can't decode — so callers can fall back to the original file
    instead of serving a broken image.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        return None
    try:
        import io as _io

        with Image.open(_io.BytesIO(content)) as opened:
            if getattr(opened, "n_frames", 1) > 1:
                return None  # animated: a still frame would be a worse experience
            image = ImageOps.exif_transpose(opened) or opened
            # Never upscale: a small source stays its own size.
            if image.width > width:
                image = image.resize(
                    (width, max(1, round(image.height * width / image.width))),
                    Image.LANCZOS,
                )
            return _encode_webp(image)
    except Exception:
        return None


def shrink_for_web(content: bytes) -> tuple[bytes, str] | None:
    """Re-encode an upload as WebP, capped to `MAX_UPLOAD_WIDTH`.

    Returns `(bytes, "webp")` on success, or None when the input should be stored
    untouched (SVG, animated images, undecodable data). Callers use the returned
    extension for the stored filename, since the format changes.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:
        return None
    try:
        import io as _io

        with Image.open(_io.BytesIO(content)) as opened:
            if (opened.format or "").upper() not in _STRIPPABLE:
                return None  # GIF/SVG keep their original encoding
            if getattr(opened, "n_frames", 1) > 1:
                return None
            image = ImageOps.exif_transpose(opened) or opened
            downscaled = image.width > MAX_UPLOAD_WIDTH
            if downscaled:
                image = image.resize(
                    (MAX_UPLOAD_WIDTH, max(1, round(image.height * MAX_UPLOAD_WIDTH / image.width))),
                    Image.LANCZOS,
                )
            encoded = _encode_webp(image, quality=85)
    except Exception:
        return None
    if not encoded:
        return None
    # When the image was actually downscaled, keep the result regardless of byte
    # count — capping the dimensions is the point, and a "did it get smaller?"
    # check would silently leave an oversized image behind. When no downscale was
    # needed this is only a format swap, so it has to earn its place on size.
    if downscaled or len(encoded) < len(content):
        return (encoded, "webp")
    return None


def strip_image_metadata(content: bytes) -> bytes:
    """Return `content` re-encoded with no EXIF/metadata.

    Returns the original bytes unchanged whenever stripping isn't safely possible,
    so a surprising input degrades to the old behaviour instead of failing the
    upload or storing a corrupt file. That applies to:

    - formats outside `_STRIPPABLE` (GIF, SVG)
    - animated images, where a naive re-save would flatten them to one frame
    - anything Pillow can't parse, and any error during re-encoding

    Orientation is baked into the pixels first (`exif_transpose`), because phone
    photos rely on an EXIF orientation tag to display upright — dropping the tag
    without rotating the pixels would leave those photos sideways.
    """
    try:
        from PIL import Image, ImageOps
    except Exception:  # Pillow missing — never break uploads over metadata
        return content

    out = io.BytesIO()
    try:
        with Image.open(io.BytesIO(content)) as opened:
            fmt = (opened.format or "").upper()
            if fmt not in _STRIPPABLE:
                return content
            # getattr: only multi-frame plugins define n_frames.
            if getattr(opened, "n_frames", 1) > 1:
                return content

            image = ImageOps.exif_transpose(opened) or opened
            # JPEG can't hold an alpha channel; convert rather than raise.
            if fmt == "JPEG" and image.mode not in ("RGB", "L", "CMYK"):
                image = image.convert("RGB")
            image.save(out, format=fmt, **_SAVE_PARAMS.get(fmt, {}))
    except Exception:
        return content

    stripped = out.getvalue()
    # A zero-byte result would mean something went wrong silently.
    return stripped or content
