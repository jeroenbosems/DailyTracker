"""v0.3.1 — Watch cap, nearly-done eligibility, rewards page data."""

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Epic, Phase, RewardLog, Step, Task, User, WatchItem
from app.watch_logic import (
    WATCH_CAP,
    WatchFullError,
    build_watch_board,
    is_nearly_done_step,
    nearly_done_candidates,
    pin_item,
    unpin_item,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session) -> User:
    user = User(username="watcher", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _epic_with_steps(
    db: Session,
    user: User,
    title: str,
    phase_step_counts: list[int],
    *,
    activate: bool = False,
) -> Epic:
    epic = Epic(user_id=user.id, title=title, legendary=True)
    db.add(epic)
    db.flush()
    for pi, n in enumerate(phase_step_counts):
        phase = Phase(epic_id=epic.id, title=f"{title}-P{pi}", sort_order=pi)
        db.add(phase)
        db.flush()
        for si in range(n):
            db.add(
                Step(
                    phase_id=phase.id,
                    title=f"{title}-P{pi}-S{si}",
                    sort_order=si,
                )
            )
    if activate:
        user.active_epic_id = epic.id
    db.commit()
    db.refresh(epic)
    _ = epic.phases
    for p in epic.phases:
        _ = p.steps
    return epic


def test_watch_pin_cap_six():
    db = _session()
    user = _user(db)
    tasks = []
    for i in range(WATCH_CAP + 1):
        t = Task(user_id=user.id, title=f"T{i}", priority=2)
        db.add(t)
        tasks.append(t)
    db.commit()
    for t in tasks[:WATCH_CAP]:
        db.refresh(t)
        pin_item(db, user, "task", t.id)
    db.commit()
    assert len(db.scalars(select(WatchItem).where(WatchItem.user_id == user.id)).all()) == 6
    db.refresh(tasks[WATCH_CAP])
    try:
        pin_item(db, user, "task", tasks[WATCH_CAP].id)
        assert False, "expected WatchFullError"
    except WatchFullError as exc:
        assert "max 6" in exc.message.lower() or "full" in exc.message.lower()


def test_nearly_done_last_incomplete_in_phase():
    db = _session()
    user = _user(db)
    epic = _epic_with_steps(db, user, "Move", [3, 2], activate=True)
    phase = sorted(epic.phases, key=lambda p: p.sort_order)[0]
    steps = sorted(phase.steps, key=lambda s: s.sort_order)
    # complete first two → last incomplete is nearly done
    steps[0].completed = True
    steps[1].completed = True
    db.commit()
    assert is_nearly_done_step(steps[2]) is True
    assert is_nearly_done_step(steps[0]) is False  # completed


def test_nearly_done_phase_progress_at_least_80():
    db = _session()
    user = _user(db)
    # 5 steps: complete 4 → 80% → remaining incomplete qualifies
    epic = _epic_with_steps(db, user, "Desk", [5], activate=True)
    phase = epic.phases[0]
    steps = sorted(phase.steps, key=lambda s: s.sort_order)
    for s in steps[:4]:
        s.completed = True
    db.commit()
    assert is_nearly_done_step(steps[4]) is True
    # 3/5 = 60% and more than one incomplete → not nearly done for remaining
    for s in steps:
        s.completed = False
    for s in steps[:3]:
        s.completed = True
    db.commit()
    remaining = [s for s in steps if not s.completed]
    assert len(remaining) == 2
    assert all(not is_nearly_done_step(s) for s in remaining)


def test_nearly_done_prefers_active_epic_and_dedupes_pins():
    db = _session()
    user = _user(db)
    parked = _epic_with_steps(db, user, "Parked", [2], activate=False)
    active = _epic_with_steps(db, user, "Active", [2], activate=True)
    # Make last incomplete in each first phase
    for epic in (parked, active):
        phase = sorted(epic.phases, key=lambda p: p.sort_order)[0]
        steps = sorted(phase.steps, key=lambda s: s.sort_order)
        steps[0].completed = True
        db.commit()
    active_last = sorted(active.phases[0].steps, key=lambda s: s.sort_order)[1]
    parked_last = sorted(parked.phases[0].steps, key=lambda s: s.sort_order)[1]
    cands = nearly_done_candidates(db, user, exclude=set())
    assert cands[0].id == active_last.id
    assert {c.id for c in cands} == {active_last.id, parked_last.id}

    pin_item(db, user, "step", active_last.id)
    db.commit()
    cands2 = nearly_done_candidates(db, user, exclude={("step", active_last.id)})
    assert all(c.id != active_last.id for c in cands2)

    board = build_watch_board(db, user)
    assert board[0].source == "pinned"
    assert board[0].ref_id == active_last.id
    assert any(r.source == "nearly" and r.ref_id == parked_last.id for r in board)


def test_completed_pins_dropped_from_board():
    db = _session()
    user = _user(db)
    task = Task(user_id=user.id, title="Done soon", priority=1)
    db.add(task)
    db.commit()
    db.refresh(task)
    pin_item(db, user, "task", task.id)
    db.commit()
    task.completed = True
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    board = build_watch_board(db, user)
    assert all(r.ref_id != task.id for r in board)
    assert len(db.scalars(select(WatchItem).where(WatchItem.user_id == user.id)).all()) == 0


def test_rewards_page_data_newest_first():
    """Rewards page lists RewardLog chronologically (newest first)."""
    db = _session()
    user = _user(db)
    older = RewardLog(
        user_id=user.id,
        tier="bronze",
        points=10,
        reason="Older reward",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = RewardLog(
        user_id=user.id,
        tier="gold",
        points=50,
        reason="Newer reward",
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    mid = RewardLog(
        user_id=user.id,
        tier="silver",
        points=25,
        reason="Mid reward",
        created_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
    )
    db.add_all([older, newer, mid])
    user.total_points = 85
    db.commit()

    logs = db.scalars(
        select(RewardLog)
        .where(RewardLog.user_id == user.id)
        .order_by(RewardLog.created_at.desc(), RewardLog.id.desc())
    ).all()
    assert [r.reason for r in logs] == ["Newer reward", "Mid reward", "Older reward"]
    assert logs[0].tier == "gold" and logs[0].points == 50
    assert logs[-1].tier == "bronze" and logs[-1].points == 10


def test_unpin_frees_slot():
    db = _session()
    user = _user(db)
    tasks = []
    for i in range(WATCH_CAP):
        t = Task(user_id=user.id, title=f"U{i}", priority=2)
        db.add(t)
        tasks.append(t)
    db.commit()
    for t in tasks:
        db.refresh(t)
        pin_item(db, user, "task", t.id)
    db.commit()
    unpin_item(db, user, "task", tasks[0].id)
    db.commit()
    extra = Task(user_id=user.id, title="Extra", priority=1)
    db.add(extra)
    db.commit()
    db.refresh(extra)
    pin_item(db, user, "task", extra.id)
    db.commit()
    assert (
        len(db.scalars(select(WatchItem).where(WatchItem.user_id == user.id)).all())
        == WATCH_CAP
    )
