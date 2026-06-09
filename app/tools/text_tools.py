"""Text tool processors.

Every processor has the signature:
    fn(files: list[Path], text: str, options: dict) -> ToolResult
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

from app.tools.registry import ToolResult, register

_LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu "
    "fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
    "culpa qui officia deserunt mollit anim id est laborum."
)


@register("word-counter")
def word_counter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    words = re.findall(r"\b\w+\b", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    reading_minutes = round(len(words) / 200, 1)  # ~200 wpm
    return ToolResult(meta={
        "words": len(words),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "").replace("\n", "")),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "reading_time_minutes": reading_minutes,
    })


@register("character-counter")
def character_counter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    return ToolResult(meta={
        "characters": len(text),
        "characters_no_spaces": len(re.sub(r"\s", "", text)),
        "lines": text.count("\n") + 1 if text else 0,
    })


@register("case-converter")
def case_converter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    mode = options.get("mode", "upper")
    if mode == "upper":
        out = text.upper()
    elif mode == "lower":
        out = text.lower()
    elif mode == "title":
        out = text.title()
    elif mode == "sentence":
        out = re.sub(r"(^\s*\w|[.!?]\s*\w)", lambda m: m.group().upper(), text.lower())
    else:
        out = text
    return ToolResult(text=out)


@register("duplicate-line-remover")
def duplicate_line_remover(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    case_sensitive = bool(options.get("case_sensitive", False))
    seen: set[str] = set()
    out_lines: list[str] = []
    for line in text.splitlines():
        key = line if case_sensitive else line.lower()
        if key not in seen:
            seen.add(key)
            out_lines.append(line)
    return ToolResult(text="\n".join(out_lines),
                      meta={"removed": text.count("\n") + 1 - len(out_lines) if text else 0})


@register("text-sorter")
def text_sorter(files, text: str, options: dict) -> ToolResult:
    lines = (text or "").splitlines()
    reverse = options.get("order", "asc") == "desc"
    lines.sort(reverse=reverse, key=str.lower)
    return ToolResult(text="\n".join(lines))


@register("text-reverser")
def text_reverser(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    mode = options.get("mode", "characters")
    if mode == "characters":
        out = text[::-1]
    elif mode == "words":
        out = " ".join(text.split()[::-1])
    else:  # lines
        out = "\n".join(text.splitlines()[::-1])
    return ToolResult(text=out)


@register("url-encoder")
def url_encoder(files, text: str, options: dict) -> ToolResult:
    return ToolResult(text=urllib.parse.quote(text or "", safe=""))


@register("url-decoder")
def url_decoder(files, text: str, options: dict) -> ToolResult:
    return ToolResult(text=urllib.parse.unquote(text or ""))


@register("lorem-ipsum-generator")
def lorem_ipsum_generator(files, text: str, options: dict) -> ToolResult:
    count = int(options.get("paragraphs", 3) or 3)
    count = max(1, min(count, 50))
    return ToolResult(text="\n\n".join([_LOREM] * count))


@register("random-text-generator")
def random_text_generator(files, text: str, options: dict) -> ToolResult:
    import secrets
    import string

    length = max(1, min(int(options.get("length", 32) or 32), 2000))
    alphabet = string.ascii_letters + string.digits
    out = "".join(secrets.choice(alphabet) for _ in range(length))
    return ToolResult(text=out)
