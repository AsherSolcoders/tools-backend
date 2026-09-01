"""JSON-LD structured data, generated from the data we already store.

Every page's schema is derived here rather than hand-written in the frontend, so
a new tool, category, blog post or FAQ gets correct structured data the moment it
is added — nobody has to remember to write it.

Each builder returns a schema.org `@graph`: the page's own type, a
`BreadcrumbList`, and a `FAQPage` when the entity has FAQs. `@id` values are
absolute canonical URLs so search engines can tie the nodes together.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.urls import canonical_url

ORG_NAME = "ToolSimpli"


def _organization() -> dict[str, Any]:
    return {
        "@type": "Organization",
        "@id": f"{canonical_url('/')}#organization",
        "name": ORG_NAME,
        "url": canonical_url("/"),
    }


def _breadcrumbs(trail: list[tuple[str, str]]) -> dict[str, Any]:
    """`trail` is [(name, path)], starting at Home."""
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": name,
                "item": canonical_url(path),
            }
            for i, (name, path) in enumerate(trail, start=1)
        ],
    }


def _faq_page(faqs: list[dict] | None, url: str) -> dict[str, Any] | None:
    """FAQPage node, or None when the entity has no FAQs.

    Accepts both {question, answer} and {q, a} shapes, since tool content and
    blog content use different keys.
    """
    if not faqs:
        return None
    entries = []
    for f in faqs:
        question = (f.get("question") or f.get("q") or "").strip()
        answer = (f.get("answer") or f.get("a") or "").strip()
        if question and answer:
            entries.append({
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            })
    if not entries:
        return None
    return {"@type": "FAQPage", "@id": f"{url}#faq", "mainEntity": entries}


def _graph(*nodes: dict[str, Any] | None) -> dict[str, Any]:
    return {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}


def tool_schema(tool: Any, *, faqs: list[dict] | None = None,
                meta_description: str = "") -> dict[str, Any]:
    """A tool page: SoftwareApplication (it's a usable app, not just an article)."""
    url = canonical_url(f"/{tool.slug}")
    # Use the registry's own label — title-casing the slug produced "Pdf Tools".
    from app.tools import list_categories
    category_name = next(
        (c.name for c in list_categories() if c.slug == tool.category),
        tool.category.replace("-", " ").title(),
    )
    app_node = {
        "@type": "SoftwareApplication",
        "@id": f"{url}#app",
        "name": tool.name,
        "url": url,
        "description": meta_description or tool.description,
        "applicationCategory": "UtilitiesApplication",
        # Browser-based, so there is no OS requirement to declare.
        "operatingSystem": "Any",
        "browserRequirements": "Requires JavaScript",
        "publisher": _organization(),
        # Every tool is free — state it explicitly so it can show as a rich result.
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "isAccessibleForFree": True,
    }
    return _graph(
        app_node,
        _breadcrumbs([("Home", "/"), (category_name, f"/{tool.category}"), (tool.name, f"/{tool.slug}")]),
        _faq_page(faqs, url),
    )


def category_schema(category: Any, tools: list[Any], *, meta_description: str = "") -> dict[str, Any]:
    """A category page: CollectionPage listing the tools it contains."""
    url = canonical_url(f"/{category.slug}")
    return _graph(
        {
            "@type": "CollectionPage",
            "@id": url,
            "name": category.name,
            "url": url,
            "description": meta_description or category.description,
            "isPartOf": {"@id": f"{canonical_url('/')}#website"},
            "publisher": _organization(),
            "mainEntity": {
                "@type": "ItemList",
                "numberOfItems": len(tools),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i,
                        "name": t.name,
                        "url": canonical_url(f"/{t.slug}"),
                    }
                    for i, t in enumerate(tools, start=1)
                ],
            },
        },
        _breadcrumbs([("Home", "/"), (category.name, f"/{category.slug}")]),
    )


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else None


