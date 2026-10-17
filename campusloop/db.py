"""Product database (SQLite): every item for sale, with its photo and quality grade.

The catalog in data/catalog.json seeds the table on first use (and stays in sync with it);
items that students sell through the app are added with their uploaded photo.
"""

import json
import os
import sqlite3
import threading
from pathlib import Path

from . import rules

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("CAMPUSLOOP_DB", ROOT / "data" / "campusloop.db"))
STATIC = ROOT / "static"
FIELDS = ["id", "name", "category", "condition", "quality_score", "defects", "model", "color", "style",
          "acquisition_cost", "refurb_cost", "resale_price", "status", "reserved_for", "photo", "source"]

_lock = threading.Lock()
_ready = set()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    if str(DB_PATH) not in _ready:
        with _lock:
            con.execute(f"CREATE TABLE IF NOT EXISTS products ({', '.join(f + ' TEXT' for f in FIELDS)}, "
                        "PRIMARY KEY (id))")
            _seed(con)
            _ready.add(str(DB_PATH))
    return con


def _seed(con):
    """Catalog rows always match catalog.json; rows added by sellers are kept."""
    for item in rules.load("catalog.json"):
        photo = f"products/{item['id']}.jpg" if (STATIC / "products" / f"{item['id']}.jpg").exists() else ""
        _write(con, {**item, "photo": photo, "source": "catalog"})
    con.commit()


def _write(con, item):
    row = {f: item.get(f) for f in FIELDS}
    row["defects"] = json.dumps(item.get("defects") or [])
    con.execute(f"INSERT OR REPLACE INTO products ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
                [row[f] for f in FIELDS])


def _row(r):
    item = dict(r)
    for f in ("acquisition_cost", "refurb_cost", "resale_price"):
        item[f] = float(item[f]) if item[f] not in (None, "") else 0.0
    item["quality_score"] = int(item["quality_score"]) if item["quality_score"] not in (None, "") else None
    item["defects"] = json.loads(item["defects"] or "[]")
    item["reserved_for"] = item["reserved_for"] or None
    return item


def products():
    """Every product in the database, in id order (fresh dicts: safe to mutate)."""
    with _connect() as con:
        return [_row(r) for r in con.execute("SELECT * FROM products ORDER BY id")]


def add_product(item, photo_bytes=None, ext="jpg"):
    """Insert a product sold through the app; saves its photo under static/uploads/. Returns the stored item."""
    with _connect() as con:
        prefix = item["id"].split("-")[0] if item.get("id") else "ITEM"
        nums = [int(r[0].split("-")[1]) for r in con.execute("SELECT id FROM products WHERE id LIKE ?", (prefix + "-%",))
                if r[0].split("-")[1].isdigit()]
        item = {**item, "id": f"{prefix}-{max(nums, default=0) + 1:02d}", "status": "available",
                "reserved_for": None, "source": "seller"}
        if photo_bytes:
            (STATIC / "uploads").mkdir(parents=True, exist_ok=True)
            (STATIC / "uploads" / f"{item['id']}.{ext}").write_bytes(photo_bytes)
            item["photo"] = f"uploads/{item['id']}.{ext}"
        _write(con, item)
        con.commit()
    return item
