"""Fixed reward shop — spend earned points on a designer catalog (no DIY prices)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Redemption, User


@dataclass(frozen=True)
class ShopItem:
    id: str
    label: str
    cost: int


# Fixed catalog — code constant only; no user-defined rewards or prices.
SHOP_CATALOG: dict[str, ShopItem] = {
    "break_15": ShopItem("break_15", "Short break (15 min)", 40),
    "snack": ShopItem("snack", "Favorite drink / snack", 80),
    "media_ep": ShopItem("media_ep", "Guilt-free media episode", 100),
    "hobby_hour": ShopItem("hobby_hour", "Hobby hour", 150),
    "meal_out": ShopItem("meal_out", "Nice meal out / takeaway", 300),
    "half_day": ShopItem("half_day", "Half-day off project", 500),
}

# Stable display order (ascending cost)
SHOP_CATALOG_ORDER: tuple[str, ...] = (
    "break_15",
    "snack",
    "media_ep",
    "hobby_hour",
    "meal_out",
    "half_day",
)


class ShopError(Exception):
    """Redeem / fulfill failure with a clear user-facing message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def catalog_items() -> list[ShopItem]:
    return [SHOP_CATALOG[cid] for cid in SHOP_CATALOG_ORDER]


def get_catalog_item(catalog_id: str) -> ShopItem | None:
    return SHOP_CATALOG.get((catalog_id or "").strip())


def redeem(db: Session, user: User, catalog_id: str) -> Redemption:
    """Spend points on a fixed catalog item.

    Raises ShopError if the catalog id is unknown or the user cannot afford it.
    """
    item = get_catalog_item(catalog_id)
    if item is None:
        raise ShopError("Unknown reward. Choose an item from the fixed catalog.")
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
    return row


def set_fulfilled_irl(db: Session, user: User, redemption_id: int, fulfilled: bool) -> Redemption:
    row = db.get(Redemption, redemption_id)
    if not row or row.user_id != user.id:
        raise ShopError("Redemption not found.")
    row.fulfilled_irl = bool(fulfilled)
    return row
