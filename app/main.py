from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.review import build_weekly_review
from app.search import search_user
from app.backup import (
    REPLACE_CONFIRM_PHRASE,
    BackupError,
    apply_restore,
    build_export,
)
from app.auth import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    read_session_token,
    verify_password,
)
from app.config import SECURE_COOKIES, SESSION_MAX_AGE
from app.database import get_db, init_db
from app.ingest import IngestError, apply_ingest
from app.life_modes import (
    LIFE_MODE_LABELS,
    LIFE_MODES,
    life_modes_from_json,
    life_modes_to_json,
    matches_epic_modes,
    matches_single_mode,
    normalize_life_mode,
    normalize_life_modes,
    parse_filter_mode,
)
from app.epics_logic import (
    FOCUSED_KEEP_PHASES,
    PATH_FOCUSED,
    PATH_FULL,
    complete_step,
    current_phase,
    epic_progress,
    next_step,
    next_step_for_mode,
    normalize_path,
    phase_progress,
    switch_epic_path,
)
from app.models import Epic, Phase, Redemption, RewardLog, Routine, Step, Task, User
from app.path_routes import apply_path_switch
from app.period_bonuses import (
    ensure_default_period_bonuses,
    period_bonus_snapshot,
    record_completion,
)
from app.rewards import grant_reward
from app.shop import (
    ShopError,
    catalog_items,
    get_catalog_item,
    history_label,
    is_legacy_irl,
    redeem,
)
from app.routines_logic import CADENCES, advance_due, streak_continues
from app.watch_logic import (
    KIND_STEP,
    KIND_TASK,
    WatchFullError,
    build_watch_board,
    cleanup_ref,
    pin_item,
    pinned_ref_set,
    unpin_item,
)

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
STARTER_TEMPLATES_DIR = REPO_ROOT / "docs" / "templates"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Daily Tracker", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

STARTER_TEMPLATE_FILES = (
    ("side-it-project.json", "Side IT project"),
    ("move-house.json", "Move house"),
    ("apartment-redo.json", "Apartment redo"),
)


def _list_starter_templates() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for filename, label in STARTER_TEMPLATE_FILES:
        path = STARTER_TEMPLATES_DIR / filename
        if path.is_file():
            rows.append({"id": filename.removesuffix(".json"), "filename": filename, "label": label})
    return rows


def _load_starter_template(template_id: str) -> str:
    safe = (template_id or "").strip().lower().replace(" ", "-")
    # Allow id with or without .json
    if safe.endswith(".json"):
        safe = safe[: -len(".json")]
    allowed = {name.removesuffix(".json") for name, _ in STARTER_TEMPLATE_FILES}
    if safe not in allowed:
        raise HTTPException(status_code=404, detail="Template not found.")
    path = STARTER_TEMPLATES_DIR / f"{safe}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Template not found.")
    return path.read_text(encoding="utf-8")


def _parse_optional_life_mode(raw: str) -> str | None:
    try:
        return normalize_life_mode(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def _parse_life_modes_form(raw_values: list[str] | None) -> str:
    try:
        return life_modes_to_json(normalize_life_modes(list(raw_values or [])))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.exception_handler(StarletteHTTPException)
async def graceful_http_exception(request: Request, exc: StarletteHTTPException):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "status_code": exc.status_code,
                "message": exc.detail if isinstance(exc.detail, str) else "Something went wrong.",
            },
            status_code=exc.status_code,
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def graceful_unhandled(request: Request, exc: Exception):  # noqa: ARG001
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "message": "Something went wrong. Please try again.",
        },
        status_code=500,
    )


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(user_id),
        httponly=True,
        samesite="lax",
        secure=SECURE_COOKIES,
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def _flash_redirect(path: str, message: str) -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{sep}flash={quote(message)}", status_code=303)


def _read_flash(request: Request) -> str | None:
    raw = request.query_params.get("flash")
    if not raw:
        return None
    return unquote(raw)


def current_user(request: Request, db: Session) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    uid = read_session_token(token)
    if uid is None:
        return None
    return db.get(User, uid)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


def user_count(db: Session) -> int:
    return len(db.scalars(select(User)).all())


def _load_epic(db: Session, epic_id: int) -> Epic | None:
    return db.scalar(
        select(Epic)
        .where(Epic.id == epic_id)
        .options(joinedload(Epic.phases).joinedload(Phase.steps))
    )


def _active_epic(db: Session, user: User) -> Epic | None:
    if not user.active_epic_id:
        return None
    epic = _load_epic(db, user.active_epic_id)
    if not epic or epic.user_id != user.id:
        return None
    return epic


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    if user_count(db) == 0:
        return RedirectResponse("/setup", status_code=303)
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/today", status_code=303)


@app.get("/setup", response_class=HTMLResponse)
def setup_get(request: Request, db: Session = Depends(get_db)):
    if user_count(db) > 0:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "setup.html",
        {"request": request, "error": None},
    )


