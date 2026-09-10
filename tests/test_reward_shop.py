"""v1.2 G1 — cosmetic shop: fixed SKUs, underfunded reject, no IRL fulfill UI."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models import Redemption, User
from app.shop import (
    LEGACY_IRL_IDS,
    SHOP_CATALOG,
    SHOP_CATALOG_ORDER,
    ShopError,
    catalog_items,
    history_label,
    redeem,
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


def test_catalog_is_fixed_cosmetics_only():
    items = catalog_items()
    assert [i.id for i in items] == list(SHOP_CATALOG_ORDER)
    assert set(SHOP_CATALOG) == set(SHOP_CATALOG_ORDER)
    assert not (set(SHOP_CATALOG) & LEGACY_IRL_IDS)
    for item in items:
        assert item.kind in {"theme", "title", "badge_frame", "today_flair"}
        assert item.cost > 0
        assert item.unlock_payload


def test_underfunded_redeem_rejected():
    db = _session()
    user = _user(db, points=59)  # frame_bronze costs 60
    with pytest.raises(ShopError) as exc:
        redeem(db, user, "frame_bronze")
    assert "not enough points" in exc.value.message.lower()
    db.rollback()
    db.refresh(user)
    assert user.total_points == 59
    assert db.scalars(select(Redemption).where(Redemption.user_id == user.id)).all() == []


def test_successful_redeem_decreases_points():
    db = _session()
    user = _user(db, points=250)
    row = redeem(db, user, "title_pathfinder")  # 100
    db.commit()
    db.refresh(user)
    db.refresh(row)
    assert user.total_points == 150
    assert row.catalog_id == "title_pathfinder"
    assert row.points_spent == 100

    with pytest.raises(ShopError):
        redeem(db, user, "title_finisher")  # 250 > 150
    db.rollback()
    db.refresh(user)
    assert user.total_points == 150


def test_legacy_irl_ids_not_redeemable():
    db = _session()
    user = _user(db, points=999)
    with pytest.raises(ShopError):
        redeem(db, user, "snack")
    assert "Legacy IRL" in history_label("snack")


def test_unknown_catalog_id_rejected():
    db = _session()
    user = _user(db, points=999)
    with pytest.raises(ShopError) as exc:
        redeem(db, user, "custom_loot")
    assert "unknown" in exc.value.message.lower()
    db.rollback()
    assert user.total_points == 999


def test_http_shop_unlock_no_irl(tmp_path, monkeypatch):
    from datetime import date

    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker as sa_sessionmaker

    import app.config as config
    import app.database as database
    import app.main as main

    db_path = tmp_path / "dailytracker.db"
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-g1")
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
            data={"catalog_id": "theme_aurora"},
            follow_redirects=False,
        )
        assert under.status_code == 400
        assert "not enough points" in under.text.lower()

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
            data={"catalog_id": "theme_aurora"},
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
            assert red.catalog_id == "theme_aurora"
        finally:
            db.close()

        # IRL fulfill route gone
        gone = client.post(
            "/shop/redemptions/1/fulfilled",
            data={"fulfilled_irl": "on"},
            follow_redirects=False,
        )
        assert gone.status_code == 404

        shop = client.get("/shop")
        assert shop.status_code == 200
        assert "Cosmetic shop" in shop.text
        assert "Done in real life" not in shop.text
        assert "break_15" not in shop.text
        assert "Aurora theme" in shop.text

        today = client.get("/today")
        assert today.status_code == 200
        body = today.text
        assert 'href="/shop"' in body
        assert "Due now" in body
        assert "Cosmetic shop" not in body.split("Due now")[0]
        assert "Reward shop" not in body.split("Due now")[0]
        assert body.index("Due now") < body.index("Active Epic")
    finally:
        main.app.dependency_overrides.clear()


def test_shop_template_afford_need_copy():
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from types import SimpleNamespace

    env = Environment(
        loader=FileSystemLoader(str(Path("app/templates"))),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("shop.html")
    user = SimpleNamespace(total_points=70, username="u")
    html = tmpl.render(
        request=SimpleNamespace(),
        user=user,
        catalog=catalog_items(),
        history=[],
        flash=None,
    )
    assert "Afford" in html  # frame_bronze 60
    assert "Need 10 more" in html  # theme_aurora 80 - 70
    assert "Need 20 more" in html  # flair_spark 90 - 70
    assert "Done in real life" not in html
    assert "Unlock" in html
