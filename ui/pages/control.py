"""Admin control room: the agent org chart, live, with what every agent is doing right now."""

import streamlit as st

from core.crusoe_client import MODELS
from ui import components as c
from ui import state

GREY, BLUE, RED, ORANGE, GREEN = "#9AA39E", "#3E63DD", "#E5484D", "#F76B15", "#30A46C"
STATUS = {  # status -> (label, color)
    "idle": ("Idle", GREY), "working": ("Working", BLUE), "rejected": ("Rejected", RED),
    "replanning": ("Replanning", ORANGE), "verified": ("Verified", GREEN), "escalated": ("Escalated", ORANGE),
    "blocked": ("Blocked item", RED), "done": ("Done", GREEN),
}

CSS = """
<style>
.oc { font-family: Inter, system-ui, sans-serif; }
.oc-top { display: flex; justify-content: center; }
.oc-top .oc-card { width: 46%; }
.oc-v { width: 0; height: 22px; border-left: 2px solid #C9CFCB; margin: 0 auto; }
.oc-bar { height: 0; border-top: 2px solid #C9CFCB; margin: 0 11.5%; }
.oc-row { display: grid; grid-template-columns: 1fr 1.35fr 1fr 1fr; gap: 12px; }
.oc-col { position: relative; padding-top: 22px; display: flex; flex-direction: column; gap: 10px; }
.oc-col::before { content: ""; position: absolute; top: 0; left: 50%; height: 22px; border-left: 2px solid #C9CFCB; }
.oc-team { border: 1.5px dashed #C9CFCB; border-radius: 16px; padding: 8px; display: flex; flex-direction: column; gap: 8px; }
.oc-team-label { font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #66706B; padding: 2px 4px; }
.oc-card { background: #fff; border: 1.5px solid #E1E4E1; border-left: 6px solid var(--c); border-radius: 14px;
           padding: 10px 12px; transition: box-shadow .2s; }
.oc-card.active { box-shadow: 0 0 0 3px color-mix(in srgb, var(--c) 35%, transparent); }
.oc-head { display: flex; align-items: center; gap: 8px; }
.oc-head .ms { font-size: 22px; color: var(--c); }
.oc-name { font-weight: 700; font-size: .86rem; line-height: 1.2; color: #14201B; }
.oc-model { font-size: .7rem; color: #66706B; }
.oc-pill { margin-left: auto; font-size: .68rem; font-weight: 700; color: #fff; background: var(--c); border-radius: 999px;
           padding: 2px 8px; white-space: nowrap; }
.oc-task { font-size: .77rem; color: #2B3631; margin-top: 6px; line-height: 1.35; }
.oc-meta { font-size: .7rem; color: #66706B; margin-top: 4px; }
.oc-world { margin-bottom: 10px; border-radius: 12px; padding: 8px 12px; font-size: .85rem; font-weight: 600;
            background: #FDECEC; border-left: 5px solid #E5484D; color: #14201B; }
.oc-now { border-radius: 14px; padding: 12px 14px; border-left: 6px solid var(--c);
          background: color-mix(in srgb, var(--c) 10%, #fff); margin-bottom: 10px; }
.oc-now .who { font-weight: 700; } .oc-now .when { font-size: .75rem; color: #66706B; }
.oc-now .what { margin-top: 4px; font-size: .92rem; line-height: 1.4; }
.oc-feed { display: flex; flex-direction: column; gap: 6px; font-family: Inter, system-ui, sans-serif; }
.oc-ev { border-left: 4px solid var(--c); background: color-mix(in srgb, var(--c) 7%, #fff); border-radius: 8px;
         padding: 6px 10px; font-size: .82rem; line-height: 1.35; }
.oc-ev b { color: #14201B; } .oc-ev .t { color: #66706B; font-family: ui-monospace, monospace; font-size: .72rem; }
@media (max-width: 900px) { .oc-row { grid-template-columns: 1fr 1fr; } .oc-bar { margin: 0 25%; } .oc-top .oc-card { width: 100%; } }
</style>
"""

FRIENDLY_MODEL = {
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B": "Nemotron 3 Super",
    "nvidia/Nemotron-3.5-Lightning-30B-A3B": "Nemotron 3.5 Lightning",
    "deepseek-ai/Deepseek-V4-Flash": "DeepSeek V4 Flash",
    "google/gemma-4-31b-it": "Gemma 4",
}


def model_label(role):
    model = MODELS[role]
    return f"{FRIENDLY_MODEL.get(model, model.split('/')[-1])} · Crusoe"


