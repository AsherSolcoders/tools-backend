"""SEO tool processors.

Every tool here works on what the visitor pastes in. Nothing is crawled: this
server never fetches a URL on someone else's behalf, which rules out a whole
class of tools (live redirect chasing, uptime checks, SSL inspection) and also
rules out being used as an open proxy into a private network.

    fn(files: list[Path], text: str, options: dict) -> ToolResult
"""
from __future__ import annotations

import json
import re
from collections import Counter
from html import escape
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from app.tools.registry import ToolResult, register

_STOP_WORDS = {
    "a","an","and","are","as","at","be","been","but","by","for","from","had","has","have",
    "he","her","his","how","i","if","in","into","is","it","its","me","my","no","not","of",
    "on","or","our","out","she","so","than","that","the","their","them","then","there",
    "these","they","this","to","up","was","we","were","what","when","where","which","who",
    "will","with","would","you","your",
}


def _int(options: dict, key: str, default: int) -> int:
    try:
        return int(float(str(options.get(key, default)).strip() or default))
    except (TypeError, ValueError):
        return default


def _flag(options: dict, key: str, default: bool = False) -> bool:
    value = options.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _opt_str(options: dict, key: str, default: str = "") -> str:
    return str(options.get(key, default) or "").strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9'-]+", text or "")


def _visible_text(html: str) -> str:
    """Body text with script, style and tags removed."""
    out = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", html or "", flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<[^>]+>", " ", out)
    return re.sub(r"\s+", " ", out).strip()


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', tag, re.IGNORECASE) or \
        re.search(rf"\b{name}\s*=\s*'([^']*)'", tag, re.IGNORECASE) or \
        re.search(rf"\b{name}\s*=\s*([^\s>]+)", tag, re.IGNORECASE)
    return m.group(1) if m else None


# ===========================================================================
# Meta and social tags
# ===========================================================================

# Google measures the SERP in pixels, not characters, but character counts are
# what people can actually check — these are the widely used equivalents.
_TITLE_MAX, _DESC_MAX = 60, 160


@register("meta-tag-generator")
def meta_tag_generator(files, text: str, options: dict) -> ToolResult:
    title = _opt_str(options, "title") or (text or "").strip().split("\n")[0]
    description = _opt_str(options, "description")
    if not title:
        return ToolResult(meta={"error": "Enter a page title."})
    tags = ["<!-- Primary meta tags -->",
            f"<title>{escape(title)}</title>",
            f'<meta name="title" content="{escape(title)}">']
    if description:
        tags.append(f'<meta name="description" content="{escape(description)}">')
    keywords = _opt_str(options, "keywords")
    if keywords:
        tags.append(f'<meta name="keywords" content="{escape(keywords)}">')
    author = _opt_str(options, "author")
    if author:
        tags.append(f'<meta name="author" content="{escape(author)}">')
    robots = _opt_str(options, "robots", "index, follow")
    tags.append(f'<meta name="robots" content="{escape(robots)}">')
    canonical = _opt_str(options, "canonical")
    if canonical:
        tags.append(f'<link rel="canonical" href="{escape(canonical)}">')
    if _flag(options, "include_viewport", True):
        tags += ['<meta charset="UTF-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1.0">']
    warnings = []
    if len(title) > _TITLE_MAX:
        warnings.append(f"Title is {len(title)} characters — Google usually cuts it near {_TITLE_MAX}.")
    if description and len(description) > _DESC_MAX:
        warnings.append(f"Description is {len(description)} characters — aim for under {_DESC_MAX}.")
    if not description:
        warnings.append("No description. Google will pick its own snippet from the page.")
    return ToolResult(text="\n".join(tags), meta={
        "title_length": len(title), "description_length": len(description),
        "warnings": warnings or ["Lengths look fine."],
    })


@register("open-graph-generator")
def open_graph_generator(files, text: str, options: dict) -> ToolResult:
    title = _opt_str(options, "title") or (text or "").strip().split("\n")[0]
    if not title:
        return ToolResult(meta={"error": "Enter a title."})
    url = _opt_str(options, "url")
    description = _opt_str(options, "description")
    image = _opt_str(options, "image")
    site = _opt_str(options, "site_name")
    kind = _opt_str(options, "type", "website")
    tags = ["<!-- Open Graph / Facebook -->",
            f'<meta property="og:type" content="{escape(kind)}">',
            f'<meta property="og:title" content="{escape(title)}">']
    if url:
        tags.append(f'<meta property="og:url" content="{escape(url)}">')
    if description:
        tags.append(f'<meta property="og:description" content="{escape(description)}">')
    if image:
        tags += [f'<meta property="og:image" content="{escape(image)}">',
                 '<meta property="og:image:width" content="1200">',
                 '<meta property="og:image:height" content="630">',
                 f'<meta property="og:image:alt" content="{escape(title)}">']
    if site:
        tags.append(f'<meta property="og:site_name" content="{escape(site)}">')
    if _flag(options, "include_twitter", True):
        tags += ["", "<!-- Twitter / X -->",
                 f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">',
                 f'<meta name="twitter:title" content="{escape(title)}">']
        if description:
            tags.append(f'<meta name="twitter:description" content="{escape(description)}">')
        if image:
            tags.append(f'<meta name="twitter:image" content="{escape(image)}">')
        handle = _opt_str(options, "twitter_handle")
        if handle:
            at = handle if handle.startswith("@") else "@" + handle
            tags.append(f'<meta name="twitter:site" content="{escape(at)}">')
    notes = []
    if not image:
        notes.append("No image. A shared link without one gets a plain text card.")
    if image and not image.startswith(("http://", "https://")):
        notes.append("og:image must be an absolute URL — relative paths are ignored.")
    return ToolResult(text="\n".join(tags), meta={"notes": notes or ["Looks complete."]})


@register("twitter-card-generator")
def twitter_card_generator(files, text: str, options: dict) -> ToolResult:
    title = _opt_str(options, "title") or (text or "").strip().split("\n")[0]
    if not title:
        return ToolResult(meta={"error": "Enter a title."})
    card = _opt_str(options, "card", "summary_large_image")
    image = _opt_str(options, "image")
    tags = [f'<meta name="twitter:card" content="{escape(card)}">',
            f'<meta name="twitter:title" content="{escape(title)}">']
    for key, value in (("description", _opt_str(options, "description")),
                       ("image", image),
                       ("image:alt", _opt_str(options, "image_alt") or title)):
        if value:
            tags.append(f'<meta name="twitter:{key}" content="{escape(value)}">')
    for key in ("site", "creator"):
        handle = _opt_str(options, key)
        if handle:
            at = handle if handle.startswith("@") else "@" + handle
            tags.append(f'<meta name="twitter:{key}" content="{escape(at)}">')
    notes = []
    if card == "summary_large_image" and not image:
        notes.append("A large-image card with no image falls back to a small one.")
    notes.append("summary_large_image wants at least 300x157px; summary wants 144x144px.")
    return ToolResult(text="\n".join(tags), meta={"card": card, "notes": notes})


@register("canonical-tag-generator")
def canonical_tag_generator(files, text: str, options: dict) -> ToolResult:
    """Builds a canonical link, and flags the URL shapes that break one."""
    url = (text or "").strip() or _opt_str(options, "url")
    if not url:
        return ToolResult(meta={"error": "Enter the page URL."})
    if not url.startswith(("http://", "https://")):
        return ToolResult(meta={"error": "A canonical URL must be absolute, starting with https://"})
    parts = urlparse(url)
    warnings = []
    if parts.scheme == "http":
        warnings.append("Points at http. Canonicalise to https, or the two versions compete.")
    if _flag(options, "strip_parameters", True) and parts.query:
        tracking = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content",
                    "gclid","fbclid","msclkid","ref","mc_cid","mc_eid"}
        kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                if k.lower() not in tracking]
        if len(kept) != len(parse_qsl(parts.query, keep_blank_values=True)):
            warnings.append("Tracking parameters removed — they must never appear in a canonical.")
        parts = parts._replace(query=urlencode(kept))
    if _flag(options, "lowercase", True) and parts.netloc != parts.netloc.lower():
        parts = parts._replace(netloc=parts.netloc.lower())
        warnings.append("Host lowercased — hostnames are case-insensitive, paths are not.")
    if parts.fragment:
        parts = parts._replace(fragment="")
        warnings.append("Fragment removed — a canonical must not carry one.")
    clean = urlunparse(parts)
    return ToolResult(text=f'<link rel="canonical" href="{escape(clean)}">', meta={
        "canonical_url": clean,
        "warnings": warnings or ["Nothing to fix."],
        "reminder": "Every page needs a canonical, including the page it points at (self-referencing).",
    })


