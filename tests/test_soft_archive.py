"""v1.1 BL-021 — soft archive Epics without wiping progress."""

from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Epic, Phase, Step, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_archive_hides_but_keeps_steps():
    db = _session()
    user = User(username="a", password_hash=hash_password("password123"))
    db.add(user)
    db.flush()
    epic = Epic(user_id=user.id, title="Keep me", path="full", completed=True)
    db.add(epic)
    db.flush()
    ph = Phase(epic_id=epic.id, title="P", sort_order=0)
    db.add(ph)
    db.flush()
    db.add(Step(phase_id=ph.id, title="S1", sort_order=0, completed=True))
    db.add(Step(phase_id=ph.id, title="S2", sort_order=1, completed=False))
    user.active_epic_id = epic.id
    db.commit()

    epic.archived = True
    user.active_epic_id = None
    db.commit()
    db.refresh(epic)
    assert epic.archived is True
    assert len(epic.phases) == 1
    assert sum(len(p.steps) for p in epic.phases) == 2
    assert {s.title for p in epic.phases for s in p.steps} == {"S1", "S2"}


def test_http_archive_restore_and_list_filter(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v11-archive")
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

        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            epic = Epic(user_id=user.id, title="Archive Me", path="focused")
            db.add(epic)
            db.flush()
            ph = Phase(epic_id=epic.id, title="P", sort_order=0)
            db.add(ph)
            db.flush()
            db.add(Step(phase_id=ph.id, title="Keep", sort_order=0, completed=True))
            db.commit()
            eid = epic.id
        finally:
            db.close()

        arch = client.post(f"/epics/{eid}/archive", follow_redirects=False)
        assert arch.status_code == 303

        listed = client.get("/epics")
        assert listed.status_code == 200
        assert "Archive Me" not in listed.text or "Show archived" in listed.text
        # default list should not show title as primary (archived hidden)
        assert 'href="/epics/%d"' % eid not in listed.text or "Show archived" in listed.text

        shown = client.get("/epics", params={"show_archived": "1"})
        assert "Archive Me" in shown.text
        assert "Archived" in shown.text

        db = database.SessionLocal()
        try:
            epic = db.get(Epic, eid)
            assert epic.archived is True
            assert sum(len(p.steps) for p in epic.phases) == 1
            assert epic.phases[0].steps[0].title == "Keep"
            assert epic.phases[0].steps[0].completed is True
        finally:
            db.close()

        rest = client.post(f"/epics/{eid}/restore", follow_redirects=False)
        assert rest.status_code == 303
        listed2 = client.get("/epics")
        assert "Archive Me" in listed2.text
    finally:
        main.app.dependency_overrides.clear()
