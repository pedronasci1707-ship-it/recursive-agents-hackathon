"""Photo and kit behavior at the SQLite/UI boundary, without model calls."""

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
