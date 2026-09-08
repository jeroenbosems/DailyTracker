"""v0.7 — authenticated JSON export / restore (no cloud sync)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Epic, Phase, Redemption, RewardLog, Routine, Step, Task, User, WatchItem

SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = {1}
REPLACE_CONFIRM_PHRASE = "REPLACE"


class BackupError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value.isoformat()


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw[:10])


def _ensure_external_id(obj: Any, prefix: str) -> str:
    eid = getattr(obj, "external_id", None)
    if eid:
        return eid
    eid = f"{prefix}-{uuid.uuid4().hex[:12]}"
    obj.external_id = eid
    return eid


def build_export(db: Session, user: User) -> dict[str, Any]:
    """Build export payload. Never includes password_hash or session secrets."""
    tasks = list(db.scalars(select(Task).where(Task.user_id == user.id)).all())
    routines = list(db.scalars(select(Routine).where(Routine.user_id == user.id)).all())
    epics = list(
        db.scalars(
            select(Epic)
            .where(Epic.user_id == user.id)
            .options(joinedload(Epic.phases).joinedload(Phase.steps))
        )
        .unique()
        .all()
    )
    rewards = list(
        db.scalars(select(RewardLog).where(RewardLog.user_id == user.id).order_by(RewardLog.id)).all()
    )
    redemptions = list(
        db.scalars(select(Redemption).where(Redemption.user_id == user.id).order_by(Redemption.id)).all()
    )

    # Stable ids for round-trip merge
    for t in tasks:
        _ensure_external_id(t, "task")
    for r in routines:
        _ensure_external_id(r, "routine")
    for e in epics:
        _ensure_external_id(e, "epic")
        for ph in e.phases:
            _ensure_external_id(ph, "phase")
            for st in ph.steps:
                _ensure_external_id(st, "step")
    for rw in rewards:
        _ensure_external_id(rw, "reward")
    for rd in redemptions:
        _ensure_external_id(rd, "redemption")
    db.flush()

    epic_by_id = {e.id: e for e in epics}
    active_ext = None
    if user.active_epic_id and user.active_epic_id in epic_by_id:
        active_ext = epic_by_id[user.active_epic_id].external_id

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "username": user.username,
            "total_points": user.total_points,
            "active_epic_external_id": active_ext,
            # intentionally omit password_hash / session secrets
        },
        "tasks": [
            {
                "external_id": t.external_id,
                "title": t.title,
                "notes": t.notes,
                "priority": t.priority,
                "due_date": _iso(t.due_date),
                "life_mode": t.life_mode,
                "completed": t.completed,
                "completed_at": _iso(t.completed_at),
                "created_at": _iso(t.created_at),
            }
            for t in tasks
        ],
        "routines": [
            {
                "external_id": r.external_id,
                "title": r.title,
                "notes": r.notes,
                "cadence": r.cadence,
                "priority": r.priority,
                "life_mode": r.life_mode,
                "streak": r.streak,
                "best_streak": r.best_streak,
                "completion_count": r.completion_count,
                "last_completed_on": _iso(r.last_completed_on),
                "next_due_on": _iso(r.next_due_on),
                "created_at": _iso(r.created_at),
            }
            for r in routines
        ],
        "epics": [],
        "reward_logs": [
            {
                "external_id": rw.external_id,
                "tier": rw.tier,
                "points": rw.points,
                "reason": rw.reason,
                "created_at": _iso(rw.created_at),
            }
            for rw in rewards
        ],
        "redemptions": [
            {
                "external_id": rd.external_id,
                "catalog_id": rd.catalog_id,
                "points_spent": rd.points_spent,
                "created_at": _iso(rd.created_at),
                "fulfilled_irl": rd.fulfilled_irl,
            }
            for rd in redemptions
        ],
    }

    for e in sorted(epics, key=lambda x: x.id):
        parent_ext = None
        if e.parent_epic_id and e.parent_epic_id in epic_by_id:
            parent_ext = epic_by_id[e.parent_epic_id].external_id
        follows_ext = None
        if e.follows_epic_id and e.follows_epic_id in epic_by_id:
            follows_ext = epic_by_id[e.follows_epic_id].external_id
        epic_blob: dict[str, Any] = {
            "external_id": e.external_id,
            "parent_external_id": parent_ext,
            "follows_external_id": follows_ext,
            "title": e.title,
            "notes": e.notes,
            "legendary": e.legendary,
            "identity_end": e.identity_end,
            "capability_end": e.capability_end,
            "preview_label": e.preview_label,
            "preview_unlocked": e.preview_unlocked,
            "path": e.path,
            "life_modes": e.life_modes,
            "completed": e.completed,
            "completed_at": _iso(e.completed_at),
            "created_at": _iso(e.created_at),
            "phases": [],
        }
        for ph in sorted(e.phases, key=lambda p: (p.sort_order, p.id)):
            phase_blob = {
                "external_id": ph.external_id,
                "title": ph.title,
                "sort_order": ph.sort_order,
                "deliverable": ph.deliverable,
                "parked": ph.parked,
                "completed": ph.completed,
                "completed_at": _iso(ph.completed_at),
                "steps": [],
            }
            for st in sorted(ph.steps, key=lambda s: (s.sort_order, s.id)):
                phase_blob["steps"].append(
                    {
                        "external_id": st.external_id,
                        "title": st.title,
                        "sort_order": st.sort_order,
                        "parallel": st.parallel,
                        "priority": st.priority,
                        "life_mode": st.life_mode,
                        "completed": st.completed,
                        "completed_at": _iso(st.completed_at),
                    }
                )
            epic_blob["phases"].append(phase_blob)
        payload["epics"].append(epic_blob)

    # Sanity: never leak secrets
    dumped = json.dumps(payload)
    if "password_hash" in dumped or "session_secret" in dumped.lower():
        raise BackupError("Export refused: secret field leaked into payload.")
    return payload


def _wipe_user_data(db: Session, user: User) -> None:
    """Delete product data for user; keep account credentials."""
    # Watch first (no cascade from tasks)
    for w in list(db.scalars(select(WatchItem).where(WatchItem.user_id == user.id)).all()):
        db.delete(w)
    for r in list(db.scalars(select(Redemption).where(Redemption.user_id == user.id)).all()):
        db.delete(r)
    for r in list(db.scalars(select(RewardLog).where(RewardLog.user_id == user.id)).all()):
        db.delete(r)
    for e in list(db.scalars(select(Epic).where(Epic.user_id == user.id)).all()):
        db.delete(e)  # cascades phases/steps
    for t in list(db.scalars(select(Task).where(Task.user_id == user.id)).all()):
        db.delete(t)
    for r in list(db.scalars(select(Routine).where(Routine.user_id == user.id)).all()):
        db.delete(r)
    user.active_epic_id = None
    user.total_points = 0
    db.flush()


def _index_by_ext(rows: list[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        if row.external_id:
            out[row.external_id] = row
    return out


def apply_restore(
    db: Session,
    user: User,
    raw_json: str | bytes,
    *,
    mode: str,
    replace_confirm_text: str = "",
    replace_confirm_checked: bool = False,
) -> str:
    mode = (mode or "").strip().lower()
    if mode not in {"merge", "replace"}:
        raise BackupError("Mode must be merge or replace.")

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise BackupError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise BackupError("Backup root must be an object.")

    version = data.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise BackupError(
            f"Unknown or unsupported schema_version: {version!r}. "
            f"Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    if mode == "replace":
        if not replace_confirm_checked:
            raise BackupError("Replace requires the confirmation checkbox.")
        if (replace_confirm_text or "").strip() != REPLACE_CONFIRM_PHRASE:
            raise BackupError(
                f'Type {REPLACE_CONFIRM_PHRASE} exactly to confirm replace (wipe then import).'
            )
        _wipe_user_data(db, user)

    user_meta = data.get("user") or {}
    if isinstance(user_meta, dict) and "total_points" in user_meta and mode == "replace":
        try:
            user.total_points = int(user_meta["total_points"])
        except (TypeError, ValueError):
            raise BackupError("user.total_points must be an integer.") from None

    # --- tasks ---
    existing_tasks = _index_by_ext(
        list(db.scalars(select(Task).where(Task.user_id == user.id)).all())
    )
    for blob in data.get("tasks") or []:
        ext = (blob.get("external_id") or "").strip()
        if not ext:
            raise BackupError("Each task needs external_id.")
        if ext in existing_tasks:
            continue  # merge: create missing only
        task = Task(
            user_id=user.id,
            external_id=ext,
            title=(blob.get("title") or "Untitled").strip()[:200],
            notes=blob.get("notes"),
            priority=int(blob.get("priority") or 2),
            due_date=_parse_date(blob.get("due_date")),
            life_mode=blob.get("life_mode"),
            completed=bool(blob.get("completed")),
            completed_at=_parse_dt(blob.get("completed_at")),
        )
        db.add(task)
        existing_tasks[ext] = task

    # --- routines ---
    existing_routines = _index_by_ext(
        list(db.scalars(select(Routine).where(Routine.user_id == user.id)).all())
    )
    for blob in data.get("routines") or []:
        ext = (blob.get("external_id") or "").strip()
        if not ext:
            raise BackupError("Each routine needs external_id.")
        if ext in existing_routines:
            continue
        next_due = _parse_date(blob.get("next_due_on")) or date.today()
        routine = Routine(
            user_id=user.id,
            external_id=ext,
            title=(blob.get("title") or "Untitled").strip()[:200],
            notes=blob.get("notes"),
            cadence=(blob.get("cadence") or "daily").strip(),
            priority=int(blob.get("priority") or 2),
            life_mode=blob.get("life_mode"),
            streak=int(blob.get("streak") or 0),
            best_streak=int(blob.get("best_streak") or 0),
            completion_count=int(blob.get("completion_count") or 0),
            last_completed_on=_parse_date(blob.get("last_completed_on")),
            next_due_on=next_due,
        )
        db.add(routine)
        existing_routines[ext] = routine

    db.flush()

    # --- epics (two passes for parent/follows) ---
    existing_epics = _index_by_ext(
        list(
            db.scalars(
                select(Epic)
                .where(Epic.user_id == user.id)
                .options(joinedload(Epic.phases).joinedload(Phase.steps))
            )
            .unique()
            .all()
        )
    )

    epic_blobs = list(data.get("epics") or [])
    for blob in epic_blobs:
        ext = (blob.get("external_id") or "").strip()
        if not ext:
            raise BackupError("Each epic needs external_id.")
        if ext in existing_epics:
            epic = existing_epics[ext]
        else:
            epic = Epic(
                user_id=user.id,
                external_id=ext,
                title=(blob.get("title") or "Untitled").strip()[:200],
                notes=blob.get("notes"),
                legendary=bool(blob.get("legendary", True)),
                identity_end=blob.get("identity_end"),
                capability_end=blob.get("capability_end"),
                preview_label=blob.get("preview_label"),
                preview_unlocked=bool(blob.get("preview_unlocked")),
                path=(blob.get("path") or "full"),
                life_modes=blob.get("life_modes") or "[]",
                completed=bool(blob.get("completed")),
                completed_at=_parse_dt(blob.get("completed_at")),
            )
            db.add(epic)
            db.flush()
            existing_epics[ext] = epic

        # phases / steps
        phase_index = _index_by_ext(list(epic.phases))
        for ph_blob in blob.get("phases") or []:
            pext = (ph_blob.get("external_id") or "").strip()
            if not pext:
                raise BackupError("Each phase needs external_id.")
            if pext in phase_index:
                phase = phase_index[pext]
            else:
                phase = Phase(
                    epic_id=epic.id,
                    external_id=pext,
                    title=(ph_blob.get("title") or "Phase").strip()[:200],
                    sort_order=int(ph_blob.get("sort_order") or 0),
                    deliverable=ph_blob.get("deliverable"),
                    parked=bool(ph_blob.get("parked")),
                    completed=bool(ph_blob.get("completed")),
                    completed_at=_parse_dt(ph_blob.get("completed_at")),
                )
                db.add(phase)
                db.flush()
                phase_index[pext] = phase

            step_index = _index_by_ext(list(phase.steps))
            for st_blob in ph_blob.get("steps") or []:
                sext = (st_blob.get("external_id") or "").strip()
                if not sext:
                    raise BackupError("Each step needs external_id.")
                if sext in step_index:
                    step = step_index[sext]
                    # merge: never overwrite completed Steps
                    if step.completed:
                        continue
                    # incomplete existing: leave as-is (create-missing only for merge intent)
                    continue
                step = Step(
                    phase_id=phase.id,
                    external_id=sext,
                    title=(st_blob.get("title") or "Step").strip()[:200],
                    sort_order=int(st_blob.get("sort_order") or 0),
                    parallel=bool(st_blob.get("parallel", True)),
                    priority=int(st_blob.get("priority") or 2),
                    life_mode=st_blob.get("life_mode"),
                    completed=bool(st_blob.get("completed")),
                    completed_at=_parse_dt(st_blob.get("completed_at")),
                )
                db.add(step)
                step_index[sext] = step

    db.flush()

    # Link parent / follows by external_id
    for blob in epic_blobs:
        ext = (blob.get("external_id") or "").strip()
        epic = existing_epics.get(ext)
        if not epic:
            continue
        parent_ext = (blob.get("parent_external_id") or "").strip() or None
        follows_ext = (blob.get("follows_external_id") or "").strip() or None
        if parent_ext and parent_ext in existing_epics:
            epic.parent_epic_id = existing_epics[parent_ext].id
        if follows_ext and follows_ext in existing_epics:
            epic.follows_epic_id = existing_epics[follows_ext].id

    # --- reward logs ---
    existing_rewards = _index_by_ext(
        list(db.scalars(select(RewardLog).where(RewardLog.user_id == user.id)).all())
    )
    for blob in data.get("reward_logs") or []:
        ext = (blob.get("external_id") or "").strip()
        if not ext:
            raise BackupError("Each reward_log needs external_id.")
        if ext in existing_rewards:
            continue
        row = RewardLog(
            user_id=user.id,
            external_id=ext,
            tier=(blob.get("tier") or "bronze").strip(),
            points=int(blob.get("points") or 0),
            reason=(blob.get("reason") or "import")[:255],
            created_at=_parse_dt(blob.get("created_at")) or datetime.now(timezone.utc),
        )
        db.add(row)
        existing_rewards[ext] = row

    # --- redemptions ---
    existing_red = _index_by_ext(
        list(db.scalars(select(Redemption).where(Redemption.user_id == user.id)).all())
    )
    for blob in data.get("redemptions") or []:
        ext = (blob.get("external_id") or "").strip()
        if not ext:
            raise BackupError("Each redemption needs external_id.")
        if ext in existing_red:
            continue
        row = Redemption(
            user_id=user.id,
            external_id=ext,
            catalog_id=(blob.get("catalog_id") or "").strip()[:32],
            points_spent=int(blob.get("points_spent") or 0),
            created_at=_parse_dt(blob.get("created_at")) or datetime.now(timezone.utc),
            fulfilled_irl=bool(blob.get("fulfilled_irl")),
        )
        db.add(row)
        existing_red[ext] = row

    db.flush()

    if isinstance(user_meta, dict):
        active_ext = (user_meta.get("active_epic_external_id") or "").strip() or None
        if active_ext and active_ext in existing_epics:
            user.active_epic_id = existing_epics[active_ext].id

    db.flush()
    return f"Restore ({mode}) applied — schema_version {SCHEMA_VERSION}."
