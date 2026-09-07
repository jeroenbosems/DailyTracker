from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    read_session_token,
    verify_password,
)
from app.chests import chest_snapshot, ensure_default_chests, record_completion
from app.config import SECURE_COOKIES, SESSION_MAX_AGE
from app.database import get_db, init_db
from app.epics_logic import act_progress, complete_bit, current_act, epic_progress, next_bit
from app.models import Act, Bit, Epic, Routine, Task, User
from app.rewards import grant_reward
from app.routines_logic import CADENCES, advance_due, streak_continues

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Daily Tracker", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


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
        .options(joinedload(Epic.acts).joinedload(Act.bits))
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
    ensure_default_chests(db, user)
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
    ensure_default_chests(db, user)
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
    ensure_default_chests(db, user)
    due_tasks, due_routines = _due_now(user, today)
    active = _active_epic(db, user)
    next_story = next_bit(active) if active else None
    act = current_act(active) if active else None
    act_done = act_total = 0
    act_pct = overall_pct = 0.0
    epic_done = epic_total = 0
    if active and act:
        act_done, act_total, act_pct = act_progress(act)
    if active:
        epic_done, epic_total, overall_pct = epic_progress(active)
    return templates.TemplateResponse(
        "today.html",
        {
            "request": request,
            "user": user,
            "today": today,
            "due_tasks": due_tasks,
            "due_routines": due_routines,
            "routines": sorted(user.routines, key=lambda r: (r.priority, r.next_due_on)),
            "open_tasks": sorted(
                [t for t in user.tasks if not t.completed],
                key=lambda t: (t.priority, t.due_date or date.max),
            ),
            "recent_rewards": sorted(user.reward_logs, key=lambda r: r.created_at, reverse=True)[:8],
            "flash": _read_flash(request),
            "cadences": CADENCES,
            "active_epic": active,
            "next_story": next_story,
            "current_act": act,
            "act_done": act_done,
            "act_total": act_total,
            "act_pct": act_pct,
            "epic_done": epic_done,
            "epic_total": epic_total,
            "overall_pct": overall_pct,
            "chests": chest_snapshot(db, user, today),
        },
    )


