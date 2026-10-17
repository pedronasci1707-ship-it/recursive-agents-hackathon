"""Turn an agent run into an animated storyboard for the admin flow view.

Each frame says where every request/listing token is, which agents are thinking (and how many
processes each one runs), which agent just acted, and the line to show. The browser animates it.
"""

import json
from pathlib import Path

from campusloop import rules
from core.crusoe_client import MODELS

TEMPLATE = Path(__file__).with_name("flowboard.html")

RENAME = [("Kit Agents", "Kit Builders"), ("Kit Agent", "Kit Builder"), ("Intake Agents", "Listing Readers"),
          ("Intake Agent", "Listing Reader"), ("Verifier", "Quality Checker"), ("Controller", "Coordinator"),
          ("Reporter", "Report Writer"), ("Outside world", "Outside buyer")]
FRIENDLY_MODEL = {
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B": "NVIDIA Nemotron 3 Super",
    "nvidia/Nemotron-3.5-Lightning-30B-A3B": "NVIDIA Nemotron 3.5 Lightning",
    "deepseek-ai/Deepseek-V4-Flash": "DeepSeek V4 Flash", "google/gemma-4-31b-it": "Google Gemma 4",
    "nvidia/NVIDIA-Nemotron-3.5-Super-VL": "NVIDIA Nemotron 3.5 Super VL",
}


def disp(text):
    for old, new in RENAME:
        text = text.replace(old, new)
    return text


def _model(role):
    m = MODELS[role]
    return f"{FRIENDLY_MODEL.get(m, m)} on Crusoe Managed Inference"


def agents(max_attempts=3):
    """Who each node is: shown when an agent is clicked."""
    return {
        "coordinator": dict(
            name="Coordinator", icon="account_tree", engine="Deterministic code: the recursive loop",
            about="Runs the whole job. Starts the other agents, sends rejected work back with the exact reasons, "
                  "shares what was learned with everyone, enforces the limits and decides when the job is really done.",
            commands=["Start a Listing Reader for every move-out listing, in parallel",
                      "Start one Kit Builder per student, all planning from the same inventory snapshot",
                      "Send every proposal to the Quality Checker before anything is reserved",
                      "Rejected? Send the reasons back to that Kit Builder and ask for a new plan",
                      "After round 1, replan one student at a time against live inventory",
                      "Broadcast what the Quality Checker learns (e.g. a recalled model) to every Kit Builder",
                      f"Stop after {max_attempts} attempts per kit and hand it to a human",
                      "Declare done only after the final audit passes"]),
        "listing_reader": dict(
            name="Listing Reader", icon="document_scanner",
            engine=f"{_model('fast')} (photos: {FRIENDLY_MODEL.get(MODELS['vision'], MODELS['vision'])})",
            about="Reads what students who are moving out wrote, or a photo of the item. Works out the product, model "
                  "number and condition, prices it, and blocks recalled models before they reach inventory.",
            commands=["Extract the product name, category, condition (A, B or C) and model number",
                      "Answer only with structured data", "Recalled model number: reject the listing (checked by code)",
                      "Price by category and condition; offer the seller 35% of the resale price (code)"]),
        "kit_builders": dict(
            name="Kit Builders", icon="shopping_bag", engine=_model("planner"),
            about="One Kit Builder per student. Each proposes a kit for that student's needs and budget; when the "
                  "Quality Checker rejects it, it fixes every reported issue and tries again.",
            commands=["Pick exactly one item for each category the student needs",
                      "Use only items from the inventory it was given", "Stay within the student's budget",
                      f"Keep at least {rules.MIN_MARGIN_PCT:.0f}% margin after the ${rules.DELIVERY_COST:.0f} delivery",
                      "Prefer better condition when the budget allows",
                      "Fix every issue the Quality Checker reports, and follow the team notes",
                      "If nothing fits, return the closest option and say so"]),
        "quality_checker": dict(
            name="Quality Checker", icon="fact_check", engine="Deterministic code: it cannot be talked around",
            about="Checks every proposal against the LIVE inventory, not the builder's snapshot. Nothing is reserved "
                  "until all 7 checks pass. At the end it audits everything that was reserved.",
            commands=["Every item exists", "No item appears twice",
                      "Every item is still available right now (catches double-booking and outside buyers)",
                      "No recalled models", "Covers everything the student needs",
                      "Within budget (up to 10% over only with a human's approval)",
                      f"At least {rules.MIN_MARGIN_PCT:.0f}% margin after the ${rules.DELIVERY_COST:.0f} delivery",
                      "Final audit: no item in two kits, everything reserved for its kit, no recalled item shipped"]),
        "report_writer": dict(
            name="Report Writer", icon="description", engine=_model("worker"),
            about="Writes the Done Report. The facts come from code; it only explains what was caught and how "
                  "the team recovered.",
            commands=["Use only facts from this run", "Explain what was caught and how it was fixed",
                      "Say plainly when a kit was handed to a human", "Never invent numbers"]),
        "inventory": dict(
            name="Photo inventory", icon="inventory_2", engine="SQLite catalog + run inventory",
            about="The product database stores available catalog and seller items with a path to each photo. "
                  "The run inventory adds inspected example listings; Kit Builders read those item records and photos.",
            commands=["Link each accepted listing to its photo path", "Give Kit Builders available item records",
                      "Reserve items only after the Quality Checker passes the kit"]),
        "blocked": dict(
            name="Blocked listings", icon="block", engine="Safety",
            about="Listings rejected at intake, for example a model under a safety recall. They never reach inventory.",
            commands=["Never sell recalled models"]),
    }