@register("hreflang-generator")
def hreflang_generator(files, text: str, options: dict) -> ToolResult:
    """Builds a reciprocal hreflang set from a list of language:URL pairs."""
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    if not lines:
        return ToolResult(meta={
            "error": "One pair per line, e.g.  en-us: https://example.com/  "
        })
    entries, bad = [], []
    for line in lines:
        code, _, url = line.partition(":")
        url = url.strip()
        code = code.strip().lower()
        if not url.startswith("http"):
            bad.append(line)
            continue
        if code != "x-default" and not re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", code):
            bad.append(line)
            continue
        entries.append((code, url))
    if not entries:
        return ToolResult(meta={"error": "No valid pairs found. Use  language-REGION: https://url"})
    tags = [f'<link rel="alternate" hreflang="{escape(c)}" href="{escape(u)}">' for c, u in entries]
    notes = []
    if not any(c == "x-default" for c, _ in entries):
        notes.append("No x-default. Add one for visitors whose language you do not cover.")
    notes.append("This exact block must appear on EVERY listed page, or the set is ignored.")
    if bad:
        notes.append(f"Skipped {len(bad)} line(s) that were not 'code: url'.")
    return ToolResult(text="\n".join(tags), meta={"languages": len(entries), "notes": notes})


@register("robots-meta-generator")
def robots_meta_generator(files, text: str, options: dict) -> ToolResult:
    directives = []
    directives.append("noindex" if _flag(options, "noindex") else "index")
    directives.append("nofollow" if _flag(options, "nofollow") else "follow")
    for flag, name in (("noarchive", "noarchive"), ("nosnippet", "nosnippet"),
                       ("noimageindex", "noimageindex"), ("notranslate", "notranslate")):
        if _flag(options, flag):
            directives.append(name)
    snippet = _int(options, "max_snippet", -1)
    if snippet != -1:
        directives.append(f"max-snippet:{snippet}")
    image_preview = _opt_str(options, "max_image_preview", "large")
    if image_preview in {"none", "standard", "large"}:
        directives.append(f"max-image-preview:{image_preview}")
    value = ", ".join(directives)
    tags = [f'<meta name="robots" content="{value}">']
    if _flag(options, "google_only"):
        tags.append(f'<meta name="googlebot" content="{value}">')
    notes = []
    if _flag(options, "noindex"):
        notes.append("noindex only works if the page is crawlable — never block it in robots.txt too.")
    return ToolResult(text="\n".join(tags),
                      meta={"content": value, "notes": notes or ["Standard indexable page."]})


@register("serp-preview")
def serp_preview(files, text: str, options: dict) -> ToolResult:
    """Shows how a result will read, and where each field gets cut."""
    title = _opt_str(options, "title") or (text or "").strip().split("\n")[0]
    if not title:
        return ToolResult(meta={"error": "Enter the page title."})
    description = _opt_str(options, "description")
    url = _opt_str(options, "url", "https://example.com/page")
    mobile = _opt_str(options, "device", "desktop") == "mobile"
    title_limit = 55 if mobile else _TITLE_MAX
    desc_limit = 120 if mobile else _DESC_MAX
    cut = lambda s, n: s if len(s) <= n else s[: n - 1].rstrip() + "…"
    breadcrumb = url.replace("https://", "").replace("http://", "").rstrip("/").replace("/", " › ")
    return ToolResult(
        text=f"{breadcrumb}\n{cut(title, title_limit)}\n{cut(description, desc_limit)}",
        meta={
            "device": "mobile" if mobile else "desktop",
            "title": cut(title, title_limit),
            "title_length": len(title),
            "title_truncated": len(title) > title_limit,
            "description": cut(description, desc_limit),
            "description_length": len(description),
            "description_truncated": len(description) > desc_limit,
            "note": "Google measures in pixels, so wide characters cut sooner than this estimate.",
        })


# ===========================================================================
# Structured data
# ===========================================================================

def _jsonld(payload: dict) -> str:
    return ('<script type="application/ld+json">\n'
            + json.dumps(payload, indent=2, ensure_ascii=False)
            + "\n</script>")


@register("schema-generator")
def schema_generator(files, text: str, options: dict) -> ToolResult:
    """JSON-LD for the schema types that actually earn rich results."""
    kind = _opt_str(options, "type", "Article")
    name = _opt_str(options, "name") or (text or "").strip().split("\n")[0]
    if not name:
        return ToolResult(meta={"error": "Enter a name or headline."})
    url = _opt_str(options, "url")
    description = _opt_str(options, "description")
    image = _opt_str(options, "image")
    author = _opt_str(options, "author")
    publisher = _opt_str(options, "publisher")
    data: dict = {"@context": "https://schema.org", "@type": kind}
    missing: list[str] = []

    if kind in ("Article", "BlogPosting", "NewsArticle"):
        data["headline"] = name
        if url:
            data["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
        data["author"] = {"@type": "Person", "name": author or "Author name"}
        data["publisher"] = {"@type": "Organization", "name": publisher or "Publisher name"}
        published = _opt_str(options, "date")
        if published:
            data["datePublished"] = published
        else:
            missing.append("datePublished is required for article rich results.")
        if not image:
            missing.append("image is required — articles without one do not get a rich result.")
    elif kind == "Product":
        data["name"] = name
        price = _opt_str(options, "price")
        data["offers"] = {
            "@type": "Offer",
            "price": price or "0.00",
            "priceCurrency": _opt_str(options, "currency", "USD"),
            "availability": "https://schema.org/InStock",
        }
        if url:
            data["offers"]["url"] = url
        if not price:
            missing.append("price is required for a product rich result.")
        rating = _opt_str(options, "rating")
        if rating:
            data["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": rating,
                                       "reviewCount": _opt_str(options, "review_count", "1")}
    elif kind == "Organization":
        data["name"] = name
        if url:
            data["url"] = url
        data["logo"] = image or "https://example.com/logo.png"
        socials = [s.strip() for s in _opt_str(options, "same_as").split(",") if s.strip()]
        if socials:
            data["sameAs"] = socials
    elif kind == "Person":
        data["name"] = name
        if url:
            data["url"] = url
        job = _opt_str(options, "author")
        if job:
            data["jobTitle"] = job
    elif kind == "Event":
        data["name"] = name
        start = _opt_str(options, "date")
        data["startDate"] = start or "2026-01-01T09:00"
        data["location"] = {"@type": "Place", "name": _opt_str(options, "publisher") or "Venue",
                            "address": _opt_str(options, "description") or "Address"}
        if not start:
            missing.append("startDate is required for an event rich result.")
    elif kind == "Recipe":
        data["name"] = name
        data["recipeIngredient"] = [i.strip() for i in _opt_str(options, "description").split(",") if i.strip()] or ["Ingredient"]
        data["author"] = {"@type": "Person", "name": author or "Author name"}
    elif kind == "VideoObject":
        data["name"] = name
        data["uploadDate"] = _opt_str(options, "date") or "2026-01-01"
        data["thumbnailUrl"] = image or "https://example.com/thumb.jpg"
        if url:
            data["contentUrl"] = url
    elif kind == "WebSite":
        data["name"] = name
        data["url"] = url or "https://example.com"
        if _flag(options, "search_box", True):
            data["potentialAction"] = {
                "@type": "SearchAction",
                "target": {"@type": "EntryPoint",
                           "urlTemplate": f"{url or 'https://example.com'}/search?q={{search_term_string}}"},
                "query-input": "required name=search_term_string",
            }
    else:
        return ToolResult(meta={"error": "Choose one of the listed schema types."})

    if description and "description" not in data:
        data["description"] = description
    if image and "image" not in data and kind not in ("Organization", "VideoObject"):
        data["image"] = image
    return ToolResult(text=_jsonld(data),
                      meta={"type": kind, "required_fields_missing": missing or ["None."]})


@register("faq-schema-generator")
def faq_schema_generator(files, text: str, options: dict) -> ToolResult:
    """FAQPage JSON-LD from question and answer lines.

    Pairs are read as question then answer, or split on a separator. Google only
    shows FAQ rich results when the same Q&A is visible on the page itself.
    """
    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={
            "error": "One question per line followed by its answer, or use 'Question | Answer'."
        })
    pairs: list[tuple[str, str]] = []
    if "|" in raw:
        for line in raw.split("\n"):
            question, _, answer = line.partition("|")
            if question.strip() and answer.strip():
                pairs.append((question.strip(), answer.strip()))
    else:
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        for i in range(0, len(lines) - 1, 2):
            pairs.append((lines[i], lines[i + 1]))
    if not pairs:
        return ToolResult(meta={"error": "Could not find any question and answer pairs."})
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ],
    }
    notes = ["Every question here must also be visible on the page — hidden FAQ markup is a violation."]
    short = [q for q, a in pairs if len(a) < 20]
    if short:
        notes.append(f"{len(short)} answer(s) are very short; Google tends to skip thin FAQ entries.")
    return ToolResult(text=_jsonld(data), meta={"questions": len(pairs), "notes": notes})


