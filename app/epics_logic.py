from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Epic, Phase, Step, User
from app.rewards import grant_fixed, grant_reward

PATH_FULL = "full"
PATH_FOCUSED = "focused"
ALLOWED_PATHS = {PATH_FULL, PATH_FOCUSED}
FOCUSED_KEEP_PHASES = 2
FULL_SUGGESTED_PHASES = 3


def normalize_path(raw: str | None) -> str:
    value = (raw or PATH_FULL).strip().lower()
    if value not in ALLOWED_PATHS:
        raise ValueError('path must be "full" or "focused".')
    return value


def active_phases(epic: Epic) -> list[Phase]:
    """Phases that count for Today / next Step / progress (skip parked)."""
    return sorted(
        (p for p in epic.phases if not getattr(p, "parked", False)),
        key=lambda p: p.sort_order,
    )


def phase_progress(phase: Phase) -> tuple[int, int, float]:
    steps = phase.steps
    total = len(steps)
    done = sum(1 for s in steps if s.completed)
    pct = (done / total * 100.0) if total else 0.0
    return done, total, pct


def epic_progress(epic: Epic) -> tuple[int, int, float]:
    steps = [s for p in active_phases(epic) for s in p.steps]
    total = len(steps)
    done = sum(1 for s in steps if s.completed)
    pct = (done / total * 100.0) if total else 0.0
    return done, total, pct


def current_phase(epic: Epic) -> Phase | None:
    for phase in active_phases(epic):
        if not phase.completed:
            return phase
    return None


def next_step(epic: Epic) -> Step | None:
    phase = current_phase(epic)
    if not phase:
        return None
    for step in sorted(phase.steps, key=lambda s: (s.completed, s.sort_order, s.id)):
        if not step.completed:
            return step
    return None



def next_step_for_mode(epic: Epic, mode_filter: str | None, matches_fn) -> Step | None:
    """Next incomplete Step in Active Epic that passes life-mode filter (tagged match or untagged)."""
    for phase in sorted(active_phases(epic), key=lambda p: p.sort_order):
        for step in sorted(phase.steps, key=lambda s: (s.completed, s.sort_order, s.id)):
            if step.completed:
                continue
            if matches_fn(getattr(step, "life_mode", None), mode_filter):
                return step
    return None


def _phase_has_completed_progress(phase: Phase) -> bool:
    if phase.completed:
        return True
    return any(s.completed for s in phase.steps)


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
        grant_fixed(db, user, "gold", 75, f"Phase complete: {phase.title}")
        flash_parts.append(f"Phase complete: {phase.title}")
        if phase.deliverable:
            flash_parts.append(f"Deliverable: {phase.deliverable}")

    epic = phase.epic
    _, _, overall = epic_progress(epic)
    if epic.preview_label and not epic.preview_unlocked and overall >= 25.0:
        epic.preview_unlocked = True
        flash_parts.append(f"Preview unlocked: {epic.preview_label}")

    active = active_phases(epic)
    if active and all(p.completed for p in active) and not epic.completed:
        epic.completed = True
        epic.completed_at = datetime.now(timezone.utc)
        grant_fixed(db, user, "gold", 150, f"Epic unlocked: {epic.title}")
        flash_parts.append(f"Epic unlocked: {epic.title}")

    return " · ".join(flash_parts)


def switch_epic_path(
    db: Session,
    epic: Epic,
    new_path: str,
    *,
    confirm_destructive: bool = False,
) -> str:
    """Switch Full ↔ Focused without silent progress loss.

    Focused→Full: unpark all; add missing Phases/Steps toward a fuller structure.
    Full→Focused: park non-focused Phases (keep first FOCUSED_KEEP_PHASES);
    with confirm_destructive, remove incomplete extras instead of parking them.
    """
    new_path = normalize_path(new_path)
    old = normalize_path(getattr(epic, "path", None) or PATH_FULL)
    if new_path == old and new_path == PATH_FOCUSED and not confirm_destructive:
        # Still allow re-apply park semantics if already focused
        pass

    if new_path == PATH_FOCUSED:
        return _switch_to_focused(db, epic, confirm_destructive=confirm_destructive)
    return _switch_to_full(db, epic)


def _switch_to_focused(
    db: Session, epic: Epic, *, confirm_destructive: bool
) -> str:
    epic.path = PATH_FOCUSED
    phases = sorted(epic.phases, key=lambda p: (p.sort_order, p.id))
    keep = phases[:FOCUSED_KEEP_PHASES]
    extras = phases[FOCUSED_KEEP_PHASES:]
    for p in keep:
        p.parked = False

    parked_n = 0
    removed_n = 0
    for phase in extras:
        if confirm_destructive and not _phase_has_completed_progress(phase):
            db.delete(phase)
            removed_n += 1
        else:
            phase.parked = True
            parked_n += 1

    db.flush()
    parts = [f"Path set to Focused (keeping {len(keep)} Phase(s) in focus)"]
    if parked_n:
        parts.append(f"parked {parked_n} Phase(s)")
    if removed_n:
        parts.append(f"removed {removed_n} incomplete Phase(s)")
    if extras and not confirm_destructive and any(
        not _phase_has_completed_progress(p) for p in extras
    ):
        parts.append("incomplete extras were parked (use confirm to remove)")
    return " · ".join(parts)


def _switch_to_full(db: Session, epic: Epic) -> str:
    epic.path = PATH_FULL
    for phase in list(epic.phases):
        phase.parked = False
    db.flush()

    phases = sorted(epic.phases, key=lambda p: (p.sort_order, p.id))
    added_phases = 0
    next_order = (max((p.sort_order for p in phases), default=-1) + 1)
    while len(phases) + added_phases < FULL_SUGGESTED_PHASES:
        phase = Phase(
            epic_id=epic.id,
            title=f"Full path · Chapter {len(phases) + added_phases + 1}",
            sort_order=next_order,
            deliverable="Usable outcome for this chapter",
            parked=False,
        )
        db.add(phase)
        db.flush()
        db.add(
            Step(
                phase_id=phase.id,
                title="Define remaining high-value work",
                sort_order=0,
                parallel=True,
            )
        )
        db.add(
            Step(
                phase_id=phase.id,
                title="Complete the next concrete deliverable",
                sort_order=1,
                parallel=True,
            )
        )
        next_order += 1
        added_phases += 1

    # Re-open Epic if newly active phases are incomplete
    db.refresh(epic)
    active = active_phases(epic)
    if epic.completed and active and any(not p.completed for p in active):
        epic.completed = False
        epic.completed_at = None

    parts = ["Path set to Full · all Phases unparked"]
    if added_phases:
        parts.append(f"added {added_phases} Phase(s) with starter Steps")
    else:
        parts.append("no Phases removed; progress preserved")
    return " · ".join(parts)
