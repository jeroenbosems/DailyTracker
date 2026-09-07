from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.chests import chest_snapshot, ensure_default_chests, period_key, record_completion
from app.database import Base
from app.epics_logic import act_progress, complete_bit, current_act, epic_progress, next_bit
from app.models import Act, Bit, Epic, User
from app.auth import hash_password


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
    act1 = Act(epic_id=epic.id, title="Pack", sort_order=0, deliverable="Boxes labeled")
    act2 = Act(epic_id=epic.id, title="Move", sort_order=1, deliverable="Furniture placed")
    db.add_all([act1, act2])
    db.flush()
    db.add_all(
        [
            Bit(act_id=act1.id, title="Pack kitchen", sort_order=0),
            Bit(act_id=act1.id, title="Pack books", sort_order=1),
            Bit(act_id=act2.id, title="Hire movers", sort_order=0),
            Bit(act_id=act2.id, title="Unload truck", sort_order=1),
        ]
    )
    db.commit()
    db.refresh(epic)
    # reload relationships
    _ = epic.acts
    for a in epic.acts:
        _ = a.bits
    return epic


def test_epic_progress_and_next_bit_order():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)

    done, total, pct = epic_progress(epic)
    assert total == 4
    assert done == 0
    assert pct == 0.0

    act = current_act(epic)
    assert act is not None
    assert act.title == "Pack"
    bit = next_bit(epic)
    assert bit is not None
    assert bit.title == "Pack kitchen"

    complete_bit(db, user, bit)
    db.commit()
    db.refresh(epic)

    bit2 = next_bit(epic)
    assert bit2 is not None
    assert bit2.title == "Pack books"

    adone, atotal, apct = act_progress(act)
    assert adone == 1 and atotal == 2 and apct == 50.0

    done, total, pct = epic_progress(epic)
    assert done == 1 and total == 4 and pct == 25.0
    assert epic.preview_unlocked is True


def test_complete_act_then_advance_to_next_act():
    db = _session()
    user = _user(db)
    epic = _sample_epic(db, user)

    # Finish first act
    for title in ("Pack kitchen", "Pack books"):
        bit = next_bit(epic)
        assert bit.title == title
        complete_bit(db, user, bit)
        db.commit()

    act = current_act(epic)
    assert act is not None
    assert act.title == "Move"
    assert next_bit(epic).title == "Hire movers"

    # Finish epic
    while (b := next_bit(epic)) is not None:
        complete_bit(db, user, b)
        db.commit()

    assert epic.completed is True
    assert current_act(epic) is None
    assert next_bit(epic) is None
    _, _, pct = epic_progress(epic)
    assert pct == 100.0


def test_soft_chest_behavior_per_period():
    db = _session()
    user = _user(db)
    ensure_default_chests(db, user)

    day1 = date(2026, 3, 10)
    # Need 3 for daily bonus
    flashes = []
    for _ in range(3):
        flashes.extend(record_completion(db, user, day1))
    db.commit()
    assert any("Daily bonus" in f for f in flashes)

    snap = chest_snapshot(db, user, day1)
    daily = next(s for s in snap if s["period"] == "daily")
    assert daily["completions"] == 3
    assert daily["chest_granted"] is True
    assert daily["glory_granted"] is False

    # Soft streak: a different day starts a fresh period key — prior progress untouched
    day2 = day1 + timedelta(days=1)
    assert period_key("daily", day1) != period_key("daily", day2)
    snap2 = chest_snapshot(db, user, day2)
    daily2 = next(s for s in snap2 if s["period"] == "daily")
    assert daily2["completions"] == 0
    assert daily2["chest_granted"] is False

    # Prior day snapshot still granted
    snap1_again = chest_snapshot(db, user, day1)
    daily1_again = next(s for s in snap1_again if s["period"] == "daily")
    assert daily1_again["completions"] == 3
    assert daily1_again["chest_granted"] is True

    # Glory at max (5)
    for _ in range(2):
        record_completion(db, user, day1)
    db.commit()
    snap_max = chest_snapshot(db, user, day1)
    daily_max = next(s for s in snap_max if s["period"] == "daily")
    assert daily_max["completions"] == 5
    assert daily_max["glory_granted"] is True

    # Further completions do not inflate past max
    record_completion(db, user, day1)
    db.commit()
    assert chest_snapshot(db, user, day1)[0]["completions"] == 5