@register("breadcrumb-schema-generator")
def breadcrumb_schema_generator(files, text: str, options: dict) -> ToolResult:
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    if not lines:
        return ToolResult(meta={"error": "One crumb per line, as  Name | https://url"})
    items = []
    for i, line in enumerate(lines, start=1):
        name, _, url = line.partition("|")
        entry: dict = {"@type": "ListItem", "position": i, "name": name.strip()}
        if url.strip():
            entry["item"] = url.strip()
        items.append(entry)
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}
    notes = ["The last crumb is the current page — leaving its URL off is correct."]
    if len(items) < 2:
        notes.append("A single-item breadcrumb has no effect. Include the path from the home page.")
    return ToolResult(text=_jsonld(data), meta={"items": len(items), "notes": notes})


@register("local-business-schema")
def local_business_schema(files, text: str, options: dict) -> ToolResult:
    name = _opt_str(options, "name") or (text or "").strip().split("\n")[0]
    if not name:
        return ToolResult(meta={"error": "Enter the business name."})
    data: dict = {
        "@context": "https://schema.org",
        "@type": _opt_str(options, "business_type", "LocalBusiness"),
        "name": name,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": _opt_str(options, "street"),
            "addressLocality": _opt_str(options, "city"),
            "addressRegion": _opt_str(options, "region"),
            "postalCode": _opt_str(options, "postal_code"),
            "addressCountry": _opt_str(options, "country", "US"),
        },
    }
    for key, field in (("phone", "telephone"), ("url", "url"), ("image", "image"),
                       ("price_range", "priceRange")):
        value = _opt_str(options, key)
        if value:
            data[field] = value
    hours = _opt_str(options, "hours")
    if hours:
        # "Mo-Fr 09:00-17:00" is schema.org's own opening-hours shorthand.
        data["openingHours"] = [h.strip() for h in hours.split(",") if h.strip()]
    lat, lon = _opt_str(options, "latitude"), _opt_str(options, "longitude")
    if lat and lon:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon}
    missing = [f for f, v in (("street", data["address"]["streetAddress"]),
                              ("city", data["address"]["addressLocality"]),
                              ("telephone", data.get("telephone", ""))) if not v]
    return ToolResult(text=_jsonld(data), meta={
        "missing_recommended": missing or ["None."],
        "note": "The name, address and phone here must match your Google Business Profile exactly.",
    })


@register("review-schema-generator")
def review_schema_generator(files, text: str, options: dict) -> ToolResult:
    """Review or AggregateRating markup.

    Google only shows review stars for reviews of something other than yourself.
    Marking up your own site's rating on your own page ("self-serving reviews")
    is ignored, and can trigger a manual action.
    """
    item = _opt_str(options, "item_name") or (text or "").strip().split("\n")[0]
    if not item:
        return ToolResult(meta={"error": "Enter the name of what is being reviewed."})
    item_type = _opt_str(options, "item_type", "Product")
    if _opt_str(options, "mode", "aggregate") == "aggregate":
        rating = _opt_str(options, "rating", "4.5")
        count = _opt_str(options, "review_count", "10")
        data = {
            "@context": "https://schema.org", "@type": item_type, "name": item,
            "aggregateRating": {
                "@type": "AggregateRating", "ratingValue": rating,
                "bestRating": _opt_str(options, "best_rating", "5"),
                "worstRating": "1", "reviewCount": count,
            },
        }
    else:
        data = {
            "@context": "https://schema.org", "@type": "Review",
            "itemReviewed": {"@type": item_type, "name": item},
            "reviewRating": {
                "@type": "Rating", "ratingValue": _opt_str(options, "rating", "5"),
                "bestRating": _opt_str(options, "best_rating", "5"), "worstRating": "1",
            },
            "author": {"@type": "Person", "name": _opt_str(options, "author") or "Reviewer name"},
            "reviewBody": _opt_str(options, "review_body") or "What the reviewer said.",
        }
    return ToolResult(text=_jsonld(data), meta={
        "warning": "Do not mark up reviews of your own business on your own site — Google ignores it.",
    })


@register("structured-data-validator")
def structured_data_validator(files, text: str, options: dict) -> ToolResult:
    """Checks JSON-LD for the fields each type actually requires."""
    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={"error": "Paste your JSON-LD, or the page HTML that contains it."})
    blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                        raw, re.DOTALL | re.IGNORECASE) or [raw]
    required = {
        "Article": ["headline", "image", "datePublished", "author"],
        "BlogPosting": ["headline", "image", "datePublished", "author"],
        "NewsArticle": ["headline", "image", "datePublished", "author"],
        "Product": ["name", "image", "offers"],
        "Recipe": ["name", "image", "recipeIngredient"],
        "Event": ["name", "startDate", "location"],
        "LocalBusiness": ["name", "address"],
        "Organization": ["name", "url"],
        "FAQPage": ["mainEntity"],
        "BreadcrumbList": ["itemListElement"],
        "VideoObject": ["name", "thumbnailUrl", "uploadDate"],
        "Person": ["name"],
    }
    findings = []
    for i, block in enumerate(blocks, start=1):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError as e:
            findings.append({"block": i, "valid_json": False, "error": f"line {e.lineno}: {e.msg}"})
            continue
        nodes = parsed.get("@graph") if isinstance(parsed, dict) and "@graph" in parsed else parsed
        for node in (nodes if isinstance(nodes, list) else [nodes]):
            if not isinstance(node, dict):
                continue
            kind = node.get("@type", "(no @type)")
            kinds = kind if isinstance(kind, list) else [kind]
            entry = {"block": i, "type": kind, "valid_json": True}
            if not isinstance(parsed, dict) or "@context" not in (parsed if isinstance(parsed, dict) else {}):
                entry["warning"] = "@context is missing — it must be https://schema.org"
            missing = [f for k in kinds for f in required.get(k, []) if f not in node]
            entry["missing_required"] = sorted(set(missing)) or None
            entry["properties"] = len([k for k in node if not k.startswith("@")])
            findings.append(entry)
    problems = sum(1 for f in findings if not f.get("valid_json") or f.get("missing_required"))
    return ToolResult(meta={
        "blocks_found": len(blocks), "results": findings, "problems": problems,
        "note": "Required-field checks against Google's documented requirements — not the full validator.",
    })


@register("google-review-link")
def google_review_link(files, text: str, options: dict) -> ToolResult:
    """Builds the direct 'leave a review' link from a Google Place ID."""
    place_id = (text or "").strip() or _opt_str(options, "place_id")
    if not place_id:
        return ToolResult(meta={
            "error": "Enter your Google Place ID. Find it at "
                     "developers.google.com/maps/documentation/places/web-service/place-id"
        })
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,}", place_id):
        return ToolResult(meta={"error": "That doesn't look like a Place ID."})
    write = f"https://search.google.com/local/writereview?placeid={quote(place_id)}"
    read = f"https://search.google.com/local/reviews?placeid={quote(place_id)}"
    maps = f"https://www.google.com/maps/place/?q=place_id:{quote(place_id)}"
    return ToolResult(text=write, meta={
        "write_a_review": write, "see_all_reviews": read, "place_on_maps": maps,
        "note": "The review box opens straight away — one less step than sending people to Maps.",
    })


# ===========================================================================
# On-page analysis (works on pasted HTML)
# ===========================================================================

def _need_html(text: str) -> str | None:
    if not (text or "").strip():
        return "Paste the page's HTML. View source in your browser and copy it in."
    return None


