"""Database engine, session, and Base model."""
from __future__ import annotations

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


# Columns added after the initial release, applied on startup if absent.
_ADDITIVE_COLUMNS: dict[str, dict[str, str]] = {
    "blogs": {
        "author": "VARCHAR(160)",
        "is_featured": "BOOLEAN DEFAULT 0",
        "is_popular": "BOOLEAN DEFAULT 0",
    },
}


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDITIVE_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
