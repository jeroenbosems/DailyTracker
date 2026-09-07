from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import REWARD_TIERS
from app.models import RewardLog, User


def tier_for_priority(priority: int) -> str:
    if priority <= 1:
        return "gold"
    if priority == 2:
        return "silver"
    return "bronze"


def grant_reward(db: Session, user: User, priority: int, reason: str) -> RewardLog:
    tier_key = tier_for_priority(priority)
    tier = REWARD_TIERS[tier_key]
    return grant_fixed(db, user, tier_key, tier["points"], reason)


def grant_fixed(db: Session, user: User, tier_key: str, points: int, reason: str) -> RewardLog:
    log = RewardLog(
        user_id=user.id,
        tier=tier_key,
        points=points,
        reason=reason,
    )
    user.total_points += points
    db.add(log)
    return log