@register("heading-analyzer")
def heading_analyzer(files, text: str, options: dict) -> ToolResult:
    """Heading order, and the mistakes that break a document outline."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    found = [(int(m.group(1)), _visible_text(m.group(2)))
             for m in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", text, re.DOTALL | re.IGNORECASE)]
    if not found:
        return ToolResult(meta={"error": "No headings found in that HTML."})
    issues, previous = [], 0
    for level, content in found:
        if previous and level > previous + 1:
            issues.append(f"H{previous} jumps straight to H{level} — levels should not be skipped.")
        if not content.strip():
            issues.append(f"An H{level} is empty.")
        previous = level
    counts = Counter(level for level, _ in found)
    if counts.get(1, 0) == 0:
        issues.append("No H1. Every page needs exactly one.")
    elif counts.get(1, 0) > 1:
        issues.append(f"{counts[1]} H1s. Use one, and let H2s carry the sections.")
    return ToolResult(
        text="\n".join(f"{'  ' * (level - 1)}H{level}: {content[:80]}" for level, content in found),
        meta={"total": len(found),
              "by_level": {f"h{i}": counts.get(i, 0) for i in range(1, 7)},
              "issues": issues or ["Heading structure looks correct."]})


@register("alt-text-checker")
def alt_text_checker(files, text: str, options: dict) -> ToolResult:
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    images = re.findall(r"<img\b[^>]*>", text, re.IGNORECASE)
    if not images:
        return ToolResult(meta={"error": "No <img> tags found in that HTML."})
    missing, empty, generic, good = [], [], [], []
    filler = {"image", "img", "photo", "picture", "graphic", "icon", "logo", "banner",
              "untitled", "screenshot", "dsc", "img_"}
    for tag in images:
        src = _attr(tag, "src") or "(no src)"
        alt = _attr(tag, "alt")
        if alt is None:
            missing.append(src)
        elif not alt.strip():
            # An empty alt is correct for a purely decorative image, so it is
            # reported separately rather than as a fault.
            empty.append(src)
        elif alt.strip().lower() in filler or len(alt.strip()) < 4:
            generic.append({"src": src, "alt": alt})
        else:
            good.append({"src": src, "alt": alt})
    return ToolResult(meta={
        "images": len(images), "with_good_alt": len(good),
        "missing_alt": missing, "decorative_empty_alt": empty, "generic_alt": generic,
        "coverage_percent": round(len(good) / len(images) * 100, 1),
        "note": 'alt="" is correct for decorative images. A missing alt attribute is not.',
    })


@register("internal-link-analyzer")
def internal_link_analyzer(files, text: str, options: dict) -> ToolResult:
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    domain = _opt_str(options, "domain").replace("https://", "").replace("http://", "").strip("/")
    internal, external, other = [], [], []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text, re.DOTALL | re.IGNORECASE):
        href = _attr(m.group(1), "href")
        if not href:
            continue
        anchor = _visible_text(m.group(2)) or "(no text)"
        rel = (_attr(m.group(1), "rel") or "").lower()
        entry = {"href": href, "anchor": anchor[:80], "nofollow": "nofollow" in rel}
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            other.append(entry)
        elif href.startswith(("http://", "https://")):
            (internal if domain and domain in href else external).append(entry)
        else:
            internal.append(entry)
    empty_anchors = [e for e in internal + external if e["anchor"] == "(no text)"]
    return ToolResult(meta={
        "internal_links": len(internal), "external_links": len(external),
        "other_links": len(other),
        "nofollow_internal": sum(1 for e in internal if e["nofollow"]),
        "links_with_no_anchor_text": len(empty_anchors),
        "internal": internal[:100], "external": external[:100],
        "note": "Set your domain in the options, or every absolute link counts as external.",
    })


@register("nofollow-link-checker")
def nofollow_link_checker(files, text: str, options: dict) -> ToolResult:
    """Which outbound links pass ranking signal, and which do not."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    domain = _opt_str(options, "domain").replace("https://", "").replace("http://", "").strip("/")
    rows = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", text, re.DOTALL | re.IGNORECASE):
        href = _attr(m.group(1), "href") or ""
        if not href.startswith(("http://", "https://")):
            continue
        if domain and domain in href:
            continue
        rel = set((_attr(m.group(1), "rel") or "").lower().split())
        rows.append({
            "href": href, "anchor": (_visible_text(m.group(2)) or "(no text)")[:60],
            "rel": " ".join(sorted(rel)) or "(none)",
            "passes_link_equity": not (rel & {"nofollow", "sponsored", "ugc"}),
            "opens_new_tab": (_attr(m.group(1), "target") or "") == "_blank",
            "missing_noopener": (_attr(m.group(1), "target") or "") == "_blank" and "noopener" not in rel,
        })
    if not rows:
        return ToolResult(meta={"error": "No outbound links found."})
    followed = [r for r in rows if r["passes_link_equity"]]
    risky = [r["href"] for r in rows if r["missing_noopener"]]
    return ToolResult(meta={
        "outbound_links": len(rows), "followed": len(followed),
        "nofollow_or_tagged": len(rows) - len(followed),
        "links": rows[:150],
        "target_blank_without_noopener": risky,
        "note": 'Paid links need rel="sponsored"; user-submitted links need rel="ugc".',
    })


@register("anchor-text-analyzer")
def anchor_text_analyzer(files, text: str, options: dict) -> ToolResult:
    """Anchor text spread — an over-optimised profile is a recognisable pattern."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    anchors = [_visible_text(m.group(1)).strip()
               for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", text, re.DOTALL | re.IGNORECASE)]
    anchors = [a for a in anchors if a]
    if not anchors:
        return ToolResult(meta={"error": "No links with anchor text found."})
    generic = {"click here", "here", "read more", "more", "link", "this", "learn more",
               "find out more", "see more", "download"}
    brand = _opt_str(options, "brand").lower()
    buckets = Counter()
    for a in anchors:
        low = a.lower()
        if low in generic:
            buckets["generic"] += 1
        elif brand and brand in low:
            buckets["branded"] += 1
        elif re.match(r"https?://", low):
            buckets["naked url"] += 1
        elif len(a.split()) > 5:
            buckets["long tail"] += 1
        else:
            buckets["keyword rich"] += 1
    total = len(anchors)
    notes = []
    if buckets["generic"] / total > 0.3:
        notes.append("Over 30% generic anchors ('click here') — they tell search engines nothing.")
    if buckets["keyword rich"] / total > 0.6:
        notes.append("Over 60% keyword-rich anchors reads as over-optimisation.")
    return ToolResult(meta={
        "total_anchors": total,
        "distribution": {k: {"count": v, "percent": round(v / total * 100, 1)}
                         for k, v in buckets.most_common()},
        "most_used": [{"anchor": a, "count": n} for a, n in Counter(anchors).most_common(15)],
        "notes": notes or ["Distribution looks reasonable."],
    })


@register("meta-tags-analyzer")
def meta_tags_analyzer(files, text: str, options: dict) -> ToolResult:
    """Pulls every SEO-relevant tag out of pasted HTML and grades it."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.DOTALL | re.IGNORECASE)
    title = _visible_text(title_match.group(1)) if title_match else ""
    found: dict = {"title": title, "title_length": len(title)}
    for tag in re.findall(r"<meta\b[^>]*>", text, re.IGNORECASE):
        name = (_attr(tag, "name") or _attr(tag, "property") or _attr(tag, "http-equiv") or "").lower()
        content = _attr(tag, "content")
        if name and content is not None:
            found[name] = content
    canonical = None
    for link in re.findall(r"<link\b[^>]*>", text, re.IGNORECASE):
        if (_attr(link, "rel") or "").lower() == "canonical":
            canonical = _attr(link, "href")
    found["canonical"] = canonical
    description = found.get("description", "")
    issues = []
    if not title:
        issues.append("No <title>.")
    elif len(title) > _TITLE_MAX:
        issues.append(f"Title is {len(title)} characters — over the ~{_TITLE_MAX} Google shows.")
    if not description:
        issues.append("No meta description.")
    elif len(description) > _DESC_MAX:
        issues.append(f"Description is {len(description)} characters — over ~{_DESC_MAX}.")
    if not canonical:
        issues.append("No canonical link.")
    if "og:title" not in found:
        issues.append("No Open Graph tags — shared links will look plain.")
    if "viewport" not in found:
        issues.append("No viewport meta — the page will not be mobile-friendly.")
    if "noindex" in str(found.get("robots", "")).lower():
        issues.append("This page is set to noindex.")
    return ToolResult(meta={"tags": found, "issues": issues or ["Nothing missing."],
                            "description_length": len(description)})


@register("canonical-checker")
def canonical_checker(files, text: str, options: dict) -> ToolResult:
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    links = [l for l in re.findall(r"<link\b[^>]*>", text, re.IGNORECASE)
             if (_attr(l, "rel") or "").lower() == "canonical"]
    hrefs = [_attr(l, "href") for l in links]
    page_url = _opt_str(options, "page_url")
    issues = []
    if not hrefs:
        issues.append("No canonical link found on this page.")
    if len(hrefs) > 1:
        issues.append(f"{len(hrefs)} canonical links — Google ignores the lot when they conflict.")
    for href in hrefs:
        if href and not href.startswith(("http://", "https://")):
            issues.append(f"Canonical {href!r} is relative. It works, but absolute is safer.")
        if href and "#" in href:
            issues.append("Canonical contains a fragment, which is not allowed.")
    if page_url and hrefs and hrefs[0]:
        same = hrefs[0].rstrip("/") == page_url.rstrip("/")
        issues.append("Self-referencing canonical — correct." if same
                      else f"Canonical points elsewhere: {hrefs[0]}")
    robots = ""
    for tag in re.findall(r"<meta\b[^>]*>", text, re.IGNORECASE):
        if (_attr(tag, "name") or "").lower() == "robots":
            robots = (_attr(tag, "content") or "").lower()
    if "noindex" in robots and hrefs:
        issues.append("noindex together with a canonical sends mixed signals — pick one.")
    return ToolResult(meta={"canonical_urls": hrefs, "robots": robots or None,
                            "findings": issues or ["Canonical looks correct."]})


