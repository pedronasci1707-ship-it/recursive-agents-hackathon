"""Admin: how the agent team works, and why it only says "done" when it is really done."""

import base64

import streamlit as st

from campusloop import rules
from core.crusoe_client import MODELS
from ui import components as c
from ui import state

BLUE, RED, ORANGE, GREEN, IDLE = "#3E63DD", "#E5484D", "#F76B15", "#30A46C", "#CBD2CE"

# id: (x, y, width, title, subtitle)
NODES = {
    "listings": (20, 40, 150, "Move-out listings", "text or photo"),
    "intake": (230, 40, 175, "Intake Agents", "parallel · recall check"),
    "inventory": (475, 40, 170, "Live inventory", "the source of truth"),
    "world": (725, 40, 170, "Outside world", "walk-in buyers"),
    "requests": (20, 190, 150, "Student requests", "needs · budget"),
    "kit": (230, 190, 175, "Kit Agents ×3", "plan in parallel"),
    "verifier": (475, 190, 170, "Verifier", "7 deterministic checks"),
    "controller": (725, 190, 170, "Recursive Controller", "replan · escalate · stop"),
    "audit": (935, 190, 150, "Final audit", "before saying done"),
    "human": (725, 335, 170, "Human review", "after max attempts"),
    "reporter": (935, 335, 150, "Reporter", "Done Report"),
}
H = 60
# id: (svg path, label, label x, label y)
EDGES = {
    "listings-intake": ("M170 70 L226 70", "", 0, 0),
    "intake-inventory": ("M405 70 L471 70", "", 0, 0),
    "world-inventory": ("M725 70 L649 70", "", 0, 0),
    "requests-kit": ("M170 220 L226 220", "", 0, 0),
    "inventory-kit": ("M500 100 L370 186", "snapshot", 395, 140),
    "inventory-verifier": ("M560 100 L560 186", "live check", 568, 148),
    "kit-verifier": ("M405 220 L471 220", "", 0, 0),
    "verifier-controller": ("M645 220 L721 220", "", 0, 0),
    "controller-audit": ("M895 220 L931 220", "", 0, 0),
    "loop": ("M770 250 C770 330 318 330 318 254", "fail → feedback + team notes → replan", 400, 318),
    "controller-human": ("M850 250 L850 331", "", 0, 0),
    "audit-reporter": ("M1010 250 L1010 331", "", 0, 0),
}


def event_focus(e):
    """Which nodes/edges an event lights up, and in what color."""
    a, k, m = e["agent"], e["kind"], e["message"]
    if a == "Intake Agent":
        ok = k == "intake"
        return (["intake", "inventory"] if ok else ["intake"]), \
            (["listings-intake", "intake-inventory"] if ok else ["listings-intake"]), (GREEN if ok else RED)
    if a.startswith("Kit Agent"):
        return ["kit"], ["requests-kit", "inventory-kit"], BLUE
    if a == "Outside world":
        return ["world", "inventory"], ["world-inventory"], RED
    if a == "Verifier":
        if "Final audit" in m:
            return ["audit"], ["controller-audit"], GREEN if k == "verify_pass" else RED
        color = {"conflict": RED, "verify_fail": RED, "verify_pass": GREEN}.get(k, BLUE)
        return ["verifier"], ["kit-verifier", "inventory-verifier"], color
    if a == "Reporter":
        return ["reporter"], ["audit-reporter"], GREEN
    # Controller
    if k == "replan" or "Broadcast" in m:
        return ["controller", "kit"], ["verifier-controller", "loop"], ORANGE
    if k == "reserve":
        return ["controller", "inventory"], ["verifier-controller"], GREEN
    if k == "escalate":
        return ["controller", "human"], ["controller-human"], ORANGE
    if k == "done":
        return ["controller", "audit", "reporter"], ["controller-audit", "audit-reporter"], GREEN
    if "Round" in m:
        return ["controller", "kit"], [], BLUE
    if "Intake" in m:
        return ["controller", "intake"], [], BLUE
    return ["controller"], [], BLUE


