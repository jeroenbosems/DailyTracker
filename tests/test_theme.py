"""BL-024 — theme toggle wiring (CSS + localStorage)."""

from pathlib import Path


def test_theme_files_and_settings_toggle():
    base = Path("app/templates/base.html").read_text()
    assert "dt-theme" in base
    assert 'data-theme' in base
    assert "theme.js" in base

    css = Path("app/static/style.css").read_text()
    assert 'data-theme="light"' in css

    js = Path("app/static/theme.js").read_text()
    assert "localStorage" in js
    assert "dt-theme" in js

    settings = Path("app/templates/settings.html").read_text()
    assert "Appearance" in settings
    assert "data-theme-toggle" in settings


def test_acceptance_documents_theme():
    acc = Path("docs/ACCEPTANCE.md").read_text()
    assert "BL-024" in acc
