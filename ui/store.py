"""Customer-side store logic on top of the last agent run (session scoped).

Every change a customer makes to a kit goes through the same Verifier rules the agents use.
"""

import copy

from campusloop import rules

RECALLS = rules.recall_list()


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
    source = res["inventory"] if res else rules.load("catalog.json")
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
    inv = inventory(res)
    tag = f"{kit['buyer']} ({kit['request_id']})"
    current = [i["id"] for i in kit["items"]]
    for iid in current:
        inv[iid]["status"], inv[iid]["reserved_for"] = "available", None
    request = {"id": kit["request_id"], "buyer": kit["buyer"], "budget": kit["budget"], "needs": kit["needs"]}
    checks, issues, _ = rules.verify_kit(request, new_ids, inv, RECALLS)
    if issues:
        for iid in current:
            inv[iid]["status"], inv[iid]["reserved_for"] = "reserved", tag
        return False, friendly(issues, kit["budget"])
    for iid in new_ids:
        inv[iid]["status"], inv[iid]["reserved_for"] = "reserved", tag
    items = [copy.deepcopy(inv[i]) for i in new_ids]
    kit.update(items=items, checks=checks, status="verified", **rules.kit_totals(items))
    kit["history"].append({"attempt": len(kit["history"]) + 1, "item_ids": new_ids, "passed": True,
                           "issues": [], "by": "customer"})
    return True, []


def swap(res, kit, old_id, new_id):
    return change_kit(res, kit, [new_id if i["id"] == old_id else i["id"] for i in kit["items"]])


def add(res, kit, item_id):
    return change_kit(res, kit, [i["id"] for i in kit["items"]] + [item_id])


def remove(res, kit, item_id):
    return change_kit(res, kit, [i["id"] for i in kit["items"] if i["id"] != item_id])
