from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.epics_logic import phase_progress
from app.models import Epic, Phase, Step, Task, User, WatchItem

WATCH_CAP = 6
KIND_STEP = "step"
KIND_TASK = "task"


class WatchFullError(Exception):
    """Raised when the user already has WATCH_CAP pinned items."""

    def __init__(self, message: str = "Watch is full (max 6 pinned). Unpin something first.") -> None:
        self.message = message
        super().__init__(message)


@dataclass
class WatchRow:
    source: str  # pinned | nearly
    kind: str  # step | task
    ref_id: int
    title: str
    priority: int
    meta: str
    href: str | None
    complete_action: str | None
    watch_id: int | None = None  # set for pinned rows


def _pin_count(db: Session, user: User) -> int:
    return len(db.scalars(select(WatchItem).where(WatchItem.user_id == user.id)).all())


def list_pins(db: Session, user: User) -> list[WatchItem]:
    return list(
        db.scalars(
            select(WatchItem)
            .where(WatchItem.user_id == user.id)
            .order_by(WatchItem.created_at.asc(), WatchItem.id.asc())
        ).all()
    )


def pin_item(db: Session, user: User, kind: str, ref_id: int) -> WatchItem:
    kind = kind.strip().lower()
    if kind not in {KIND_STEP, KIND_TASK}:
        raise ValueError("Invalid watch kind.")
    existing = db.scalar(
        select(WatchItem).where(
            WatchItem.user_id == user.id,
            WatchItem.kind == kind,
            WatchItem.ref_id == ref_id,
        )
    )
    if existing:
        return existing
    if _pin_count(db, user) >= WATCH_CAP:
        raise WatchFullError()
    if kind == KIND_STEP:
        step = db.get(Step, ref_id)
        if not step or step.phase.epic.user_id != user.id:
            raise ValueError("Step not found.")
        if step.completed:
            raise ValueError("Completed steps cannot be pinned.")
    else:
        task = db.get(Task, ref_id)
        if not task or task.user_id != user.id:
            raise ValueError("Task not found.")
        if task.completed:
            raise ValueError("Completed tasks cannot be pinned.")
    item = WatchItem(user_id=user.id, kind=kind, ref_id=ref_id)
    db.add(item)
    db.flush()
    return item


def unpin_item(db: Session, user: User, kind: str, ref_id: int) -> bool:
    kind = kind.strip().lower()
    item = db.scalar(
        select(WatchItem).where(
            WatchItem.user_id == user.id,
            WatchItem.kind == kind,
            WatchItem.ref_id == ref_id,
        )
    )
    if not item:
        return False
    db.delete(item)
    return True


def unpin_by_id(db: Session, user: User, watch_id: int) -> bool:
    item = db.get(WatchItem, watch_id)
    if not item or item.user_id != user.id:
        return False
    db.delete(item)
    return True


def cleanup_completed_pins(db: Session, user: User) -> int:
    """Drop pins whose Step/Task is completed or missing. Returns removed count."""
    removed = 0
    for pin in list_pins(db, user):
        drop = False
        if pin.kind == KIND_STEP:
            step = db.get(Step, pin.ref_id)
            drop = step is None or step.completed or step.phase.epic.user_id != user.id
        elif pin.kind == KIND_TASK:
            task = db.get(Task, pin.ref_id)
            drop = task is None or task.completed or task.user_id != user.id
        else:
            drop = True
        if drop:
            db.delete(pin)
            removed += 1
    return removed


def cleanup_ref(db: Session, user: User, kind: str, ref_id: int) -> None:
    unpin_item(db, user, kind, ref_id)


def is_nearly_done_step(step: Step) -> bool:
    """Incomplete Step is nearly done if last incomplete in Phase, or Phase ≥ 80%."""
    if step.completed:
        return False
    phase = step.phase
    incomplete = [s for s in phase.steps if not s.completed]
    if not incomplete:
        return False
    if len(incomplete) == 1 and incomplete[0].id == step.id:
        return True
    _, _, pct = phase_progress(phase)
    return pct >= 80.0


def _step_row(step: Step, source: str, watch_id: int | None = None) -> WatchRow:
    epic = step.phase.epic
    return WatchRow(
        source=source,
        kind=KIND_STEP,
        ref_id=step.id,
        title=step.title,
        priority=step.priority,
        meta=f"Step · {epic.title} · {step.phase.title}",
        href=f"/epics/{epic.id}",
        complete_action=f"/steps/{step.id}/complete",
        watch_id=watch_id,
    )


def _task_row(task: Task, source: str, watch_id: int | None = None) -> WatchRow:
    due = task.due_date.isoformat() if task.due_date else "no due date"
    return WatchRow(
        source=source,
        kind=KIND_TASK,
        ref_id=task.id,
        title=task.title,
        priority=task.priority,
        meta=f"Task · {due}",
        href=None,
        complete_action=f"/tasks/{task.id}/complete",
        watch_id=watch_id,
    )


def _load_user_epics(db: Session, user: User) -> list[Epic]:
    return list(
        db.scalars(
            select(Epic)
            .where(Epic.user_id == user.id, Epic.completed.is_(False))
            .options(joinedload(Epic.phases).joinedload(Phase.steps))
        )
        .unique()
        .all()
    )


def nearly_done_candidates(db: Session, user: User, exclude: set[tuple[str, int]]) -> list[Step]:
    """Incomplete nearly-done Steps; Active Epic first, then others. Deduped vs exclude."""
    epics = _load_user_epics(db, user)
    active_id = user.active_epic_id
    ordered = sorted(
        epics,
        key=lambda e: (0 if e.id == active_id else 1, e.id),
    )
    out: list[Step] = []
    seen: set[int] = set()
    for epic in ordered:
        for phase in sorted(epic.phases, key=lambda p: p.sort_order):
            if getattr(phase, "parked", False):
                continue
            for step in sorted(phase.steps, key=lambda s: (s.sort_order, s.id)):
                if step.completed or step.id in seen:
                    continue
                if (KIND_STEP, step.id) in exclude:
                    continue
                if is_nearly_done_step(step):
                    out.append(step)
                    seen.add(step.id)
    return out


def build_watch_board(db: Session, user: User) -> list[WatchRow]:
    """Pinned first (created order), then auto Nearly done filling to WATCH_CAP."""
    cleanup_completed_pins(db, user)
    db.flush()

    rows: list[WatchRow] = []
    pinned_keys: set[tuple[str, int]] = set()
    for pin in list_pins(db, user):
        if pin.kind == KIND_STEP:
            step = db.get(Step, pin.ref_id)
            if step and not step.completed and step.phase.epic.user_id == user.id:
                rows.append(_step_row(step, "pinned", watch_id=pin.id))
                pinned_keys.add((KIND_STEP, step.id))
        elif pin.kind == KIND_TASK:
            task = db.get(Task, pin.ref_id)
            if task and not task.completed and task.user_id == user.id:
                rows.append(_task_row(task, "pinned", watch_id=pin.id))
                pinned_keys.add((KIND_TASK, task.id))

    remaining = WATCH_CAP - len(rows)
    if remaining > 0:
        for step in nearly_done_candidates(db, user, pinned_keys)[:remaining]:
            rows.append(_step_row(step, "nearly"))
    return rows


def pinned_ref_set(db: Session, user: User) -> set[tuple[str, int]]:
    cleanup_completed_pins(db, user)
    return {(p.kind, p.ref_id) for p in list_pins(db, user)}
