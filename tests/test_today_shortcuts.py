"""BL-023 — Today keyboard shortcuts legend + wiring."""

from pathlib import Path


def test_today_shortcut_legend_and_script():
    today = Path("app/templates/today.html").read_text()
    assert "shortcut-complete-next-step" in today
    assert "today-shortcuts.js" in today
    assert "shortcuts-legend" in today
    assert ">c</kbd>" in today or "kbd class=\"kbd\">c</kbd>" in today
    assert ">r</kbd>" in today or "kbd class=\"kbd\">r</kbd>" in today

    js = Path("app/static/today-shortcuts.js").read_text()
    assert "shortcut-complete-next-step" in js
    assert "/review" in js
    assert "textarea" in js  # ignore while typing


def test_acceptance_documents_shortcuts():
    acc = Path("docs/ACCEPTANCE.md").read_text()
    assert "Keyboard shortcuts" in acc
    assert "`c`" in acc or "c completes" in acc
