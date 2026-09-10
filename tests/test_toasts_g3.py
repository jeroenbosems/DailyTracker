"""G3 — toast JS + title unlock flash copy."""

from pathlib import Path


def test_toast_script_and_base_include():
    assert Path("app/static/toast.js").is_file()
    base = Path("app/templates/base.html").read_text()
    assert "toast.js" in base
    css = Path("app/static/style.css").read_text()
    assert "toast-celebrate" in css or ".flash.toast" in css


def test_today_and_shop_mark_celebration_flash():
    today = Path("app/templates/today.html").read_text()
    shop = Path("app/templates/shop.html").read_text()
    assert "toast-celebrate" in today
    assert "toast-celebrate" in shop


def test_title_unlock_flash_copy():
    main = Path("app/main.py").read_text()
    assert "Title unlocked:" in main
