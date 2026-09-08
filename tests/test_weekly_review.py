"""v0.9 — weekly review read-only snapshot."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Epic, Phase, RewardLog, Routine, Step, Task, User
from app.review import build_weekly_review, week_bounds


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_week_bounds_iso():
    # 2026-09-08 is a Tuesday → week starts Mon 2026-09-07
    start, end, label = week_bounds(date(2026, 9, 8))
    assert start == date(2026, 9, 7)
    assert end == date(2026, 9, 13)
    assert label == "2026-W37"


def test_build_weekly_review_counts_week_completions():
    db = _session()
    user = User(username="rev", password_hash=hash_password("password123"), total_points=0)
    db.add(user)
    db.flush()
    today = date(2026, 9, 8)
    now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    old = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

    db.add(Task(user_id=user.id, title="This week", completed=True, completed_at=now, priority=1))
    db.add(Task(user_id=user.id, title="Old", completed=True, completed_at=old, priority=1))
    db.add(
        Routine(
            user_id=user.id,
            title="Daily stretch",
            cadence="daily",
            next_due_on=today,
            last_completed_on=today,
        )
    )
    db.add(RewardLog(user_id=user.id, tier="gold", points=50, reason="task", created_at=now))
    db.add(RewardLog(user_id=user.id, tier="bronze", points=10, reason="old", created_at=old))

    epic = Epic(user_id=user.id, title="Ship", path="full")
    db.add(epic)
    db.flush()
    ph = Phase(epic_id=epic.id, title="P", sort_order=0)
    db.add(ph)
    db.flush()
    db.add(Step(phase_id=ph.id, title="Done step", sort_order=0, completed=True, completed_at=now))
    db.add(Step(phase_id=ph.id, title="Next", sort_order=1, completed=False))
    user.active_epic_id = epic.id
    db.commit()

    review = build_weekly_review(db, user, day=today)
    assert review["week_label"] == "2026-W37"
    assert len(review["tasks"]) == 1
    assert review["tasks"][0].title == "This week"
    assert len(review["routines"]) == 1
    assert len(review["steps"]) == 1
    assert review["points_earned"] == 50
    assert review["active_epic"].title == "Ship"
    assert review["active_next"].title == "Next"
    assert review["active_pct"] == 50.0
    assert any(b["period"] == "daily" for b in review["period_bonuses"])
    assert any(b["period"] == "weekly" for b in review["period_bonuses"])


def test_http_review_readonly_and_cta(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v09")
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

        page = client.get("/review")
        assert page.status_code == 200
        assert "Weekly review" in page.text
        assert "Back to Today" in page.text
        assert 'href="/today"' in page.text
        # read-only: no complete/redeem forms on review
        assert 'action="/tasks/' not in page.text
        assert 'action="/shop/redeem"' not in page.text

        today = client.get("/today")
        assert 'href="/review"' in today.text
        assert "Weekly review" in today.text
    finally:
        main.app.dependency_overrides.clear()
