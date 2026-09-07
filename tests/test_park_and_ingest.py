"""v0.3: Park preserves progress; LLM ingest new/update + destructive guard."""

from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.epics_logic import complete_step, epic_progress
from app.ingest import IngestError, apply_ingest
from app.models import Epic, Phase, Step, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session) -> User:
    user = User(username="tester", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _sample_epic(db: Session, user: User, *, external_id: str = "epic_apt") -> Epic:
    epic = Epic(
        user_id=user.id,
        external_id=external_id,
        title="Apartment move",
        legendary=True,
        identity_end="Settled at home",
        capability_end="Keys in hand",
        preview_label="Trial week",
    )
    db.add(epic)
    db.flush()
    phase1 = Phase(
        epic_id=epic.id,
        external_id="phase_1",
        title="Pack",
        sort_order=1,
        deliverable="Boxes labeled",
    )
    phase2 = Phase(
        epic_id=epic.id,
        external_id="phase_2",
        title="Move",
        sort_order=2,
        deliverable="Furniture placed",
    )
    db.add_all([phase1, phase2])
    db.flush()
    db.add_all(
        [
            Step(phase_id=phase1.id, external_id="step_1", title="Pack kitchen", sort_order=1),
            Step(phase_id=phase1.id, external_id="step_2", title="Pack books", sort_order=2),
            Step(phase_id=phase2.id, external_id="step_3", title="Hire movers", sort_order=1),
            Step(phase_id=phase2.id, external_id="step_4", title="Unload truck", sort_order=2),
        ]
    )
    db.commit()
    db.refresh(epic)
    _ = epic.phases
    for p in epic.phases:
        _ = p.steps
    return epic


def test_park_preserves_progress():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)
    user.active_epic_id = epic.id
    db.commit()

    step = next(s for p in epic.phases for s in p.steps if s.external_id == "step_1")
    complete_step(db, user, step)
    db.commit()
    db.refresh(epic)
    done_before, total_before, pct_before = epic_progress(epic)
    assert done_before == 1
    assert step.completed is True
    title_before = epic.title

    # Park: clear active only
    assert user.active_epic_id == epic.id
    user.active_epic_id = None
    db.commit()

    db.refresh(epic)
    db.refresh(step)
    done, total, pct = epic_progress(epic)
    assert user.active_epic_id is None
    assert done == done_before and total == total_before and pct == pct_before
    assert step.completed is True
    assert epic.title == title_before
    assert epic.identity_end == "Settled at home"


def test_ingest_new_creates_epic_phases_steps():
    db = _session()
    user = _user(db)
    payload = {
        "mode": "new",
        "confirm_destructive": False,
        "epic": {
            "id": "epic_home",
            "title": "Redo the apartment",
            "identity": "Calm home base",
            "capability": "Live without renovation hanging over me",
            "preview": "One corner done",
            "status": "active",
            "phases": [
                {
                    "id": "phase_1",
                    "title": "Plan & declutter",
                    "order": 1,
                    "deliverable": "Plan staged",
                    "steps": [
                        {
                            "id": "step_1",
                            "title": "Photograph each room",
                            "order": 1,
                            "parallel": True,
                            "priority": 1,
                        },
                        {
                            "id": "step_2",
                            "title": "Donate first bag",
                            "order": 2,
                            "parallel": True,
                            "priority": 2,
                        },
                    ],
                },
                {
                    "id": "phase_2",
                    "title": "Paint",
                    "order": 2,
                    "deliverable": "Living room painted",
                    "steps": [
                        {
                            "id": "step_3",
                            "title": "Buy paint",
                            "order": 1,
                            "parallel": True,
                            "priority": 2,
                        }
                    ],
                },
            ],
        },
    }
    msg = apply_ingest(db, user, json.dumps(payload), ui_confirm_destructive=False)
    db.commit()
    assert "Imported new Epic" in msg

    epic = db.query(Epic).filter_by(user_id=user.id, external_id="epic_home").one()
    assert epic.title == "Redo the apartment"
    assert epic.identity_end == "Calm home base"
    assert len(epic.phases) == 2
    phases = sorted(epic.phases, key=lambda p: p.sort_order)
    assert phases[0].external_id == "phase_1"
    assert len(phases[0].steps) == 2
    assert phases[0].steps[0].priority == 1
    assert user.active_epic_id == epic.id