@register("hreflang-checker")
def hreflang_checker(files, text: str, options: dict) -> ToolResult:
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    entries = []
    for link in re.findall(r"<link\b[^>]*>", text, re.IGNORECASE):
        if (_attr(link, "rel") or "").lower() != "alternate":
            continue
        code = (_attr(link, "hreflang") or "").lower()
        if code:
            entries.append({"hreflang": code, "href": _attr(link, "href") or ""})
    if not entries:
        return ToolResult(meta={"error": "No hreflang tags found."})
    issues, seen = [], set()
    for e in entries:
        code = e["hreflang"]
        if code in seen:
            issues.append(f"{code} is declared more than once.")
        seen.add(code)
        if code != "x-default" and not re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", code):
            issues.append(f"{code!r} is not a valid language or language-region code.")
        if not e["href"].startswith(("http://", "https://")):
            issues.append(f"{code} points at a relative URL — hreflang needs absolute URLs.")
    if "x-default" not in seen:
        issues.append("No x-default entry.")
    return ToolResult(meta={
        "entries": entries, "languages": sorted(seen),
        "issues": issues or ["Tags look valid."],
        "reminder": "Every listed page must carry this same set, pointing back — otherwise it is ignored.",
    })


@register("amp-validator")
def amp_validator(files, text: str, options: dict) -> ToolResult:
    """Checks the AMP rules that are simple, absolute and easy to break."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    issues = []
    if not re.search(r"<html[^>]*\s(amp|⚡)(\s|=|>)", text, re.IGNORECASE):
        issues.append("The <html> tag is missing the amp (or ⚡) attribute.")
    if "cdn.ampproject.org/v0.js" not in text:
        issues.append("The AMP runtime script is missing.")
    if not re.search(r'<link[^>]*rel=["\']?canonical', text, re.IGNORECASE):
        issues.append("No canonical link — every AMP page needs one.")
    if not re.search(r"<meta[^>]*charset=[\"']?utf-8", text, re.IGNORECASE):
        issues.append('<meta charset="utf-8"> must be the first tag in <head>.')
    if not re.search(r"amp-boilerplate", text):
        issues.append("The AMP boilerplate style is missing.")
    for tag in ("img", "video", "audio", "iframe"):
        if re.search(rf"<{tag}\b", text, re.IGNORECASE):
            issues.append(f"<{tag}> is not allowed — use <amp-{tag}> instead.")
    if re.search(r"<script(?![^>]*(application/ld\+json|amp))", text, re.IGNORECASE):
        issues.append("Custom <script> tags are not allowed in AMP.")
    if re.search(r'\bstyle\s*=\s*["\']', text, re.IGNORECASE):
        issues.append("Inline style attributes are not allowed — use <style amp-custom>.")
    for tag in re.findall(r"<style\b[^>]*>", text, re.IGNORECASE):
        if "amp-custom" not in tag and "amp-boilerplate" not in tag:
            issues.append("A <style> block is neither amp-custom nor amp-boilerplate.")
    return ToolResult(meta={
        "valid": not issues, "issues_found": len(issues), "issues": issues,
        "note": "The common AMP rules — not the official validator.",
    })


@register("code-to-text-ratio")
def code_to_text_ratio(files, text: str, options: dict) -> ToolResult:
    """How much of a page is content versus markup."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    total = len(text)
    body = _visible_text(text)
    scripts = sum(len(m) for m in re.findall(r"<script\b.*?</script>", text, re.DOTALL | re.IGNORECASE))
    styles = sum(len(m) for m in re.findall(r"<style\b.*?</style>", text, re.DOTALL | re.IGNORECASE))
    ratio = len(body) / total * 100 if total else 0
    if ratio >= 25:
        verdict = "Healthy — plenty of content relative to markup."
    elif ratio >= 10:
        verdict = "Typical for a modern page. Worth checking the content is substantial."
    else:
        verdict = "Very low. The page is mostly code — check the content is not rendered by JavaScript."
    return ToolResult(meta={
        "total_characters": total, "text_characters": len(body),
        "script_characters": scripts, "style_characters": styles,
        "code_to_text_ratio_percent": round(ratio, 2),
        "words": len(_words(body)),
        "verdict": verdict,
        "note": "This is a rough health signal, not a ranking factor in its own right.",
    })


@register("seo-report-generator")
def seo_report_generator(files, text: str, options: dict) -> ToolResult:
    """One pass over a page: titles, headings, images, links and content."""
    error = _need_html(text)
    if error:
        return ToolResult(meta={"error": error})
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.DOTALL | re.IGNORECASE)
    title = _visible_text(title_match.group(1)) if title_match else ""
    description = ""
    for tag in re.findall(r"<meta\b[^>]*>", text, re.IGNORECASE):
        if (_attr(tag, "name") or "").lower() == "description":
            description = _attr(tag, "content") or ""
    body = _visible_text(text)
    words = _words(body)
    headings = re.findall(r"<h([1-6])[^>]*>", text, re.IGNORECASE)
    images = re.findall(r"<img\b[^>]*>", text, re.IGNORECASE)
    no_alt = [i for i in images if _attr(i, "alt") is None]
    links = re.findall(r"<a\b[^>]*href=", text, re.IGNORECASE)
    canonical = any((_attr(l, "rel") or "").lower() == "canonical"
                    for l in re.findall(r"<link\b[^>]*>", text, re.IGNORECASE))

    checks = [
        ("Title present", bool(title), f"{len(title)} characters"),
        ("Title within ~60 characters", 0 < len(title) <= _TITLE_MAX, f"{len(title)}"),
        ("Meta description present", bool(description), f"{len(description)} characters"),
        ("Description within ~160 characters", 0 < len(description) <= _DESC_MAX, f"{len(description)}"),
        ("Exactly one H1", headings.count("1") == 1, f"{headings.count('1')} found"),
        ("Has subheadings", len(headings) > 1, f"{len(headings)} headings"),
        ("At least 300 words", len(words) >= 300, f"{len(words)} words"),
        ("Every image has alt", not no_alt, f"{len(no_alt)} missing of {len(images)}"),
        ("Canonical link", canonical, "present" if canonical else "missing"),
        ("Has links", bool(links), f"{len(links)} links"),
        ("Viewport meta", "viewport" in text.lower(), ""),
    ]
    passed = sum(1 for _, ok, _ in checks if ok)
    score = round(passed / len(checks) * 100)
    return ToolResult(
        text="\n".join(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else "")
                       for name, ok, detail in checks),
        meta={
            "score_out_of_100": score,
            "passed": passed, "total_checks": len(checks),
            "failed": [name for name, ok, _ in checks if not ok],
            "word_count": len(words),
            "note": "On-page checks against the pasted HTML. Nothing is crawled.",
        })


# ===========================================================================
# Keywords and content
# ===========================================================================

@register("keyword-combiner")
def keyword_combiner(files, text: str, options: dict) -> ToolResult:
    """Every combination of two or three keyword lists — the classic PPC mixer."""
    import itertools

    lists = [[w.strip() for w in group.split("\n") if w.strip()]
             for group in re.split(r"\n\s*\n", text or "") if group.strip()]
    if len(lists) < 2:
        extra = _opt_str(options, "second_list")
        if extra:
            lists.append([w.strip() for w in extra.split("\n") if w.strip()])
    if len(lists) < 2:
        return ToolResult(meta={
            "error": "Give at least two lists, separated by a blank line. "
                     "One keyword per line in each."
        })
    total = 1
    for group in lists:
        total *= len(group)
    if total > 20000:
        return ToolResult(meta={"error": f"That would make {total:,} combinations. Trim the lists."})
    joiner = {"space": " ", "hyphen": "-", "plus": " + ", "none": ""}.get(
        _opt_str(options, "joiner", "space"), " ")
    combos = [joiner.join(parts) for parts in itertools.product(*lists)]
    if _flag(options, "include_reversed") and len(lists) == 2:
        combos += [joiner.join(reversed(parts)) for parts in itertools.product(*lists)]
    match_type = _opt_str(options, "match_type", "broad")
    if match_type == "phrase":
        combos = [f'"{c}"' for c in combos]
    elif match_type == "exact":
        combos = [f"[{c}]" for c in combos]
    return ToolResult(text="\n".join(dict.fromkeys(combos)),
                      meta={"lists": len(lists), "combinations": len(set(combos))})


