"""Deterministic business rules: pricing, margins, recalls and kit verification.

The LLM agents decide; this module is the ground truth they are checked against.
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"

MIN_MARGIN_PCT = 30.0
DELIVERY_COST = 20.0          # our cost to deliver one kit
BUDGET_TOLERANCE_PCT = 10.0   # up to 10% over budget -> a human may approve it

CATEGORIES = [
    "mini_fridge", "microwave", "desk_lamp", "fan", "desk_chair",
    "desk", "storage_bins", "shelf", "kitchen_basics", "other",
]
# Resale price for a condition-A item, by category (USD)
BASE_RESALE = {
    "mini_fridge": 95, "microwave": 55, "desk_lamp": 22, "fan": 28, "desk_chair": 70,
    "desk": 75, "storage_bins": 18, "shelf": 40, "kitchen_basics": 45, "other": 20,
}
CONDITION_FACTOR = {"A": 1.0, "B": 0.75, "C": 0.5}
REFURB_COST = {
    "mini_fridge": 10, "microwave": 5, "desk_chair": 8, "desk": 10,
    "fan": 3, "shelf": 4, "kitchen_basics": 6,
}
ACQUISITION_SHARE = 0.35      # we offer sellers 35% of the expected resale price


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def recall_list():
    return load("recalls.json")["models"]


def _norm(model):
    return re.sub(r"[^A-Z0-9]", "", str(model or "").upper())


def recall_reason(model, recalls):
    """Recall description if the model number matches a recalled one, else None."""
    m = _norm(model)
    if not m:
        return None
    for recalled, reason in recalls.items():
        if _norm(recalled) in m:
            return reason
    return None


def price_listing(category, condition):
    """Offer to the seller and resale price for a new move-out listing."""
    category = category if category in BASE_RESALE else "other"
    resale = round(BASE_RESALE[category] * CONDITION_FACTOR.get(condition, 0.5))
    return {
        "acquisition_cost": round(resale * ACQUISITION_SHARE),
        "refurb_cost": REFURB_COST.get(category, 2),
        "resale_price": resale,
    }


def unit_margin(item):
    return item["resale_price"] - item["acquisition_cost"] - item["refurb_cost"]


def kit_totals(items):
    price = float(sum(i["resale_price"] for i in items))
    cost = float(sum(i["acquisition_cost"] + i["refurb_cost"] for i in items) + DELIVERY_COST)
    margin = price - cost
    return {
        "price": price,
        "cost": cost,
        "margin": margin,
        "margin_pct": round(100 * margin / price, 1) if price else 0.0,
    }


def verify_kit(request, item_ids, inventory, recalls):
    """Check a proposed kit against live inventory and business rules.

    Returns (checks, issues, soft_only):
      checks    - list of {name, passed, detail}
      issues    - human-readable problems, fed back to the Kit Agent
      soft_only - True when the only failure is a small budget overrun a human may approve
    """
    checks, issues, hard = [], [], False

    def check(name, passed, detail, soft=False):
        nonlocal hard
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            issues.append(detail)
            hard = hard or not soft

    unknown = [i for i in item_ids if i not in inventory]
    check("items_exist", not unknown,
          f"Unknown item IDs: {', '.join(unknown)}" if unknown else "All items exist in inventory")

    dupes = sorted({i for i in item_ids if item_ids.count(i) > 1})
    check("no_duplicates", not dupes,
          f"Duplicate items: {', '.join(dupes)}" if dupes else "No duplicate items")

    items = [inventory[i] for i in dict.fromkeys(item_ids) if i in inventory]

    taken = [i for i in items if i["status"] != "available"]
    check("available_now", not taken,
          "; ".join(f"{i['id']} ({i['name']}) is already reserved for {i['reserved_for']}" for i in taken)
          if taken else "Every item is still available in live inventory")

    recalled = [(i, recall_reason(i["model"], recalls)) for i in items]
    recalled = [(i, r) for i, r in recalled if r]
    check("no_safety_recalls", not recalled,
          "; ".join(f"{i['id']} (model {i['model']}) is under a safety recall: {r}" for i, r in recalled)
          if recalled else "No recalled models")

    covered = {i["category"] for i in items}
    missing = [n for n in request["needs"] if n not in covered]
    check("covers_needs", not missing,
          f"Missing required categories: {', '.join(missing)}" if missing
          else f"Covers every need: {', '.join(request['needs'])}")

    totals = kit_totals(items)
    budget = request["budget"]
    over = totals["price"] - budget
    if over <= 0:
        check("within_budget", True, f"Price ${totals['price']:.0f} fits the ${budget:.0f} budget")
    elif over <= budget * BUDGET_TOLERANCE_PCT / 100:
        check("within_budget", False,
              f"Price ${totals['price']:.0f} is ${over:.0f} over the ${budget:.0f} budget "
              f"(within {BUDGET_TOLERANCE_PCT:.0f}% tolerance: needs human approval)", soft=True)
    else:
        check("within_budget", False, f"Price ${totals['price']:.0f} exceeds the ${budget:.0f} budget by ${over:.0f}")

    check("min_margin", totals["margin_pct"] >= MIN_MARGIN_PCT,
          f"Margin {totals['margin_pct']:.0f}% (${totals['margin']:.0f})"
          + (" meets" if totals["margin_pct"] >= MIN_MARGIN_PCT else " is below")
          + f" the {MIN_MARGIN_PCT:.0f}% minimum")

    return checks, issues, bool(issues) and not hard