KIND_COLOR = {"verify_fail": RED, "conflict": RED, "verify_pass": GREEN, "reserve": GREEN, "done": GREEN,
              "replan": ORANGE, "escalate": ORANGE, "plan": BLUE, "intake": GREEN}


def short(text, n=120):
    return text if len(text) <= n else text[:n - 1] + "…"


def initial_agents(reqs, max_attempts):
    agents = {
        "controller": {"name": "Recursive Controller", "icon": "account_tree", "model": "orchestrator · code",
                       "status": "idle", "task": "Waiting for a goal", "meta": f"limit: {max_attempts} attempts per kit"},
        "intake": {"name": "Intake Agents", "icon": "inventory", "model": model_label("fast"),
                   "status": "idle", "task": "Waiting for move-out listings", "meta": "", "ok": 0, "blocked": 0},
        "verifier": {"name": "Verifier", "icon": "fact_check", "model": "7 checks · code",
                     "status": "idle", "task": "Waiting for proposals", "meta": "", "pass": 0, "fail": 0},
        "reporter": {"name": "Reporter", "icon": "description", "model": model_label("worker"),
                     "status": "idle", "task": "Writes the Done Report at the end", "meta": ""},
    }
    for r in reqs:
        agents[f"kit:{r['buyer']}"] = {"name": f"Kit Agent · {r['buyer']}", "icon": "person",
                                       "model": model_label("planner"), "status": "idle",
                                       "task": f"Needs {', '.join(n.replace('_', ' ') for n in r['needs'])} · ${r['budget']}",
                                       "meta": "", "attempts": 0}
    return agents


def apply(agents, e, max_attempts):
    """Update the org chart state from one event. Returns the id of the agent that acted."""
    a, k, m, buyer = e["agent"], e["kind"], e["message"], e["data"].get("buyer")
    kit = agents.get(f"kit:{buyer}") if buyer else None
    if a == "Intake Agent":
        ag = agents["intake"]
        if k == "intake":
            ag["ok"] += 1
        else:
            ag["blocked"] += 1
        ag.update(status="blocked" if k != "intake" else "working", task=short(m),
                  meta=f"{ag['ok']} accepted · {ag['blocked']} blocked")
        return "intake"
    if a.startswith("Kit Agent") and kit:
        kit["attempts"] += 1
        price = m.split("(")[1].split(")")[0] if "(" in m else ""
        items = m.replace("Proposes ", "").split(" (")[0]
        kit.update(status="working", task=f"Proposed {items} {f'({price})' if price else ''}".strip(),
                   meta=f"attempt {kit['attempts']}/{max_attempts}")
        return f"kit:{buyer}"
    if a == "Verifier":
        ag = agents["verifier"]
        if "Final audit" in m:
            ag.update(status="done" if k == "verify_pass" else "rejected", task=short(m))
            return "verifier"
        if k in ("conflict", "verify_fail"):
            ag["fail"] += 1
            ag.update(status="rejected", task=short(m))
            if kit:
                kit.update(status="rejected", task=short("Rejected: " + m.split("REJECTED: ", 1)[-1], 110))
        elif k == "verify_pass":
            ag["pass"] += 1
            ag.update(status="verified", task=short(m))
            if kit:
                kit.update(status="verified", task="Passed all 7 checks")
        else:
            ag.update(status="working", task=short(m))
        ag["meta"] = f"{ag['pass']} passed · {ag['fail']} rejected"
        return "verifier"
    if a == "Reporter":
        agents["reporter"].update(status="done", task="Done Report written")
        return "reporter"
    if a == "Outside world":
        return "world"
    ctl = agents["controller"]
    if k == "replan" and kit:
        kit.update(status="replanning", task="Replanning with the Verifier's feedback")
        ctl.update(status="working", task=short(m))
    elif k == "reserve" and kit:
        kit.update(status="verified", task=short(m, 110))
        ctl.update(status="working", task=short(m))
    elif k == "escalate" and kit:
        kit.update(status="escalated", task="Out of attempts: handed to a human")
        ctl.update(status="escalated", task=short(m))
    elif k == "done":
        ctl.update(status="done", task=short(m))
    else:
        ctl.update(status="working", task=short(m))
        if m.startswith("Round 1") and agents["intake"]["status"] != "idle":
            agents["intake"].update(status="done", task="Intake finished: new items are in live inventory")
    return "controller"