def test_ingest_update_refuses_silent_delete_of_completed_step():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)
    user.active_epic_id = epic.id
    step = next(s for p in epic.phases for s in p.steps if s.external_id == "step_1")
    complete_step(db, user, step)
    db.commit()

    # Update omits completed step_1 — destructive without confirms
    payload = {
        "mode": "update",
        "confirm_destructive": False,
        "epic": {
            "id": "epic_apt",
            "title": "Apartment move (revised)",
            "phases": [
                {
                    "id": "phase_1",
                    "title": "Pack",
                    "order": 1,
                    "steps": [
                        {
                            "id": "step_2",
                            "title": "Pack books",
                            "order": 1,
                            "parallel": True,
                            "priority": 2,
                        }
                    ],
                },
                {
                    "id": "phase_2",
                    "title": "Move",
                    "order": 2,
                    "steps": [
                        {
                            "id": "step_3",
                            "title": "Hire movers",
                            "order": 1,
                            "parallel": True,
                            "priority": 2,
                        },
                        {
                            "id": "step_4",
                            "title": "Unload truck",
                            "order": 2,
                            "parallel": True,
                            "priority": 2,
                        },
                    ],
                },
            ],
        },
    }
    try:
        apply_ingest(db, user, json.dumps(payload), ui_confirm_destructive=False)
        assert False, "expected IngestError"
    except IngestError as exc:
        assert "confirm_destructive" in exc.message.lower() or "remove" in exc.message.lower()

    db.rollback()
    db.refresh(step)
    assert step.completed is True
    assert db.get(Step, step.id) is not None


def test_ingest_update_with_confirm_destructive_allowed():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)
    step = next(s for p in epic.phases for s in p.steps if s.external_id == "step_1")
    complete_step(db, user, step)
    db.commit()
    step_id = step.id

    payload = {
        "mode": "update",
        "confirm_destructive": True,
        "epic": {
            "id": "epic_apt",
            "title": "Apartment move (revised)",
            "phases": [
                {
                    "id": "phase_1",
                    "title": "Pack revised",
                    "order": 1,
                    "deliverable": "Boxes labeled",
                    "steps": [
                        {
                            "id": "step_2",
                            "title": "Pack books carefully",
                            "order": 1,
                            "parallel": True,
                            "priority": 1,
                        }
                    ],
                },
                {
                    "id": "phase_2",
                    "title": "Move",
                    "order": 2,
                    "steps": [
                        {
                            "id": "step_3",
                            "title": "Hire movers",
                            "order": 1,
                            "parallel": True,
                            "priority": 2,
                        },
                        {
                            "id": "step_4",
                            "title": "Unload truck",
                            "order": 2,
                            "parallel": True,
                            "priority": 2,
                        },
                    ],
                },
            ],
        },
    }
    msg = apply_ingest(db, user, json.dumps(payload), ui_confirm_destructive=True)
    db.commit()
    assert "Updated" in msg

    assert db.get(Step, step_id) is None
    db.refresh(epic)
    phase1 = next(p for p in epic.phases if p.external_id == "phase_1")
    assert phase1.title == "Pack revised"
    assert len(phase1.steps) == 1
    assert phase1.steps[0].external_id == "step_2"
    assert phase1.steps[0].title == "Pack books carefully"
    assert epic.title == "Apartment move (revised)"


def test_ingest_update_title_preserves_completion():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)
    step = next(s for p in epic.phases for s in p.steps if s.external_id == "step_1")
    complete_step(db, user, step)
    db.commit()

    payload = {
        "mode": "update",
        "confirm_destructive": False,
        "epic": {
            "id": "epic_apt",
            "title": "Apartment move — renamed",
            "identity": "Homebody",
            "phases": [
                {
                    "id": "phase_1",
                    "title": "Pack",
                    "order": 1,
                    "steps": [
                        {
                            "id": "step_1",
                            "title": "Pack kitchen (done)",
                            "order": 1,
                            "parallel": True,
                            "priority": 2,
                        },
                        {
                            "id": "step_2",
                            "title": "Pack books",
                            "order": 2,
                            "parallel": True,
                            "priority": 2,
                        },
                    ],
                },
                {
                    "id": "phase_2",
                    "title": "Move",
                    "order": 2,
                    "steps": [
                        {
                            "id": "step_3",
                            "title": "Hire movers",
                            "order": 1,
                            "parallel": True,
                            "priority": 2,
                        },
                        {
                            "id": "step_4",
                            "title": "Unload truck",
                            "order": 2,
                            "parallel": True,
                            "priority": 2,
                        },
                    ],
                },
            ],
        },
    }
    apply_ingest(db, user, json.dumps(payload), ui_confirm_destructive=False)
    db.commit()
    db.refresh(step)
    db.refresh(epic)
    assert step.completed is True
    assert step.title == "Pack kitchen (done)"
    assert epic.title == "Apartment move — renamed"
    assert epic.identity_end == "Homebody"