@app.post("/tasks")
def create_task(
    title: str = Form(...),
    notes: str = Form(""),
    priority: int = Form(2),
    due_date: str = Form(""),
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
        # Auto-complete linked stories
        linked = db.scalars(select(Bit).where(Bit.task_id == task.id, Bit.completed.is_(False))).all()
        for bit in linked:
            # ensure act/epic loaded
            _ = bit.act.epic
            flashes.append(complete_bit(db, user, bit))
        db.commit()
    return _flash_redirect("/today", " · ".join(flashes) if flashes else "Already completed")


@app.post("/routines")
def create_routine(
    title: str = Form(...),
    notes: str = Form(""),
    cadence: str = Form(...),
    priority: int = Form(2),
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
        select(Bit).where(Bit.routine_id == routine.id, Bit.completed.is_(False))
    ).all()
    for bit in linked:
        _ = bit.act.epic
        flashes.append(complete_bit(db, user, bit))
    db.commit()
    return _flash_redirect("/today", " · ".join(flashes))


# ---------------------------------------------------------------------------
# Epics (v0.2)
# ---------------------------------------------------------------------------


@app.get("/epics", response_class=HTMLResponse)
def epics_list(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    epics = db.scalars(
        select(Epic)
        .where(Epic.user_id == user.id)
        .options(joinedload(Epic.acts).joinedload(Act.bits))
        .order_by(Epic.created_at.desc())
    ).unique().all()
    rows = []
    for epic in epics:
        done, total, pct = epic_progress(epic)
        rows.append(
            {
                "epic": epic,
                "done": done,
                "total": total,
                "pct": pct,
                "active": user.active_epic_id == epic.id,
            }
        )
    return templates.TemplateResponse(
        "epics.html",
        {
            "request": request,
            "user": user,
            "rows": rows,
            "flash": _read_flash(request),
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
    act_titles: list[str] = Form(...),
    act_bits: list[str] = Form(...),
    act_deliverables: list[str] = Form([]),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Epic title is required.")

    # Pair titles with bits; drop empty trailing slots
    acts_data: list[tuple[str, list[str], str | None]] = []
    for i, raw_title in enumerate(act_titles):
        at = (raw_title or "").strip()
        bits_raw = act_bits[i] if i < len(act_bits) else ""
        bit_lines = [ln.strip() for ln in bits_raw.splitlines() if ln.strip()]
        deliverable = None
        if i < len(act_deliverables):
            deliverable = (act_deliverables[i] or "").strip() or None
        if not at and not bit_lines:
            continue
        if not at:
            raise HTTPException(status_code=400, detail="Each Act needs a title.")
        if not bit_lines:
            raise HTTPException(status_code=400, detail=f"Act “{at}” needs at least one Story (newline-separated).")
        acts_data.append((at, bit_lines, deliverable))

    if len(acts_data) < 2:
        raise HTTPException(status_code=400, detail="An Epic needs at least 2 Acts, each with Stories.")

    epic = Epic(
        user_id=user.id,
        title=title,
        notes=notes.strip() or None,
        legendary=legendary == "on",
        identity_end=identity_end.strip() or None,
        capability_end=capability_end.strip() or None,
        preview_label=preview_label.strip() or None,
    )
    db.add(epic)
    db.flush()
    for sort_i, (at, bit_lines, deliverable) in enumerate(acts_data):
        act = Act(
            epic_id=epic.id,
            title=at,
            sort_order=sort_i,
            deliverable=deliverable,
        )
        db.add(act)
        db.flush()
        for bit_i, bit_title in enumerate(bit_lines):
            db.add(
                Bit(
                    act_id=act.id,
                    title=bit_title,
                    sort_order=bit_i,
                    parallel=True,
                )
            )
    if not user.active_epic_id:
        user.active_epic_id = epic.id
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", "Epic created")


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
    acts_view = []
    for act in sorted(epic.acts, key=lambda a: a.sort_order):
        done, total, pct = act_progress(act)
        acts_view.append(
            {
                "act": act,
                "done": done,
                "total": total,
                "pct": pct,
                "bits": sorted(act.bits, key=lambda b: (b.sort_order, b.id)),
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
            "acts_view": acts_view,
            "epic_done": edone,
            "epic_total": etotal,
            "overall_pct": epct,
            "is_active": user.active_epic_id == epic.id,
            "next_story": next_bit(epic),
            "open_tasks": open_tasks,
            "routines": routines,
            "flash": _read_flash(request),
        },
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


@app.post("/bits/{bit_id}/complete")
def complete_bit_route(
    bit_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    bit = db.get(Bit, bit_id)
    if not bit:
        raise HTTPException(status_code=404, detail="Story not found.")
    act = bit.act
    epic = act.epic
    if epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Story not found.")
    msg = complete_bit(db, user, bit)
    flashes = [msg]
    if "Already" not in msg:
        flashes.extend(record_completion(db, user))
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", " · ".join(flashes))


@app.post("/bits/{bit_id}/link")
def link_bit(
    bit_id: int,
    task_id: str = Form(""),
    routine_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    bit = db.get(Bit, bit_id)
    if not bit:
        raise HTTPException(status_code=404, detail="Story not found.")
    epic = bit.act.epic
    if epic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Story not found.")

    tid = int(task_id) if task_id.strip().isdigit() else None
    rid = int(routine_id) if routine_id.strip().isdigit() else None
    if tid is not None:
        task = db.get(Task, tid)
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=400, detail="Invalid task.")
        bit.task_id = tid
    else:
        bit.task_id = None
    if rid is not None:
        routine = db.get(Routine, rid)
        if not routine or routine.user_id != user.id:
            raise HTTPException(status_code=400, detail="Invalid routine.")
        bit.routine_id = rid
    else:
        bit.routine_id = None
    db.commit()
    return _flash_redirect(f"/epics/{epic.id}", "Story linked")


@app.get("/health")
def health():
    return {"status": "ok"}
