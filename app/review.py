"""v0.9 — read-only weekly review snapshot."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.epics_logic import epic_progress, next_step
from app.models import Epic, Phase, RewardLog, Routine, Step, Task, User
from app.period_bonuses import ensure_default_period_bonuses, period_bonus_snapshot


def week_bounds(day: date | None = None) -> tuple[date, date, str]:
    """ISO week Mon–Sun containing day. Returns (start, end, label)."""
    day = day or date.today()
    iso = day.isocalendar()
    start = date.fromisocalendar(iso.year, iso.week, 1)
    end = start + timedelta(days=6)
    label = f"{iso.year}-W{iso.week:02d}"
    return start, end, label


def _in_week(dt: datetime | date | None, start: date, end: date) -> bool:
    if dt is None:
        return False
    if isinstance(dt, datetime):
        d = dt.astimezone(timezone.utc).date() if dt.tzinfo else dt.date()
    else:
        d = dt
    return start <= d <= end


def build_weekly_review(db: Session, user: User, day: date | None = None) -> dict:
    ensure_default_period_bonuses(db, user)
    start, end, label = week_bounds(day)
    day = day or date.today()

    tasks = [
        t
        for t in db.scalars(select(Task).where(Task.user_id == user.id, Task.completed.is_(True))).all()
        if _in_week(t.completed_at, start, end)
    ]
    tasks.sort(key=lambda t: t.completed_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    routines = [
        r
        for r in db.scalars(select(Routine).where(Routine.user_id == user.id)).all()
        if _in_week(r.last_completed_on, start, end)
    ]
    routines.sort(key=lambda r: r.last_completed_on or date.min, reverse=True)

    steps: list[Step] = []
    for epic in db.scalars(
        select(Epic)
        .where(Epic.user_id == user.id)
        .options(joinedload(Epic.phases).joinedload(Phase.steps))
    ).unique().all():
        for ph in epic.phases:
            for st in ph.steps:
                if st.completed and _in_week(st.completed_at, start, end):
                    steps.append(st)
    steps.sort(key=lambda s: s.completed_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    rewards = [
        rw
        for rw in db.scalars(select(RewardLog).where(RewardLog.user_id == user.id)).all()
        if _in_week(rw.created_at, start, end)
    ]
    points_earned = sum(rw.points for rw in rewards)

    active = None
    active_pct = 0.0
    active_done = 0
    active_total = 0
    active_next = None
    if user.active_epic_id:
        active = db.scalar(
            select(Epic)
            .where(Epic.id == user.active_epic_id, Epic.user_id == user.id)
            .options(joinedload(Epic.phases).joinedload(Phase.steps))
        )
        if active:
            active_done, active_total, active_pct = epic_progress(active)
            active_next = next_step(active)

    return {
        "week_label": label,
        "week_start": start,
        "week_end": end,
        "tasks": tasks,
        "routines": routines,
        "steps": steps,
        "points_earned": points_earned,
        "reward_count": len(rewards),
        "period_bonuses": period_bonus_snapshot(db, user, day),
        "active_epic": active,
        "active_pct": active_pct,
        "active_done": active_done,
        "active_total": active_total,
        "active_next": active_next,
    }
