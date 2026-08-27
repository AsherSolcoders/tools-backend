#!/usr/bin/env python3
"""Parse the tool-list .docx files and report which tools are new.

Run it again whenever a list is updated — tools already in the registry are
skipped automatically, so re-running never produces duplicates.

    python scripts/import_tool_lists.py ~/path/to/docs           # report
    python scripts/import_tool_lists.py ~/path/to/docs --json out.json

The .docx files follow one shape:

    1. Section Heading
    Tool Name
    Usage: what it does
    Features: bullet-ish description

Matching is by significant words, not exact strings, so "Merge PDF" is
recognised as the existing `pdf-merge` and "Crop Image" as `image-crop`.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import zipfile
from pathlib import Path

# docx filename -> category slug it belongs to.
FILE_CATEGORIES: dict[str, str] = {
    "PDF Tools List.docx": "pdf-tools",
    "The Complete Image Tools List.docx": "image-tools",
    "The Complete Text Tools List.docx": "text-tools",
    "The Complete Developer Tools List.docx": "developer-tools",
    "The Complete SEO Tools.docx": "seo-tools",
    "List of Calculators.docx": "calculators",
}

# Words too generic to identify a tool, dropped before comparing names.
_STOPWORDS = {
    "a", "an", "the", "to", "of", "and", "or", "for", "from",
    "tool", "online", "free", "converter", "generator",
}


# --- Self-contained vs external ---------------------------------------------
#
# Only tools that run entirely on our own machine can be built here: anything
# that needs live third-party data (search rankings, WHOIS, backlink indexes,
# traffic estimates) would require an external API, a paid data provider, or
# crawling someone else's site.
#
# Matched against name + usage + features, so a tool is judged on what it
# actually does rather than just its title.

_EXTERNAL_SIGNALS = (
    # live lookups against someone else's service
    "whois", "dns", "nameserver", "ip address", "ip lookup", "geolocation",
    "ping", "uptime", "traceroute", "port scan", "ssl check", "http header",
    # search-engine / ranking data
    "serp", "rank track", "rank check", "keyword volume", "search volume",
    "keyword difficulty", "competitor", "domain authority", "page authority",
    "domain rating", "backlink", "referring domain", "index check", "indexed",
    "crawl", "crawler", "spider", "google search console", "google analytics",
    "google trends", "adwords", "ahrefs", "semrush", "moz",
    # anything that fetches a URL to analyse it
    "fetch the url", "fetches", "enter a url", "given url", "live url",
    "website speed", "page speed", "core web vitals", "lighthouse",
    "traffic estimat", "social media api", "api key",
)

_AI_SIGNALS = ("ai-based", "ai based", "ai-powered", "ai powered", "machine learning",
               "neural", "gpt", "llm", "super-resolution", "generative")


# Generators/analysers that only ever act on text the user pastes in. Their
# descriptions mention crawlers and search engines, which would otherwise trip
# the external signals below.
_ALWAYS_SELF_CONTAINED = (
    "robots.txt generator", "sitemap generator", "meta tag generator",
    "schema", "structured data", "snippet preview", "serp snippet",
    "keyword density", "permutation", "combinator", "length checker",
    "utm", "canonical tag", "hreflang", "open graph", "twitter card",
    "slug generator", "anchor text", "readability",
)

# Tools whose whole purpose is pulling data from someone else's service, even
# when the wording sounds self-contained.
_ALWAYS_EXTERNAL = (
    "keyword research", "keyword suggestion", "autocomplete", "suggest scraper",
    "people also ask", "related keywords", "question keyword",
    "lsi", "semantic keyword", "long-tail keyword", "search intent classifier",
    "on-page seo analyzer", "seo checker", "site audit",
)


def classify(tool: dict) -> str:
    """'self-contained', 'external' or 'ai-model'."""
    name = tool["name"].lower()
    if any(sig in name for sig in _ALWAYS_EXTERNAL):
        return "external"
    if any(sig in name for sig in _ALWAYS_SELF_CONTAINED):
        return "self-contained"
    blob = f"{tool['name']} {tool.get('usage','')} {tool.get('features','')}".lower()
    if any(sig in blob for sig in _EXTERNAL_SIGNALS):
        return "external"
    if any(sig in blob for sig in _AI_SIGNALS):
        return "ai-model"
    return "self-contained"


def _paragraphs(path: Path) -> list[str]:
    """Plain-text paragraphs from a .docx, in document order."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    text = html.unescape(re.sub(r"<[^>]+>", "", xml))
    return [line.strip() for line in text.split("\n") if line.strip()]