@app.post("/setup", response_class=HTMLResponse)
def setup_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if user_count(db) > 0:
        return RedirectResponse("/login", status_code=303)
    error = None
    username = username.strip()
    if len(username) < 2:
        error = "Username must be at least 2 characters."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != password_confirm:
        error = "Passwords do not match."
    if error:
        return templates.TemplateResponse(
            "setup.html",
            {"request": request, "error": error},
            status_code=400,
        )
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_default_period_bonuses(db, user)
    response = RedirectResponse("/today", status_code=303)
    _set_session_cookie(response, user.id)
    return response


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request, db: Session = Depends(get_db)):
    if user_count(db) == 0:
        return RedirectResponse("/setup", status_code=303)
    if current_user(request, db):
        return RedirectResponse("/today", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.username == username.strip()))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."},
            status_code=401,
        )
    ensure_default_period_bonuses(db, user)
    response = RedirectResponse("/today", status_code=303)
    _set_session_cookie(response, user.id)
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def _due_now(user: User, today: date) -> tuple[list[Task], list[Routine]]:
    open_tasks = [t for t in user.tasks if not t.completed]
    due_tasks = [
        t
        for t in open_tasks
        if t.due_date is not None and t.due_date <= today
    ]
    due_tasks.sort(key=lambda t: (t.priority, t.due_date or today, t.created_at, t.id))
    due_routines = [r for r in user.routines if r.next_due_on <= today]
    due_routines.sort(key=lambda r: (r.priority, r.next_due_on, r.created_at, r.id))
    return due_tasks, due_routines


