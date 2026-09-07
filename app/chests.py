from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChestDef, ChestProgress, User
from app.rewards import grant_fixed


def period_key(period: str, day: date) -> str:
    if period == "daily":
        return day.isoformat()
    # ISO week
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def ensure_default_chests(db: Session, user: User) -> None:
    existing = db.scalars(select(ChestDef).where(ChestDef.user_id == user.id)).all()
    if existing:
        return
    db.add_all(
        [
            ChestDef(
                user_id=user.id,
                period="daily",
                need_count=3,
                max_count=5,
                reward_tier="bronze",
                reward_points=15,
                glory_tier="silver",
                glory_points=10,
                title="Daily bonus",
            ),
            ChestDef(
                user_id=user.id,
                period="weekly",
                need_count=10,
                max_count=15,
                reward_tier="silver",
                reward_points=60,
                glory_tier="gold",
                glory_points=30,
                title="Weekly bonus",
            ),
        ]
    )
    db.commit()


def _get_progress(db: Session, user: User, chest: ChestDef, day: date) -> ChestProgress:
    key = period_key(chest.period, day)
    row = db.scalar(
        select(ChestProgress).where(
            ChestProgress.user_id == user.id,
            ChestProgress.chest_def_id == chest.id,
            ChestProgress.period_key == key,
        )
    )
    if row:
        return row
    row = ChestProgress(
        user_id=user.id,
        chest_def_id=chest.id,
        period_key=key,
        completions=0,
    )
    db.add(row)
    db.flush()
    return row


def record_completion(db: Session, user: User, day: date | None = None) -> list[str]:
    """Soft streak: missing a period simply means no grant — progress never wiped."""
    day = day or date.today()
    ensure_default_chests(db, user)
    flashes: list[str] = []
    chests = db.scalars(select(ChestDef).where(ChestDef.user_id == user.id)).all()
    for chest in chests:
        prog = _get_progress(db, user, chest, day)
        if prog.completions >= chest.max_count:
            continue
        prog.completions += 1
        if prog.completions >= chest.need_count and not prog.chest_granted:
            grant_fixed(
                db,
                user,
                chest.reward_tier,
                chest.reward_points,
                f"{chest.title} ({chest.period})",
            )
            prog.chest_granted = True
            flashes.append(f"{chest.title} opened (+{chest.reward_points})")
        if (
            chest.glory_tier
            and prog.completions >= chest.max_count
            and not prog.glory_granted
        ):
            grant_fixed(
                db,
                user,
                chest.glory_tier,
                chest.glory_points,
                f"{chest.title} glory ({chest.period})",
            )
            prog.glory_granted = True
            flashes.append(f"{chest.title} glory (+{chest.glory_points})")
    return flashes


def chest_snapshot(db: Session, user: User, day: date | None = None) -> list[dict]:
    day = day or date.today()
    ensure_default_chests(db, user)
    out = []
    for chest in db.scalars(select(ChestDef).where(ChestDef.user_id == user.id)).all():
        prog = _get_progress(db, user, chest, day)
        out.append(
            {
                "title": chest.title,
                "period": chest.period,
                "need": chest.need_count,
                "max": chest.max_count,
                "completions": prog.completions,
                "chest_granted": prog.chest_granted,
                "glory_granted": prog.glory_granted,
                "reward_points": chest.reward_points,
            }
        )
    return out
