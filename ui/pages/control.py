"""Admin control room: a simple live org chart of the agents. Click an agent to see what it does."""

import streamlit as st

from campusloop import rules
from core.crusoe_client import MODELS
from ui import components as c
from ui import state

GREY, BLUE, RED, ORANGE, GREEN = "#9AA39E", "#3E63DD", "#E5484D", "#F76B15", "#30A46C"
STATUS = {  # status -> (label, color)
    "idle": ("Waiting", GREY), "working": ("Working", BLUE), "rejected": ("Rejected", RED),
    "replanning": ("Replanning", ORANGE), "verified": ("Verified", GREEN), "escalated": ("Handed to a human", ORANGE),
    "blocked": ("Blocked an unsafe item", RED), "done": ("Done", GREEN),
}
KIND_COLOR = {"verify_fail": RED, "conflict": RED, "verify_pass": GREEN, "reserve": GREEN, "done": GREEN,
              "replan": ORANGE, "escalate": ORANGE, "plan": BLUE, "intake": GREEN}
# Engine names -> names by function, used everywhere on this page.
RENAME = [("Kit Agents", "Kit Builders"), ("Kit Agent", "Kit Builder"), ("Intake Agents", "Listing Readers"),
          ("Intake Agent", "Listing Reader"), ("Verifier", "Quality Checker"), ("Controller", "Coordinator"),
          ("Reporter", "Report Writer"), ("Outside world", "Outside buyer")]
FRIENDLY_MODEL = {
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B": "NVIDIA Nemotron 3 Super",
    "nvidia/Nemotron-3.5-Lightning-30B-A3B": "NVIDIA Nemotron 3.5 Lightning",
    "deepseek-ai/Deepseek-V4-Flash": "DeepSeek V4 Flash", "google/gemma-4-31b-it": "Google Gemma 4",
}


def disp(text):
    for old, new in RENAME:
        text = text.replace(old, new)
    return text


def model(role):
    m = MODELS[role]
    return f"{FRIENDLY_MODEL.get(m, m)} on Crusoe Managed Inference"


