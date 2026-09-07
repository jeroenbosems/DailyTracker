"""v0.3.2 — Full vs Focused Epic paths; parked Phases skipped by next_step."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Prefer DATA_DIR temp when tests need file-backed SQLite (verify hint).
_TMP = tempfile.mkdtemp(prefix="dt-v032-")
os.environ["DATA_DIR"] = _TMP

from app.auth import hash_password
from app.database import Base
from app.epics_logic import (
    PATH_FOCUSED,
    PATH_FULL,
    complete_step,
    current_phase,
    next_step,
    switch_epic_path,
)
from app.models import Epic, Phase, Step, User
from app.watch_logic import nearly_done_candidates


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session) -> User:
    user = User(username="pathuser", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _full_epic(db: Session, user: User) -> Epic:
    epic = Epic(user_id=user.id, title="Home redo", path=PATH_FULL, legendary=True)
    db.add(epic)
    db.flush()
    phases = []
    for i, title in enumerate(("Plan", "Build", "Polish")):
        ph = Phase(epic_id=epic.id, title=title, sort_order=i, parked=False)
        db.add(ph)
        db.flush()
        db.add(Step(phase_id=ph.id, title=f"{title}-A", sort_order=0))
        db.add(Step(phase_id=ph.id, title=f"{title}-B", sort_order=1))
        phases.append(ph)
    db.commit()
    db.refresh(epic)
    _ = epic.phases
    for p in epic.phases:
        _ = p.steps
    return epic


def test_next_step_skips_parked_phases():
    db = _session()
    user = _user(db)
    epic = _full_epic(db, user)
    phases = sorted(epic.phases, key=lambda p: p.sort_order)
    assert next_step(epic).title == "Plan-A"

    phases[0].parked = True
    db.commit()
    db.refresh(epic)
    assert current_phase(epic).title == "Build"
    assert next_step(epic).title == "Build-A"

    # Complete build steps → polish
    for _ in range(2):
        s = next_step(epic)
        complete_step(db, user, s)
        db.commit()
    assert next_step(epic).title == "Polish-A"


def test_full_to_focused_parks_extras():
    db = _session()
    user = _user(db)
    epic = _full_epic(db, user)
    # Complete one step in phase 3 so progress must not be wiped
    polish = next(p for p in epic.phases if p.title == "Polish")
    step = sorted(polish.steps, key=lambda s: s.sort_order)[0]
    complete_step(db, user, step)
    db.commit()

    msg = switch_epic_path(db, epic, PATH_FOCUSED, confirm_destructive=False)
    db.commit()
    db.refresh(epic)
    assert epic.path == PATH_FOCUSED
    assert "park" in msg.lower()
    phases = sorted(epic.phases, key=lambda p: p.sort_order)
    assert phases[0].parked is False
    assert phases[1].parked is False
    assert phases[2].parked is True
    # completed step preserved
    db.refresh(step)
    assert step.completed is True
    assert next_step(epic).title == "Plan-A"


def test_focused_to_full_adds_phases_and_unparks():
    db = _session()
    user = _user(db)
    epic = Epic(user_id=user.id, title="Lean epic", path=PATH_FOCUSED, legendary=True)
    db.add(epic)
    db.flush()
    for i, title in enumerate(("Start", "Finish")):
        ph = Phase(epic_id=epic.id, title=title, sort_order=i)
        db.add(ph)
        db.flush()
        db.add(Step(phase_id=ph.id, title=f"{title}-1", sort_order=0))
    db.commit()
    db.refresh(epic)
    _ = epic.phases

    # Mark second phase parked as if already focused
    sorted(epic.phases, key=lambda p: p.sort_order)[1].parked = True
    db.commit()

    done_step = next(s for p in epic.phases for s in p.steps if s.title == "Start-1")
    complete_step(db, user, done_step)
    db.commit()

    msg = switch_epic_path(db, epic, PATH_FULL, confirm_destructive=False)
    db.commit()
    db.refresh(epic)
    assert epic.path == PATH_FULL
    assert all(not p.parked for p in epic.phases)
    assert len(epic.phases) >= 3
    assert "added" in msg.lower()
    db.refresh(done_step)
    assert done_step.completed is True


def test_focused_destructive_removes_incomplete_extras_only():
    db = _session()
    user = _user(db)
    epic = _full_epic(db, user)
    polish = next(p for p in epic.phases if p.title == "Polish")
    polish_id = polish.id
    # leave polish incomplete; complete a step in Build so Build is not removable if kept
    msg = switch_epic_path(db, epic, PATH_FOCUSED, confirm_destructive=True)
    db.commit()
    assert epic.path == PATH_FOCUSED
    assert "removed" in msg.lower()
    assert db.get(Phase, polish_id) is None
    assert len(epic.phases) == 2


def test_nearly_done_skips_parked_phase_steps():
    db = _session()
    user = _user(db)
    epic = _full_epic(db, user)
    user.active_epic_id = epic.id
    plan = sorted(epic.phases, key=lambda p: p.sort_order)[0]
    # Complete one of two → 50% not nearly; complete to leave one → nearly
    steps = sorted(plan.steps, key=lambda s: s.sort_order)
    complete_step(db, user, steps[0])
    db.commit()
    # now 50% — not nearly by 80% rule; last incomplete makes nearly
    candidates = nearly_done_candidates(db, user, set())
    assert any(c.id == steps[1].id for c in candidates)

    plan.parked = True
    db.commit()
    candidates2 = nearly_done_candidates(db, user, set())
    assert all(c.id != steps[1].id for c in candidates2)


def test_data_dir_temp_is_set():
    assert Path(os.environ["DATA_DIR"]).is_dir()