@register("keyword-prominence")
def keyword_prominence(files, text: str, options: dict) -> ToolResult:
    """Where a keyword appears, not just how often.

    A term in the title and the first paragraph carries far more weight than the
    same term buried at the bottom, which raw density never shows.
    """
    keyword = _opt_str(options, "keyword").lower()
    body = _visible_text(text) if "<" in (text or "") else (text or "")
    if not keyword:
        return ToolResult(meta={"error": "Enter the keyword to look for."})
    if not body.strip():
        return ToolResult(meta={"error": "Paste your content or page HTML."})
    words = [w.lower() for w in _words(body)]
    if not words:
        return ToolResult(meta={"error": "No words found."})
    parts = keyword.split()
    positions = [i for i in range(len(words) - len(parts) + 1)
                 if words[i:i + len(parts)] == parts]
    count = len(positions)
    first = positions[0] if positions else None
    # Prominence: 100 when the first mention is the opening word, 0 at the very end.
    prominence = round((1 - first / len(words)) * 100, 1) if first is not None else 0.0
    html = text or ""
    in_title = bool(re.search(rf"<title[^>]*>[^<]*{re.escape(keyword)}", html, re.IGNORECASE))
    in_h1 = bool(re.search(rf"<h1[^>]*>[^<]*{re.escape(keyword)}", html, re.IGNORECASE))
    first_100 = keyword in " ".join(words[:100])
    notes = []
    density = count / len(words) * 100
    if density > 3:
        notes.append(f"Density is {density:.1f}% — over about 3% starts to read as stuffing.")
    if not first_100 and count:
        notes.append("Not in the first 100 words. Move a mention earlier.")
    if not count:
        notes.append("The keyword does not appear at all.")
    return ToolResult(meta={
        "keyword": keyword, "occurrences": count, "total_words": len(words),
        "density_percent": round(density, 2),
        "first_position": first, "prominence_score": prominence,
        "in_title_tag": in_title, "in_h1": in_h1, "in_first_100_words": first_100,
        "notes": notes or ["Placement looks reasonable."],
    })


@register("seo-slug-generator")
def seo_slug_generator(files, text: str, options: dict) -> ToolResult:
    """A clean URL slug, with the SEO trims applied."""
    import unicodedata

    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={"error": "Enter a title to turn into a slug."})
    results = []
    for line in raw.split("\n"):
        if not line.strip():
            continue
        # NFKD folds accents onto plain letters, so "café" becomes "cafe" rather
        # than being dropped entirely.
        folded = unicodedata.normalize("NFKD", line).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")
        if _flag(options, "remove_stop_words"):
            kept = [w for w in slug.split("-") if w and w not in _STOP_WORDS]
            slug = "-".join(kept) or slug
        separator = _opt_str(options, "separator", "-")
        if separator != "-":
            slug = slug.replace("-", separator)
        limit = _int(options, "max_length", 60)
        if limit and len(slug) > limit:
            slug = slug[:limit].rsplit(separator, 1)[0]
        results.append(slug)
    notes = ["Hyphens, not underscores — Google treats an underscore as a word joiner."]
    if any(len(s) > 60 for s in results):
        notes.append("Long slugs get truncated in search results.")
    return ToolResult(text="\n".join(results),
                      meta={"slugs": len(results), "notes": notes})


@register("near-me-keyword-tool")
def near_me_keyword_tool(files, text: str, options: dict) -> ToolResult:
    """Builds local search variations from a service and a list of locations."""
    services = [s.strip() for s in (text or "").split("\n") if s.strip()]
    locations = [l.strip() for l in re.split(r"[,\n]+", _opt_str(options, "locations")) if l.strip()]
    if not services:
        return ToolResult(meta={"error": "Enter one service per line, e.g. 'plumber'."})
    if not locations:
        return ToolResult(meta={"error": "Enter the locations to target, separated by commas."})
    if len(services) * len(locations) > 5000:
        return ToolResult(meta={"error": "That is too many combinations. Trim one of the lists."})
    patterns = ["{s} in {l}", "{s} {l}", "best {s} in {l}", "{s} near me {l}",
                "affordable {s} in {l}", "{l} {s}", "top {s} {l}", "{s} services in {l}",
                "local {s} {l}", "{s} company in {l}"]
    wanted = max(1, min(_int(options, "variations", 6), len(patterns)))
    out = [p.format(s=s, l=l) for s in services for l in locations for p in patterns[:wanted]]
    if _flag(options, "include_near_me", True):
        out += [f"{s} near me" for s in services]
    return ToolResult(text="\n".join(dict.fromkeys(out)), meta={
        "services": len(services), "locations": len(locations), "keywords": len(set(out)),
        "note": "Only build a page for a location you genuinely serve — doorway pages get penalised.",
    })


@register("keyword-value-calculator")
def keyword_value_calculator(files, text: str, options: dict) -> ToolResult:
    """What ranking for a keyword is worth, from your own numbers."""
    try:
        volume = float(_opt_str(options, "monthly_searches", "1000") or 1000)
        cpc = float(_opt_str(options, "cpc", "2.00") or 2)
        conversion = float(_opt_str(options, "conversion_rate", "2") or 2)
        value = float(_opt_str(options, "order_value", "100") or 100)
    except ValueError:
        return ToolResult(meta={"error": "All four figures must be numbers."})
    if volume < 0 or cpc < 0:
        return ToolResult(meta={"error": "Searches and CPC cannot be negative."})
    position = _int(options, "position", 1)
    # Organic click-through by position — widely published industry averages, and
    # the reason position 1 is worth several times position 5.
    ctr_by_position = {1: 27.6, 2: 15.8, 3: 11.0, 4: 8.4, 5: 6.3, 6: 4.9, 7: 3.9,
                       8: 3.3, 9: 2.7, 10: 2.4}
    ctr = ctr_by_position.get(max(1, min(position, 10)), 2.0)
    clicks = volume * ctr / 100
    conversions = clicks * conversion / 100
    revenue = conversions * value
    return ToolResult(meta={
        "position": position, "assumed_click_through_rate": f"{ctr}%",
        "monthly_clicks": round(clicks),
        "monthly_conversions": round(conversions, 1),
        "monthly_revenue": round(revenue, 2),
        "annual_revenue": round(revenue * 12, 2),
        "equivalent_ppc_cost_per_month": round(clicks * cpc, 2),
        "note": "Click-through rates are industry averages — your own Search Console data is better.",
    })


@register("content-brief-generator")
def content_brief_generator(files, text: str, options: dict) -> ToolResult:
    """A structured brief for a writer, built around your keyword.

    A template with the target figures filled in, not researched competitor data
    — nothing here is fetched. Use it as the shape of the article, then add the
    substance from your own research.
    """
    keyword = (text or "").strip().split("\n")[0] or _opt_str(options, "keyword")
    if not keyword:
        return ToolResult(meta={"error": "Enter the target keyword."})
    intent = _opt_str(options, "intent", "informational")
    words = _int(options, "word_count", 1500)
    audience = _opt_str(options, "audience") or "people searching for this topic"
    title = keyword.title()
    sections = {
        "informational": ["What is {k}?", "Why {k} matters", "How {k} works, step by step",
                          "Common mistakes with {k}", "{k} best practices", "FAQs"],
        "commercial": ["What to look for in {k}", "Top options compared",
                       "How we evaluated them", "Pricing", "Which one to choose", "FAQs"],
        "transactional": ["{k} at a glance", "Features", "Pricing and plans",
                          "How to get started", "What customers say", "FAQs"],
        "navigational": ["About {k}", "How to access it", "Key features", "Support", "FAQs"],
    }[intent]
    outline = [f"H2: {s.format(k=keyword)}" for s in sections]
    brief = [
        f"# Content brief: {title}", "",
        f"**Target keyword:** {keyword}",
        f"**Search intent:** {intent}",
        f"**Audience:** {audience}",
        f"**Target length:** {words} words",
        f"**Title tag (≤{_TITLE_MAX} chars):** {title} — [add a benefit]"[:120],
        f"**Meta description (≤{_DESC_MAX} chars):** [One sentence on what the reader gets, "
        f"including '{keyword}'.]", "",
        "## Outline", "", f"H1: {title}", *outline, "",
        "## Requirements", "",
        f"- Use '{keyword}' in the H1, the first 100 words, and one H2",
        f"- Keep keyword density under 3% (about {max(1, round(words * 0.02))} mentions)",
        "- Add 2-4 internal links to related pages",
        "- Add 1-2 links to authoritative external sources",
        "- Every image needs descriptive alt text",
        "- Add FAQ schema for the FAQ section", "",
        "## Questions to answer", "",
        f"- What is {keyword}?", f"- How does {keyword} work?",
        f"- How much does {keyword} cost?", f"- Is {keyword} worth it?",
    ]
    return ToolResult(text="\n".join(brief), meta={
        "keyword": keyword, "intent": intent, "target_words": words,
        "note": "A template, not competitor research — nothing was crawled to build this.",
    })