def agent_defs(reqs, max_attempts):
    defs = {
        "controller": dict(
            name="Coordinator", icon="account_tree", engine="Deterministic code: the recursive loop",
            about="Runs the whole job. Starts the other agents, sends rejected work back with the exact reasons, "
                  "shares what was learned with everyone, enforces the limits and decides when the job is really done.",
            commands=["Start a Listing Reader for every move-out listing, in parallel",
                      "Start one Kit Builder per student, all planning from the same inventory snapshot",
                      "Send every proposal to the Quality Checker before anything is reserved",
                      "Rejected? Send the reasons back to that Kit Builder and ask for a new plan",
                      "After round 1, replan one student at a time against live inventory, so builders can't collide again",
                      "Broadcast what the Quality Checker learns (e.g. a recalled model) to every Kit Builder",
                      f"Stop after {max_attempts} attempts per kit and hand it to a human",
                      "Declare done only after the final audit passes"],
            match=lambda e: e["agent"] == "Controller"),
        "intake": dict(
            name="Listing Reader", icon="document_scanner", engine=f"{model('fast')} (photos: {FRIENDLY_MODEL.get(MODELS['vision'], MODELS['vision'])})",
            about="Reads what students who are moving out wrote, or a photo of the item. Works out the product, "
                  "model number and condition, prices it, and blocks recalled models before they reach inventory.",
            commands=["Extract the product name, category, condition (A, B or C) and model number",
                      "Answer only with structured data, never free text",
                      "If the model number is on the recall list, reject the listing (checked by code)",
                      "Price by category and condition; offer the seller 35% of the resale price (code)"],
            match=lambda e: e["agent"] == "Intake Agent"),
        "verifier": dict(
            name="Quality Checker", icon="fact_check", engine="Deterministic code: it cannot be talked around",
            about="Checks every proposal against the LIVE inventory, not the builder's snapshot. Nothing is reserved "
                  "until all 7 checks pass. At the end it runs a final audit of everything reserved.",
            commands=["Every item exists", "No item appears twice",
                      "Every item is still available right now (catches double-booking and outside buyers)",
                      "No recalled models", "Covers everything the student needs",
                      "Within the student's budget (up to 10% over only with a human's approval)",
                      f"At least {rules.MIN_MARGIN_PCT:.0f}% margin after the ${rules.DELIVERY_COST:.0f} delivery",
                      "Final audit: no item in two kits, every item reserved for its kit, no recalled item shipped"],
            match=lambda e: e["agent"] == "Verifier"),
        "reporter": dict(
            name="Report Writer", icon="description", engine=model("worker"),
            about="Writes the Done Report for the operations team. The facts (verdict and table) come from code; "
                  "it only explains what was caught and how the team recovered.",
            commands=["Use only facts from this run", "Explain what was caught and how it was fixed",
                      "Say plainly when a kit was handed to a human", "Never invent numbers"],
            match=lambda e: e["agent"] == "Reporter"),
    }
    for r in reqs:
        needs = ", ".join(n.replace("_", " ") for n in r["needs"])
        defs[f"kit_{r['buyer']}"] = dict(
            name=f"Kit Builder · {r['buyer']}", icon="shopping_bag", engine=model("planner"), buyer=r["buyer"],
            about=f"Builds {r['buyer']}'s move-in kit: {needs}, within ${r['budget']:.0f}. Proposes items; when the "
                  "Quality Checker rejects a proposal, it fixes every reported issue and tries again.",
            commands=["Pick exactly one item for each category the student needs",
                      "Use only items from the inventory it was given", "Stay within the student's budget",
                      f"Keep at least {rules.MIN_MARGIN_PCT:.0f}% margin after the ${rules.DELIVERY_COST:.0f} delivery",
                      "Prefer better condition when the budget allows",
                      "Fix every issue the Quality Checker reports, and follow the team notes",
                      "If nothing fits, return the closest option and say so"],
            match=lambda e, b=r["buyer"]: e["data"].get("buyer") == b)
    return defs


def statuses(defs, events):
    """Status of every agent after these events, plus the agent that acted last."""
    st_, active, world = {k: "idle" for k in defs}, None, None
    for e in events:
        a, k, m, buyer = e["agent"], e["kind"], e["message"], e["data"].get("buyer")
        kit = f"kit_{buyer}" if buyer and f"kit_{buyer}" in defs else None
        if a == "Intake Agent":
            st_["intake"], active = ("working" if k == "intake" else "blocked"), "intake"
        elif a.startswith("Kit Agent") and kit:
            st_[kit], active = "working", kit
        elif a == "Verifier":
            active = "verifier"
            if "Final audit" in m:
                st_["verifier"] = "done" if k == "verify_pass" else "rejected"
            elif k in ("conflict", "verify_fail"):
                st_["verifier"] = "rejected"
                if kit:
                    st_[kit] = "rejected"
            elif k == "verify_pass":
                st_["verifier"] = "verified"
                if kit:
                    st_[kit] = "verified"
            else:
                st_["verifier"] = "working"
        elif a == "Reporter":
            st_["reporter"], active = "done", "reporter"
        elif a == "Outside world":
            world = e["message"]
        else:  # Controller
            active = "controller"
            if k == "replan" and kit:
                st_[kit] = "replanning"
            elif k == "escalate" and kit:
                st_[kit] = "escalated"
            st_["controller"] = "done" if k == "done" else "escalated" if k == "escalate" else "working"
            if m.startswith("Round 1") and st_["intake"] != "idle":
                st_["intake"] = "done"
    return st_, active, world


