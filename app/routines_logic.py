from __future__ import annotations

from datetime import date, timedelta
from calendar import monthrange


CADENCES = ("daily", "weekly", "monthly", "yearly")


def advance_due(cadence: str, from_day: date) -> date:
    if cadence == "daily":
        return from_day + timedelta(days=1)
    if cadence == "weekly":
        return from_day + timedelta(days=7)
    if cadence == "monthly":
        year, month = from_day.year, from_day.month + 1
        if month > 12:
            year += 1
            month = 1
        day = min(from_day.day, monthrange(year, month)[1])
        return date(year, month, day)
    if cadence == "yearly":
        year = from_day.year + 1
        day = min(from_day.day, monthrange(year, from_day.month)[1])
        return date(year, from_day.month, day)
    raise ValueError(f"Unknown cadence: {cadence}")


def period_start(cadence: str, day: date) -> date:
    if cadence == "daily":
        return day
    if cadence == "weekly":
        return day - timedelta(days=day.weekday())
    if cadence == "monthly":
        return day.replace(day=1)
    if cadence == "yearly":
        return day.replace(month=1, day=1)
    raise ValueError(f"Unknown cadence: {cadence}")


def streak_continues(cadence: str, last_completed: date | None, today: date) -> bool:
    if last_completed is None:
        return False
    # Still in the same period, or completed the immediately previous period
    if period_start(cadence, last_completed) == period_start(cadence, today):
        return True
    # Previous period relative to today
    if cadence == "daily":
        return last_completed == today - timedelta(days=1)
    if cadence == "weekly":
        prev = period_start(cadence, today) - timedelta(days=7)
        return period_start(cadence, last_completed) == prev
    if cadence == "monthly":
        first = today.replace(day=1)
        prev_month_last = first - timedelta(days=1)
        return period_start(cadence, last_completed) == prev_month_last.replace(day=1)
    if cadence == "yearly":
        return last_completed.year == today.year - 1
    return False
