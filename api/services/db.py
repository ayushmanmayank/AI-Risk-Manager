"""SQLite storage for scored predictions (Day 3 MVP; swap for Postgres later)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "predictions.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist yet, and apply small additive
    migrations for tables that already exist from a prior schema version.

    Safe to call on every startup: create_all() only creates missing
    tables, so an existing SQLite file that predates a new column needs a
    lightweight ALTER TABLE here or every startup after a schema change
    would otherwise mean deleting the whole database. Rows written before
    a migrated column existed simply get NULL for it (see
    db_models.py:content_hash) -- there is no raw data left to backfill
    them from.
    """
    from api.services import db_models  # noqa: F401  (registers the model with Base)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()


def _migrate_add_missing_columns() -> None:
    inspector = inspect(engine)
    if "predictions" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("predictions")}
    with engine.begin() as connection:
        if "content_hash" not in existing_columns:
            connection.execute(text("ALTER TABLE predictions ADD COLUMN content_hash VARCHAR"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_predictions_content_hash ON predictions (content_hash)")
            )