def chart_css(defs, st_, active):
    rules_ = []
    for aid in defs:
        color = STATUS[st_[aid]][1]
        glow = f"box-shadow: 0 0 0 6px {color}55 !important;" if aid == active else "box-shadow: none !important;"
        rules_.append(
            f".st-key-ag_{aid} button {{ min-height: 86px; border-radius: 18px !important; border: 3px solid {color} !important;"
            f" background: color-mix(in srgb, {color} 13%, #fff) !important; {glow} }}"
            f".st-key-ag_{aid} button p {{ font-size: 1.12rem !important; font-weight: 800 !important; color: #14201B !important;"
            f" line-height: 1.2 !important; }}"
            f".st-key-ag_{aid} button, .st-key-ag_{aid} button * {{ white-space: normal !important; overflow: visible !important;"
            f" text-overflow: clip !important; }}"
            f".st-key-ag_{aid} button [data-testid='stIconMaterial'] {{ color: {color} !important; font-size: 1.7rem !important; }}")
    return "<style>" + "".join(rules_) + "</style>"


CONNECTOR = """<div style="padding:4px 0 2px">
<div style="width:0;height:22px;border-left:3px solid #C9CFCB;margin:0 auto"></div>
<div style="border-top:3px solid #C9CFCB;margin:0 12.5%"></div>
<div style="display:grid;grid-template-columns:repeat(4,1fr)">""" + \
    "".join('<div style="height:22px;border-left:3px solid #C9CFCB;margin-left:50%"></div>' for _ in range(4)) + \
    "</div></div>"


def legend():
    return ('<div style="display:flex;flex-wrap:wrap;gap:20px;font-size:1rem;margin:2px 0 10px">'
            + "".join(f'<span><span style="color:{col};font-size:1.3rem">●</span> {lab}</span>'
                      for lab, col in [("Waiting", GREY), ("Working", BLUE), ("Rejected", RED),
                                       ("Replanning / human", ORANGE), ("Verified / done", GREEN)]) + "</div>")


def now_html(e):
    color = KIND_COLOR.get(e["kind"], BLUE)
    return (f'<div style="border-left:6px solid {color};background:color-mix(in srgb,{color} 10%,#fff);border-radius:14px;'
            f'padding:12px 16px;font-size:1.02rem;line-height:1.45"><b>{c.esc(disp(e["agent"]))}</b><br>'
            f'{c.esc(disp(e["message"]))}</div>')


def feed_html(events):
    return '<div style="display:flex;flex-direction:column;gap:7px">' + "".join(
        f'<div style="border-left:4px solid {KIND_COLOR.get(e["kind"], GREY)};background:#fff;border-radius:8px;'
        f'padding:7px 11px;font-size:.92rem;line-height:1.4"><b>{c.esc(disp(e["agent"]))}</b>: {c.esc(disp(e["message"]))}</div>'
        for e in reversed(events)) + "</div>"


@st.dialog("Agent details", width="large")
def show_agent(aid, defs, st_, events, res):
    d = defs[aid]
    label, color = STATUS[st_[aid]]
    mine = [e for e in events if d["match"](e)]
    st.markdown(f"## :material/{d['icon']}: {d['name']}")
    st.html(f'<span style="background:{color};color:#fff;border-radius:999px;padding:4px 14px;font-weight:700;'
            f'font-size:1rem">{label}</span>')
    st.markdown(f"**What it does.** {c.md_safe(d['about'])}")
    st.markdown(f"**Runs on.** {d['engine']}")
    st.markdown("**Doing now**")
    st.info(c.md_safe(disp(mine[-1]["message"])) if mine else "Not started yet.")
    st.markdown("**Its commands**")
    for cmd in d["commands"]:
        st.markdown(f"- {c.md_safe(cmd)}")
    if res and "buyer" in d:
        kit = next((k for k in res["kits"] if k["buyer"] == d["buyer"]), None)
        if kit:
            st.markdown("**Its attempts**")
            for a in kit["history"]:
                text = "passed all 7 checks" if a["passed"] else disp("; ".join(a["issues"]))
                st.markdown(f"{':material/check_circle:' if a['passed'] else ':material/cancel:'} "
                            f"**Attempt {a['attempt']}**: {', '.join(a['item_ids'])} · {c.md_safe(text)}")
    st.markdown(f"**Everything it did in this run** ({len(mine)})")
    if not mine:
        st.caption("Nothing yet. Press Start the agents.")
    for e in mine:
        st.markdown(f"`{e['ts']:.1f}s` {c.md_safe(disp(e['message']))}")