def blog_schema(post: Any, *, faqs: list[dict] | None = None) -> dict[str, Any]:
    """A blog post: BlogPosting, plus FAQPage when the post carries FAQs."""
    url = canonical_url(f"/{post.slug}")
    published = _iso(getattr(post, "display_date", None) or getattr(post, "published_at", None)
                     or getattr(post, "created_at", None))
    article = {
        "@type": "BlogPosting",
        "@id": f"{url}#article",
        "headline": post.title,
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "description": getattr(post, "seo_description", None) or getattr(post, "excerpt", None) or "",
        "publisher": _organization(),
    }
    if published:
        article["datePublished"] = published
    updated = _iso(getattr(post, "updated_at", None))
    if updated:
        article["dateModified"] = updated
    if getattr(post, "featured_image", None):
        article["image"] = post.featured_image
    # Prefer the linked profile: pointing `author` at a real URL with its own
    # Person node is what lets a search engine connect the byline to the E-E-A-T
    # signals on the profile page, which a bare name cannot do.
    profile = getattr(post, "author_user", None)
    author = getattr(post, "author", None)
    if profile is not None and getattr(profile, "slug", None) and getattr(profile, "profile_public", True):
        article["author"] = {
            "@type": "Person",
            "@id": f"{canonical_url(f'/author/{profile.slug}')}#person",
            "name": profile.name,
            "url": canonical_url(f"/author/{profile.slug}"),
        }
    elif author:
        article["author"] = {"@type": "Person", "name": author}
    else:
        article["author"] = _organization()

    category = (getattr(post, "categories", None) or [None])[0]
    trail = [("Home", "/"), ("Blog", "/blog")]
    if category is not None:
        trail.append((category.name, f"/{category.slug}"))
    trail.append((post.title, f"/{post.slug}"))

    return _graph(article, _breadcrumbs(trail), _faq_page(faqs, url))


def page_schema(name: str, path: str, description: str = "",
                faqs: list[dict] | None = None) -> dict[str, Any]:
    """A static page (About, FAQs, Privacy…). Adds FAQPage when FAQs are given."""
    url = canonical_url(path)
    return _graph(
        {
            "@type": "WebPage",
            "@id": url,
            "name": name,
            "url": url,
            "description": description,
            "isPartOf": {"@id": f"{canonical_url('/')}#website"},
            "publisher": _organization(),
        },
        _breadcrumbs([("Home", "/"), (name, path)]),
        _faq_page(faqs, url),
    )


def website_schema() -> dict[str, Any]:
    """Site-wide WebSite node, rendered once on the home page."""
    home = canonical_url("/")
    return _graph(
        {
            "@type": "WebSite",
            "@id": f"{home}#website",
            "name": ORG_NAME,
            "url": home,
            "publisher": _organization(),
        },
        _organization(),
    )


def author_schema(author: Any, posts: list[Any] | None = None) -> dict[str, Any]:
    """An author profile: ProfilePage wrapping a Person, plus what they wrote.

    `ProfilePage` is Google's own recommendation for a page *about* a person, as
    opposed to `Person` alone, which describes the entity but not the page.
    """
    url = canonical_url(f"/author/{author.slug}")
    socials = [
        getattr(author, key, None)
        for key in ("facebook", "twitter", "linkedin", "instagram", "youtube", "website")
    ]
    person: dict[str, Any] = {
        "@type": "Person",
        "@id": f"{url}#person",
        "name": author.name,
        "url": url,
    }
    if getattr(author, "profession", None):
        person["jobTitle"] = author.profession
    if getattr(author, "bio", None):
        person["description"] = author.bio
    if getattr(author, "image", None):
        person["image"] = author.image
    # Only the address the user opted into publishing — never the login email.
    if getattr(author, "contact_email", None):
        person["email"] = author.contact_email
    if getattr(author, "address", None):
        person["address"] = author.address
    if getattr(author, "education", None):
        person["alumniOf"] = {"@type": "EducationalOrganization", "name": author.education}
    skills = [s.strip() for s in (getattr(author, "skills", None) or "").split(",") if s.strip()]
    if skills:
        person["knowsAbout"] = skills
    links = [s for s in socials if s]
    if links:
        person["sameAs"] = links
    person["worksFor"] = _organization()

    profile = {
        "@type": "ProfilePage",
        "@id": url,
        "url": url,
        "name": author.name,
        "mainEntity": {"@id": f"{url}#person"},
        "isPartOf": {"@id": f"{canonical_url('/')}#website"},
    }
    if posts:
        profile["hasPart"] = [
            {
                "@type": "BlogPosting",
                "headline": p.title,
                "url": canonical_url(f"/{p.slug}"),
            }
            for p in posts
        ]
    return _graph(
        profile,
        person,
        _breadcrumbs([("Home", "/"), ("Blog", "/blog"), (author.name, f"/author/{author.slug}")]),
    )
