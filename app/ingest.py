"""LLM JSON ingest for Epic → Phase → Step plans (R8.*)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.epics_logic import PATH_FULL, normalize_path
from app.life_modes import life_modes_to_json, normalize_life_mode, normalize_life_modes
from app.models import Epic, Phase, Step, User


class IngestError(Exception):
    """User-facing validation or apply failure (no stack traces)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


ALLOWED_MODES = {"new", "update"}
ALLOWED_STATUS = {"active", "parked", None}


def parse_ingest_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise IngestError("Paste JSON from your LLM plan before importing.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise IngestError("Invalid JSON — check braces, commas, and quotes.") from None
    if not isinstance(data, dict):
        raise IngestError("Top level must be a JSON object.")
    return data


def validate_ingest(data: dict[str, Any]) -> dict[str, Any]:
    mode = data.get("mode")
    if mode not in ALLOWED_MODES:
        raise IngestError('mode must be "new" or "update".')

    confirm_destructive = bool(data.get("confirm_destructive", False))

    epic = data.get("epic")
    if not isinstance(epic, dict):
        raise IngestError("epic object is required.")

    title = (epic.get("title") or "").strip() if isinstance(epic.get("title"), str) else ""
    if not title:
        raise IngestError("epic.title is required.")

    external_id = epic.get("id")
    if external_id is not None and not isinstance(external_id, str):
        raise IngestError("epic.id must be a string when present.")
    external_id = (external_id or "").strip() or None

    if mode == "update" and not external_id:
        raise IngestError("update mode requires epic.id (external_id) to match an existing Epic.")

    status = epic.get("status")
    if status is not None and not isinstance(status, str):
        raise IngestError("epic.status must be a string when present.")
    if status is not None:
        status = status.strip().lower()
        if status not in {"active", "parked"}:
            raise IngestError('epic.status must be "active" or "parked" when set.')

    path_raw = epic.get("path", PATH_FULL)
    if path_raw is not None and not isinstance(path_raw, str):
        raise IngestError("epic.path must be a string when present.")
    try:
        epic_path = normalize_path(path_raw if path_raw is not None else PATH_FULL)
    except ValueError as exc:
        raise IngestError(str(exc)) from None

    try:
        epic_life_modes = normalize_life_modes(epic.get("life_modes", []))
    except ValueError as exc:
        raise IngestError(str(exc)) from None

    phases_raw = epic.get("phases")
    if not isinstance(phases_raw, list) or not phases_raw:
        raise IngestError("epic.phases must be a non-empty array.")

    phases: list[dict[str, Any]] = []
    seen_phase_ids: set[str] = set()
    for i, phase in enumerate(phases_raw):
        if not isinstance(phase, dict):
            raise IngestError(f"phases[{i}] must be an object.")
        pt = (phase.get("title") or "").strip() if isinstance(phase.get("title"), str) else ""
        if not pt:
            raise IngestError(f"phases[{i}].title is required.")
        pid = phase.get("id")
        if pid is not None and not isinstance(pid, str):
            raise IngestError(f"phases[{i}].id must be a string when present.")
        pid = (pid or "").strip() or None
        if pid:
            if pid in seen_phase_ids:
                raise IngestError(f"Duplicate phase id “{pid}”.")
            seen_phase_ids.add(pid)
        order = phase.get("order", i + 1)
        if not isinstance(order, int) or isinstance(order, bool):
            raise IngestError(f"phases[{i}].order must be an integer.")
        deliverable = phase.get("deliverable")
        if deliverable is not None and not isinstance(deliverable, str):
            raise IngestError(f"phases[{i}].deliverable must be a string when present.")
        deliverable = (deliverable or "").strip() or None

        steps_raw = phase.get("steps")
        if not isinstance(steps_raw, list) or not steps_raw:
            raise IngestError(f"phases[{i}].steps must be a non-empty array.")
        steps: list[dict[str, Any]] = []
        seen_step_ids: set[str] = set()
        for j, step in enumerate(steps_raw):
            if not isinstance(step, dict):
                raise IngestError(f"phases[{i}].steps[{j}] must be an object.")
            st = (step.get("title") or "").strip() if isinstance(step.get("title"), str) else ""
            if not st:
                raise IngestError(f"phases[{i}].steps[{j}].title is required.")
            sid = step.get("id")
            if sid is not None and not isinstance(sid, str):
                raise IngestError(f"phases[{i}].steps[{j}].id must be a string when present.")
            sid = (sid or "").strip() or None
            if sid:
                if sid in seen_step_ids:
                    raise IngestError(f"Duplicate step id “{sid}” in phase “{pt}”.")
                seen_step_ids.add(sid)
            sorder = step.get("order", j + 1)
            if not isinstance(sorder, int) or isinstance(sorder, bool):
                raise IngestError(f"phases[{i}].steps[{j}].order must be an integer.")
            parallel = step.get("parallel", True)
            if not isinstance(parallel, bool):
                raise IngestError(f"phases[{i}].steps[{j}].parallel must be a boolean.")
            priority = step.get("priority", 2)
            if not isinstance(priority, int) or isinstance(priority, bool) or priority < 1 or priority > 3:
                raise IngestError(f"phases[{i}].steps[{j}].priority must be 1, 2, or 3.")
            try:
                step_life_mode = normalize_life_mode(step.get("life_mode"))
            except ValueError as exc:
                raise IngestError(f"phases[{i}].steps[{j}].{exc}") from None
            steps.append(
                {
                    "external_id": sid,
                    "title": st,
                    "order": sorder,
                    "parallel": parallel,
                    "priority": priority,
                    "life_mode": step_life_mode,
                }
            )
        phases.append(
            {
                "external_id": pid,
                "title": pt,
                "order": order,
                "deliverable": deliverable,
                "steps": steps,
            }
        )

    if mode == "new" and len(phases) < 1:
        raise IngestError("new mode needs at least one Phase with Steps.")

    identity = epic.get("identity")
    capability = epic.get("capability")
    preview = epic.get("preview")
    for label, val in (("identity", identity), ("capability", capability), ("preview", preview)):
        if val is not None and not isinstance(val, str):
            raise IngestError(f"epic.{label} must be a string when present.")

    return {
        "mode": mode,
        "confirm_destructive": confirm_destructive,
        "epic": {
            "external_id": external_id,
            "title": title,
            "identity": (identity or "").strip() or None if isinstance(identity, str) else None,
            "capability": (capability or "").strip() or None if isinstance(capability, str) else None,
            "preview": (preview or "").strip() or None if isinstance(preview, str) else None,
            "status": status,
            "path": epic_path,
            "life_modes": epic_life_modes,
            "phases": phases,
        },
    }


def _load_epic_by_external(db: Session, user: User, external_id: str) -> Epic | None:
    return db.scalar(
        select(Epic)
        .where(Epic.user_id == user.id, Epic.external_id == external_id)
        .options(joinedload(Epic.phases).joinedload(Phase.steps))
    )


def _phase_has_completed_progress(phase: Phase) -> bool:
    if phase.completed:
        return True
    return any(s.completed for s in phase.steps)


def _apply_new(db: Session, user: User, payload: dict[str, Any]) -> str:
    epic_data = payload["epic"]
    if epic_data["external_id"]:
        existing = _load_epic_by_external(db, user, epic_data["external_id"])
        if existing:
            raise IngestError(
                f"Epic id “{epic_data['external_id']}” already exists — use mode “update”."
            )

    epic = Epic(
        user_id=user.id,
        external_id=epic_data["external_id"],
        title=epic_data["title"],
        identity_end=epic_data["identity"],
        capability_end=epic_data["capability"],
        preview_label=epic_data["preview"],
        path=epic_data.get("path") or PATH_FULL,
        life_modes=life_modes_to_json(epic_data.get("life_modes") or []),
        legendary=True,
    )
    db.add(epic)
    db.flush()

    for phase_data in sorted(epic_data["phases"], key=lambda p: p["order"]):
        phase = Phase(
            epic_id=epic.id,
            external_id=phase_data["external_id"],
            title=phase_data["title"],
            sort_order=phase_data["order"],
            deliverable=phase_data["deliverable"],
        )
        db.add(phase)
        db.flush()
        for step_data in sorted(phase_data["steps"], key=lambda s: s["order"]):
            db.add(
                Step(
                    phase_id=phase.id,
                    external_id=step_data["external_id"],
                    title=step_data["title"],
                    sort_order=step_data["order"],
                    parallel=step_data["parallel"],
                    priority=step_data["priority"],
                    life_mode=step_data.get("life_mode"),
                )
            )

    activate = False
    if epic_data["status"] == "active":
        activate = True
    elif not user.active_epic_id:
        # First epic (or no active) — activate calmly without parking punishment
        activate = True

    if activate:
        user.active_epic_id = epic.id

    db.flush()
    status_note = "Active" if user.active_epic_id == epic.id else "Parked"
    path_label = "Focused" if epic.path == "focused" else "Full"
    return f"Imported new Epic “{epic.title}” ({status_note}, {path_label}) with {len(epic_data['phases'])} Phase(s)."


def _apply_update(
    db: Session,
    user: User,
    payload: dict[str, Any],
    ui_confirm_destructive: bool,
) -> str:
    epic_data = payload["epic"]
    epic = _load_epic_by_external(db, user, epic_data["external_id"])
    if not epic:
        raise IngestError(f"No Epic with id “{epic_data['external_id']}” for this user.")

    # Ensure relationships loaded
    phases = list(epic.phases)
    for p in phases:
        _ = p.steps

    json_phase_ids = {p["external_id"] for p in epic_data["phases"] if p["external_id"]}
    existing_by_ext = {p.external_id: p for p in phases if p.external_id}

    # Detect removals
    phases_to_remove = [
        p for p in phases if p.external_id and p.external_id not in json_phase_ids
    ]
    # Phases without external_id that aren't matched can't be kept by id from JSON —
    # only remove if JSON lists phases all with ids and this one has an id not listed.
    # Also: phases with no external_id stay unless confirm_destructive and we're replacing all?
    # Keep unmatched (no external_id) phases unless destructive confirmed and they're orphans.
    orphan_phases = [p for p in phases if not p.external_id]

    steps_to_remove: list[Step] = []
    for phase_data in epic_data["phases"]:
        if not phase_data["external_id"]:
            continue
        existing_phase = existing_by_ext.get(phase_data["external_id"])
        if not existing_phase:
            continue
        json_step_ids = {s["external_id"] for s in phase_data["steps"] if s["external_id"]}
        for step in existing_phase.steps:
            if step.external_id and step.external_id not in json_step_ids:
                steps_to_remove.append(step)

    destructive_needed = bool(phases_to_remove or steps_to_remove)
    # Removing orphan phases (no external_id) when update only lists id'd phases:
    # leave them alone unless confirm — safer default.
    completed_at_risk = any(_phase_has_completed_progress(p) for p in phases_to_remove) or any(
        s.completed for s in steps_to_remove
    )

    if destructive_needed:
        json_ok = payload["confirm_destructive"]
        if not (json_ok and ui_confirm_destructive):
            detail = "completed progress" if completed_at_risk else "existing Steps/Phases"
            raise IngestError(
                "Update would remove "
                + detail
                + ". Set confirm_destructive: true in JSON and check the Import confirmation box."
            )

    # Apply epic field updates — never reset completion
    epic.title = epic_data["title"]
    if epic_data["identity"] is not None:
        epic.identity_end = epic_data["identity"]
    if epic_data["capability"] is not None:
        epic.capability_end = epic_data["capability"]
    if epic_data["preview"] is not None:
        epic.preview_label = epic_data["preview"]

    if epic_data.get("path"):
        epic.path = epic_data["path"]

    if "life_modes" in epic_data:
        epic.life_modes = life_modes_to_json(epic_data.get("life_modes") or [])

    if epic_data["status"] == "active":
        user.active_epic_id = epic.id
    elif epic_data["status"] == "parked" and user.active_epic_id == epic.id:
        user.active_epic_id = None

    # Removals (only when confirmed)
    if destructive_needed:
        for step in steps_to_remove:
            db.delete(step)
        for phase in phases_to_remove:
            db.delete(phase)

    db.flush()

    # Upsert phases/steps from JSON (reload relationships after possible deletes)
    db.refresh(epic)
    phases = list(epic.phases)
    for p in phases:
        _ = p.steps
    existing_by_ext = {p.external_id: p for p in phases if p.external_id}

    for phase_data in sorted(epic_data["phases"], key=lambda p: p["order"]):
        phase = existing_by_ext.get(phase_data["external_id"]) if phase_data["external_id"] else None
        if phase is None:
            phase = Phase(
                epic_id=epic.id,
                external_id=phase_data["external_id"],
                title=phase_data["title"],
                sort_order=phase_data["order"],
                deliverable=phase_data["deliverable"],
            )
            db.add(phase)
            db.flush()
            existing_by_ext[phase_data["external_id"]] = phase if phase_data["external_id"] else None
        else:
            phase.title = phase_data["title"]
            phase.sort_order = phase_data["order"]
            if phase_data["deliverable"] is not None:
                phase.deliverable = phase_data["deliverable"]
            # never reset phase.completed here

        step_by_ext = {s.external_id: s for s in phase.steps if s.external_id}
        for step_data in sorted(phase_data["steps"], key=lambda s: s["order"]):
            step = step_by_ext.get(step_data["external_id"]) if step_data["external_id"] else None
            if step is None:
                db.add(
                    Step(
                        phase_id=phase.id,
                        external_id=step_data["external_id"],
                        title=step_data["title"],
                        sort_order=step_data["order"],
                        parallel=step_data["parallel"],
                        priority=step_data["priority"],
                        life_mode=step_data.get("life_mode"),
                    )
                )
            else:
                step.title = step_data["title"]
                step.sort_order = step_data["order"]
                step.parallel = step_data["parallel"]
                step.priority = step_data["priority"]
                if "life_mode" in step_data:
                    step.life_mode = step_data.get("life_mode")
                # never reset step.completed

    # Silence unused (orphan_phases kept intentionally)
    _ = orphan_phases

    db.flush()
    return f"Updated Epic “{epic.title}” (progress preserved)."


def apply_ingest(
    db: Session,
    user: User,
    raw_json: str,
    *,
    ui_confirm_destructive: bool = False,
) -> str:
    data = parse_ingest_json(raw_json)
    payload = validate_ingest(data)
    if payload["mode"] == "new":
        return _apply_new(db, user, payload)
    return _apply_update(db, user, payload, ui_confirm_destructive)
