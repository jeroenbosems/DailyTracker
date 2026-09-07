"""Life-mode tags and Today filter helpers (v0.4)."""

from __future__ import annotations

import json
from typing import Any

LIFE_MODES: tuple[str, ...] = ("work", "health", "home", "learning")
LIFE_MODE_LABELS: dict[str, str] = {
    "work": "Work",
    "health": "Health",
    "home": "Home",
    "learning": "Learning",
}


def normalize_life_mode(raw: Any) -> str | None:
    """Single optional life_mode for Task / Routine / Step. Empty → None."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("life_mode must be a string when present.")
    value = raw.strip().lower()
    if not value:
        return None
    if value not in LIFE_MODES:
        raise ValueError(f"life_mode must be one of: {', '.join(LIFE_MODES)}.")
    return value


def normalize_life_modes(raw: Any) -> list[str]:
    """Epic multi-select → ordered unique list. Accepts list or JSON string."""
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("life_modes must be a JSON array of mode strings.") from exc
        raw = parsed
    if not isinstance(raw, list):
        raise ValueError("life_modes must be a list of mode strings.")
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        mode = normalize_life_mode(item)
        if mode and mode not in seen:
            seen.add(mode)
            out.append(mode)
    return out


def life_modes_to_json(modes: list[str] | None) -> str:
    return json.dumps(normalize_life_modes(modes or []), separators=(",", ":"))


def life_modes_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        return normalize_life_modes(raw)
    except ValueError:
        return []


def parse_filter_mode(raw: str | None) -> str | None:
    """Today ?mode= query. None / empty / all → no filter."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value or value == "all":
        return None
    if value not in LIFE_MODES:
        return None
    return value


def matches_single_mode(item_mode: str | None, filter_mode: str | None) -> bool:
    """Under a mode filter: tagged that mode OR untagged. All shows everything."""
    if filter_mode is None:
        return True
    if item_mode is None or item_mode == "":
        return True
    return item_mode == filter_mode


def matches_epic_modes(life_modes_json: str | None, filter_mode: str | None) -> bool:
    if filter_mode is None:
        return True
    modes = life_modes_from_json(life_modes_json)
    if not modes:
        return True  # untagged epic
    return filter_mode in modes
