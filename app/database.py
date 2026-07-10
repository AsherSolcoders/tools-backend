"""Database engine, session, and Base model."""
from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite needs check_same_thread=False for FastAPI's threaded request handling.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and apply small additive column migrations.

    There is no Alembic here, and `create_all` only creates *missing tables* — it
    never alters an existing one. So new nullable columns on already-created tables
    are added by hand below (idempotent: skipped if the column already exists).
    """
    # Import models so they register with Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Add post-release columns to existing tables (idempotent, dialect-aware).

    Wrapped defensively: a migration hiccup logs a warning but never prevents the
    app from starting. Boolean defaults differ per dialect (Postgres rejects `0`).
    """
    is_postgres = engine.dialect.name == "postgresql"
    false_default = "FALSE" if is_postgres else "0"
    ts_type = "TIMESTAMPTZ" if is_postgres else "DATETIME"

    additive_columns: dict[str, dict[str, str]] = {
        "blogs": {
            "author": "VARCHAR(160)",
            "is_featured": f"BOOLEAN DEFAULT {false_default}",
            "is_popular": f"BOOLEAN DEFAULT {false_default}",
            "created_by_id": "INTEGER",
            "updated_by_id": "INTEGER",
            "old_slugs": "VARCHAR(1000)",
            "display_date": ts_type,
        },
        "blog_categories": {
            "meta_title": "VARCHAR(255)",
            "meta_description": "VARCHAR(500)",
        },
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in additive_columns.items():
        if table not in existing_tables:
            continue
        present = {c["name"] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name in present:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
            except Exception as exc:  # noqa: BLE001 — never block startup on a migration
                logging.getLogger("uvicorn.error").warning(
                    "Could not add column %s.%s: %s", table, name, exc
                )