@register("featured-snippet-optimizer")
def featured_snippet_optimizer(files, text: str, options: dict) -> ToolResult:
    """Checks whether content is shaped the way snippets get pulled from."""
    body = _visible_text(text) if "<" in (text or "") else (text or "")
    if not body.strip():
        return ToolResult(meta={"error": "Paste your content, or the page HTML."})
    keyword = _opt_str(options, "keyword").lower()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    findings, wins = [], []
    # Paragraph snippets are pulled from 40-60 word answers placed right after
    # the question — that shape is the single strongest signal here.
    answers = [s for s in sentences if 20 <= len(_words(s)) <= 60]
    if answers:
        wins.append(f"{len(answers)} sentence(s) are the right length for a paragraph snippet.")
    else:
        findings.append("No 20-60 word sentences. Add a direct, self-contained answer.")
    has_list = bool(re.search(r"<(ul|ol)\b", text or "", re.IGNORECASE)) or \
        len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+", text or "", re.MULTILINE)) >= 3
    (wins if has_list else findings).append(
        "Contains a list — list snippets are the most commonly awarded type."
        if has_list else "No list. Numbered steps and bulleted lists win list snippets.")
    has_table = "<table" in (text or "").lower()
    if has_table:
        wins.append("Contains a table — eligible for a table snippet.")
    questions = [s for s in sentences if s.rstrip().endswith("?")] + \
                re.findall(r"<h[2-4][^>]*>([^<]*\?)</h[2-4]>", text or "", re.IGNORECASE)
    (wins if questions else findings).append(
        f"{len(questions)} question heading(s) or sentence(s) found."
        if questions else "No questions. Use the question itself as an H2, then answer it directly.")
    if keyword:
        first = " ".join(_words(body)[:100]).lower()
        (wins if keyword in first else findings).append(
            "Keyword appears in the first 100 words."
            if keyword in first else "Keyword is not in the first 100 words.")
    score = round(len(wins) / max(1, len(wins) + len(findings)) * 100)
    return ToolResult(meta={
        "snippet_readiness_score": score,
        "working": wins, "to_fix": findings,
        "candidate_answers": answers[:5],
        "note": "Structure only. A snippet still requires ranking on page one first.",
    })


