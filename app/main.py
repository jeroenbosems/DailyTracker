from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    read_session_token,
    verify_password,
)
from app.config import SECURE_COOKIES, SESSION_MAX_AGE
from app.database import get_db, init_db
from app.models import Routine, Task, User
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
    due_tasks, due_routines = _due_now(user, today)
    flash = request.query_params.get("flash")
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
            "flash": flash,
            "cadences": CADENCES,
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
    return RedirectResponse("/today?flash=Task+created", status_code=303)


@app.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    task = db.get(Task, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found.")
    if not task.completed:
        task.completed = True
        task.completed_at = datetime.now(timezone.utc)
        grant_reward(db, user, task.priority, f"Completed task: {task.title}")
        db.commit()
    return RedirectResponse("/today?flash=Task+completed", status_code=303)


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
    return RedirectResponse("/today?flash=Routine+created", status_code=303)


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
            return RedirectResponse("/today?flash=Already+completed+today", status_code=303)
        if routine.last_completed_on and routine.cadence != "daily":
            from app.routines_logic import period_start

            if period_start(routine.cadence, routine.last_completed_on) == period_start(routine.cadence, today):
                return RedirectResponse("/today?flash=Already+completed+this+period", status_code=303)
        routine.streak += 1
    else:
        routine.streak = 1
    routine.best_streak = max(routine.best_streak, routine.streak)
    routine.completion_count += 1
    routine.last_completed_on = today
    routine.next_due_on = advance_due(routine.cadence, today)
    grant_reward(db, user, routine.priority, f"Completed {routine.cadence} routine: {routine.title}")
    db.commit()
    return RedirectResponse("/today?flash=Routine+completed", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok"}