# ---------------------------------------------------------------- page
st.markdown("## :material/hub: Agent control room")
st.markdown("Done Means Done: nothing is finished until the **Quality Checker** passes it. "
            "**Click any agent** to see what it does and what it's doing.")

live, chaos, max_attempts, speed = state.run_mode_controls("control")
start = st.sidebar.button("▶ Start the agents", type="primary", width="stretch")

transform = state.SCENARIOS[st.session_state.get("scenario", "standard")][2]
reqs = transform(state.requests()) if transform else state.requests()
res = state.result()
max_att = res["config"]["max_attempts"] if res and not start else max_attempts
defs = agent_defs(reqs, max_att)
events = res["events"] if res and not start else []
st_, active, world = statuses(defs, events)

style = st.empty()
chart_col, side_col = st.columns([2.3, 1], gap="medium")
with chart_col:
    st.html(legend())
    banner = st.empty()
    _, mid, _ = st.columns([1, 1.25, 1])
    clicked = None
    if mid.button(defs["controller"]["name"], key="ag_controller", icon=f":material/{defs['controller']['icon']}:",
                  width="stretch"):
        clicked = "controller"
    st.html(CONNECTOR)
    cols = st.columns(4)
    if cols[0].button(defs["intake"]["name"], key="ag_intake", icon=":material/document_scanner:", width="stretch"):
        clicked = "intake"
    for r in reqs:
        aid = f"kit_{r['buyer']}"
        if cols[1].button(defs[aid]["name"], key=f"ag_{aid}", icon=":material/shopping_bag:", width="stretch"):
            clicked = aid
    if cols[2].button(defs["verifier"]["name"], key="ag_verifier", icon=":material/fact_check:", width="stretch"):
        clicked = "verifier"
    if cols[3].button(defs["reporter"]["name"], key="ag_reporter", icon=":material/description:", width="stretch"):
        clicked = "reporter"
with side_col:
    st.markdown("#### Happening now")
    now = st.empty()
    st.markdown("#### Live feed")
    feed = st.container(height=440, border=True).empty()


def paint(evts):
    s, act, wld = statuses(defs, evts)
    style.html(chart_css(defs, s, act))
    if wld:
        banner.html(f'<div style="border-left:6px solid {RED};background:#FDECEC;border-radius:12px;padding:10px 14px;'
                    f'font-size:1rem;font-weight:600;margin-bottom:8px">Outside buyer: {c.esc(wld)}</div>')
    if evts:
        now.html(now_html(evts[-1]))
        feed.html(feed_html(evts))
    else:
        now.info("Press **▶ Start the agents** in the sidebar.")
        feed.markdown("Events will stream here.")


paint(events)

if start:
    seen = []

    def on_event(e):
        seen.append(e)
        paint(seen)

    state.run_agents(on_event, live=live, chaos=chaos, max_attempts=max_attempts, speed=speed)
    st.rerun()

if clicked:
    show_agent(clicked, defs, st_, events, res)

if res:
    kits = res["kits"]
    st.divider()
    m = st.columns(5)
    m[0].metric("Kits verified", f"{sum(k['status'] == 'verified' for k in kits)}/{len(kits)}")
    m[1].metric("Proposals rejected", sum(not a["passed"] for k in kits for a in k["history"]))
    m[2].metric("Handed to a human", sum(k["status"] != "verified" for k in kits))
    m[3].metric("Shipped unverified", sum(k["status"] == "verified" and not all(ch["passed"] for ch in k["checks"])
                                          for k in kits))
    m[4].metric("Run time", f"{res['duration_s']:.1f}s")
