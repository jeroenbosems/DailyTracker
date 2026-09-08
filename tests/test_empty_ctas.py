"""v0.8 — empty states expose one clear CTA."""

from pathlib import Path


def test_today_epics_shop_empty_ctas():
    today = Path("app/templates/today.html").read_text()
    assert "Choose an Epic" in today
    assert 'href="/epics"' in today
    assert "Add a task" in today
    assert 'href="#add-task"' in today

    epics = Path("app/templates/epics.html").read_text()
    assert "Create an Epic" in epics
    assert 'href="#new-epic"' in epics

    shop = Path("app/templates/shop.html").read_text()
    assert "Earn points on Today" in shop
    assert 'href="/today"' in shop
