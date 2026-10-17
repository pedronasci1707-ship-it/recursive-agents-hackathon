"""Recursive Controller: plan -> verify -> replan until every kit is really done.

Run from the repo root:
    python -m campusloop.engine            # live run, prints the timeline
    python -m campusloop.engine --save     # also writes demo/sample_run.json
"""

import copy
import json
import sys
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from core.crusoe_client import MODELS, USAGE, usage_summary

from . import agents, db, rules

ID_PREFIX = {
    "mini_fridge": "FRIDGE", "microwave": "MICRO", "desk_lamp": "LAMP", "fan": "FAN",
    "desk_chair": "CHAIR", "desk": "DESK", "storage_bins": "BINS", "shelf": "SHELF",
    "kitchen_basics": "KITCH", "other": "ITEM",
}
OUTSIDE_BUYER = "walk-in buyer (outside CampusLoop)"


def run(on_event=None, simulate_outside_buyer=True, max_attempts=3, requests=None, listings=None):
    """Run the whole agent team once. Returns the result dict described in docs/CONTRACT.md.

    `requests` / `listings` override the demo data (e.g. a student's custom kit request).
    """
    USAGE.clear()
    started = time.time()
    started_at = _now()
    events = []

    def emit(agent, kind, message, **data):
        event = {"ts": round(time.time() - started, 2), "agent": agent, "kind": kind,
                 "message": message, "data": data}
        events.append(event)
        if on_event:
            on_event(event)

    inventory = {i["id"]: i for i in db.products()}
    requests = requests if requests is not None else rules.load("requests.json")
    listings = listings if listings is not None else rules.load("intake.json")
    recalls = rules.recall_list()

    emit("Controller", "info",
         f"Goal: process {len(listings)} move-out listings and deliver verified kits to {len(requests)} "
         f"incoming students. Limits: {max_attempts} attempts per kit, {rules.MIN_MARGIN_PCT:.0f}% minimum margin.")

    intake = _run_intake(listings, inventory, recalls, emit)
    kits = _build_kits(requests, inventory, recalls, emit, simulate_outside_buyer, max_attempts)
    audit_ok = _final_audit(kits, inventory, recalls, emit)

    verified = sum(k["status"] == "verified" for k in kits)
    if not audit_ok:
        status = "failed"
    elif verified == len(kits):
        status = "done"
    else:
        status = "done_with_escalations"

    summary = {
        "status": status,
        "intake": [{"listing": e["listing_id"], "accepted": e["accepted"], "reason": e["reason"]} for e in intake],
        "kits": [{"buyer": k["buyer"], "status": k["status"], "attempts": k["attempts"], "price": k["price"],
                  "margin_pct": k["margin_pct"], "final_items": [f"{i['id']} {i['name']}" for i in k["items"]],
                  "rejected_attempts": [{"attempt": a["attempt"], "items": a["item_ids"], "why_rejected": a["issues"]}
                                        for a in k["history"] if not a["passed"]]} for k in kits],
    }
    report = _report(summary, emit)

    escalated = len(kits) - verified
    emit("Controller", "done",
         f"Done means done: {verified}/{len(kits)} kits verified"
         + (f", {escalated} escalated to a human" if escalated else "")
         + f", {sum(not e['accepted'] for e in intake)} unsafe/unclear listing(s) blocked. Stopping.")

    return {
        "run_id": uuid.uuid4().hex[:8],
        "status": status,
        "started_at": started_at,
        "finished_at": _now(),
        "duration_s": round(time.time() - started, 2),
        "config": {"max_attempts": max_attempts, "min_margin_pct": rules.MIN_MARGIN_PCT,
                   "simulate_outside_buyer": simulate_outside_buyer, "models": dict(MODELS)},
        "intake": intake,
        "kits": kits,
        "events": events,
        "inventory": list(inventory.values()),
        "report": report,
        "usage": usage_summary(),
    }


