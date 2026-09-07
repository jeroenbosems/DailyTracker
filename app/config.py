from __future__ import annotations

import os
import secrets
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'dailytracker.db'}"

_SECRET_FILE = DATA_DIR / ".session_secret"


def get_session_secret() -> str:
    env = os.environ.get("SESSION_SECRET")
    if env:
        return env
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(32)
    _SECRET_FILE.write_text(secret, encoding="utf-8")
    try:
        _SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return secret


SESSION_COOKIE = "dt_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 14  # 14 days
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "").lower() in {"1", "true", "yes"}

# Fixed standardized reward tiers (not user-configurable)
REWARD_TIERS = {
    "bronze": {"label": "Bronze", "points": 10, "min_priority": 3},
    "silver": {"label": "Silver", "points": 25, "min_priority": 2},
    "gold": {"label": "Gold", "points": 50, "min_priority": 1},
}
