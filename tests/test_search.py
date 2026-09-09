"""v1.1 BL-020 — search by title substring; R7.1 Today untouched."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Epic, Phase, Routine, Step, Task, User
from app.search import search_user


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_search_matches_kinds_case_insensitive():
    db = _session()
    user = User(username="s", password_hash=hash_password("password123"))
    db.add(user)
    db.flush()
    db.add(Task(user_id=user.id, title="Ship MVP notes", priority=1))
    db.add(Routine(user_id=user.id, title="Ship checklist", cadence="daily", next_due_on=__import__("datetime").date.today()))
    epic = Epic(user_id=user.id, title="Ship the product", path="full")
    db.add(epic)
    db.flush()
    ph = Phase(epic_id=epic.id, title="Build", sort_order=0)
    db.add(ph)
    db.flush()
    db.add(Step(phase_id=ph.id, title="Ship docs", sort_order=0))
    db.add(Task(user_id=user.id, title="Unrelated", priority=2))
    db.commit()

    hits = search_user(db, user, "ship")
    kinds = {h.kind for h in hits}
    assert kinds == {"task", "routine", "epic", "step"}
    assert all("ship" in h.title.casefold() for h in hits)
    assert search_user(db, user, "") == []
    assert search_user(db, user, "zzzz-nope") == []


def test_http_search_and_today_order_unchanged(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v11-search")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(database, "DATABASE_URL", f"sqlite:///{db_path}")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    database.engine = engine
    database.SessionLocal = sa_sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    database._migrate_schema()

    def _override_db():
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[database.get_db] = _override_db
    client = TestClient(main.app)
    try:
        assert client.post(
            "/setup",
            data={
                "username": "alice",
                "password": "password123",
                "password_confirm": "password123",
            },
            follow_redirects=False,
        ).status_code == 303

        client.post(
            "/tasks",
            data={"title": "Findme task", "priority": "1", "due_date": ""},
            follow_redirects=False,
        )

        page = client.get("/search", params={"q": "Findme"})
        assert page.status_code == 200
        assert "Findme task" in page.text
        assert 'href="/search"' in page.text

        today = client.get("/today")
        assert today.status_code == 200
        body = today.text
        assert "Due now" in body and "Active Epic" in body
        assert body.index("Due now") < body.index("Active Epic")
        # Search must not inject a results board above Due now
        assert "Results for" not in body.split("Due now")[0]
    finally:
        main.app.dependency_overrides.clear()