def _run_intake(listings, inventory, recalls, emit):
    emit("Controller", "info", f"Spinning up {len(listings)} Intake Agents in parallel for move-out listings")
    def inspect(listing):
        rel = listing.get("photo")
        if not rel:
            raise agents.AgentError("a product photo is required")
        static = (Path(__file__).resolve().parents[1] / "static").resolve()
        path = (static / rel).resolve()
        if not path.is_relative_to(static) or not path.is_file():
            raise agents.AgentError("product photo is missing")
        mime = "image/png" if path.suffix.lower() == ".png" else "image/webp" if path.suffix.lower() == ".webp" else "image/jpeg"
        return agents.intake_listing(listing, image=path.read_bytes(), mime=mime)

    for listing in listings:
        emit("Seller photo", "photo_received", f"{listing['id']}: photo {listing.get('photo') or '(missing)'} submitted with the listing",
             listing_id=listing["id"], photo=listing.get("photo"))
    results = _parallel(inspect, listings)
    out = []
    for listing, res in zip(listings, results):
        entry = {"listing_id": listing["id"], "seller": listing["seller"], "text": listing["text"],
                 "photo": listing.get("photo", ""),
                 "accepted": False, "reason": "", "item": None}
        if isinstance(res, Exception):
            entry["reason"] = f"Could not parse the listing ({res}); sent to human review"
            emit("Intake Agent", "escalate", f"{listing['id']}: {entry['reason']}")
        elif res.get("quality_score", 3) < 3:
            entry["reason"] = "Rejected: item appears broken or unsafe; needs human inspection"
            emit("Intake Agent", "verify_fail", f"{listing['id']}: {entry['reason']}")
        elif recall := rules.recall_reason(res.get("model"), recalls):
            entry["reason"] = f"Rejected: model {res.get('model')} is under a safety recall ({recall})"
            emit("Intake Agent", "verify_fail", f"{listing['id']} · {res.get('name')}: {entry['reason']}")
        else:
            item = {"id": _new_id(res["category"], inventory), "name": res.get("name") or "Unnamed item",
                    "category": res["category"], "condition": res["condition"], "model": res.get("model") or "",
                    "quality_score": res.get("quality_score"), "defects": res.get("defects") or [],
                    "photo": listing.get("photo", ""),
                    "color": res.get("color", "other"), "style": res.get("style", "minimal"),
                    **rules.price_listing(res["category"], res["condition"], res.get("quality_score")),
                    "status": "available", "reserved_for": None}
            inventory[item["id"]] = item
            emit("Inventory", "inventory_add",
                 f"{listing['id']} photo {item['photo']} linked to {item['id']} in the run inventory",
                 listing_id=listing["id"], item_id=item["id"], photo=item["photo"])
            entry.update(accepted=True, item=item,
                         reason=f"Accepted as {item['id']}: offer seller ${item['acquisition_cost']}, "
                                f"resell at ${item['resale_price']}")
            emit("Intake Agent", "intake",
                 f"{listing['id']} → {item['id']} {item['name']} (condition {item['condition']}): "
                 f"offer seller ${item['acquisition_cost']}, resell at ${item['resale_price']}",
                 item={k: item[k] for k in ("id", "name", "category", "resale_price")})
        out.append(entry)
    return out


