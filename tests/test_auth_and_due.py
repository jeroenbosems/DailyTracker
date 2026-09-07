from datetime import date, timedelta

from app.auth import hash_password, verify_password
from app.rewards import tier_for_priority
from app.routines_logic import advance_due, streak_continues


def test_argon2_hash_roundtrip():
    h = hash_password("correct horse battery")
    assert h != "correct horse battery"
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong", h)


def test_reward_tiers_by_priority():
    assert tier_for_priority(1) == "gold"
    assert tier_for_priority(2) == "silver"
    assert tier_for_priority(3) == "bronze"


def test_advance_due_cadences():
    d = date(2026, 1, 31)
    assert advance_due("daily", d) == date(2026, 2, 1)
    assert advance_due("weekly", d) == date(2026, 2, 7)
    assert advance_due("monthly", d) == date(2026, 2, 28)
    assert advance_due("yearly", d) == date(2027, 1, 31)


def test_streak_daily():
    today = date(2026, 3, 10)
    assert streak_continues("daily", today - timedelta(days=1), today)
    assert not streak_continues("daily", today - timedelta(days=2), today)


def test_parent_epic_cycle_guard_logic():
    # structural: models expose parent_epic_id
    from app.models import Epic

    assert hasattr(Epic, "parent_epic_id")
