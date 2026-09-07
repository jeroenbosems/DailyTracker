from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.epics_logic import (
    complete_step,
    current_phase,
    epic_progress,
    next_step,
    phase_progress,
)
from app.models import Epic, Phase, Step, User
from app.period_bonuses import (
    ensure_default_period_bonuses,
    period_bonus_snapshot,
    period_key,
    record_completion,
)


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


def _sample_epic(db: Session, user: User) -> Epic:
    epic = Epic(
        user_id=user.id,
        title="Apartment move",
        legendary=True,
        identity_end="Settled at home",
        capability_end="Keys in hand",
        preview_label="Trial week living as if moved",
    )
    db.add(epic)
    db.flush()
    phase1 = Phase(epic_id=epic.id, title="Pack", sort_order=0, deliverable="Boxes labeled")
    phase2 = Phase(epic_id=epic.id, title="Move", sort_order=1, deliverable="Furniture placed")
    db.add_all([phase1, phase2])
    db.flush()
    db.add_all(
        [
            Step(phase_id=phase1.id, title="Pack kitchen", sort_order=0),
            Step(phase_id=phase1.id, title="Pack books", sort_order=1),
            Step(phase_id=phase2.id, title="Hire movers", sort_order=0),
            Step(phase_id=phase2.id, title="Unload truck", sort_order=1),
        ]
    )
    db.commit()
    db.refresh(epic)
    # reload relationships
    _ = epic.phases
    for p in epic.phases:
        _ = p.steps
    return epic


def test_epic_progress_and_next_step_order():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)

    done, total, pct = epic_progress(epic)
    assert total == 4
    assert done == 0
    assert pct == 0.0

    phase = current_phase(epic)
    assert phase is not None
    assert phase.title == "Pack"
    step = next_step(epic)
    assert step is not None
    assert step.title == "Pack kitchen"

    complete_step(db, user, step)
    db.commit()
    db.refresh(epic)

    step2 = next_step(epic)
    assert step2 is not None
    assert step2.title == "Pack books"

    pdone, ptotal, ppct = phase_progress(phase)
    assert pdone == 1 and ptotal == 2 and ppct == 50.0

    done, total, pct = epic_progress(epic)
    assert done == 1 and total == 4 and pct == 25.0
    assert epic.preview_unlocked is True


def test_complete_phase_then_advance_to_next_phase():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)

    # Finish first phase
    for title in ("Pack kitchen", "Pack books"):
        step = next_step(epic)
        assert step.title == title
        complete_step(db, user, step)
        db.commit()

    phase = current_phase(epic)
    assert phase is not None
    assert phase.title == "Move"
    assert next_step(epic).title == "Hire movers"

    # Finish epic
    while (s := next_step(epic)) is not None:
        complete_step(db, user, s)
        db.commit()

    assert epic.completed is True
    assert current_phase(epic) is None
    assert next_step(epic) is None
    _, _, pct = epic_progress(epic)
    assert pct == 100.0


def test_soft_period_bonus_behavior_per_period():
    db = _session()
    user = _user(db)
    ensure_default_period_bonuses(db, user)

    day1 = date(2026, 3, 10)
    # Need 3 for daily Period bonus
    flashes = []
    for _ in range(3):
        flashes.extend(record_completion(db, user, day1))
    db.commit()
    assert any("Daily Period bonus" in f for f in flashes)

    snap = period_bonus_snapshot(db, user, day1)
    daily = next(s for s in snap if s["period"] == "daily")
    assert daily["completions"] == 3
    assert daily["bonus_granted"] is True
    assert daily["glory_granted"] is False

    # Soft streak: a different day starts a fresh period key — prior progress untouched
    day2 = day1 + timedelta(days=1)
    assert period_key("daily", day1) != period_key("daily", day2)
    snap2 = period_bonus_snapshot(db, user, day2)
    daily2 = next(s for s in snap2 if s["period"] == "daily")
    assert daily2["completions"] == 0
    assert daily2["bonus_granted"] is False

    # Prior day snapshot still granted
    snap1_again = period_bonus_snapshot(db, user, day1)
    daily1_again = next(s for s in snap1_again if s["period"] == "daily")
    assert daily1_again["completions"] == 3
    assert daily1_again["bonus_granted"] is True

    # Glory at max (5)
    for _ in range(2):
        record_completion(db, user, day1)
    db.commit()
    snap_max = period_bonus_snapshot(db, user, day1)
    daily_max = next(s for s in snap_max if s["period"] == "daily")
    assert daily_max["completions"] == 5
    assert daily_max["glory_granted"] is True

    # Further completions do not inflate past max
    record_completion(db, user, day1)
    db.commit()
    assert period_bonus_snapshot(db, user, day1)[0]["completions"] == 5
