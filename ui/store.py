"""Customer-side store logic on top of the last agent run (session scoped).

Every change a customer makes to a kit goes through the same Verifier rules the agents use.
"""

import copy

from campusloop import db, rules

RECALLS = rules.recall_list()


def reservation_tag(kit):
    return f"{kit['buyer']} ({kit['request_id']})"


def _owned_by(live, kit):
    return bool(live) and live.get("status") == "reserved" and live.get("reserved_for") == reservation_tag(kit)


def inventory(res):
    """Live inventory objects of the run (mutations persist in the session's result)."""
    return {i["id"]: i for i in res["inventory"]}


def kit_for(res, request_id):
    if not res:
        return None
    return next((k for k in res["kits"] if k["request_id"] == request_id), None)


def is_safe(item):
    return not rules.recall_reason(item["model"], RECALLS)


def shop_items(res):
    """What a customer can buy: available, never recalled."""
    source = list(res["inventory"]) if res else db.products()
    if res:  # items students listed after this run was made are in the database too
        known = {i["id"] for i in source}
        source += [i for i in db.products() if i.get("source") == "seller" and i["id"] not in known]
    return [i for i in source if i["status"] == "available" and is_safe(i)]


def alternatives(res, item):
    return sorted((i for i in shop_items(res) if i["category"] == item["category"] and i["id"] != item["id"]),
                  key=lambda i: i["resale_price"])


def friendly(issues, budget):
    out = []
    for issue in issues:
        if "already reserved" in issue:
            out.append("That item was just reserved by someone else.")
        elif "Missing required" in issue:
            out.append("Your kit would be missing something you need: " + issue.split(": ", 1)[-1].replace("_", " ") + ".")
        elif "budget" in issue:
            out.append(f"That would put your kit over your ${budget:.0f} budget.")
        elif "safety recall" in issue:
            out.append("That item didn't pass our safety checks.")
        elif "Margin" in issue:
            out.append("That combination isn't available at this price. Try another item.")
        else:
            out.append("That change isn't possible right now. Try another item.")
    return list(dict.fromkeys(out))


def change_kit(res, kit, new_ids):
    """Re-verify the kit with new items; reserve them if every check passes. Returns (ok, messages)."""
    known = {i["id"] for i in res["inventory"]}
    res["inventory"] += [i for i in db.products() if i["id"] in new_ids and i["id"] not in known]
    inv = inventory(res)
    tag = reservation_tag(kit)
    current = [i["id"] for i in kit["items"]]
    released = {}
    for iid in current:
        live = inv.get(iid)
        if _owned_by(live, kit):
            released[iid] = (live["status"], live["reserved_for"])
            live["status"], live["reserved_for"] = "available", None
    request = {"id": kit["request_id"], "buyer": kit["buyer"], "budget": kit["budget"],
               "needs": kit["needs"], "min_condition": kit.get("min_condition"),
               "item_prefs": kit.get("item_prefs") or {}}
    checks, issues, _ = rules.verify_kit(request, new_ids, inv, RECALLS)
    if issues:
        for iid, old in released.items():
            inv[iid]["status"], inv[iid]["reserved_for"] = old
        return False, friendly(issues, kit["budget"])
    for iid in new_ids:
        inv[iid]["status"], inv[iid]["reserved_for"] = "reserved", tag
    items = [copy.deepcopy(inv[i]) for i in new_ids]
    kit.update(items=items, checks=checks, status="verified", **rules.kit_totals(items))
    history = kit.setdefault("history", [])
    history.append({"attempt": len(history) + 1, "item_ids": new_ids, "passed": True,
                    "issues": [], "by": "customer"})
    return True, []


def final_check(res, kit):
    """Checkout: re-verify against live inventory that every item is still reserved for this student and safe.
    Returns a list of problems (empty = OK to charge)."""
    inv = inventory(res)
    problems = []
    for item in kit["items"]:
        live = inv.get(item["id"])
        if not _owned_by(live, kit):
            problems.append(f"{item['name']} is no longer reserved for you.")
        elif not is_safe(live):
            problems.append(f"{item['name']} didn't pass our safety checks.")
    return problems


def is_held(res, kit):
    """True while every item of the kit is still reserved for this student."""
    inv = inventory(res)
    return bool(kit["items"]) and all(
        _owned_by(inv.get(i["id"]), kit) for i in kit["items"])


def release(res, kit):
    """Checkout abandoned: give the kit's held items back to the shop so other students can buy them."""
    inv = inventory(res)
    for item in kit["items"]:
        live = inv.get(item["id"])
        if _owned_by(live, kit):
            live["status"], live["reserved_for"] = "available", None


def hold_again(res, kit):
    """Re-reserve the same items after a hold ended, only if each one is still free (never takes another
    student's item). Returns (ok, messages)."""
    inv = inventory(res)
    tag = reservation_tag(kit)
    taken = [i["name"] for i in kit["items"]
             if not (live := inv.get(i["id"])) or not is_safe(live)
             or (live["status"] != "available" and not _owned_by(live, kit))]
    if taken:
        return False, [f"{name} was just taken by someone else." for name in taken]
    for item in kit["items"]:
        inv[item["id"]]["status"], inv[item["id"]]["reserved_for"] = "reserved", tag
    return True, []


def mark_sold(res, kit):
    """Paid: the items leave the shop for good."""
    inv = inventory(res)
    for item in kit["items"]:
        live = inv.get(item["id"])
        if _owned_by(live, kit):
            live["status"], live["reserved_for"] = "sold", None


def swap(res, kit, old_id, new_id):
    return change_kit(res, kit, [new_id if i["id"] == old_id else i["id"] for i in kit["items"]])


def add(res, kit, item_id):
    return change_kit(res, kit, [i["id"] for i in kit["items"]] + [item_id])


def remove(res, kit, item_id):
    return change_kit(res, kit, [i["id"] for i in kit["items"] if i["id"] != item_id])
