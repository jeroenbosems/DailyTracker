"""v0.4 — life-mode filter (tagged+untagged); section order; templates don't wipe."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.ingest import apply_ingest
from app.life_modes import (
    LIFE_MODES,
    matches_epic_modes,
    matches_single_mode,
    parse_filter_mode,
)
from app.models import Epic, Phase, Step, Task, User

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "docs" / "templates"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session) -> User:
    user = User(username="modeuser", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_matches_single_mode_tagged_or_untagged():
    assert matches_single_mode(None, None) is True
    assert matches_single_mode("work", None) is True
    assert matches_single_mode(None, "work") is True  # untagged shows under filter
    assert matches_single_mode("work", "work") is True
    assert matches_single_mode("home", "work") is False
    assert matches_single_mode("", "health") is True


def test_matches_epic_modes_empty_is_untagged():
    assert matches_epic_modes("[]", "work") is True
    assert matches_epic_modes(None, "work") is True
    assert matches_epic_modes('["home"]', "work") is False
    assert matches_epic_modes('["home","work"]', "work") is True


def test_parse_filter_mode():
    assert parse_filter_mode(None) is None
    assert parse_filter_mode("all") is None
    assert parse_filter_mode("WORK") == "work"
    assert parse_filter_mode("nope") is None
    assert set(LIFE_MODES) == {"work", "health", "home", "learning"}


def test_today_filter_shows_tagged_and_untagged_hides_other():
    """Under a mode filter: tagged that mode OR untagged; other tags hidden."""
    db = _session()
    user = _user(db)
    today = date.today()
    db.add_all(
        [
            Task(user_id=user.id, title="Work due", priority=1, due_date=today, life_mode="work"),
            Task(user_id=user.id, title="Untagged due", priority=2, due_date=today, life_mode=None),
            Task(user_id=user.id, title="Home due", priority=2, due_date=today, life_mode="home"),
            Task(user_id=user.id, title="Work undated", priority=1, due_date=None, life_mode="work"),
        ]
    )
    db.commit()
    db.refresh(user)

    due = [t for t in user.tasks if not t.completed and t.due_date is not None and t.due_date <= today]
    filtered = [t for t in due if matches_single_mode(t.life_mode, "work")]
    titles = {t.title for t in filtered}
    assert titles == {"Work due", "Untagged due"}
    assert "Home due" not in titles


def test_section_order_unchanged_conceptually():
    """Today sections stay Due now → Active Epic → Watch → Period bonuses regardless of filter."""
    # Conceptual contract mirrored in today.html structure
    html = (REPO / "app" / "templates" / "today.html").read_text(encoding="utf-8")
    i_due = html.index("Due now")
    i_active = html.index("Active Epic")
    i_watch = html.index("Watch / Nearly done")
    i_period = html.index("Period bonuses")
    assert i_due < i_active < i_watch < i_period
    # Filter chips exist but must appear before Due now (not reorder sections)
    assert "mode-chips" in html
    assert html.index("mode-chips") < i_due


def test_starter_templates_valid_mode_new():
    for name in ("side-it-project.json", "move-house.json", "apartment-redo.json"):
        path = TEMPLATES / name
        assert path.is_file(), name
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mode"] == "new"
        assert data["confirm_destructive"] is False
        epic = data["epic"]
        assert epic["title"]
        assert epic.get("identity")
        assert epic.get("capability")
        assert epic.get("preview")
        assert epic.get("path") in ("full", "focused")
        assert isinstance(epic.get("life_modes"), list)
        assert all(m in LIFE_MODES for m in epic["life_modes"])
        assert len(epic["phases"]) >= 2
        for phase in epic["phases"]:
            assert phase["title"] and phase["steps"]
            for step in phase["steps"]:
                assert step["title"]
                if "life_mode" in step and step["life_mode"] is not None:
                    assert step["life_mode"] in LIFE_MODES


def test_template_load_creates_new_does_not_wipe_existing():
    db = _session()
    user = _user(db)
    # Existing epic with progress
    epic = Epic(
        user_id=user.id,
        external_id="existing_epic",
        title="Already in progress",
        life_modes='["work"]',
        legendary=True,
    )
    db.add(epic)
    db.flush()
    phase = Phase(epic_id=epic.id, title="P1", sort_order=1)
    db.add(phase)
    db.flush()
    step = Step(phase_id=phase.id, title="Done step", sort_order=1, completed=True)
    db.add(step)
    user.active_epic_id = epic.id
    db.commit()

    raw = (TEMPLATES / "move-house.json").read_text(encoding="utf-8")
    msg = apply_ingest(db, user, raw, ui_confirm_destructive=False)
    db.commit()

    db.refresh(epic)
    db.refresh(step)
    assert step.completed is True
    assert epic.title == "Already in progress"
    epics = db.scalars(select(Epic).where(Epic.user_id == user.id)).all()
    assert len(epics) == 2
    new_ones = [e for e in epics if e.external_id == "tpl_move_house"]
    assert len(new_ones) == 1
    assert "Imported new Epic" in msg
    # Existing progress untouched
    assert db.get(Step, step.id).completed is True


def test_ingest_life_modes_on_new():
    db = _session()
    user = _user(db)
    payload = {
        "mode": "new",
        "confirm_destructive": False,
        "epic": {
            "id": "epic_lm",
            "title": "Learn Rust",
            "identity": "Capable systems learner",
            "capability": "Ship a small CLI",
            "preview": "Hello-world binary",
            "status": "parked",
            "path": "focused",
            "life_modes": ["learning", "work"],
            "phases": [
                {
                    "id": "p1",
                    "title": "Basics",
                    "order": 1,
                    "deliverable": "Notes",
                    "steps": [
                        {
                            "id": "s1",
                            "title": "Read ownership chapter",
                            "order": 1,
                            "parallel": True,
                            "priority": 1,
                            "life_mode": "learning",
                        }
                    ],
                }
            ],
        },
    }
    apply_ingest(db, user, json.dumps(payload), ui_confirm_destructive=False)
    db.commit()
    epic = db.scalar(select(Epic).where(Epic.external_id == "epic_lm"))
    assert epic is not None
    assert json.loads(epic.life_modes) == ["learning", "work"]
    step = epic.phases[0].steps[0]
    assert step.life_mode == "learning"


def test_http_template_start_and_today_filter(tmp_path, monkeypatch):
    """Integration: Today filter + Start from template via TestClient on isolated DB."""
    import app.config as config
    import app.database as database
    import app.main as main
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v04")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(database, "DATABASE_URL", f"sqlite:///{db_path}")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    database._migrate_schema()

    # Point get_db at our engine
    def _override_db():
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[database.get_db] = _override_db
    # Also patch main.get_db import path used via Depends
    from app.database import get_db as real_get_db  # noqa: F401

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

        client.post(
            "/tasks",
            data={
                "title": "Work task",
                "priority": "1",
                "due_date": date.today().isoformat(),
                "life_mode": "work",
            },
            follow_redirects=False,
        )
        client.post(
            "/tasks",
            data={
                "title": "Untagged task",
                "priority": "2",
                "due_date": date.today().isoformat(),
                "life_mode": "",
            },
            follow_redirects=False,
        )
        client.post(
            "/tasks",
            data={
                "title": "Home task",
                "priority": "2",
                "due_date": date.today().isoformat(),
                "life_mode": "home",
            },
            follow_redirects=False,
        )

        page = client.get("/today?mode=work")
        assert page.status_code == 200
        body = page.text
        assert "Work task" in body
        assert "Untagged task" in body
        assert "Home task" not in body
        assert body.index("Due now") < body.index("Active Epic") < body.index(
            "Watch / Nearly done"
        ) < body.index("Period bonuses")

        client.post(
            "/epics",
            data={
                "title": "Keep me",
                "path": "focused",
                "legendary": "on",
                "life_modes": ["work"],
                "phase_titles": ["A", "B"],
                "phase_steps": ["Step A1\nStep A2", "Step B1\nStep B2"],
                "phase_deliverables": ["", ""],
            },
            follow_redirects=False,
        )
        assert "Keep me" in client.get("/epics").text

        start = client.post("/templates/side-it-project/start", follow_redirects=False)
        assert start.status_code == 303
        after = client.get("/epics").text
        assert "Keep me" in after
        assert "Ship a useful side IT project" in after
    finally:
        main.app.dependency_overrides.clear()
