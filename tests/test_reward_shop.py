"""v0.5 — fixed reward shop: underfunded reject, redeem decreases points, fulfilled_irl toggle."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Redemption, User
from app.shop import (
    SHOP_CATALOG,
    SHOP_CATALOG_ORDER,
    ShopError,
    catalog_items,
    redeem,
    set_fulfilled_irl,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _user(db: Session, points: int = 0) -> User:
    user = User(username="shopper", password_hash=hash_password("password123"), total_points=points)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_catalog_is_fixed_and_complete():
    items = catalog_items()
    assert [i.id for i in items] == list(SHOP_CATALOG_ORDER)
    expected = {
        "break_15": 40,
        "snack": 80,
        "media_ep": 100,
        "hobby_hour": 150,
        "meal_out": 300,
        "half_day": 500,
    }
    for cid, cost in expected.items():
        assert SHOP_CATALOG[cid].cost == cost
        assert SHOP_CATALOG[cid].label  # non-empty adult productivity label


def test_underfunded_redeem_rejected():
    db = _session()
    user = _user(db, points=39)  # break_15 costs 40
    with pytest.raises(ShopError) as exc:
        redeem(db, user, "break_15")
    assert "not enough points" in exc.value.message.lower()
    db.rollback()
    db.refresh(user)
    assert user.total_points == 39
    assert db.scalars(select(Redemption).where(Redemption.user_id == user.id)).all() == []


def test_successful_redeem_decreases_points():
    db = _session()
    user = _user(db, points=250)
    row = redeem(db, user, "hobby_hour")  # 150
    db.commit()
    db.refresh(user)
    db.refresh(row)
    assert user.total_points == 100
    assert row.catalog_id == "hobby_hour"
    assert row.points_spent == 150
    assert row.fulfilled_irl is False
    rows = db.scalars(select(Redemption).where(Redemption.user_id == user.id)).all()
    assert len(rows) == 1

    # Second redeem that would overspend
    with pytest.raises(ShopError):
        redeem(db, user, "meal_out")  # 300 > 100
    db.rollback()
    db.refresh(user)
    assert user.total_points == 100


def test_fulfilled_irl_toggle():
    db = _session()
    user = _user(db, points=80)
    row = redeem(db, user, "snack")
    db.commit()
    db.refresh(row)
    assert row.fulfilled_irl is False

    updated = set_fulfilled_irl(db, user, row.id, True)
    db.commit()
    db.refresh(updated)
    assert updated.fulfilled_irl is True

    updated = set_fulfilled_irl(db, user, row.id, False)
    db.commit()
    db.refresh(updated)
    assert updated.fulfilled_irl is False


def test_unknown_catalog_id_rejected():
    db = _session()
    user = _user(db, points=999)
    with pytest.raises(ShopError) as exc:
        redeem(db, user, "custom_loot")
    assert "unknown" in exc.value.message.lower()
    db.rollback()
    assert user.total_points == 999


def test_http_shop_redeem_and_fulfill(tmp_path, monkeypatch):
    """Integration: underfunded → 400; redeem decreases pts; fulfilled toggle."""
    from datetime import date

    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-v05")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(database, "DATABASE_URL", f"sqlite:///{db_path}")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    database.engine = engine
    database.SessionLocal = sa_sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    database._migrate_schema()

    def _override_db():
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[database.get_db] = _override_db
    client = TestClient(main.app)
    try:
        r = client.post(
            "/setup",
            data={
                "username": "alice",
                "password": "password123",
                "password_confirm": "password123",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303

        # Seed points via a completed task (Gold = 50) — still underfunded for snack (80)
        client.post(
            "/tasks",
            data={
                "title": "Earn a little",
                "priority": "1",
                "due_date": date.today().isoformat(),
                "life_mode": "",
            },
            follow_redirects=False,
        )
        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            assert user is not None
            task_id = user.tasks[0].id
        finally:
            db.close()
        client.post(f"/tasks/{task_id}/complete", follow_redirects=False)

        under = client.post(
            "/shop/redeem",
            data={"catalog_id": "snack"},
            follow_redirects=False,
        )
        assert under.status_code == 400
        assert "not enough points" in under.text.lower()

        # Top up points and redeem successfully
        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            assert user is not None
            user.total_points = 200
            db.commit()
        finally:
            db.close()

        ok = client.post(
            "/shop/redeem",
            data={"catalog_id": "snack"},
            follow_redirects=False,
        )
        assert ok.status_code == 303
        assert "/shop" in ok.headers.get("location", "")

        db = database.SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "alice"))
            assert user is not None
            assert user.total_points == 120  # 200 - 80
            red = db.scalars(select(Redemption).where(Redemption.user_id == user.id)).one()
            assert red.catalog_id == "snack"
            assert red.fulfilled_irl is False
            rid = red.id
        finally:
            db.close()

        toggle = client.post(
            f"/shop/redemptions/{rid}/fulfilled",
            data={"fulfilled_irl": "on"},
            follow_redirects=False,
        )
        assert toggle.status_code == 303

        db = database.SessionLocal()
        try:
            red = db.get(Redemption, rid)
            assert red is not None
            assert red.fulfilled_irl is True
        finally:
            db.close()

        # Today: pts link to shop; no shop section above Due now
        today = client.get("/today")
        assert today.status_code == 200
        body = today.text
        assert 'href="/shop"' in body
        assert "class=\"points\"" in body or "class='points'" in body or 'class="points"' in body
        assert "Due now" in body
        # Must not inject a Reward shop card before Due now
        assert "Reward shop" not in body.split("Due now")[0]
        assert body.index("Due now") < body.index("Active Epic")
    finally:
        main.app.dependency_overrides.clear()
