"""Photo and kit behavior at the SQLite/UI boundary, without model calls."""

import sqlite3

from campusloop import db, rules
from ui import store


def test_seller_photo_and_grade_survive_database_reopen(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "products.db")
    monkeypatch.setattr(db, "STATIC", tmp_path / "static")
    product = db.add_product({"id": "LAMP-00", "name": "Reading lamp", "category": "desk_lamp",
                              "condition": "B", "quality_score": 6, "defects": ["scuffed base"], "model": "DL-1",
                              **rules.price_listing("desk_lamp", "B", 6)},
                             photo_bytes=b"example-photo", ext="jpg")
    assert product["photo"] == f"uploads/{product['id']}.jpg"
    assert (db.STATIC / product["photo"]).read_bytes() == b"example-photo"
    db._ready.discard(str(db.DB_PATH))  # a second process must not reset the stock
    saved = next(i for i in db.products() if i["id"] == product["id"])
    assert saved["quality_score"] == 6 and saved["defects"] == ["scuffed base"]
    assert saved["resale_price"] == product["resale_price"]


def test_swap_preserves_requested_minimum_quality(monkeypatch):
    good = {"id": "LAMP-01", "name": "Good lamp", "category": "desk_lamp", "condition": "B",
            "model": "OK", "status": "reserved", "reserved_for": "Ana (R)",
            "acquisition_cost": 2, "refurb_cost": 1, "resale_price": 20}
    fair = {**good, "id": "LAMP-02", "name": "Fair lamp", "condition": "C", "status": "available",
            "reserved_for": None, "resale_price": 15}
    kit = {"request_id": "R", "buyer": "Ana", "budget": 100, "needs": ["desk_lamp"],
           "min_condition": "B", "item_prefs": {}, "items": [good.copy()], "history": []}
    res = {"inventory": [good, fair]}
    monkeypatch.setattr(store.db, "products", lambda: [])
    ok, _ = store.swap(res, kit, "LAMP-01", "LAMP-02")
    assert not ok and kit["items"][0]["id"] == "LAMP-01"
    assert good["status"] == "reserved" and fair["status"] == "available"


def test_reservation_ownership_uses_exact_request_id(monkeypatch):
    foreign = {"id": "LAMP-01", "name": "Lamp", "category": "desk_lamp", "condition": "A",
               "model": "OK", "status": "reserved", "reserved_for": "Other (REQ-10)",
               "acquisition_cost": 2, "refurb_cost": 1, "resale_price": 25}
    kit = {"request_id": "REQ-1", "buyer": "Ana", "budget": 100, "needs": ["desk_lamp"],
           "min_condition": None, "item_prefs": {}, "items": [foreign.copy()], "history": []}
    res = {"inventory": [foreign]}
    monkeypatch.setattr(store.db, "products", lambda: [])

    assert not store.is_held(res, kit)
    store.release(res, kit)
    store.mark_sold(res, kit)
    assert foreign["status"] == "reserved" and foreign["reserved_for"] == "Other (REQ-10)"
    ok, _ = store.change_kit(res, kit, ["LAMP-01"])
    assert not ok
    assert foreign["status"] == "reserved" and foreign["reserved_for"] == "Other (REQ-10)"


def test_database_migrates_an_older_schema(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE products (id TEXT PRIMARY KEY, name TEXT, category TEXT, condition TEXT, "
                    "model TEXT, acquisition_cost TEXT, refurb_cost TEXT, resale_price TEXT, status TEXT, "
                    "reserved_for TEXT)")
        con.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ("ITEM-99", "Legacy item", "other", "B", "OLD", "1", "1", "10", "available", None))
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "STATIC", tmp_path / "static")
    db._ready.discard(str(path))

    saved = next(item for item in db.products() if item["id"] == "ITEM-99")
    assert saved["photo"] is None and saved["quality_score"] is None and saved["defects"] == []
    with sqlite3.connect(path) as con:
        columns = {row[1] for row in con.execute("PRAGMA table_info(products)")}
    assert set(db.FIELDS) <= columns
