from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL, ensure_data_dir

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_schema() -> None:
    """Add columns to existing SQLite DBs (create_all does not ALTER)."""
    alterations = [
        ("epics", "external_id", "ALTER TABLE epics ADD COLUMN external_id VARCHAR(128)"),
        ("phases", "external_id", "ALTER TABLE phases ADD COLUMN external_id VARCHAR(128)"),
        ("steps", "external_id", "ALTER TABLE steps ADD COLUMN external_id VARCHAR(128)"),
        ("epics", "path", "ALTER TABLE epics ADD COLUMN path VARCHAR(16) DEFAULT 'full'"),
        ("phases", "parked", "ALTER TABLE phases ADD COLUMN parked BOOLEAN DEFAULT 0"),
        ("tasks", "life_mode", "ALTER TABLE tasks ADD COLUMN life_mode VARCHAR(16)"),
        ("routines", "life_mode", "ALTER TABLE routines ADD COLUMN life_mode VARCHAR(16)"),
        ("steps", "life_mode", "ALTER TABLE steps ADD COLUMN life_mode VARCHAR(16)"),
        ("epics", "life_modes", "ALTER TABLE epics ADD COLUMN life_modes TEXT DEFAULT '[]'"),
        ("epics", "follows_epic_id", "ALTER TABLE epics ADD COLUMN follows_epic_id INTEGER"),
        ("tasks", "external_id", "ALTER TABLE tasks ADD COLUMN external_id VARCHAR(128)"),
        ("routines", "external_id", "ALTER TABLE routines ADD COLUMN external_id VARCHAR(128)"),
        ("reward_logs", "external_id", "ALTER TABLE reward_logs ADD COLUMN external_id VARCHAR(128)"),
        ("redemptions", "external_id", "ALTER TABLE redemptions ADD COLUMN external_id VARCHAR(128)"),
        ("epics", "archived", "ALTER TABLE epics ADD COLUMN archived BOOLEAN DEFAULT 0"),
        ("routines", "last_skipped_on", "ALTER TABLE routines ADD COLUMN last_skipped_on DATE"),
        ("routines", "last_skip_reason", "ALTER TABLE routines ADD COLUMN last_skip_reason VARCHAR(255)"),
        ("users", "equipped_theme", "ALTER TABLE users ADD COLUMN equipped_theme VARCHAR(32)"),
        ("users", "equipped_title", "ALTER TABLE users ADD COLUMN equipped_title VARCHAR(32)"),
        ("users", "equipped_badge_frame", "ALTER TABLE users ADD COLUMN equipped_badge_frame VARCHAR(32)"),
        ("users", "equipped_today_flair", "ALTER TABLE users ADD COLUMN equipped_today_flair VARCHAR(32)"),
    ]
    with engine.begin() as conn:
        for table, column, ddl in alterations:
            try:
                names = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            except Exception:
                continue
            if not names:
                continue  # table not created yet
            if column not in names:
                conn.execute(text(ddl))


def init_db() -> None:
    from app import models  # noqa: F401

    ensure_data_dir()
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
