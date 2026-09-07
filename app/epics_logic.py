from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Epic, Phase, Step, User
from app.rewards import grant_fixed, grant_reward


def phase_progress(phase: Phase) -> tuple[int, int, float]:
    steps = phase.steps
    total = len(steps)
    done = sum(1 for s in steps if s.completed)
    pct = (done / total * 100.0) if total else 0.0
    return done, total, pct


def epic_progress(epic: Epic) -> tuple[int, int, float]:
    steps = [s for p in epic.phases for s in p.steps]
    total = len(steps)
    done = sum(1 for s in steps if s.completed)
    pct = (done / total * 100.0) if total else 0.0
    return done, total, pct


def current_phase(epic: Epic) -> Phase | None:
    for phase in sorted(epic.phases, key=lambda p: p.sort_order):
        if not phase.completed:
            return phase
    return None


def next_step(epic: Epic) -> Step | None:
    phase = current_phase(epic)
    if not phase:
        return None
    # Prefer incomplete steps; parallel steps can be any order — use sort_order
    for step in sorted(phase.steps, key=lambda s: (s.completed, s.sort_order, s.id)):
        if not step.completed:
            return step
    return None


def complete_step(db: Session, user: User, step: Step) -> str:
    if step.completed:
        return "Already completed"
    step.completed = True
    step.completed_at = datetime.now(timezone.utc)
    grant_reward(db, user, step.priority, f"Step done: {step.title}")
    flash_parts = ["Step completed"]

    phase = step.phase
    done, total, _ = phase_progress(phase)
    if total and done == total and not phase.completed:
        phase.completed = True
        phase.completed_at = datetime.now(timezone.utc)
        grant_fixed(db, user, "silver", 40, f"Phase complete: {phase.title}")
        flash_parts.append(f"Phase complete: {phase.title}")
        if phase.deliverable:
            flash_parts.append(f"Deliverable: {phase.deliverable}")

    epic = phase.epic
    # Mid-journey preview unlock at >= 25% overall
    _, _, overall = epic_progress(epic)
    if epic.preview_label and not epic.preview_unlocked and overall >= 25.0:
        epic.preview_unlocked = True
        flash_parts.append(f"Preview unlocked: {epic.preview_label}")

    if all(p.completed for p in epic.phases) and epic.phases and not epic.completed:
        epic.completed = True
        epic.completed_at = datetime.now(timezone.utc)
        grant_fixed(db, user, "gold", 100, f"Epic unlocked: {epic.title}")
        flash_parts.append(f"Epic unlocked: {epic.title}")

    return " · ".join(flash_parts)
