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
    """Add v0.3 columns to existing SQLite DBs (create_all does not ALTER)."""
    alterations = [
        ("epics", "external_id", "ALTER TABLE epics ADD COLUMN external_id VARCHAR(128)"),
        ("phases", "external_id", "ALTER TABLE phases ADD COLUMN external_id VARCHAR(128)"),
        ("steps", "external_id", "ALTER TABLE steps ADD COLUMN external_id VARCHAR(128)"),
        ("epics", "path", "ALTER TABLE epics ADD COLUMN path VARCHAR(16) DEFAULT 'full'"),
        ("phases", "parked", "ALTER TABLE phases ADD COLUMN parked BOOLEAN DEFAULT 0"),
    ]
    with engine.begin() as conn:
        for table, column, ddl in alterations:
            try:
                names = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            except Exception:
                continue
            if column not in names:
                conn.execute(text(ddl))


def init_db() -> None:
    from app import models  # noqa: F401

    ensure_data_dir()
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
