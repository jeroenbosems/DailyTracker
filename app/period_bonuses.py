from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PeriodBonusDef, PeriodBonusProgress, User
from app.rewards import grant_fixed


def period_key(period: str, day: date) -> str:
    if period == "daily":
        return day.isoformat()
    # ISO week
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def ensure_default_period_bonuses(db: Session, user: User) -> None:
    existing = db.scalars(
        select(PeriodBonusDef).where(PeriodBonusDef.user_id == user.id)
    ).all()
    if existing:
        return
    db.add_all(
        [
            PeriodBonusDef(
                user_id=user.id,
                period="daily",
                need_count=3,
                max_count=5,
                reward_tier="bronze",
                reward_points=15,
                glory_tier="silver",
                glory_points=10,
                title="Daily Period bonus",
            ),
            PeriodBonusDef(
                user_id=user.id,
                period="weekly",
                need_count=10,
                max_count=15,
                reward_tier="silver",
                reward_points=60,
                glory_tier="gold",
                glory_points=30,
                title="Weekly Period bonus",
            ),
        ]
    )
    db.commit()


def _get_progress(
    db: Session, user: User, bonus_def: PeriodBonusDef, day: date
) -> PeriodBonusProgress:
    key = period_key(bonus_def.period, day)
    row = db.scalar(
        select(PeriodBonusProgress).where(
            PeriodBonusProgress.user_id == user.id,
            PeriodBonusProgress.period_bonus_def_id == bonus_def.id,
            PeriodBonusProgress.period_key == key,
        )
    )
    if row:
        return row
    row = PeriodBonusProgress(
        user_id=user.id,
        period_bonus_def_id=bonus_def.id,
        period_key=key,
        completions=0,
    )
    db.add(row)
    db.flush()
    return row


def record_completion(db: Session, user: User, day: date | None = None) -> list[str]:
    """Soft streak: missing a period simply means no grant — progress never wiped."""
    day = day or date.today()
    ensure_default_period_bonuses(db, user)
    flashes: list[str] = []
    defs = db.scalars(
        select(PeriodBonusDef).where(PeriodBonusDef.user_id == user.id)
    ).all()
    for bonus_def in defs:
        prog = _get_progress(db, user, bonus_def, day)
        if prog.completions >= bonus_def.max_count:
            continue
        prog.completions += 1
        if prog.completions >= bonus_def.need_count and not prog.bonus_granted:
            grant_fixed(
                db,
                user,
                bonus_def.reward_tier,
                bonus_def.reward_points,
                f"{bonus_def.title} ({bonus_def.period})",
            )
            prog.bonus_granted = True
            flashes.append(f"{bonus_def.title} earned (+{bonus_def.reward_points})")
        if (
            bonus_def.glory_tier
            and prog.completions >= bonus_def.max_count
            and not prog.glory_granted
        ):
            grant_fixed(
                db,
                user,
                bonus_def.glory_tier,
                bonus_def.glory_points,
                f"{bonus_def.title} glory ({bonus_def.period})",
            )
            prog.glory_granted = True
            flashes.append(f"{bonus_def.title} glory (+{bonus_def.glory_points})")
    return flashes


def period_bonus_snapshot(db: Session, user: User, day: date | None = None) -> list[dict]:
    day = day or date.today()
    ensure_default_period_bonuses(db, user)
    out = []
    for bonus_def in db.scalars(
        select(PeriodBonusDef).where(PeriodBonusDef.user_id == user.id)
    ).all():
        prog = _get_progress(db, user, bonus_def, day)
        out.append(
            {
                "title": bonus_def.title,
                "period": bonus_def.period,
                "need": bonus_def.need_count,
                "max": bonus_def.max_count,
                "completions": prog.completions,
                "bonus_granted": prog.bonus_granted,
                "glory_granted": prog.glory_granted,
                "reward_points": bonus_def.reward_points,
            }
        )
    return out