def _build_kits(requests, inventory, recalls, emit, simulate_outside_buyer, max_attempts):
    kits = {r["id"]: {"request_id": r["id"], "buyer": r["buyer"], "profile": r["profile"],
                      "budget": float(r["budget"]), "needs": r["needs"],
                      "min_condition": r.get("min_condition"), "item_prefs": r.get("item_prefs") or {},
                      "status": "pending", "attempts": 0,
                      "items": [], "price": 0.0, "cost": 0.0, "margin": 0.0, "margin_pct": 0.0,
                      "checks": [], "history": [], "rationale": ""} for r in requests}
    feedback = {r["id"]: None for r in requests}
    shared_notes = []   # facts the Verifier learned, broadcast to every Kit Agent
    pending = list(requests)

    def plan_for(r, snapshot):
        # May run in a worker thread: must not emit events here.
        try:
            return agents.plan_kit(r, snapshot, feedback[r["id"]], shared_notes)
        except Exception as e:
            return {**_fallback_plan(r, snapshot), "error": f"{type(e).__name__}: {e}"}

    def announce(r, plan):
        if plan.get("error"):
            emit(f"Kit Agent · {r['buyer']}", "info", f"Model call failed ({plan['error']}); using the fallback planner")
        ids = plan["item_ids"]
        price = sum(inventory[i]["resale_price"] for i in ids if i in inventory)
        emit(f"Kit Agent · {r['buyer']}", "plan", f"Proposes {', '.join(ids)} (${price:.0f}) · {plan['rationale']}",
             item_ids=ids, buyer=r["buyer"])
        for iid in ids:
            if iid in inventory:
                emit("Inventory", "inventory_take", f"{r['buyer']} selects {iid} with photo {inventory[iid].get('photo') or '(none)'}",
                     item_id=iid, buyer=r["buyer"], photo=inventory[iid].get("photo"))

    def verify_and_commit(r, plan, last_try):
        """Verify one plan against live inventory; reserve on success. True when the kit is done."""
        kit = kits[r["id"]]
        kit["attempts"] += 1
        checks, issues, soft_only = rules.verify_kit(r, plan["item_ids"], inventory, recalls)
        items = [inventory[i] for i in dict.fromkeys(plan["item_ids"]) if i in inventory]
        kit.update(checks=checks, rationale=plan["rationale"], **rules.kit_totals(items))
        kit["history"].append({"attempt": kit["attempts"], "item_ids": plan["item_ids"],
                               "passed": not issues, "issues": issues})
        if not issues:
            for item in items:
                item["status"], item["reserved_for"] = "reserved", f"{r['buyer']} ({r['id']})"
            kit["status"] = "verified"
            emit("Verifier", "verify_pass",
                 f"{r['buyer']}'s kit passed all {len(checks)} checks: ${kit['price']:.0f}, margin {kit['margin_pct']:.0f}%",
                 buyer=r["buyer"], item_ids=[i["id"] for i in items])
            emit("Controller", "reserve", f"Reserved {', '.join(i['id'] for i in items)} for {r['buyer']}",
                 buyer=r["buyer"])
        else:
            conflict = any("already reserved" in x for x in issues)
            emit("Verifier", "conflict" if conflict else "verify_fail",
                 f"{r['buyer']}'s kit REJECTED: " + " | ".join(issues),
                 buyer=r["buyer"], issues=issues)
            kit["status"] = "needs_approval" if soft_only else "failed"
            feedback[r["id"]] = issues
            for item in items:
                note = f"{item['id']} is a recalled model ({item['model']}): never use it"
                if rules.recall_reason(item["model"], recalls) and note not in shared_notes:
                    shared_notes.append(note)
                    emit("Controller", "info", f"Broadcast to all Kit Agents: {note}")
            if not last_try:
                emit("Controller", "replan",
                     f"Not done yet: sending the Verifier's feedback back to Kit Agent · {r['buyer']} to replan",
                     buyer=r["buyer"])
        kit["items"] = [copy.deepcopy(i) for i in items]
        return not issues

    # Round 1: every Kit Agent plans in parallel from the same snapshot, so they can collide.
    snapshot = [copy.deepcopy(i) for i in inventory.values() if i["status"] == "available"]
    emit("Controller", "info",
         f"Round 1: {len(pending)} Kit Agents planning in parallel from the same inventory snapshot "
         f"({len(snapshot)} available items)")
    plans = _parallel(lambda r: plan_for(r, snapshot), pending)
    for r, plan in zip(pending, plans):
        announce(r, plan)
    if simulate_outside_buyer and (grabbed := _outside_buyer(plans, inventory)):
        emit("Outside world", "reserve",
             f"A walk-in buyer just bought {grabbed['id']} ({grabbed['name']}): inventory changed "
             "while the agents were planning", item_id=grabbed["id"])
    emit("Verifier", "info", "Checking every proposal against LIVE inventory, safety recalls, budget and margin")
    pending = [r for r, plan in zip(pending, plans) if not verify_and_commit(r, plan, max_attempts == 1)]

    # Later rounds: agents that lost replan one at a time against live inventory, so they cannot collide again.
    for round_no in range(2, max_attempts + 1):
        if not pending:
            break
        emit("Controller", "info",
             f"Round {round_no}: {len(pending)} Kit Agent(s) replanning one at a time against live inventory")
        still_pending = []
        for r in pending:
            snapshot = [copy.deepcopy(i) for i in inventory.values() if i["status"] == "available"]
            plan = plan_for(r, snapshot)
            announce(r, plan)
            if not verify_and_commit(r, plan, round_no == max_attempts):
                still_pending.append(r)
        pending = still_pending

    for r in pending:
        kit = kits[r["id"]]
        if kit["status"] == "needs_approval":
            emit("Controller", "escalate",
                 f"{r['buyer']}: out of attempts and the only issue is a small budget overrun; asking a human to approve",
                 buyer=r["buyer"])
        else:
            emit("Controller", "escalate",
                 f"{r['buyer']}: still failing after {kit['attempts']} attempts; escalating to a human "
                 "instead of shipping a bad kit", buyer=r["buyer"])
    return list(kits.values())


def _final_audit(kits, inventory, recalls, emit):
    """Re-check the finished state before declaring done."""
    problems, seen = [], {}
    for kit in kits:
        if kit["status"] != "verified":
            continue
        for item in kit["items"]:
            live = inventory[item["id"]]
            if item["id"] in seen:
                problems.append(f"{item['id']} is in two kits ({seen[item['id']]} and {kit['buyer']})")
            seen[item["id"]] = kit["buyer"]
            if kit["request_id"] not in (live["reserved_for"] or ""):
                problems.append(f"{item['id']} is not reserved for {kit['buyer']}")
            if rules.recall_reason(live["model"], recalls):
                problems.append(f"{item['id']} is a recalled model")
    verified = sum(k["status"] == "verified" for k in kits)
    if problems:
        emit("Verifier", "verify_fail", "Final audit FAILED: " + " | ".join(problems))
        return False
    emit("Verifier", "verify_pass",
         f"Final audit passed: {verified} verified kit(s), {len(seen)} reserved items, "
         "0 double-bookings, 0 recalled items shipped")
    return True