@register("nap-consistency-checker")
def nap_consistency_checker(files, text: str, options: dict) -> ToolResult:
    """Compares your business name, address and phone across listings.

    Inconsistent NAP is the most common reason a local business ranks below a
    weaker competitor — directories treat two spellings as two businesses.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text or "") if b.strip()]
    if len(blocks) < 2:
        return ToolResult(meta={
            "error": "Paste each listing as its own block, separated by a blank line. "
                     "Three lines each: name, address, phone."
        })

    def normalise_phone(value: str) -> str:
        return re.sub(r"\D", "", value)[-10:]

    def normalise_address(value: str) -> str:
        out = value.lower()
        for long, short in (("street", "st"), ("avenue", "ave"), ("road", "rd"),
                            ("boulevard", "blvd"), ("suite", "ste"), ("drive", "dr"),
                            ("north", "n"), ("south", "s"), ("east", "e"), ("west", "w")):
            out = re.sub(rf"\b{long}\b", short, out)
        return re.sub(r"[^a-z0-9]", "", out)

    listings = []
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        phone = next((ln for ln in lines if len(re.sub(r"\D", "", ln)) >= 7), "")
        address = next((ln for ln in lines[1:] if ln != phone), "")
        listings.append({"name": lines[0] if lines else "", "address": address, "phone": phone})

    issues = []
    for field, normalise in (("name", lambda v: re.sub(r"[^a-z0-9]", "", v.lower())),
                             ("address", normalise_address),
                             ("phone", normalise_phone)):
        variants = {normalise(l[field]) for l in listings if l[field]}
        if len(variants) > 1:
            issues.append({
                "field": field,
                "problem": f"{len(variants)} different versions",
                "found": sorted({l[field] for l in listings if l[field]}),
            })
    return ToolResult(meta={
        "listings_checked": len(listings), "listings": listings,
        "inconsistencies": issues or "None — every listing matches.",
        "consistent": not issues,
    })


@register("disavow-file-generator")
def disavow_file_generator(files, text: str, options: dict) -> ToolResult:
    """Formats a Google disavow file from a list of URLs or domains.

    Disavowing is close to a last resort. Google ignores most spam links on its
    own, and disavowing good links costs you rankings you had.
    """
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    if not lines:
        return ToolResult(meta={"error": "Paste the URLs or domains to disavow, one per line."})
    domains, urls, skipped = set(), [], []
    whole_domain = _flag(options, "domain_level", True)
    for line in lines:
        if line.startswith("#"):
            continue
        candidate = line if line.startswith("http") else "http://" + line
        host = urlparse(candidate).netloc.lower().lstrip("www.")
        if not host or "." not in host:
            skipped.append(line)
            continue
        if whole_domain or "/" not in line.replace("://", "", 1).split("/", 1)[0]:
            domains.add(host)
        else:
            urls.append(line)
    if not domains and not urls:
        return ToolResult(meta={"error": "No valid domains or URLs found."})
    out = ["# Disavow file", f"# {len(domains)} domain(s), {len(urls)} URL(s)", ""]
    out += [f"domain:{d}" for d in sorted(domains)]
    out += sorted(urls)
    return ToolResult(text="\n".join(out), meta={
        "domains": len(domains), "urls": len(urls), "skipped": skipped,
        "warning": "Upload to Search Console only after trying to get the links removed. "
                   "Disavowing a good link loses you its value permanently.",
    })


@register("domain-name-generator")
def domain_name_generator(files, text: str, options: dict) -> ToolResult:
    """Builds domain ideas from your keywords.

    Availability is not checked — that needs a live registry lookup, which this
    server does not make. Check the shortlist with a registrar.
    """
    words = [w.strip().lower() for w in re.split(r"[,\s\n]+", text or "") if w.strip()]
    if not words:
        return ToolResult(meta={"error": "Enter one or more keywords."})
    words = [re.sub(r"[^a-z0-9]", "", w) for w in words]
    words = [w for w in words if w]
    prefixes = [p.strip() for p in _opt_str(options, "prefixes", "get,try,my,the,go").split(",") if p.strip()]
    suffixes = [s.strip() for s in _opt_str(options, "suffixes", "hub,ly,app,hq,lab,ify,zone").split(",") if s.strip()]
    tlds = [t.strip().lstrip(".") for t in _opt_str(options, "tlds", "com,io,co,net,app").split(",") if t.strip()]
    ideas: list[str] = []
    for word in words:
        ideas.append(word)
        ideas += [p + word for p in prefixes]
        ideas += [word + s for s in suffixes]
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            ideas.append(a + b)
    limit = max(1, min(_int(options, "limit", 60), 500))
    unique = [n for n in dict.fromkeys(ideas) if 3 <= len(n) <= 24][:limit]
    out = [f"{name}.{tld}" for name in unique for tld in tlds]
    return ToolResult(text="\n".join(out), meta={
        "names": len(unique), "with_extensions": len(out),
        "note": "Availability is NOT checked here — verify your shortlist with a registrar.",
    })


@register("utm-builder")
def utm_builder(files, text: str, options: dict) -> ToolResult:
    """Builds a campaign URL with the UTM parameters set correctly."""
    url = (text or "").strip() or _opt_str(options, "url")
    if not url:
        return ToolResult(meta={"error": "Enter the destination URL."})
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    source = _opt_str(options, "source")
    medium = _opt_str(options, "medium")
    campaign = _opt_str(options, "campaign")
    if not (source and medium and campaign):
        return ToolResult(meta={
            "error": "utm_source, utm_medium and utm_campaign are all required — "
                     "without the three, the visit lands in 'direct'."
        })
    parts = urlparse(url)
    existing = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                if not k.lower().startswith("utm_")]
    lower = _flag(options, "lowercase", True)
    clean = (lambda v: v.strip().lower().replace(" ", "-")) if lower else (lambda v: v.strip())
    params = [("utm_source", clean(source)), ("utm_medium", clean(medium)),
              ("utm_campaign", clean(campaign))]
    for key in ("term", "content", "id"):
        value = _opt_str(options, key)
        if value:
            params.append((f"utm_{key}", clean(value)))
    final = urlunparse(parts._replace(query=urlencode(existing + params), fragment=""))
    notes = ["Analytics treats Source and Medium as case-sensitive — 'Google' and 'google' "
             "become two entries, which is why these are lowercased."]
    if parts.fragment:
        notes.append("Fragment removed — anything after # never reaches the server.")
    return ToolResult(text=final, meta={
        "url": final, "parameters": dict(params), "notes": notes,
    })


# ===========================================================================
# Technical SEO
# ===========================================================================

@register("robots-txt-generator")
def robots_txt_generator(files, text: str, options: dict) -> ToolResult:
    sitemap = _opt_str(options, "sitemap")
    disallow = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    lines: list[str] = []
    if _flag(options, "block_everything"):
        lines += ["User-agent: *", "Disallow: /"]
        warning = "This blocks the entire site from every crawler. Only correct for a staging site."
    else:
        lines.append("User-agent: *")
        lines += [f"Disallow: {p if p.startswith('/') else '/' + p}" for p in disallow]
        if not disallow:
            lines.append("Disallow:")
        for path in [ln.strip() for ln in _opt_str(options, "allow").split("\n") if ln.strip()]:
            lines.append(f"Allow: {path if path.startswith('/') else '/' + path}")
        warning = None
    if _flag(options, "block_ai_crawlers"):
        for bot in ("GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "PerplexityBot",
                    "Bytespider", "anthropic-ai"):
            lines += ["", f"User-agent: {bot}", "Disallow: /"]
    delay = _int(options, "crawl_delay", 0)
    if delay > 0:
        lines.append(f"Crawl-delay: {delay}")
    if sitemap:
        lines += ["", f"Sitemap: {sitemap}"]
    notes = [n for n in [
        warning,
        "robots.txt stops crawling, not indexing. Use a noindex meta tag to keep a page "
        "out of results — and leave it crawlable so the tag can be read.",
        "Never Disallow a path you also want deindexed; the crawler then cannot see the noindex.",
        None if sitemap else "No sitemap listed. Add one so crawlers find your URLs.",
    ] if n]
    return ToolResult(text="\n".join(lines), meta={"rules": len(lines), "notes": notes})


@register("robots-txt-tester")
def robots_txt_tester(files, text: str, options: dict) -> ToolResult:
    """Tests a path against a pasted robots.txt, using the longest-match rule.

    Google does not take the first matching line: the most specific rule wins,
    and Allow beats Disallow when both are the same length. That is why a
    robots.txt can behave the opposite of how it reads top to bottom.
    """
    content = text or ""
    path = _opt_str(options, "path", "/")
    agent = _opt_str(options, "user_agent", "*").lower()
    if not content.strip():
        return ToolResult(meta={"error": "Paste the contents of your robots.txt."})
    if not path.startswith("/"):
        path = "/" + path

    groups: dict[str, list[tuple[str, str]]] = {}
    current: list[str] = []
    for raw in content.split("\n"):
        line = raw.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            current = current if current and current[-1] == "pending" else []
            current = [value.lower()]
            groups.setdefault(value.lower(), [])
        elif field in ("allow", "disallow") and current:
            groups.setdefault(current[0], []).append((field, value))

    rules = groups.get(agent) or groups.get("*") or []
    matched = None
    for kind, pattern in rules:
        if pattern == "" and kind == "disallow":
            continue  # "Disallow:" with nothing after it allows everything
        regex = "^" + re.escape(pattern).replace(r"\*", ".*").replace(r"\$", "$")
        if re.match(regex, path):
            # Longest pattern wins; Allow beats Disallow at equal length.
            if (matched is None or len(pattern) > len(matched[1])
                    or (len(pattern) == len(matched[1]) and kind == "allow")):
                matched = (kind, pattern)
    allowed = matched is None or matched[0] == "allow"
    sitemaps = re.findall(r"^\s*sitemap:\s*(\S+)", content, re.IGNORECASE | re.MULTILINE)
    return ToolResult(meta={
        "path": path, "user_agent": agent or "*",
        "allowed": allowed,
        "matched_rule": f"{matched[0].title()}: {matched[1]}" if matched else "no rule — allowed by default",
        "group_used": agent if agent in groups else ("*" if "*" in groups else "none"),
        "sitemaps_declared": sitemaps or ["none"],
        "note": "Longest matching rule wins; Allow beats Disallow at the same length.",
    })


@register("xml-sitemap-generator")
def xml_sitemap_generator(files, text: str, options: dict) -> ToolResult:
    urls = [u.strip() for u in (text or "").split("\n") if u.strip()]
    if not urls:
        return ToolResult(meta={"error": "Paste one URL per line."})
    if len(urls) > 50000:
        return ToolResult(meta={"error": "A sitemap holds 50,000 URLs. Split it and use an index."})
    frequency = _opt_str(options, "changefreq", "weekly")
    priority = _opt_str(options, "priority", "0.8")
    lastmod = _opt_str(options, "lastmod")
    skipped, entries = [], []
    for url in urls:
        if not url.startswith(("http://", "https://")):
            skipped.append(url)
            continue
        # Ampersands and angle brackets in a query string break the XML.
        entry = [f"    <loc>{escape(url, quote=False)}</loc>"]
        if lastmod:
            entry.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
        if frequency != "none":
            entry.append(f"    <changefreq>{frequency}</changefreq>")
        if priority != "none":
            entry.append(f"    <priority>{priority}</priority>")
        entries.append("  <url>\n" + "\n".join(entry) + "\n  </url>")
    if not entries:
        return ToolResult(meta={"error": "No absolute URLs found. Each line must start with https://"})
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(entries) + "\n</urlset>")
    notes = ["Only canonical, indexable URLs belong here — never a redirect or a noindex page."]
    if skipped:
        notes.append(f"Skipped {len(skipped)} line(s) that were not absolute URLs.")
    return ToolResult(text=xml, meta={"urls": len(entries), "skipped": skipped, "notes": notes})


@register("sitemap-validator")
def sitemap_validator(files, text: str, options: dict) -> ToolResult:
    import xml.etree.ElementTree as ET

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste your sitemap XML."})
    if len(src) > 5_000_000:
        return ToolResult(meta={"error": "That sitemap is over 5 MB — the limit is 50 MB uncompressed, "
                                         "but paste a smaller one here."})
    try:
        root = ET.fromstring(src)
    except ET.ParseError as e:
        return ToolResult(meta={"error": f"Not valid XML: {e}"})
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    tag = root.tag.replace(namespace, "")
    issues: list[str] = []
    if namespace.strip("{}") not in root.tag:
        issues.append("Missing the sitemap namespace on <urlset> or <sitemapindex>.")
    if tag == "sitemapindex":
        locations = [e.text for e in root.iter(f"{namespace}loc")]
        return ToolResult(meta={"type": "sitemap index", "sitemaps": len(locations),
                                "urls": locations[:100],
                                "issues": issues or ["Index looks valid."]})
    if tag != "urlset":
        return ToolResult(meta={"error": f"Root element is <{tag}> — expected <urlset>."})
    entries = list(root.iter(f"{namespace}url"))
    locations, duplicates, relative = [], [], []
    for entry in entries:
        loc = entry.find(f"{namespace}loc")
        if loc is None or not (loc.text or "").strip():
            issues.append("A <url> entry has no <loc>.")
            continue
        value = loc.text.strip()
        if value in locations:
            duplicates.append(value)
        locations.append(value)
        if not value.startswith(("http://", "https://")):
            relative.append(value)
        priority = entry.find(f"{namespace}priority")
        if priority is not None:
            try:
                if not 0 <= float(priority.text) <= 1:
                    issues.append(f"priority {priority.text} is outside 0.0-1.0 for {value}")
            except (TypeError, ValueError):
                issues.append(f"priority {priority.text!r} is not a number for {value}")
    if len(entries) > 50000:
        issues.append(f"{len(entries)} URLs — the limit is 50,000 per sitemap.")
    if duplicates:
        issues.append(f"{len(duplicates)} duplicate URL(s).")
    if relative:
        issues.append(f"{len(relative)} relative URL(s) — every <loc> must be absolute.")
    hosts = {urlparse(u).netloc for u in locations if u.startswith("http")}
    if len(hosts) > 1:
        issues.append(f"URLs span {len(hosts)} hosts: {', '.join(sorted(hosts))}. "
                      "A sitemap should cover one host.")
    return ToolResult(meta={
        "type": "urlset", "urls": len(locations), "unique_urls": len(set(locations)),
        "hosts": sorted(hosts),
        "issues": issues or ["Sitemap looks valid."],
    })


@register("htaccess-redirect-generator")
def htaccess_redirect_generator(files, text: str, options: dict) -> ToolResult:
    """Redirect rules for Apache or nginx, from a list of old and new paths."""
    pairs = []
    bad = []
    for line in [ln.strip() for ln in (text or "").split("\n") if ln.strip()]:
        parts = re.split(r"\s*(?:\||,|\s{2,}|\t|->)\s*", line, maxsplit=1)
        if len(parts) != 2 or not parts[1]:
            bad.append(line)
            continue
        pairs.append((parts[0].strip(), parts[1].strip()))
    if not pairs:
        return ToolResult(meta={
            "error": "One redirect per line, as  /old-path | /new-path"
        })
    server = _opt_str(options, "server", "apache")
    code = _int(options, "status", 301)
    if code not in (301, 302, 307, 308):
        return ToolResult(meta={"error": "Use 301, 302, 307 or 308."})
    lines: list[str] = []
    if server == "nginx":
        # `location =` is an exact match, which is both the fastest lookup nginx
        # has and the safest default — a prefix match would catch child paths too.
        lines = [f"location = {old} {{ return {code} {new}; }}" for old, new in pairs]
    else:
        lines = ["<IfModule mod_rewrite.c>", "RewriteEngine On", ""]
        lines += [f"Redirect {code} {old} {new}" if not any(c in old for c in "*?()[]")
                  else f"RewriteRule ^{old.lstrip('/')}$ {new} [R={code},L]"
                  for old, new in pairs]
        lines.append("</IfModule>")
    notes = ["301 is permanent and gets cached hard by browsers — test with 302 first if unsure.",
             "Redirect to the closest equivalent page. Sending everything to the home page "
             "is treated as a soft 404."]
    if bad:
        notes.append(f"Skipped {len(bad)} line(s) that were not 'old | new'.")
    return ToolResult(text="\n".join(lines),
                      meta={"redirects": len(pairs), "server": server, "status": code, "notes": notes})
