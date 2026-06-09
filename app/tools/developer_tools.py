"""Developer tool processors."""
from __future__ import annotations

import base64
import binascii
import json
import re
import secrets
import string
import uuid

from app.tools.registry import ToolResult, register


@register("json-formatter")
def json_formatter(files, text: str, options: dict) -> ToolResult:
    indent = int(options.get("indent", 2) or 0)
    try:
        parsed = json.loads(text or "")
    except json.JSONDecodeError as e:
        return ToolResult(meta={"valid": False, "error": str(e)})
    pretty = json.dumps(parsed, indent=indent if indent > 0 else None, ensure_ascii=False)
    return ToolResult(text=pretty, meta={"valid": True})


@register("json-validator")
def json_validator(files, text: str, options: dict) -> ToolResult:
    try:
        json.loads(text or "")
        return ToolResult(meta={"valid": True, "message": "Valid JSON ✓"})
    except json.JSONDecodeError as e:
        return ToolResult(meta={
            "valid": False,
            "error": e.msg,
            "line": e.lineno,
            "column": e.colno,
        })


@register("json-minifier")
def json_minifier(files, text: str, options: dict) -> ToolResult:
    try:
        parsed = json.loads(text or "")
    except json.JSONDecodeError as e:
        return ToolResult(meta={"valid": False, "error": str(e)})
    return ToolResult(text=json.dumps(parsed, separators=(",", ":"), ensure_ascii=False),
                      meta={"valid": True})


@register("base64-encoder")
def base64_encoder(files, text: str, options: dict) -> ToolResult:
    encoded = base64.b64encode((text or "").encode("utf-8")).decode("ascii")
    return ToolResult(text=encoded)


@register("base64-decoder")
def base64_decoder(files, text: str, options: dict) -> ToolResult:
    try:
        decoded = base64.b64decode((text or "").encode("ascii"), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:
        return ToolResult(meta={"valid": False, "error": f"Invalid Base64: {e}"})
    return ToolResult(text=decoded, meta={"valid": True})


@register("uuid-generator")
def uuid_generator(files, text: str, options: dict) -> ToolResult:
    count = max(1, min(int(options.get("count", 1) or 1), 500))
    return ToolResult(text="\n".join(str(uuid.uuid4()) for _ in range(count)))


@register("password-generator")
def password_generator(files, text: str, options: dict) -> ToolResult:
    length = max(4, min(int(options.get("length", 16) or 16), 128))
    alphabet = string.ascii_letters
    if options.get("digits", True):
        alphabet += string.digits
    if options.get("symbols", True):
        alphabet += "!@#$%^&*()-_=+[]{};:,.<>?"
    pwd = "".join(secrets.choice(alphabet) for _ in range(length))
    return ToolResult(text=pwd)


@register("css-minifier")
def css_minifier(files, text: str, options: dict) -> ToolResult:
    css = text or ""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)          # comments
    css = re.sub(r"\s+", " ", css)                                # collapse whitespace
    css = re.sub(r"\s*([{}:;,>~+])\s*", r"\1", css)               # around tokens
    css = css.replace(";}", "}").strip()
    return ToolResult(text=css, meta={"original": len(text or ""), "minified": len(css)})


@register("js-minifier")
def js_minifier(files, text: str, options: dict) -> ToolResult:
    js = text or ""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)            # block comments
    js = re.sub(r"(?<![:\\])//[^\n]*", "", js)                    # line comments
    lines = [ln.strip() for ln in js.splitlines()]
    js = "\n".join(ln for ln in lines if ln)
    return ToolResult(text=js, meta={"original": len(text or ""), "minified": len(js)})


@register("html-formatter")
def html_formatter(files, text: str, options: dict) -> ToolResult:
    indent_size = int(options.get("indent", 2) or 0)
    pad = " " * indent_size
    # Split into tags and text nodes.
    tokens = re.split(r"(<[^>]+>)", text or "")
    out: list[str] = []
    depth = 0
    void = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed",
            "source", "track", "wbr"}
    for tok in tokens:
        chunk = tok.strip()
        if not chunk:
            continue
        if chunk.startswith("</"):
            depth = max(depth - 1, 0)
            out.append(pad * depth + chunk)
        elif chunk.startswith("<"):
            tag = re.match(r"<\s*([a-zA-Z0-9]+)", chunk)
            name = tag.group(1).lower() if tag else ""
            self_closing = chunk.endswith("/>") or name in void or chunk.startswith("<!")
            out.append(pad * depth + chunk)
            if not self_closing:
                depth += 1
        else:
            out.append(pad * depth + chunk)
    return ToolResult(text="\n".join(out))