def parse_docx(path: Path) -> list[dict]:
    """Extract tools. A tool is a line immediately followed by `Usage:`."""
    lines = _paragraphs(path)
    tools: list[dict] = []
    section: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\d+\.\s+\S", line):
            section = re.sub(r"^\d+\.\s+", "", line)
            i += 1
            continue
        if i + 1 < len(lines) and lines[i + 1].startswith("Usage:"):
            features = ""
            if i + 2 < len(lines) and lines[i + 2].startswith("Features:"):
                features = lines[i + 2][len("Features:"):].strip()
            tools.append({
                # The SEO list prefixes names with "A1." / "C12." — drop it.
                "name": re.sub(r"^[A-Z]?\d+[.)]\s*", "", line),
                "section": section,
                "usage": lines[i + 1][len("Usage:"):].strip(),
                "features": features,
            })
            i += 3
            continue
        i += 1
    return tools


def match_key(value: str) -> frozenset[str]:
    words = re.sub(r"[^a-z0-9 ]", " ", value.lower()).split()
    return frozenset(w for w in words if w not in _STOPWORDS)


def existing_keys() -> dict[frozenset[str], str]:
    """Match keys for every tool already in the registry."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.tools import list_tools

    keys: dict[frozenset[str], str] = {}
    for tool in list_tools():
        keys.setdefault(match_key(tool.name), tool.slug)
        keys.setdefault(match_key(tool.slug.replace("-", " ")), tool.slug)
    return keys


def is_existing(name: str, keys: dict[frozenset[str], str]) -> str | None:
    key = match_key(name)
    if key in keys:
        return keys[key]
    # Subset match catches "Rotate PDF" vs "PDF Rotate Pages".
    for existing, slug in keys.items():
        if not existing or not key:
            continue
        if existing <= key or key <= existing:
            return slug
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", type=Path, help="folder holding the .docx lists")
    ap.add_argument("--json", type=Path, help="write the new-tool list to this file")
    args = ap.parse_args()

    keys = existing_keys()
    new_by_category: dict[str, list[dict]] = {}
    skipped = 0
    missing_files: list[str] = []

    for filename, category in FILE_CATEGORIES.items():
        path = args.directory / filename
        if not path.is_file():
            missing_files.append(filename)
            continue
        fresh = []
        for tool in parse_docx(path):
            if is_existing(tool["name"], keys):
                skipped += 1
            else:
                tool["category"] = category
                tool["kind"] = classify(tool)
                fresh.append(tool)
        new_by_category[category] = fresh

    total_new = sum(len(v) for v in new_by_category.values())
    counts = lambda ts, k: sum(1 for t in ts if t["kind"] == k)
    print(f"already in the registry (skipped): {skipped}")
    print(f"new tools found                  : {total_new}\n")
    print(f"  {'category':18} {'new':>5} {'buildable':>10} {'external':>9} {'ai':>4}")
    for category, tools in new_by_category.items():
        print(f"  {category:18} {len(tools):>5} {counts(tools,'self-contained'):>10} "
              f"{counts(tools,'external'):>9} {counts(tools,'ai-model'):>4}")
    buildable = sum(counts(t, "self-contained") for t in new_by_category.values())
    print(f"\n  BUILDABLE (no external data): {buildable}")
    if missing_files:
        print("\n  not found in that folder:")
        for name in missing_files:
            print(f"    - {name}")

    if args.json:
        args.json.write_text(json.dumps(new_by_category, indent=1))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
