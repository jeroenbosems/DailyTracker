"""v0.6 — Follow-on Epic: explicit CTA, follows_epic_id, no wipe of completed."""

from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

_TMP = tempfile.mkdtemp(prefix="dt-v06-")
os.environ.setdefault("DATA_DIR", _TMP)

from app.auth import hash_password
from app.database import Base
from app.epics_logic import complete_step, next_step
from app.models import Epic, Phase, Step, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session, username: str = "followuser") -> User:
    user = User(username=username, password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _complete_tiny_epic(db: Session, user: User, title: str = "Ship MVP") -> Epic:
    epic = Epic(
        user_id=user.id,
        title=title,
        path="full",
        identity_end="Builder",
        capability_end="Ship weekly",
        life_modes='["work"]',
        legendary=True,
    )
    db.add(epic)
    db.flush()
    for i, (pt, steps) in enumerate(
        (("Plan", ["Outline"]), ("Build", ["Code", "Test"]))
    ):
        ph = Phase(epic_id=epic.id, title=pt, sort_order=i)
        db.add(ph)
        db.flush()
        for j, st in enumerate(steps):
            db.add(Step(phase_id=ph.id, title=st, sort_order=j))
    db.commit()
    db.refresh(epic)
    user.active_epic_id = epic.id
    db.commit()
    while True:
        s = next_step(epic)
        if not s:
            break
        complete_step(db, user, s)
        db.commit()
        db.refresh(epic)
        for phase in epic.phases:
            _ = phase.steps
    assert epic.completed
    return epic


def test_follow_on_creates_new_epic_without_wiping_source():
    db = _session()
    user = _user(db)
    source = _complete_tiny_epic(db, user)
    snap = {
        "title": source.title,
        "completed": source.completed,
        "identity_end": source.identity_end,
        "capability_end": source.capability_end,
        "life_modes": source.life_modes,
        "notes": source.notes,
    }
    phase_count = len(source.phases)
    step_count = sum(len(p.steps) for p in source.phases)

    child = Epic(
        user_id=user.id,
        follows_epic_id=source.id,
        title=f"Follow-on: {source.title}",
        path="focused",
        identity_end=f"{source.identity_end} (refine / maintain)",
        capability_end=f"{source.capability_end} (refine / maintain)",
        life_modes=source.life_modes,
        notes="Refine / maintain",
    )
    db.add(child)
    db.flush()
    for i, title in enumerate(("Stabilize", "Improve")):
        ph = Phase(epic_id=child.id, title=title, sort_order=i)
        db.add(ph)
        db.flush()
        db.add(Step(phase_id=ph.id, title=f"{title}-1", sort_order=0))
    db.commit()
    db.refresh(source)
    db.refresh(child)

    assert child.follows_epic_id == source.id
    assert child.id != source.id
    assert not child.completed
    for k, v in snap.items():
        assert getattr(source, k) == v
    assert len(source.phases) == phase_count
    assert sum(len(p.steps) for p in source.phases) == step_count


def test_http_follow_on_cta_and_create(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v06")
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
        r = client.post(
            "/setup",
            data={
                "username": "alice",
                "password": "password123",
                "password_confirm": "password123",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303

        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            assert user is not None
            source = _complete_tiny_epic(db, user)
            source_id = source.id
            title_before = source.title
        finally:
            db.close()

        page = client.get(f"/epics/{source_id}/follow-on")
        assert page.status_code == 200
        assert "Start follow-on" in page.text
        assert "Follow-on: Ship MVP" in page.text
        assert "Stabilize" in page.text

        detail = client.get(f"/epics/{source_id}")
        assert detail.status_code == 200
        assert "Start follow-on" in detail.text

        create = client.post(
            f"/epics/{source_id}/follow-on",
            data={
                "title": "Follow-on: Ship MVP",
                "notes": "Refine / maintain",
                "identity_end": "Builder (refine / maintain)",
                "capability_end": "Ship weekly (refine / maintain)",
                "path": "focused",
                "life_modes": ["work"],
                "phase_titles": ["Stabilize", "Improve"],
                "phase_steps": ["Review\nLock", "Refine\nShip"],
            },
            follow_redirects=False,
        )
        assert create.status_code == 303
        loc = create.headers.get("location", "")
        assert loc.startswith("/epics/")

        db = database.SessionLocal()
        try:
            source = db.get(Epic, source_id)
            assert source is not None
            assert source.title == title_before
            assert source.completed is True
            kids = list(db.scalars(select(Epic).where(Epic.follows_epic_id == source_id)).all())
            assert len(kids) == 1
            kid = kids[0]
            assert kid.title == "Follow-on: Ship MVP"
            assert kid.path == "focused"
            assert {p.title for p in kid.phases} >= {"Stabilize", "Improve"}
            kid_id = kid.id
        finally:
            db.close()

        kid_page = client.get(f"/epics/{kid_id}")
        assert "Follows:" in kid_page.text
        assert "Ship MVP" in kid_page.text

        parent_page = client.get(f"/epics/{source_id}")
        assert "Follow-ons" in parent_page.text
        assert "Follow-on: Ship MVP" in parent_page.text
    finally:
        main.app.dependency_overrides.clear()


def test_follow_on_rejected_if_not_completed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v06b")
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
        client.post(
            "/setup",
            data={
                "username": "bob",
                "password": "password123",
                "password_confirm": "password123",
            },
            follow_redirects=False,
        )
        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "bob"))
            epic = Epic(user_id=user.id, title="Open", path="focused", completed=False)
            db.add(epic)
            db.flush()
            ph = Phase(epic_id=epic.id, title="A", sort_order=0)
            db.add(ph)
            db.flush()
            db.add(Step(phase_id=ph.id, title="s", sort_order=0))
            db.commit()
            eid = epic.id
        finally:
            db.close()

        r = client.get(f"/epics/{eid}/follow-on")
        assert r.status_code == 400
    finally:
        main.app.dependency_overrides.clear()
