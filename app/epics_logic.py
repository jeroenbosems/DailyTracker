from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Act, Bit, Epic, User
from app.rewards import grant_fixed, grant_reward


def act_progress(act: Act) -> tuple[int, int, float]:
    bits = act.bits
    total = len(bits)
    done = sum(1 for b in bits if b.completed)
    pct = (done / total * 100.0) if total else 0.0
    return done, total, pct


def epic_progress(epic: Epic) -> tuple[int, int, float]:
    bits = [b for a in epic.acts for b in a.bits]
    total = len(bits)
    done = sum(1 for b in bits if b.completed)
    pct = (done / total * 100.0) if total else 0.0
    return done, total, pct


def current_act(epic: Epic) -> Act | None:
    for act in sorted(epic.acts, key=lambda a: a.sort_order):
        if not act.completed:
            return act
    return None


def next_bit(epic: Epic) -> Bit | None:
    act = current_act(epic)
    if not act:
        return None
    # Prefer incomplete bits; parallel bits can be any order — use sort_order
    for bit in sorted(act.bits, key=lambda b: (b.completed, b.sort_order, b.id)):
        if not bit.completed:
            return bit
    return None


def complete_bit(db: Session, user: User, bit: Bit) -> str:
    if bit.completed:
        return "Already completed"
    bit.completed = True
    bit.completed_at = datetime.now(timezone.utc)
    grant_reward(db, user, bit.priority, f"Story done: {bit.title}")
    flash_parts = ["Story completed"]

    act = bit.act
    done, total, _ = act_progress(act)
    if total and done == total and not act.completed:
        act.completed = True
        act.completed_at = datetime.now(timezone.utc)
        grant_fixed(db, user, "silver", 40, f"Act complete: {act.title}")
        flash_parts.append(f"Act unlocked: {act.title}")
        if act.deliverable:
            flash_parts.append(f"Deliverable: {act.deliverable}")

    epic = act.epic
    # Mid-journey preview unlock at >= 25% overall
    _, _, overall = epic_progress(epic)
    if epic.preview_label and not epic.preview_unlocked and overall >= 25.0:
        epic.preview_unlocked = True
        flash_parts.append(f"Preview unlocked: {epic.preview_label}")

    if all(a.completed for a in epic.acts) and epic.acts and not epic.completed:
        epic.completed = True
        epic.completed_at = datetime.now(timezone.utc)
        grant_fixed(db, user, "gold", 100, f"Epic unlocked: {epic.title}")
        flash_parts.append(f"Epic unlocked: {epic.title}")

    return " · ".join(flash_parts)
