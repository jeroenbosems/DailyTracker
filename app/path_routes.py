"""HTTP helpers for Epic Full/Focused path switching (v0.3.2)."""

from __future__ import annotations

from fastapi import Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.epics_logic import normalize_path, switch_epic_path
from app.models import Epic, User


def apply_path_switch(
    epic: Epic,
    path: str,
    confirm_destructive: str,
    db: Session,
    flash_redirect,
) -> RedirectResponse:
    try:
        target = normalize_path(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    ui_confirm = confirm_destructive == "on"
    msg = switch_epic_path(db, epic, target, confirm_destructive=ui_confirm)
    db.commit()
    return flash_redirect(f"/epics/{epic.id}", msg)
