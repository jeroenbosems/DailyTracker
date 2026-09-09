"""v1.1 BL-020 — title substring search across Tasks / Routines / Epics / Steps."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Epic, Phase, Routine, Step, Task, User


@dataclass
class SearchHit:
    kind: str  # task | routine | epic | step
    id: int
    title: str
    href: str
    meta: str = ""


def search_user(db: Session, user: User, query: str, *, limit: int = 50) -> list[SearchHit]:
    q = (query or "").strip()
    if len(q) < 1:
        return []
    needle = q.casefold()
    hits: list[SearchHit] = []

    for t in db.scalars(select(Task).where(Task.user_id == user.id)).all():
        if needle in (t.title or "").casefold():
            hits.append(
                SearchHit(
                    kind="task",
                    id=t.id,
                    title=t.title,
                    href="/today",
                    meta="Task" + (" · done" if t.completed else " · open"),
                )
            )

    for r in db.scalars(select(Routine).where(Routine.user_id == user.id)).all():
        if needle in (r.title or "").casefold():
            hits.append(
                SearchHit(
                    kind="routine",
                    id=r.id,
                    title=r.title,
                    href="/today",
                    meta=f"Routine · {r.cadence}",
                )
            )

    for e in db.scalars(select(Epic).where(Epic.user_id == user.id)).all():
        if needle in (e.title or "").casefold():
            hits.append(
                SearchHit(
                    kind="epic",
                    id=e.id,
                    title=e.title,
                    href=f"/epics/{e.id}",
                    meta="Epic" + (" · done" if e.completed else ""),
                )
            )

    for e in db.scalars(
        select(Epic)
        .where(Epic.user_id == user.id)
        .options(joinedload(Epic.phases).joinedload(Phase.steps))
    ).unique().all():
        for ph in e.phases:
            for st in ph.steps:
                if needle in (st.title or "").casefold():
                    hits.append(
                        SearchHit(
                            kind="step",
                            id=st.id,
                            title=st.title,
                            href=f"/epics/{e.id}",
                            meta=f"Step · {e.title}" + (" · done" if st.completed else ""),
                        )
                    )

    order = {"epic": 0, "step": 1, "task": 2, "routine": 3}
    hits.sort(key=lambda h: (order.get(h.kind, 9), h.title.casefold()))
    return hits[:limit]
