"""v0.7 — export strips secrets; merge/replace restore rules."""

from __future__ import annotations

import json
import os
import tempfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

_TMP = tempfile.mkdtemp(prefix="dt-v07-")
os.environ.setdefault("DATA_DIR", _TMP)

from app.auth import hash_password
from app.backup import SCHEMA_VERSION, BackupError, apply_restore, build_export
from app.database import Base
from app.models import Epic, Phase, RewardLog, Step, Task, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session) -> User:
    user = User(
        username="backup",
        password_hash=hash_password("password123"),
        total_points=40,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_export_strips_secrets_and_has_schema():
    db = _session()
    user = _user(db)
    db.add(Task(user_id=user.id, title="T1", priority=1))
    db.add(RewardLog(user_id=user.id, tier="bronze", points=10, reason="x"))
    db.commit()
    payload = build_export(db, user)
    db.commit()
    dumped = json.dumps(payload)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert "exported_at" in payload
    assert "password_hash" not in dumped
    assert "session" not in dumped.lower() or "session_secret" not in dumped.lower()
    assert payload["user"]["username"] == "backup"
    assert "password_hash" not in payload["user"]
    assert len(payload["tasks"]) == 1
    assert payload["tasks"][0]["external_id"]


def test_merge_never_overwrites_completed_step():
    db = _session()
    user = _user(db)
    epic = Epic(user_id=user.id, title="E", external_id="epic-1", path="full")
    db.add(epic)
    db.flush()
    ph = Phase(epic_id=epic.id, title="P", external_id="phase-1", sort_order=0)
    db.add(ph)
    db.flush()
    st = Step(
        phase_id=ph.id,
        title="Original",
        external_id="step-1",
        sort_order=0,
        completed=True,
    )
    db.add(st)
    db.commit()

    blob = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": "2026-09-08T00:00:00+00:00",
        "user": {"username": "backup", "total_points": 40},
        "tasks": [],
        "routines": [],
        "epics": [
            {
                "external_id": "epic-1",
                "title": "E",
                "path": "full",
                "life_modes": "[]",
                "phases": [
                    {
                        "external_id": "phase-1",
                        "title": "P",
                        "sort_order": 0,
                        "steps": [
                            {
                                "external_id": "step-1",
                                "title": "HACKED",
                                "sort_order": 0,
                                "completed": False,
                            }
                        ],
                    }
                ],
            }
        ],
        "reward_logs": [],
        "redemptions": [],
    }
    apply_restore(db, user, json.dumps(blob), mode="merge")
    db.commit()
    db.refresh(st)
    assert st.title == "Original"
    assert st.completed is True


def test_replace_requires_confirm_and_unknown_schema_rejected():
    db = _session()
    user = _user(db)
    db.add(Task(user_id=user.id, title="Keep?", external_id="task-keep"))
    db.commit()
    good = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": "2026-09-08T00:00:00+00:00",
        "user": {"username": "backup", "total_points": 7},
        "tasks": [
            {
                "external_id": "task-new",
                "title": "Imported",
                "priority": 2,
                "completed": False,
            }
        ],
        "routines": [],
        "epics": [],
        "reward_logs": [],
        "redemptions": [],
    }
    with pytest.raises(BackupError):
        apply_restore(
            db,
            user,
            json.dumps(good),
            mode="replace",
            replace_confirm_text="REPLACE",
            replace_confirm_checked=False,
        )
    db.rollback()

    with pytest.raises(BackupError) as exc:
        apply_restore(db, user, json.dumps({**good, "schema_version": 99}), mode="merge")
    assert "schema_version" in exc.value.message.lower()

    apply_restore(
        db,
        user,
        json.dumps(good),
        mode="replace",
        replace_confirm_text="REPLACE",
        replace_confirm_checked=True,
    )
    db.commit()
    titles = [t.title for t in db.scalars(select(Task).where(Task.user_id == user.id)).all()]
    assert titles == ["Imported"]
    db.refresh(user)
    assert user.total_points == 7
    assert user.password_hash  # account kept


# import pytest for raises
import pytest  # noqa: E402


def test_http_settings_export_no_secrets_on_today(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v07")
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

        exp = client.get("/settings/export.json")
        assert exp.status_code == 200
        data = exp.json()
        assert data["schema_version"] == SCHEMA_VERSION
        assert "password_hash" not in exp.text

        today = client.get("/today")
        assert today.status_code == 200
        # no restore/export clutter above Due now
        before_due = today.text.split("Due now")[0]
        assert "Download JSON export" not in before_due
        assert "Restore from backup" not in before_due
        assert 'href="/settings"' in today.text

        settings = client.get("/settings")
        assert settings.status_code == 200
        assert "Download JSON export" in settings.text
        assert "Restore" in settings.text
    finally:
        main.app.dependency_overrides.clear()
