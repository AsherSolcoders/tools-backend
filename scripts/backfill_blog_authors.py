"""Give every existing post a linked author, and every staff account a profile URL.

Posts written before author profiles existed carry a free-text `author` name and
no `author_id`, so their byline links nowhere. This attaches them to a real
account so the credit becomes a working profile link.

Nothing is destroyed: the original free-text name is printed before it is
replaced, and only rows with no `author_id` are touched — so this is safe to run
twice, and safe to run on a live database.

Usage — with the virtualenv's Python, not the system one, which has none of the
app's dependencies:

    .venv/bin/python scripts/backfill_blog_authors.py            # show the plan
    .venv/bin/python scripts/backfill_blog_authors.py --apply    # write it
    .venv/bin/python scripts/backfill_blog_authors.py --apply --author-email you@site.com

It prints the database it is connected to before doing anything, so a wrong
DATABASE_URL is visible rather than silent.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
# Settings read `.env` relative to the working directory, so running this from
# anywhere else silently fell back to the default SQLite URL — it would report
# "0 posts" against an empty file while the real database sat untouched.
os.chdir(BACKEND)

from sqlalchemy import select  # noqa: E402

from app.core.slug import slugify  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Blog, User  # noqa: E402
from app.models.user import UserRole  # noqa: E402


def pick_default_author(db, email: str | None) -> User:
    if email:
        user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
        if not user:
            raise SystemExit(f"No account with email {email!r}.")
        return user
    # Otherwise the oldest super_admin — the "Admin" the site already runs under.
    user = db.execute(
        select(User).where(User.role == UserRole.super_admin).order_by(User.id)
    ).scalars().first()
    if not user:
        raise SystemExit("No super_admin account found. Pass --author-email instead.")
    return user


def unique_slug(db, user: User) -> str:
    base = slugify(user.slug or user.name) or f"author-{user.id}"
    candidate, n = base, 2
    while db.execute(
        select(User).where(User.slug == candidate, User.id != user.id)
    ).scalar_one_or_none():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--author-email", help="credit this account instead of the super admin")
    args = ap.parse_args()

    # Print the target before touching anything. This script writes to live data,
    # and a wrong DATABASE_URL is the one mistake that would not be obvious.
    from app.config import settings

    url = settings.database_url
    print(f"Database: {url.split('@')[-1] if '@' in url else url}")
    if url.startswith("sqlite"):
        print("  ^ that is SQLite. If you expected Postgres, check .env before continuing.\n")
    else:
        print()

    db = SessionLocal()
    try:
        default = pick_default_author(db, args.author_email)
        print(f"Default author: {default.name} <{default.email}> (id {default.id})\n")

        # 1. Every account needs a slug, or its profile page has no URL.
        missing_slug = db.execute(select(User).where(User.slug.is_(None))).scalars().all()
        for user in missing_slug:
            slug = unique_slug(db, user)
            print(f"  user {user.id:>3}  {user.name!r}  ->  /author/{slug}")
            if args.apply:
                user.slug = slug
        print(f"{len(missing_slug)} account(s) needed a profile URL.\n")

        # 2. Posts with no linked account get the default one.
        orphans = db.execute(select(Blog).where(Blog.author_id.is_(None))).scalars().all()
        for post in orphans:
            was = post.author or "(no byline)"
            print(f"  post {post.id:>3}  {post.slug:<45}  {was!r} -> {default.name!r}")
            if args.apply:
                post.author_id = default.id
                post.author = default.name
        print(f"{len(orphans)} post(s) had no linked author.")

        if args.apply:
            db.commit()
            print("\nApplied.")
        else:
            print("\nDry run — nothing written. Re-run with --apply.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
