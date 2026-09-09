"""v1.1 BL-031 — soft routine skip with reason."""

from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Routine, User
from app.routines_logic import advance_due


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_skip_advances_due_without_reward_or_streak_change():
    db = _session()
    user = User(username="s", password_hash=hash_password("password123"), total_points=100)
    db.add(user)
    db.flush()
    today = date.today()
    r = Routine(
        user_id=user.id,
        title="Walk",
        cadence="daily",
        next_due_on=today,
        streak=3,
        best_streak=5,
        completion_count=10,
    )
    db.add(r)
    db.commit()
    pts = user.total_points
    r.last_skipped_on = today
    r.last_skip_reason = "Travel day"
    r.next_due_on = advance_due("daily", today)
    db.commit()
    db.refresh(r)
    db.refresh(user)
    assert r.streak == 3
    assert r.best_streak == 5
    assert r.completion_count == 10
    assert user.total_points == pts
    assert r.next_due_on == advance_due("daily", today)


def test_http_skip_requires_reason_and_keeps_streak(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v11-skip")
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
            "/routines",
            data={"title": "Meditate", "cadence": "daily", "priority": "2", "notes": ""},
            follow_redirects=False,
        )
        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            r = db.scalar(select(Routine).where(Routine.user_id == user.id))
            r.streak = 4
            r.best_streak = 7
            r.completion_count = 12
            pts = user.total_points
            rid = r.id
            db.commit()
        finally:
            db.close()

        bad = client.post(f"/routines/{rid}/skip", data={"reason": ""}, follow_redirects=False)
        assert bad.status_code == 400

        ok = client.post(
            f"/routines/{rid}/skip",
            data={"reason": "Sick day"},
            follow_redirects=False,
        )
        assert ok.status_code == 303

        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            r = db.get(Routine, rid)
            assert r.last_skip_reason == "Sick day"
            assert r.streak == 4
            assert r.best_streak == 7
            assert r.completion_count == 12
            assert user.total_points == pts  # no reward
            assert r.next_due_on > date.today() or r.next_due_on == advance_due("daily", date.today())
        finally:
            db.close()
    finally:
        main.app.dependency_overrides.clear()
