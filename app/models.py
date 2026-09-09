from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
    period_bonus_progress: Mapped[list[PeriodBonusProgress]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    watch_items: Mapped[list[WatchItem]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    redemptions: Mapped[list[Redemption]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_task_user_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    life_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="tasks")


class Routine(Base):
    __tablename__ = "routines"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_routine_user_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cadence: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    life_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    completion_count: Mapped[int] = mapped_column(Integer, default=0)
    last_completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_skipped_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="routines")


class RewardLog(Base):
    __tablename__ = "reward_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_reward_user_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="reward_logs")


class Epic(Base):
    """Month-scale ambition goal (Legendary when flagged)."""

    __tablename__ = "epics"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_epic_user_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parent_epic_id: Mapped[int | None] = mapped_column(ForeignKey("epics.id"), nullable=True)
    follows_epic_id: Mapped[int | None] = mapped_column(ForeignKey("epics.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    legendary: Mapped[bool] = mapped_column(Boolean, default=True)
    identity_end: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capability_end: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    path: Mapped[str] = mapped_column(String(16), default="full")  # full | focused
    life_modes: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of life modes
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(
        back_populates="epics", foreign_keys=[user_id]
    )
    parent: Mapped[Epic | None] = relationship(
        remote_side=[id], foreign_keys=[parent_epic_id]
    )
    phases: Mapped[list[Phase]] = relationship(
        back_populates="epic", cascade="all, delete-orphan", order_by="Phase.sort_order"
    )


class Phase(Base):
    """Week-scale chapter inside an Epic."""

    __tablename__ = "phases"
    __table_args__ = (
        UniqueConstraint("epic_id", "external_id", name="uq_phase_epic_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    epic_id: Mapped[int] = mapped_column(ForeignKey("epics.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deliverable: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parked: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    epic: Mapped[Epic] = relationship(back_populates="phases")
    steps: Mapped[list[Step]] = relationship(
        back_populates="phase", cascade="all, delete-orphan", order_by="Step.sort_order"
    )


class Step(Base):
    """Day-scale next action inside a Phase."""

    __tablename__ = "steps"
    __table_args__ = (
        UniqueConstraint("phase_id", "external_id", name="uq_step_phase_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phase_id: Mapped[int] = mapped_column(ForeignKey("phases.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    parallel: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    life_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    routine_id: Mapped[int | None] = mapped_column(ForeignKey("routines.id"), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    phase: Mapped[Phase] = relationship(back_populates="steps")


class PeriodBonusDef(Base):
    """Fixed N-of-M daily/weekly period bonus definition."""

    __tablename__ = "period_bonus_defs"

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


class PeriodBonusProgress(Base):
    __tablename__ = "period_bonus_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    period_bonus_def_id: Mapped[int] = mapped_column(
        ForeignKey("period_bonus_defs.id"), nullable=False
    )
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)  # YYYY-MM-DD or YYYY-Www
    completions: Mapped[int] = mapped_column(Integer, default=0)
    bonus_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    glory_granted: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="period_bonus_progress")


class WatchItem(Base):
    """Pinned Step or Task on Today Watch / Nearly done (max 6 per user)."""

    __tablename__ = "watch_items"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "ref_id", name="uq_watch_user_kind_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # step | task
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="watch_items")


class Redemption(Base):
    """Spend of fixed shop catalog points (v0.5)."""

    __tablename__ = "redemptions"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_redemption_user_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    catalog_id: Mapped[str] = mapped_column(String(32), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    fulfilled_irl: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="redemptions")