def storyboard(res):
    """Frames for one run (see module docstring)."""
    events = res["events"]
    kits = res["kits"]
    tokens = [{"id": k["request_id"], "label": k["buyer"][0], "name": k["buyer"], "kind": "request"} for k in kits]
    tokens += [{"id": i["listing_id"], "label": "L" + i["listing_id"].split("-")[-1],
                "name": f"Listing {i['listing_id'].split('-')[-1]} ({i['seller'].split(' ')[0]})", "kind": "listing"}
               for i in res["intake"]]
    by_buyer = {k["buyer"]: k["request_id"] for k in kits}
    pos = {t["id"]: "inbox" for t in tokens}
    status = {t["id"]: "wait" for t in tokens}
    thinking = {}
    frames = []
    seq = {"on": False}

    def snap(t, node, msg, kind="info", agent="", flash=None):
        frames.append({"t": round(t, 2), "pos": dict(pos), "status": dict(status),
                       "thinking": {k: v for k, v in thinking.items() if v > 0}, "node": node,
                       "msg": disp(msg), "agent": disp(agent), "kind": kind, "flash": flash})

    def dec(node):
        thinking[node] = max(0, thinking.get(node, 0) - 1)

    def queue_next(i, t):
        """Sequential rounds: the next Kit Builder to plan moves in and starts thinking."""
        for ev in events[i + 1:]:
            if ev["kind"] == "plan":
                tok = by_buyer.get(ev["data"].get("buyer"))
                if tok:
                    pos[tok], status[tok] = "kit_builders", "work"
                    thinking["kit_builders"] = 1
                    snap(t + 0.01, "kit_builders", f"Kit Builder · {ev['data']['buyer']} is thinking…", "plan",
                         "Kit Builders")
                return
            if ev["message"].startswith("Round") or ev["kind"] == "done" or "Final audit" in ev["message"]:
                return

    for i, e in enumerate(events):
        a, k, m, t = e["agent"], e["kind"], e["message"], e["ts"]
        tok = by_buyer.get(e["data"].get("buyer"))
        if k == "photo_received":
            lid = e["data"].get("listing_id")
            if lid in pos:
                pos[lid], status[lid] = "listing_reader", "work"
            snap(t, "listing_reader", m, k, a, "listing_reader")
        elif k == "inventory_add":
            lid = e["data"].get("listing_id")
            if lid in pos:
                pos[lid], status[lid] = "inventory", "ok"
            snap(t, "inventory", m, k, a, "inventory")
        elif k == "inventory_take":
            snap(t, "inventory", m, k, a, "inventory")
        elif a == "Controller" and m.startswith("Spinning up"):
            for tk in tokens:
                if tk["kind"] == "listing":
                    pos[tk["id"]], status[tk["id"]] = "listing_reader", "work"
            thinking["listing_reader"] = len(res["intake"])
            snap(t, "listing_reader", m, k, a)
        elif a == "Intake Agent":
            lid = m.split(" ")[0]
            dec("listing_reader")
            if lid in pos:
                ok = k == "intake"
                pos[lid], status[lid] = ("inventory", "ok") if ok else ("blocked", "bad")
            snap(t, "listing_reader", m, k, a, "listing_reader")
        elif a == "Controller" and m.startswith("Round 1"):
            for tk in tokens:
                if tk["kind"] == "request":
                    pos[tk["id"]], status[tk["id"]] = "coordinator", "work"
            snap(t, "coordinator", m, k, a)
            for tk in tokens:
                if tk["kind"] == "request":
                    pos[tk["id"]] = "kit_builders"
            thinking["kit_builders"] = len(kits)
            snap(t + 0.01, "kit_builders", "Kit Builders are thinking in parallel…", "plan", "Kit Builders")
        elif a == "Controller" and m.startswith("Round"):
            seq["on"] = True
            snap(t, "coordinator", m, k, a)
            queue_next(i, t)
        elif a.startswith("Kit Agent") and tok:
            if k == "plan":
                dec("kit_builders")
                status[tok] = "proposal"
            snap(t, "kit_builders", m, k, a)
            if k == "plan" and seq["on"]:
                pos[tok] = "quality_checker"
                thinking["quality_checker"] = 1
                snap(t + 0.01, "quality_checker", "Quality Checker is checking against live inventory…", "info",
                     "Quality Checker")
        elif a == "Outside world":
            snap(t, "inventory", m, k, a, "inventory")
        elif a == "Verifier" and m.startswith("Checking every proposal"):
            moved = [tk for tk, p in pos.items() if p == "kit_builders" and status[tk] == "proposal"]
            for tk in moved:
                pos[tk] = "quality_checker"
            thinking["quality_checker"] = len(moved)
            snap(t, "quality_checker", m, k, a)
        elif a == "Verifier" and "Final audit" in m:
            thinking["report_writer"] = 1
            snap(t, "quality_checker", m, k, a, "quality_checker")
        elif a == "Verifier" and tok:
            dec("quality_checker")
            status[tok] = "ok" if k == "verify_pass" else "bad"
            snap(t, "quality_checker", m, k, a, "quality_checker")
        elif a == "Reporter":
            dec("report_writer")
            snap(t, "report_writer", m, k, a)
        elif a == "Controller" and k == "replan" and tok:
            pos[tok], status[tok] = "coordinator", "bad"
            snap(t, "coordinator", m, k, a)
            queue_next(i, t)
        elif a == "Controller" and k == "reserve" and tok:
            pos[tok], status[tok] = "coordinator", "ok"
            snap(t, "coordinator", m, k, a)
            pos[tok], status[tok] = "finished_done", "done"
            snap(t + 0.01, "finished", f"{e['data']['buyer']}'s kit is verified and reserved", "done", "Finished")
            queue_next(i, t + 0.01)
        elif a == "Controller" and k == "escalate" and tok:
            pos[tok], status[tok] = "finished_human", "human"
            snap(t, "finished", m, k, a)
            queue_next(i, t)
        elif a == "Controller" and "Broadcast" in m:
            snap(t, "coordinator", m, k, a, "kit_builders")
        elif a == "Controller" and k == "done":
            snap(t, "finished", m, k, a)
        else:
            snap(t, "coordinator" if a == "Controller" else "kit_builders", m, k, a)

    history = {}
    for kit in kits:
        lines = [{"t": e["ts"], "agent": disp(e["agent"]), "msg": disp(e["message"]), "kind": e["kind"]}
                 for e in events if e["data"].get("buyer") == kit["buyer"]]
        history[kit["request_id"]] = {"name": kit["buyer"], "status": kit["status"], "attempts": kit["attempts"],
                                      "price": kit["price"], "items": [i["name"] for i in kit["items"]], "lines": lines}
    for entry in res["intake"]:
        history[entry["listing_id"]] = {"name": f"Listing from {entry['seller']}", "status":
                                        "accepted" if entry["accepted"] else "blocked",
                                        "photo": entry.get("photo") or (entry.get("item") or {}).get("photo"),
                                        "lines": [{"t": e["ts"], "agent": disp(e["agent"]),
                                                   "msg": disp(e["message"]), "kind": e["kind"]}
                                                  for e in events if e["data"].get("listing_id") == entry["listing_id"]]
                                        + [{"t": 0, "agent": "Listing Reader", "msg": disp(entry["reason"]),
                                            "kind": "intake" if entry["accepted"] else "verify_fail"}]}
    return {"tokens": tokens, "frames": frames, "history": history, "status": res["status"],
            "duration": res["duration_s"]}


def render_html(boards, labels, start_key, autoplay, max_attempts=3):
    data = {"boards": boards, "labels": labels, "start": start_key, "autoplay": autoplay,
            "agents": agents(max_attempts)}
    # "</" escaped so model-written text can never close the <script> tag; the page escapes it again on display.
    payload = json.dumps(data).replace("</", r"<\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