@app.get("/today", response_class=HTMLResponse)
def today_view(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    today = date.today()
    ensure_default_period_bonuses(db, user)
    mode_filter = parse_filter_mode(request.query_params.get("mode"))
    due_tasks, due_routines = _due_now(user, today)
    # Life-mode filter: hide/show within lists only — never reorder sections
    due_tasks = [t for t in due_tasks if matches_single_mode(t.life_mode, mode_filter)]
    due_routines = [r for r in due_routines if matches_single_mode(r.life_mode, mode_filter)]
    active = _active_epic(db, user)
    active_hidden_by_filter = bool(active) and not matches_epic_modes(
        getattr(active, "life_modes", None), mode_filter
    )
    show_active = bool(active) and not active_hidden_by_filter
    next_step_item = None
    phase = None
    phase_done = phase_total = 0
    phase_pct = overall_pct = 0.0
    epic_done = epic_total = 0
    epic_truly_complete = False
    next_step_filtered_out = False
    if show_active and active:
        epic_truly_complete = bool(active.completed) or next_step(active) is None
        next_step_item = next_step_for_mode(active, mode_filter, matches_single_mode)
        if not next_step_item and not epic_truly_complete and mode_filter:
            next_step_filtered_out = True
        phase = current_phase(active)
        if phase:
            phase_done, phase_total, phase_pct = phase_progress(phase)
        epic_done, epic_total, overall_pct = epic_progress(active)
    all_epics = db.scalars(select(Epic).where(Epic.user_id == user.id)).all()
    parked_count = sum(
        1
        for e in all_epics
        if not e.completed and e.id != user.active_epic_id
    )
    watch_rows = build_watch_board(db, user)
    db.commit()  # persist any completed-pin cleanup
    # Filter Watch rows by underlying item life_mode (untagged OR matching)
    filtered_watch = []
    for w in watch_rows:
        item_mode = None
        if w.kind == "task":
            task = db.get(Task, w.ref_id)
            item_mode = task.life_mode if task else None
        elif w.kind == "step":
            step = db.get(Step, w.ref_id)
            item_mode = step.life_mode if step else None
        if matches_single_mode(item_mode, mode_filter):
            filtered_watch.append(w)
    pins = pinned_ref_set(db, user)
    open_tasks = sorted(
        [t for t in user.tasks if not t.completed and matches_single_mode(t.life_mode, mode_filter)],
        key=lambda t: (t.priority, t.due_date or date.max),
    )
    routines = sorted(
        [r for r in user.routines if matches_single_mode(r.life_mode, mode_filter)],
        key=lambda r: (r.priority, r.next_due_on),
    )
    return templates.TemplateResponse(
        "today.html",
        {
            "request": request,
            "user": user,
            "today": today,
            "due_tasks": due_tasks,
            "due_routines": due_routines,
            "routines": routines,
            "open_tasks": open_tasks,
            "recent_rewards": sorted(user.reward_logs, key=lambda r: r.created_at, reverse=True)[:8],
            "flash": _read_flash(request),
            "cadences": CADENCES,
            "active_epic": active if show_active else None,
            "active_hidden_by_filter": active_hidden_by_filter,
            "has_active_epic": bool(active),
            "epic_truly_complete": epic_truly_complete,
            "next_step_filtered_out": next_step_filtered_out,
            "next_step": next_step_item,
            "current_phase": phase,
            "phase_done": phase_done,
            "phase_total": phase_total,
            "phase_pct": phase_pct,
            "epic_done": epic_done,
            "epic_total": epic_total,
            "overall_pct": overall_pct,
            "period_bonuses": period_bonus_snapshot(db, user, today),
            "parked_count": parked_count,
            "watch_rows": filtered_watch,
            "pinned_refs": pins,
            "life_modes": LIFE_MODES,
            "life_mode_labels": LIFE_MODE_LABELS,
            "mode_filter": mode_filter,
        },
    )


@app.post("/tasks")
def create_task(
    title: str = Form(...),
    notes: str = Form(""),
    priority: int = Form(2),
    due_date: str = Form(""),
    life_mode: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    priority = min(3, max(1, priority))
    parsed_due = date.fromisoformat(due_date) if due_date else None
    task = Task(
        user_id=user.id,
        title=title,
        notes=notes.strip() or None,
        priority=priority,
        due_date=parsed_due,
        life_mode=_parse_optional_life_mode(life_mode),
    )
    db.add(task)
    db.commit()
    return _flash_redirect("/today", "Task created")


@app.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    task = db.get(Task, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found.")
    flashes: list[str] = []
    if not task.completed:
        task.completed = True
        task.completed_at = datetime.now(timezone.utc)
        grant_reward(db, user, task.priority, f"Completed task: {task.title}")
        flashes.append("Task completed")
        flashes.extend(record_completion(db, user))
        cleanup_ref(db, user, KIND_TASK, task.id)
        # Auto-complete linked steps
        linked = db.scalars(
            select(Step).where(Step.task_id == task.id, Step.completed.is_(False))
        ).all()
        for step in linked:
            _ = step.phase.epic
            flashes.append(complete_step(db, user, step))
            cleanup_ref(db, user, KIND_STEP, step.id)
        db.commit()
    return _flash_redirect("/today", " · ".join(flashes) if flashes else "Already completed")


@app.post("/routines")
def create_routine(
    title: str = Form(...),
    notes: str = Form(""),
    cadence: str = Form(...),
    priority: int = Form(2),
    life_mode: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    title = title.strip()
    cadence = cadence.strip().lower()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    if cadence not in CADENCES:
        raise HTTPException(status_code=400, detail="Invalid cadence.")
    priority = min(3, max(1, priority))
    today = date.today()
    routine = Routine(
        user_id=user.id,
        title=title,
        notes=notes.strip() or None,
        cadence=cadence,
        priority=priority,
        life_mode=_parse_optional_life_mode(life_mode),
        next_due_on=today,
    )
    db.add(routine)
    db.commit()
    return _flash_redirect("/today", "Routine created")


@app.post("/routines/{routine_id}/complete")
def complete_routine(
    routine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    routine = db.get(Routine, routine_id)
    if not routine or routine.user_id != user.id:
        raise HTTPException(status_code=404, detail="Routine not found.")
    today = date.today()
    if streak_continues(routine.cadence, routine.last_completed_on, today):
        # Same period already done — ignore double-complete for streak bump
        if routine.last_completed_on and routine.last_completed_on == today and routine.cadence == "daily":
            return _flash_redirect("/today", "Already completed today")
        if routine.last_completed_on and routine.cadence != "daily":
            from app.routines_logic import period_start

            if period_start(routine.cadence, routine.last_completed_on) == period_start(routine.cadence, today):
                return _flash_redirect("/today", "Already completed this period")
        routine.streak += 1
    else:
        # Soft streak: miss resets current streak only — never wipe best_streak
        routine.streak = 1
    routine.best_streak = max(routine.best_streak, routine.streak)
    routine.completion_count += 1
    routine.last_completed_on = today
    routine.next_due_on = advance_due(routine.cadence, today)
    grant_reward(db, user, routine.priority, f"Completed {routine.cadence} routine: {routine.title}")
    flashes = ["Routine completed"]
    flashes.extend(record_completion(db, user, today))
    linked = db.scalars(
        select(Step).where(Step.routine_id == routine.id, Step.completed.is_(False))
    ).all()
    for step in linked:
        _ = step.phase.epic
        flashes.append(complete_step(db, user, step))
        cleanup_ref(db, user, KIND_STEP, step.id)
    db.commit()
    return _flash_redirect("/today", " · ".join(flashes))


@app.post("/routines/{routine_id}/skip")
def skip_routine(
    routine_id: int,
    reason: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Soft skip: advance due, no reward, no Period-bonus credit, streaks untouched."""
    routine = db.get(Routine, routine_id)
    if not routine or routine.user_id != user.id:
        raise HTTPException(status_code=404, detail="Routine not found.")
    today = date.today()
    reason = (reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Skip needs a short reason.")
    if len(reason) > 255:
        reason = reason[:255]

    # Snapshot streak fields — must not change
    streak_before = routine.streak
    best_before = routine.best_streak
    count_before = routine.completion_count

    routine.last_skipped_on = today
    routine.last_skip_reason = reason
    routine.next_due_on = advance_due(routine.cadence, today)
    # Explicitly do NOT: grant_reward, record_completion, bump streak/count
    db.commit()
    db.refresh(routine)
    assert routine.streak == streak_before
    assert routine.best_streak == best_before
    assert routine.completion_count == count_before
    return _flash_redirect(
        "/today",
        f"Skipped {routine.title} (no reward) — {reason}",
    )


# ---------------------------------------------------------------------------
# Epics (v0.2) — hierarchy Epic → Phase → Step
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Epics (v0.2) — hierarchy Epic → Phase → Step
# ---------------------------------------------------------------------------


@app.get("/epics", response_class=HTMLResponse)
def epics_list(
    request: Request,
    show_archived: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    include_archived = show_archived in {"1", "true", "on", "yes"}
    all_epics = db.scalars(
        select(Epic)
        .where(Epic.user_id == user.id)
        .options(joinedload(Epic.phases).joinedload(Phase.steps))
        .order_by(Epic.created_at.desc())
    ).unique().all()
    by_id = {e.id: e for e in all_epics}
    visible = [e for e in all_epics if include_archived or not e.archived]
    rows = []
    for epic in visible:
        done, total, pct = epic_progress(epic)
        parent = by_id.get(epic.parent_epic_id) if epic.parent_epic_id else None
        rows.append(
            {
                "epic": epic,
                "done": done,
                "total": total,
                "pct": pct,
                "active": user.active_epic_id == epic.id,
                "parent": parent,
            }
        )
    parent_choices = [e for e in all_epics if not e.completed and not e.archived]
    archived_count = sum(1 for e in all_epics if e.archived)
    return templates.TemplateResponse(
        "epics.html",
        {
            "request": request,
            "user": user,
            "rows": rows,
            "parent_choices": parent_choices,
            "flash": _read_flash(request),
            "life_modes": LIFE_MODES,
            "life_mode_labels": LIFE_MODE_LABELS,
            "starter_templates": _list_starter_templates(),
            "show_archived": include_archived,
            "archived_count": archived_count,
        },
    )


@app.post("/epics")
def create_epic(
    title: str = Form(...),
    notes: str = Form(""),
    identity_end: str = Form(""),
    capability_end: str = Form(""),
    preview_label: str = Form(""),
    legendary: str = Form("on"),
    parent_epic_id: str = Form(""),
    path: str = Form("full"),
    life_modes: list[str] = Form([]),
    phase_titles: list[str] = Form(...),
    phase_steps: list[str] = Form(...),
    phase_deliverables: list[str] = Form([]),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Epic title is required.")
    try:
        epic_path = normalize_path(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    # Pair titles with steps; drop empty trailing slots
    phases_data: list[tuple[str, list[str], str | None]] = []
    for i, raw_title in enumerate(phase_titles):
        pt = (raw_title or "").strip()
        steps_raw = phase_steps[i] if i < len(phase_steps) else ""
        step_lines = [ln.strip() for ln in steps_raw.splitlines() if ln.strip()]
        deliverable = None
        if i < len(phase_deliverables):
            deliverable = (phase_deliverables[i] or "").strip() or None
        if not pt and not step_lines:
            continue
        if not pt:
            raise HTTPException(status_code=400, detail="Each Phase needs a title.")
        if not step_lines:
            raise HTTPException(
                status_code=400,
                detail=f"Phase “{pt}” needs at least one Step (newline-separated).",
            )
        phases_data.append((pt, step_lines, deliverable))

    if len(phases_data) < 2:
        raise HTTPException(
            status_code=400,
            detail="An Epic needs at least 2 Phases, each with Steps.",
        )

    parent_id = None
    raw_parent = (parent_epic_id or "").strip()
    if raw_parent:
        if not raw_parent.isdigit():
            raise HTTPException(status_code=400, detail="Invalid parent Epic.")
        parent_id = int(raw_parent)
        parent = db.get(Epic, parent_id)
        if not parent or parent.user_id != user.id:
            raise HTTPException(status_code=400, detail="Parent Epic not found.")

    epic = Epic(
        user_id=user.id,
        parent_epic_id=parent_id,
        title=title,
        notes=notes.strip() or None,
        legendary=legendary == "on",
        identity_end=identity_end.strip() or None,
        capability_end=capability_end.strip() or None,
        preview_label=preview_label.strip() or None,
        path=epic_path,
        life_modes=_parse_life_modes_form(life_modes),
    )
    db.add(epic)
    db.flush()
    for sort_i, (pt, step_lines, deliverable) in enumerate(phases_data):
        phase = Phase(
            epic_id=epic.id,
            title=pt,
            sort_order=sort_i,
            deliverable=deliverable,
        )
        db.add(phase)
        db.flush()
        for step_i, step_title in enumerate(step_lines):
            db.add(
                Step(
                    phase_id=phase.id,
                    title=step_title,
                    sort_order=step_i,
                    parallel=True,
                )
            )
    if not user.active_epic_id:
        user.active_epic_id = epic.id

    # Focused create: auto-park Phases beyond the condensed set (no re-apply needed)
    if epic_path == PATH_FOCUSED:
        from app.epics_logic import FOCUSED_KEEP_PHASES

        db.flush()
        for phase in sorted(epic.phases, key=lambda ph: ph.sort_order):
            if phase.sort_order >= FOCUSED_KEEP_PHASES:
                phase.parked = True

    db.commit()
    label = "Focused" if epic_path == PATH_FOCUSED else "Full"
    return _flash_redirect(f"/epics/{epic.id}", f"Epic created ({label} path)")


@app.get("/epics/{epic_id}", response_class=HTMLResponse)
def epic_detail(
    epic_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    epic = _load_epic(db, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    phases_view = []
    for phase in sorted(epic.phases, key=lambda p: p.sort_order):
        done, total, pct = phase_progress(phase)
        phases_view.append(
            {
                "phase": phase,
                "done": done,
                "total": total,
                "pct": pct,
                "steps": sorted(phase.steps, key=lambda s: (s.sort_order, s.id)),
            }
        )
    edone, etotal, epct = epic_progress(epic)
    open_tasks = sorted(
        [t for t in user.tasks if not t.completed],
        key=lambda t: (t.priority, t.title),
    )
    routines = sorted(user.routines, key=lambda r: (r.priority, r.title))
    return templates.TemplateResponse(
        "epic_detail.html",
        {
            "request": request,
            "user": user,
            "epic": epic,
            "phases_view": phases_view,
            "epic_done": edone,
            "epic_total": etotal,
            "overall_pct": epct,
            "is_active": user.active_epic_id == epic.id,
            "next_step": next_step(epic),
            "parent": db.get(Epic, epic.parent_epic_id) if epic.parent_epic_id else None,
            "parent_choices": [
                e
                for e in db.scalars(
                    select(Epic).where(Epic.user_id == user.id, Epic.id != epic.id)
                ).all()
            ],
            "open_tasks": open_tasks,
            "routines": routines,
            "flash": _read_flash(request),
            "pinned_refs": pinned_ref_set(db, user),
            "life_modes": LIFE_MODES,
            "life_mode_labels": LIFE_MODE_LABELS,
            "epic_life_modes": life_modes_from_json(epic.life_modes),
            "follows_from": (
                db.get(Epic, epic.follows_epic_id) if epic.follows_epic_id else None
            ),
            "follow_ons": list(
                db.scalars(
                    select(Epic).where(
                        Epic.user_id == user.id,
                        Epic.follows_epic_id == epic.id,
                    )
                ).all()
            ),
        },
    )


DEFAULT_FOLLOW_ON_PHASES = (
    (
        "Stabilize",
        "Review what landed\nCapture open threads\nLock the wins",
    ),
    (
        "Improve",
        "Pick one refinement\nShip a small improvement\nRe-check the identity goal",
    ),
)


@app.get("/epics/{epic_id}/follow-on", response_class=HTMLResponse)
def follow_on_form(
    epic_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Explicit Start follow-on CTA only — never auto-starts."""
    source = _load_epic(db, epic_id)
    if not source or source.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    if not source.completed:
        raise HTTPException(
            status_code=400,
            detail="Follow-on is only offered after the Epic is completed.",
        )
    modes = life_modes_from_json(source.life_modes)
    id_end = source.identity_end or ""
    cap_end = source.capability_end or ""
    if id_end and "refine" not in id_end.lower():
        id_prefill = f"{id_end} (refine / maintain)"
    else:
        id_prefill = id_end or "Refine / maintain who you became"
    if cap_end and "refine" not in cap_end.lower() and "maintain" not in cap_end.lower():
        cap_prefill = f"{cap_end} (refine / maintain)"
    else:
        cap_prefill = cap_end or "Keep and refine the capability"
    return templates.TemplateResponse(
        "follow_on.html",
        {
            "request": request,
            "user": user,
            "source": source,
            "flash": _read_flash(request),
            "prefill_title": f"Follow-on: {source.title}",
            "prefill_identity": id_prefill,
            "prefill_capability": cap_prefill,
            "prefill_notes": "Refine / maintain — explicit follow-on from a completed Epic.",
            "prefill_modes": modes,
            "phase_rows": [
                {"title": t, "steps": s} for t, s in DEFAULT_FOLLOW_ON_PHASES
            ],
            "life_modes": LIFE_MODES,
            "life_mode_labels": LIFE_MODE_LABELS,
        },
    )


@app.post("/epics/{epic_id}/follow-on")
def create_follow_on(
    epic_id: int,
    title: str = Form(...),
    notes: str = Form(""),
    identity_end: str = Form(""),
    capability_end: str = Form(""),
    path: str = Form("focused"),
    life_modes: list[str] = Form([]),
    phase_titles: list[str] = Form(...),
    phase_steps: list[str] = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    source = db.get(Epic, epic_id)
    if not source or source.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    if not source.completed:
        raise HTTPException(
            status_code=400,
            detail="Follow-on is only offered after the Epic is completed.",
        )

    # Snapshot source fields before create — must remain unchanged after commit
    source_snapshot = {
        "id": source.id,
        "title": source.title,
        "completed": source.completed,
        "completed_at": source.completed_at,
        "identity_end": source.identity_end,
        "capability_end": source.capability_end,
        "life_modes": source.life_modes,
        "path": source.path,
        "notes": source.notes,
    }

    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Epic title is required.")
    try:
        epic_path = normalize_path(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    phases_data: list[tuple[str, list[str]]] = []
    for i, raw_title in enumerate(phase_titles):
        pt = (raw_title or "").strip()
        steps_raw = phase_steps[i] if i < len(phase_steps) else ""
        step_lines = [ln.strip() for ln in steps_raw.splitlines() if ln.strip()]
        if not pt and not step_lines:
            continue
        if not pt:
            raise HTTPException(status_code=400, detail="Each Phase needs a title.")
        if not step_lines:
            raise HTTPException(
                status_code=400,
                detail=f"Phase “{pt}” needs at least one Step (newline-separated).",
            )
        phases_data.append((pt, step_lines))

    if len(phases_data) < 1:
        raise HTTPException(
            status_code=400,
            detail="Follow-on needs at least one Phase with Steps.",
        )

    epic = Epic(
        user_id=user.id,
        follows_epic_id=source.id,
        title=title,
        notes=notes.strip() or None,
        legendary=True,
        identity_end=identity_end.strip() or None,
        capability_end=capability_end.strip() or None,
        path=epic_path,
        life_modes=_parse_life_modes_form(life_modes),
        completed=False,
        completed_at=None,
    )
    db.add(epic)
    db.flush()
    for sort_i, (pt, step_lines) in enumerate(phases_data):
        phase = Phase(
            epic_id=epic.id,
            title=pt,
            sort_order=sort_i,
            parked=False,
        )
        db.add(phase)
        db.flush()
        for step_i, step_title in enumerate(step_lines):
            db.add(
                Step(
                    phase_id=phase.id,
                    title=step_title,
                    sort_order=step_i,
                    parallel=True,
                )
            )

    if epic_path == PATH_FOCUSED:
        db.flush()
        for phase in sorted(epic.phases, key=lambda ph: ph.sort_order):
            if phase.sort_order >= FOCUSED_KEEP_PHASES:
                phase.parked = True

    db.commit()

    # Re-load source — must be byte-identical on protected fields
    db.refresh(source)
    for key, val in source_snapshot.items():
        if getattr(source, key) != val:
            raise HTTPException(
                status_code=500,
                detail="Follow-on must not mutate the completed Epic.",
            )

    return _flash_redirect(
        f"/epics/{epic.id}",
        f"Follow-on created (follows Epic #{source.id})",
    )


@app.post("/epics/{epic_id}/activate")
def activate_epic(
    epic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    epic = db.get(Epic, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    user.active_epic_id = epic.id
    db.commit()
    return _flash_redirect("/today", f"Active Epic: {epic.title}")


@app.post("/epics/{epic_id}/park")
def park_epic(
    epic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    epic = db.get(Epic, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    # Park clears Active only — never wipes progress, titles, or completions (R5.12)
    if user.active_epic_id == epic.id:
        user.active_epic_id = None
        db.commit()
        return _flash_redirect(f"/epics/{epic.id}", f"Parked: {epic.title}")
    return _flash_redirect(f"/epics/{epic.id}", f"Already Parked: {epic.title}")

@app.post("/epics/{epic_id}/archive")
def archive_epic(
    epic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Soft archive — hide from default list; never wipe progress."""
    epic = db.get(Epic, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    # Snapshot progress must remain
    phase_ids = [p.id for p in epic.phases]
    step_count = sum(len(p.steps) for p in epic.phases)
    epic.archived = True
    if user.active_epic_id == epic.id:
        user.active_epic_id = None
    db.commit()
    db.refresh(epic)
    assert epic.archived is True
    assert len(epic.phases) == len(phase_ids)
    assert sum(len(p.steps) for p in epic.phases) == step_count
    return _flash_redirect("/epics", f"Archived (progress kept): {epic.title}")


@app.post("/epics/{epic_id}/restore")
def restore_epic(
    epic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    epic = db.get(Epic, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    epic.archived = False
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", f"Restored: {epic.title}")


@app.post("/epics/{epic_id}/path")
def set_epic_path(
    epic_id: int,
    path: str = Form(...),
    confirm_destructive: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    epic = _load_epic(db, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    return apply_path_switch(epic, path, confirm_destructive, db, _flash_redirect)


@app.post("/epics/{epic_id}/parent")
def set_epic_parent(
    epic_id: int,
    parent_epic_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    epic = db.get(Epic, epic_id)
    if not epic or epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Epic not found.")
    raw = (parent_epic_id or "").strip()
    if not raw:
        epic.parent_epic_id = None
        db.commit()
        return _flash_redirect(f"/epics/{epic.id}", "Parent cleared")
    if not raw.isdigit():
        raise HTTPException(status_code=400, detail="Invalid parent Epic.")
    parent_id = int(raw)
    if parent_id == epic.id:
        raise HTTPException(status_code=400, detail="An Epic cannot be its own parent.")
    parent = db.get(Epic, parent_id)
    if not parent or parent.user_id != user.id:
        raise HTTPException(status_code=400, detail="Parent Epic not found.")
    walk = parent
    seen = {epic.id}
    while walk is not None:
        if walk.id in seen:
            raise HTTPException(status_code=400, detail="That parent would create a cycle.")
        seen.add(walk.id)
        walk = db.get(Epic, walk.parent_epic_id) if walk.parent_epic_id else None
    epic.parent_epic_id = parent_id
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", f"Parent set: {parent.title}")


@app.post("/steps/{step_id}/complete")
def complete_step_route(
    step_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    step = db.get(Step, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")
    phase = step.phase
    epic = phase.epic
    if epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Step not found.")
    msg = complete_step(db, user, step)
    flashes = [msg]
    if "Already" not in msg:
        flashes.extend(record_completion(db, user))
        cleanup_ref(db, user, KIND_STEP, step.id)
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", " · ".join(flashes))


@app.post("/steps/{step_id}/link")
def link_step(
    step_id: int,
    task_id: str = Form(""),
    routine_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    step = db.get(Step, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")
    epic = step.phase.epic
    if epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Step not found.")

    tid = int(task_id) if task_id.strip().isdigit() else None
    rid = int(routine_id) if routine_id.strip().isdigit() else None
    if tid is not None:
        task = db.get(Task, tid)
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=400, detail="Invalid task.")
        step.task_id = tid
    else:
        step.task_id = None
    if rid is not None:
        routine = db.get(Routine, rid)
        if not routine or routine.user_id != user.id:
            raise HTTPException(status_code=400, detail="Invalid routine.")
        step.routine_id = rid
    else:
        step.routine_id = None
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", "Step linked")


@app.post("/phases/{phase_id}/steps")
def create_step(
    phase_id: int,
    title: str = Form(...),
    priority: int = Form(2),
    life_mode: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    phase = db.get(Phase, phase_id)
    if not phase or phase.epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Phase not found.")
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Step title is required.")
    priority = min(3, max(1, priority))
    max_order = max((s.sort_order for s in phase.steps), default=-1)
    db.add(
        Step(
            phase_id=phase.id,
            title=title,
            sort_order=max_order + 1,
            parallel=True,
            priority=priority,
            life_mode=_parse_optional_life_mode(life_mode),
        )
    )
    db.commit()
    return _flash_redirect(f"/epics/{phase.epic_id}", "Step created")


# ---------------------------------------------------------------------------
# Search (v1.1 BL-020)
# ---------------------------------------------------------------------------


@app.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    hits = search_user(db, user, q)
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "user": user,
            "q": (q or "").strip(),
            "hits": hits,
            "flash": _read_flash(request),
        },
    )


# ---------------------------------------------------------------------------
# Weekly review (v0.9) — read-only
# ---------------------------------------------------------------------------


@app.get("/review", response_class=HTMLResponse)
def weekly_review_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    ensure_default_period_bonuses(db, user)
    review = build_weekly_review(db, user)
    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "user": user,
            "review": review,
            "flash": _read_flash(request),
        },
    )


# ---------------------------------------------------------------------------
# Settings — export / restore (v0.7)
# ---------------------------------------------------------------------------


@app.get("/settings", response_class=HTMLResponse)
def settings_get(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "flash": _read_flash(request),
            "error": None,
            "replace_phrase": REPLACE_CONFIRM_PHRASE,
        },
    )


@app.get("/settings/export.json")
def settings_export(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    payload = build_export(db, user)
    db.commit()  # persist any newly minted external_ids
    body = __import__("json").dumps(payload, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="dailytracker-export.json"'
        },
    )


@app.post("/settings/restore", response_class=HTMLResponse)
async def settings_restore(
    request: Request,
    mode: str = Form("merge"),
    replace_confirm_text: str = Form(""),
    replace_confirm: str = Form(""),
    backup_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    raw = await backup_file.read()
    try:
        msg = apply_restore(
            db,
            user,
            raw,
            mode=mode,
            replace_confirm_text=replace_confirm_text,
            replace_confirm_checked=replace_confirm == "on",
        )
        db.commit()
        return _flash_redirect("/settings", msg)
    except BackupError as exc:
        db.rollback()
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "user": user,
                "flash": None,
                "error": exc.message,
                "replace_phrase": REPLACE_CONFIRM_PHRASE,
            },
            status_code=400,
        )


# ---------------------------------------------------------------------------
# LLM ingest (v0.3) — New / Update via JSON (R8.*)
# ---------------------------------------------------------------------------


@app.get("/import", response_class=HTMLResponse)
def import_get(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    prefill = ""
    template_id = request.query_params.get("template")
    if template_id:
        try:
            prefill = _load_starter_template(template_id)
        except HTTPException:
            prefill = ""
    return templates.TemplateResponse(
        "import.html",
        {
            "request": request,
            "user": user,
            "flash": _read_flash(request),
            "error": None,
            "json_text": prefill,
            "confirm_destructive": False,
            "starter_templates": _list_starter_templates(),
        },
    )


@app.post("/import", response_class=HTMLResponse)
def import_post(
    request: Request,
    json_text: str = Form(""),
    confirm_destructive: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    ui_confirm = confirm_destructive == "on"
    try:
        msg = apply_ingest(db, user, json_text, ui_confirm_destructive=ui_confirm)
        db.commit()
        return _flash_redirect("/import", msg)
    except IngestError as exc:
        db.rollback()
        return templates.TemplateResponse(
            "import.html",
            {
                "request": request,
                "user": user,
                "flash": None,
                "error": exc.message,
                "json_text": json_text,
                "confirm_destructive": ui_confirm,
                "starter_templates": _list_starter_templates(),
            },
            status_code=400,
        )


@app.post("/templates/{template_id}/start")
def start_from_template(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Create a brand-new Epic from a starter template (mode:new ingest). Never mutates existing."""
    import json as _json
    import uuid as _uuid

    raw = _load_starter_template(template_id)
    try:
        data = _json.loads(raw)
        # Fresh external ids per start so templates can be used repeatedly without colliding
        suffix = _uuid.uuid4().hex[:8]
        epic = data.get("epic") or {}
        if isinstance(epic.get("id"), str) and epic["id"]:
            epic["id"] = f"{epic['id']}_{suffix}"
        for phase in epic.get("phases") or []:
            if isinstance(phase, dict) and isinstance(phase.get("id"), str) and phase["id"]:
                phase["id"] = f"{phase['id']}_{suffix}"
            for step in (phase.get("steps") if isinstance(phase, dict) else None) or []:
                if isinstance(step, dict) and isinstance(step.get("id"), str) and step["id"]:
                    step["id"] = f"{step['id']}_{suffix}"
        data["mode"] = "new"
        data["confirm_destructive"] = False
        msg = apply_ingest(db, user, _json.dumps(data), ui_confirm_destructive=False)
        db.commit()
        return _flash_redirect("/epics", msg)
    except IngestError as exc:
        db.rollback()
        return _flash_redirect("/epics", f"Template failed: {exc.message}")


# ---------------------------------------------------------------------------
# Rewards history + Watch / Nearly done (v0.3.1)
# ---------------------------------------------------------------------------


@app.get("/rewards", response_class=HTMLResponse)
def rewards_history(
    request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)
):
    logs = db.scalars(
        select(RewardLog)
        .where(RewardLog.user_id == user.id)
        .order_by(RewardLog.created_at.desc(), RewardLog.id.desc())
    ).all()
    return templates.TemplateResponse(
        "rewards.html",
        {
            "request": request,
            "user": user,
            "logs": logs,
            "flash": _read_flash(request),
        },
    )


@app.post("/watch/pin")
def watch_pin(
    kind: str = Form(...),
    ref_id: int = Form(...),
    next: str = Form("/today"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    dest = next.strip() or "/today"
    if not dest.startswith("/"):
        dest = "/today"
    try:
        pin_item(db, user, kind, ref_id)
        db.commit()
        return _flash_redirect(dest, "Pinned to Watch")
    except WatchFullError as exc:
        db.rollback()
        return _flash_redirect(dest, exc.message)
    except ValueError as exc:
        db.rollback()
        return _flash_redirect(dest, str(exc))


@app.post("/watch/unpin")
def watch_unpin(
    kind: str = Form(...),
    ref_id: int = Form(...),
    next: str = Form("/today"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    dest = next.strip() or "/today"
    if not dest.startswith("/"):
        dest = "/today"
    unpin_item(db, user, kind, ref_id)
    db.commit()
    return _flash_redirect(dest, "Unpinned from Watch")



# ---------------------------------------------------------------------------
# Cosmetic shop (v1.2 G1) — fixed catalog unlocks; no IRL fulfill
# ---------------------------------------------------------------------------


@app.get("/shop", response_class=HTMLResponse)
def shop_view(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    history = db.scalars(
        select(Redemption)
        .where(Redemption.user_id == user.id)
        .order_by(Redemption.created_at.desc(), Redemption.id.desc())
    ).all()
    rows = []
    for row in history:
        rows.append(
            {
                "redemption": row,
                "label": history_label(row.catalog_id),
                "legacy": is_legacy_irl(row.catalog_id),
            }
        )
    return templates.TemplateResponse(
        "shop.html",
        {
            "request": request,
            "user": user,
            "catalog": catalog_items(),
            "history": rows,
            "flash": _read_flash(request),
        },
    )


@app.post("/shop/redeem")
def shop_redeem(
    catalog_id: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    try:
        row = redeem(db, user, catalog_id)
        db.commit()
        label = history_label(row.catalog_id)
        return _flash_redirect("/shop", f"Unlocked: {label} (−{row.points_spent} pts)")
    except ShopError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=exc.message) from None


@app.get("/health")
def health():
    return {"status": "ok"}