def diagram(nodes=(), edges=(), color=BLUE):
    parts = ['<svg viewBox="0 0 1100 410" width="100%" xmlns="http://www.w3.org/2000/svg" '
             'style="font-family:Inter,system-ui,sans-serif">',
             "<defs>"]
    for name, col in (("idle", IDLE), ("on", color)):
        parts.append(f'<marker id="arr-{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
                     f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{col}"/></marker>')
    parts.append("</defs>")
    for eid, (path, label, lx, ly) in EDGES.items():
        on = eid in edges
        parts.append(f'<path d="{path}" fill="none" stroke="{color if on else IDLE}" stroke-width="{3 if on else 1.6}" '
                     f'stroke-dasharray="{"" if on or eid != "loop" else "6 5"}" marker-end="url(#arr-{"on" if on else "idle"})"/>')
        if label:
            parts.append(f'<text x="{lx}" y="{ly}" font-size="12" fill="{color if on else "#66706B"}" '
                         f'font-weight="{600 if on else 400}">{c.esc(label)}</text>')
    for nid, (x, y, w, title, sub) in NODES.items():
        on = nid in nodes
        fill = f"{color}1F" if on else "#FFFFFF"
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{H}" rx="14" fill="{fill}" '
                     f'stroke="{color if on else "#E1E4E1"}" stroke-width="{2.5 if on else 1.2}"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 26}" font-size="14.5" font-weight="700" fill="#14201B">{c.esc(title)}</text>')
        parts.append(f'<text x="{x + 14}" y="{y + 45}" font-size="12" fill="#66706B">{c.esc(sub)}</text>')
    parts.append("</svg>")
    # As an <img>: st.html's sanitizer drops inline <svg>.
    data = base64.b64encode("".join(parts).encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{data}" style="width:100%;max-width:1100px" alt="Agent flow">'


def now_box(e, color):
    return (f'<div style="border-left:5px solid {color};background:{color}14;border-radius:10px;padding:10px 14px;'
            f'font-size:.95rem"><b>{c.esc(e["agent"])}</b> · <span style="opacity:.6">{e["ts"]:.1f}s</span><br>'
            f'{c.esc(e["message"])}</div>')


def scorecard(res):
    kits = res["kits"]
    proposals = sum(len(k["history"]) for k in kits)
    rejected = sum(not a["passed"] for k in kits for a in k["history"])
    recovered = sum(k["status"] == "verified" and any(not a["passed"] for a in k["history"]) for k in kits)
    escalated = sum(k["status"] != "verified" for k in kits)
    unverified = sum(k["status"] == "verified" and not all(ch["passed"] for ch in k["checks"]) for k in kits)
    m = st.columns(6)
    m[0].metric("Proposals", proposals)
    m[1].metric("Rejected by Verifier", rejected)
    m[2].metric("Kits recovered", recovered)
    m[3].metric("Escalated to a human", escalated)
    m[4].metric("Shipped unverified", unverified, help="Kits marked done without passing every check. Must be 0.")
    m[5].metric("Max attempts used", f"{max(k['attempts'] for k in kits)}/{res['config']['max_attempts']}")


def short_reason(issue):
    for needle, text in (("already reserved", "item already reserved"), ("recall", "safety recall"),
                         ("budget", "over budget"), ("Margin", "margin too low"), ("Missing", "missing a need")):
        if needle in issue:
            return text
    return issue[:40]


def trace_html(kit):
    chips = []
    for a in kit["history"]:
        col = GREEN if a["passed"] else RED
        why = "passed all 7 checks" if a["passed"] else short_reason(a["issues"][0])
        chips.append(f'<div style="border:1.5px solid {col};background:{col}12;border-radius:12px;padding:8px 12px;'
                     f'min-width:150px"><div style="font-weight:700;color:{col}">{"✓" if a["passed"] else "✗"} '
                     f'Attempt {a["attempt"]}</div><div style="font-size:.8rem;opacity:.75">{c.esc(", ".join(a["item_ids"]))}</div>'
                     f'<div style="font-size:.82rem;margin-top:2px">{c.esc(why)}</div></div>')
    end = {"verified": (GREEN, "DONE · reserved"), "needs_approval": (ORANGE, "HUMAN APPROVAL"),
           "failed": (ORANGE, "ESCALATED · stopped")}.get(kit["status"], (IDLE, kit["status"]))
    chips.append(f'<div style="background:{end[0]};color:#fff;border-radius:12px;padding:8px 12px;font-weight:700;'
                 f'align-self:center">{end[1]}</div>')
    arrow = '<div style="align-self:center;color:#9AA39E;font-size:1.2rem">→</div>'
    return (f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0 14px;flex-wrap:wrap">'
            f'<div style="width:70px;font-weight:700">{c.esc(kit["buyer"])}</div>' + arrow.join(chips) + "</div>")


# ---------------------------------------------------------------- page
st.markdown("## :material/account_tree: How it works: Done Means Done")
st.caption("A team of agents that plans, gets checked against reality, fixes its own mistakes, and only says "
           "\"done\" when every kit passes verification. Or stops and hands it to a human.")

live, chaos, max_attempts, speed = state.run_mode_controls("flow")
start = st.sidebar.button("▶ Run and watch the flow", type="primary", width="stretch")

legend = (f'<div style="display:flex;gap:18px;font-size:.85rem;color:#66706B;margin:-4px 0 8px">'
          f'<span><b style="color:{BLUE}">■</b> working</span><span><b style="color:{RED}">■</b> rejected / conflict</span>'
          f'<span><b style="color:{ORANGE}">■</b> replan / escalate</span><span><b style="color:{GREEN}">■</b> verified</span></div>')
st.html(legend)
canvas = st.empty()
now = st.empty()
score = st.container()

if start:
    def on_event(e):
        nodes, edges, color = event_focus(e)
        canvas.html(diagram(nodes, edges, color))
        now.html(now_box(e, color))

    canvas.html(diagram())
    state.run_agents(on_event, live=live, chaos=chaos, max_attempts=max_attempts, speed=speed)
    st.rerun()

res = state.result()
canvas.html(diagram())
if res:
    last = res["events"][-1]
    now.html(now_box(last, GREEN if res["status"] == "done" else ORANGE))
    with score:
        scorecard(res)
else:
    now.info("Press **▶ Run and watch the flow** in the sidebar to see each agent light up as it works.")

st.divider()
left, right = st.columns(2, gap="large")
with left:
    st.markdown("#### :material/fact_check: Definition of Done")
    st.caption("A kit is done only when ALL of these pass against **live** inventory, not the agent's snapshot.")
    checks = [
        ("Items exist", "Every proposed ID is real inventory"),
        ("No duplicates", "No item appears twice"),
        ("Available now", "Still free in live inventory: catches double-booking and outside buyers"),
        ("No safety recalls", "Model number is not on the recall list"),
        ("Covers needs", "One item for every category the student asked for"),
        ("Within budget", "Up to 10% over only with a human's approval"),
        (f"Margin ≥ {rules.MIN_MARGIN_PCT:.0f}%", f"After the ${rules.DELIVERY_COST:.0f} delivery cost"),
    ]
    for title, text in checks:
        st.markdown(f":material/check_circle: **{title}**: {text}")
    st.markdown(":material/verified: **Final audit**: no item in two kits, every item reserved for its kit, "
                "no recalled item shipped. Only then the Controller declares done.")
with right:
    st.markdown("#### :material/rule: How the loop is kept honest")
    for ico, title, text in [
        ("sync", "Plan → verify → replan", "A rejected kit goes back to its Kit Agent with the Verifier's exact reasons."),
        ("campaign", "Shared team notes", "What the Verifier learns (e.g. a recalled fridge) is broadcast to every agent."),
        ("queue", "No repeat collisions", "After round 1, agents replan one at a time against live inventory."),
        ("timer", "Hard limits", "Max attempts per kit (default 3), timeouts and retries on every model call."),
        ("support_agent", "Knows when to stop", "Out of attempts? Escalate to a human, never ship an unverified kit."),
        ("shield", "Code checks, LLMs decide", "Money, inventory and safety rules are deterministic code, so they can't be talked around."),
    ]:
        st.markdown(f":material/{ico}: **{title}**: {text}")

if res:
    st.divider()
    st.markdown("#### :material/timeline: Recursion trace of this run")
    st.caption(f"Scenario: {state.SCENARIOS[st.session_state.get('scenario', 'standard')][0]} · "
               f"{st.session_state.get('source', 'run')} · run `{res['run_id']}`")
    st.html("".join(trace_html(k) for k in res["kits"]))

st.divider()
st.markdown("#### :material/memory: Agents on Crusoe Managed Inference")
st.dataframe([
    {"Agent": "Intake Agents (parallel)", "Job": "Read move-out listings (text or photo), extract item, model, condition",
     "Model": f"{MODELS['fast']} · photos: {MODELS['vision']}"},
    {"Agent": "Kit Agents (one per student)", "Job": "Plan a kit for needs + budget, replan from feedback",
     "Model": MODELS["planner"]},
    {"Agent": "Verifier", "Job": "7 checks against live inventory + final audit", "Model": "deterministic code"},
    {"Agent": "Recursive Controller", "Job": "Loop, broadcast notes, enforce limits, escalate, declare done",
     "Model": "deterministic code"},
    {"Agent": "Reporter", "Job": "Write the Done Report narrative (facts come from code)", "Model": MODELS["worker"]},
], hide_index=True, width="stretch")
