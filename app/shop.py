"""Fixed cosmetic / title shop — spend earned points on designer SKUs (no DIY, no IRL)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Redemption, User

LEGACY_IRL_IDS = frozenset(
    {"break_15", "snack", "media_ep", "hobby_hour", "meal_out", "half_day"}
)


@dataclass(frozen=True)
class ShopItem:
    id: str
    kind: str  # theme | title | badge_frame | today_flair
    label: str
    cost: int
    unlock_payload: str


SHOP_CATALOG: dict[str, ShopItem] = {
    "theme_aurora": ShopItem("theme_aurora", "theme", "Aurora theme", 80, "aurora"),
    "theme_ember": ShopItem("theme_ember", "theme", "Ember theme", 120, "ember"),
    "title_pathfinder": ShopItem(
        "title_pathfinder", "title", "Title: Pathfinder", 100, "Pathfinder"
    ),
    "title_steady": ShopItem(
        "title_steady", "title", "Title: Steady Hand", 150, "Steady Hand"
    ),
    "title_finisher": ShopItem(
        "title_finisher", "title", "Title: Finisher", 250, "Finisher"
    ),
    "frame_bronze": ShopItem(
        "frame_bronze", "badge_frame", "Bronze badge frame", 60, "frame-bronze"
    ),
    "frame_silver": ShopItem(
        "frame_silver", "badge_frame", "Silver badge frame", 140, "frame-silver"
    ),
    "flair_spark": ShopItem(
        "flair_spark", "today_flair", "Today spark flair", 90, "flair-spark"
    ),
}

SHOP_CATALOG_ORDER: tuple[str, ...] = (
    "frame_bronze",
    "theme_aurora",
    "flair_spark",
    "title_pathfinder",
    "theme_ember",
    "frame_silver",
    "title_steady",
    "title_finisher",
)

KIND_EQUIP_ATTR = {
    "theme": "equipped_theme",
    "title": "equipped_title",
    "badge_frame": "equipped_badge_frame",
    "today_flair": "equipped_today_flair",
}


class ShopError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def catalog_items() -> list[ShopItem]:
    return [SHOP_CATALOG[cid] for cid in SHOP_CATALOG_ORDER]


def get_catalog_item(catalog_id: str) -> ShopItem | None:
    return SHOP_CATALOG.get((catalog_id or "").strip())


def history_label(catalog_id: str) -> str:
    item = get_catalog_item(catalog_id)
    if item:
        return item.label
    if catalog_id in LEGACY_IRL_IDS:
        return f"Legacy IRL reward (retired) · {catalog_id}"
    return catalog_id or "Unknown"


def is_legacy_irl(catalog_id: str) -> bool:
    return (catalog_id or "") in LEGACY_IRL_IDS


def unlocked_ids(db: Session, user: User) -> set[str]:
    return {row.catalog_id for row in user.redemptions if row.catalog_id in SHOP_CATALOG}


def redeem(db: Session, user: User, catalog_id: str) -> Redemption:
    item = get_catalog_item(catalog_id)
    if item is None:
        raise ShopError("Unknown unlock. Choose an item from the fixed catalog.")
    if catalog_id in unlocked_ids(db, user):
        raise ShopError(f"“{item.label}” is already unlocked.")
    if user.total_points < item.cost:
        raise ShopError(
            f"Not enough points. “{item.label}” costs {item.cost} pts; "
            f"you have {user.total_points} pts."
        )
    user.total_points -= item.cost
    row = Redemption(
        user_id=user.id,
        catalog_id=item.id,
        points_spent=item.cost,
        fulfilled_irl=False,
    )
    db.add(row)
    attr = KIND_EQUIP_ATTR.get(item.kind)
    if attr and not getattr(user, attr, None):
        setattr(user, attr, item.id)
    return row


def wear(db: Session, user: User, catalog_id: str) -> ShopItem:
    item = get_catalog_item(catalog_id)
    if item is None:
        raise ShopError("Unknown unlock. Choose an item from the fixed catalog.")
    if catalog_id not in unlocked_ids(db, user):
        raise ShopError(f"“{item.label}” is locked. Unlock it in the shop first.")
    attr = KIND_EQUIP_ATTR.get(item.kind)
    if not attr:
        raise ShopError("That item cannot be equipped.")
    setattr(user, attr, item.id)
    return item


def title_label_for_user(user: User) -> str | None:
    item = get_catalog_item(getattr(user, "equipped_title", None) or "")
    return item.unlock_payload if item else None


def theme_payload_for_user(user: User) -> str | None:
    item = get_catalog_item(getattr(user, "equipped_theme", None) or "")
    return item.unlock_payload if item else None


def frame_class_for_user(user: User) -> str:
    item = get_catalog_item(getattr(user, "equipped_badge_frame", None) or "")
    return item.unlock_payload if item else ""


def flair_class_for_user(user: User) -> str:
    item = get_catalog_item(getattr(user, "equipped_today_flair", None) or "")
    return item.unlock_payload if item else ""
