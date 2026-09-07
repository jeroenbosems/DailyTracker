from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    active_epic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tasks: Mapped[list[Task]] = relationship(back_populates="user", cascade="all, delete-orphan")
    routines: Mapped[list[Routine]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reward_logs: Mapped[list[RewardLog]] = relationship(back_populates="user", cascade="all, delete-orphan")
    epics: Mapped[list[Epic]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Epic.user_id",
    )
    chest_progress: Mapped[list[ChestProgress]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="tasks")


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    completion_count: Mapped[int] = mapped_column(Integer, default=0)
    last_completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="routines")


class RewardLog(Base):
    __tablename__ = "reward_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="reward_logs")


class Epic(Base):
    """Month-scale ambition goal (Legendary when flagged)."""

    __tablename__ = "epics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_epic_id: Mapped[int | None] = mapped_column(ForeignKey("epics.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    legendary: Mapped[bool] = mapped_column(Boolean, default=True)
    identity_end: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capability_end: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(
        back_populates="epics", foreign_keys=[user_id]
    )
    parent: Mapped[Epic | None] = relationship(
        remote_side=[id], foreign_keys=[parent_epic_id]
    )
    acts: Mapped[list[Act]] = relationship(
        back_populates="epic", cascade="all, delete-orphan", order_by="Act.sort_order"
    )


class Act(Base):
    """Week-scale Feature / chapter inside an Epic."""

    __tablename__ = "acts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    epic_id: Mapped[int] = mapped_column(ForeignKey("epics.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deliverable: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    epic: Mapped[Epic] = relationship(back_populates="acts")
    bits: Mapped[list[Bit]] = relationship(
        back_populates="act", cascade="all, delete-orphan", order_by="Bit.sort_order"
    )


class Bit(Base):
    """Day-scale Story / checklist item inside an Act."""

    __tablename__ = "bits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    act_id: Mapped[int] = mapped_column(ForeignKey("acts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    parallel: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    routine_id: Mapped[int | None] = mapped_column(ForeignKey("routines.id"), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    act: Mapped[Act] = relationship(back_populates="bits")


class ChestDef(Base):
    """Fixed N-of-M daily/weekly completion chest."""

    __tablename__ = "chest_defs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)  # daily | weekly
    need_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False)
    glory_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    glory_points: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(120), nullable=False)


class ChestProgress(Base):
    __tablename__ = "chest_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    chest_def_id: Mapped[int] = mapped_column(ForeignKey("chest_defs.id"), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)  # YYYY-MM-DD or YYYY-Www
    completions: Mapped[int] = mapped_column(Integer, default=0)
    chest_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    glory_granted: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="chest_progress")