def _report(summary, emit):
    """Facts (verdict, table) come from code; the Reporter agent only narrates what was caught."""
    kits = summary["kits"]
    verified = sum(k["status"] == "verified" for k in kits)
    escalated = [k["buyer"] for k in kits if k["status"] != "verified"]
    if summary["status"] == "done":
        verdict = f"DONE: {verified}/{len(kits)} kits verified, final audit passed."
    elif summary["status"] == "done_with_escalations":
        verdict = f"DONE WITH ESCALATIONS: {verified}/{len(kits)} kits verified; needs a human: {', '.join(escalated)}."
    else:
        verdict = "FAILED: the final audit found problems; nothing should ship."
    lines = [f"**{verdict}**", "", "| Student | Status | Attempts | Price | Margin |", "|---|---|---|---|---|"]
    lines += [f"| {k['buyer']} | {k['status']} | {k['attempts']} | ${k['price']:.0f} | {k['margin_pct']:.0f}% |"
              for k in kits]
    blocked = [i for i in summary["intake"] if not i["accepted"]]
    if blocked:
        lines += ["", "**Blocked at intake:** " + "; ".join(f"{i['listing']}: {i['reason']}" for i in blocked)]
    try:
        narrative = agents.write_report(summary)
    except agents.AgentError as e:
        emit("Reporter", "info", f"Model call failed ({e}); report without narrative")
        narrative = ""
    if narrative:
        lines += ["", "**What the agents caught and fixed**", "", narrative]
    emit("Reporter", "info", "Done Report written")
    return "\n".join(lines)


def _outside_buyer(plans, inventory):
    """Chaos: someone outside the system buys the most valuable item the first agent picked."""
    for plan in plans:
        candidates = [inventory[i] for i in plan["item_ids"]
                      if i in inventory and inventory[i]["status"] == "available"]
        if candidates:
            item = max(candidates, key=lambda i: (i["category"] == "mini_fridge", i["resale_price"]))
            item["status"], item["reserved_for"] = "reserved", OUTSIDE_BUYER
            return item
    return None


def _fallback_plan(request, snapshot):
    """Plan used only when the model call fails: per needed category, a safe item that meets the minimum quality,
    preferring the student's color/style, then better condition, then the higher price."""
    recalls = rules.recall_list()
    ids = []
    for need in request["needs"]:
        min_rank = rules.QUALITY_RANK.get(rules.min_quality_for(request, need), 0)
        look = (request.get("item_prefs") or {}).get(need, {})
        colors = [look["color"]] if look.get("color") else request.get("colors") or []
        style = look.get("style") or request.get("style")
        options = [i for i in snapshot if i["category"] == need
                   and rules.QUALITY_RANK.get(i["condition"], 0) >= min_rank
                   and not rules.recall_reason(i.get("model"), recalls)]
        if options:
            best = max(options, key=lambda i: ((i.get("color") in colors) + (i.get("style") == style),
                                               rules.QUALITY_RANK.get(i["condition"], 0), i["resale_price"]))
            ids.append(best["id"])
    return {"item_ids": ids, "rationale": "Fallback plan (model unavailable): safe items that meet your quality, "
                                          "closest to your colors and style."}


def _parallel(fn, args):
    """Run fn over args in threads; results (or the raised exception) in input order."""
    def safe(a):
        try:
            return fn(a)
        except Exception as e:
            return e
    with ThreadPoolExecutor(max_workers=max(1, len(args))) as pool:
        return list(pool.map(safe, args))


def _new_id(category, inventory):
    prefix = ID_PREFIX.get(category, "ITEM")
    nums = [int(i.split("-")[1]) for i in inventory if i.startswith(prefix + "-")]
    return f"{prefix}-{max(nums, default=0) + 1:02d}"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    result = run(on_event=lambda e: print(f"{e['ts']:6.1f}s  {e['agent']:<20} {e['kind']:<12} {e['message']}"))
    print("\n" + result["report"])
    print("\nstatus:", result["status"], "| duration:", result["duration_s"], "s")
    for model, u in result["usage"].items():
        print(f"  {model}: {u}")
    if "--save" in sys.argv:
        with open("demo/sample_run.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("saved demo/sample_run.json")