def card(ag, active):
    label, color = STATUS[ag["status"]]
    return (f'<div class="oc-card{" active" if active else ""}" style="--c:{color}">'
            f'<div class="oc-head"><span class="ms">{ag["icon"]}</span><div><div class="oc-name">{c.esc(ag["name"])}</div>'
            f'<div class="oc-model">{c.esc(ag["model"])}</div></div><span class="oc-pill">{label}</span></div>'
            f'<div class="oc-task">{c.esc(ag["task"])}</div>'
            + (f'<div class="oc-meta">{c.esc(ag["meta"])}</div>' if ag["meta"] else "") + "</div>")


def org_html(agents, active, world):
    kits = [k for k in agents if k.startswith("kit:")]
    team = ('<div class="oc-team"><div class="oc-team-label">Kit Agents · parallel</div>'
            + "".join(card(agents[k], k == active) for k in kits) + "</div>")
    banner = f'<div class="oc-world">⚡ Outside world: {c.esc(world)}</div>' if world else ""
    return (f'<div class="oc">{banner}<div class="oc-top">{card(agents["controller"], active == "controller")}</div>'
            '<div class="oc-v"></div><div class="oc-bar"></div><div class="oc-row">'
            f'<div class="oc-col">{card(agents["intake"], active == "intake")}</div>'
            f'<div class="oc-col">{team}</div>'
            f'<div class="oc-col">{card(agents["verifier"], active == "verifier")}</div>'
            f'<div class="oc-col">{card(agents["reporter"], active == "reporter")}</div></div></div>')


def now_html(e):
    color = KIND_COLOR.get(e["kind"], BLUE)
    return (f'<div class="oc-now" style="--c:{color}"><div class="who">{c.esc(e["agent"])} '
            f'<span class="when">· {e["ts"]:.1f}s</span></div><div class="what">{c.esc(e["message"])}</div></div>')


def feed_html(events):
    rows = [f'<div class="oc-ev" style="--c:{KIND_COLOR.get(e["kind"], GREY)}"><span class="t">{e["ts"]:5.1f}s</span> '
            f'<b>{c.esc(e["agent"])}</b>: {c.esc(e["message"])}</div>' for e in reversed(events)]
    return '<div class="oc-feed">' + "".join(rows) + "</div>"


# ---------------------------------------------------------------- page
st.html(CSS)
st.markdown("## :material/hub: Agent control room")
st.caption("Challenge 01 · Done Means Done. Watch the team work: nothing is done until the Verifier passes it, "
           "and anything that can't be fixed is handed to a human.")

live, chaos, max_attempts, speed = state.run_mode_controls("control")
start = st.sidebar.button("▶ Start the agents", type="primary", width="stretch")

transform = state.SCENARIOS[st.session_state.get("scenario", "standard")][2]
reqs = transform(state.requests()) if transform else state.requests()

chart_col, side_col = st.columns([2.2, 1], gap="medium")
with chart_col:
    st.markdown("**Who is working on what**")
    chart = st.empty()
with side_col:
    st.markdown("**Happening now**")
    now = st.empty()
    st.markdown("**Live feed**")
    feed = st.container(height=470, border=True).empty()
results = st.container()


def render(events, max_att):
    agents, active, world = initial_agents(reqs, max_att), None, None
    for e in events:
        active = apply(agents, e, max_att)
        if active == "world":
            world = e["message"]
    chart.html(org_html(agents, active, world))
    if events:
        now.html(now_html(events[-1]))
        feed.html(feed_html(events))
    else:
        now.info("Press **▶ Start the agents** in the sidebar.")
        feed.caption("Events will stream here.")


if start:
    seen = []

    def on_event(e):
        seen.append(e)
        render(seen, max_attempts)

    render([], max_attempts)
    state.run_agents(on_event, live=live, chaos=chaos, max_attempts=max_attempts, speed=speed)
    st.rerun()

res = state.result()
render(res["events"] if res else [], res["config"]["max_attempts"] if res else max_attempts)

if res:
    kits = res["kits"]
    with results:
        st.divider()
        m = st.columns(5)
        m[0].metric("Kits verified", f"{sum(k['status'] == 'verified' for k in kits)}/{len(kits)}")
        m[1].metric("Proposals rejected", sum(not a["passed"] for k in kits for a in k["history"]))
        m[2].metric("Escalated to a human", sum(k["status"] != "verified" for k in kits))
        m[3].metric("Shipped unverified", sum(k["status"] == "verified" and not all(ch["passed"] for ch in k["checks"])
                                              for k in kits), help="Kits marked done without passing every check. Must be 0.")
        m[4].metric("Run time", f"{res['duration_s']:.1f}s")
        with st.expander("Done Report"):
            st.markdown(c.md_safe(res["report"]))
