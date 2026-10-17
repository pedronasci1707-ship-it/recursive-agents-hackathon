"""CampusLoop AI: Streamlit demo UI.

Run from the repo root:  streamlit run app.py
Talks to the engine only through campusloop.engine.run() (see docs/CONTRACT.md).
"""

import html
import json
import time
from pathlib import Path

import streamlit as st

SAMPLE_RUN = Path(__file__).parent / "demo" / "sample_run.json"

# Event kind -> (label, accent color). Colors from docs/CONTRACT.md: failures red, success green, replans orange.
KINDS = {
    "verify_fail": ("FAIL", "#e5484d"),
    "conflict": ("CONFLICT", "#e5484d"),
    "verify_pass": ("PASS", "#30a46c"),
    "reserve": ("RESERVE", "#30a46c"),
    "done": ("DONE", "#30a46c"),
    "replan": ("REPLAN", "#f76b15"),
    "escalate": ("ESCALATE", "#f76b15"),
    "plan": ("PLAN", "#3e63dd"),
    "intake": ("INTAKE", "#8e8c99"),
    "info": ("INFO", "#8e8c99"),
}
KIT_STATUS = {
    "verified": ("✅", "verified", "green"),
    "needs_approval": ("⚠️", "needs approval", "orange"),
    "failed": ("❌", "failed", "red"),
    "pending": ("⏳", "pending", "gray"),
}
# Rough price of a comparable NEW item (USD), only for the "students saved" estimate in the impact row.
NEW_RETAIL = {
    "mini_fridge": 170, "microwave": 90, "desk_lamp": 30, "fan": 40, "desk_chair": 120,
    "desk": 150, "storage_bins": 30, "shelf": 60, "kitchen_basics": 70, "other": 30,
}
RUN_STATUS = {
    "done": ("✅ Done", "Every kit verified and the final audit passed."),
    "done_with_escalations": ("⚠️ Done with escalations", "Some kits were handed to a human instead of shipping a bad kit."),
    "failed": ("❌ Failed", "The final audit found problems; nothing ships."),
}

st.set_page_config(page_title="CampusLoop AI", page_icon="♻️", layout="wide")

st.html("""
<style>
.cl-timeline { display: flex; flex-direction: column; gap: 4px; font-size: 0.92rem; }
.cl-row { display: grid; grid-template-columns: 52px 150px 86px 1fr; gap: 10px; align-items: baseline;
          padding: 6px 10px; border-radius: 6px; border-left: 4px solid var(--accent);
          background: color-mix(in srgb, var(--accent) 9%, transparent); }
.cl-ts { font-family: ui-monospace, monospace; opacity: 0.65; text-align: right; }
.cl-agent { font-weight: 600; }
.cl-kind { font-family: ui-monospace, monospace; font-size: 0.75rem; font-weight: 700; color: var(--accent); }
.cl-msg { line-height: 1.35; }
.cl-attempt { padding: 8px 12px; border-radius: 6px; margin: 6px 0; border-left: 4px solid var(--accent);
              background: color-mix(in srgb, var(--accent) 10%, transparent); font-size: 0.92rem; }
.cl-attempt b { color: var(--accent); }
@media (max-width: 700px) { .cl-row { grid-template-columns: 44px 1fr; } .cl-kind, .cl-agent { grid-column: 2; } }
</style>
""")


def money(value):
    """Dollar amount safe for st.markdown ("$" would otherwise start a LaTeX formula)."""
    return f"\\${value:,.0f}"


def md_safe(text):
    return str(text).replace("$", "\\$")


def timeline_html(events):
    rows = []
    for e in events:
        label, color = KINDS.get(e["kind"], (e["kind"].upper(), "#8e8c99"))
        rows.append(
            f'<div class="cl-row" style="--accent:{color}">'
            f'<span class="cl-ts">{e["ts"]:.1f}s</span>'
            f'<span class="cl-agent">{html.escape(e["agent"])}</span>'
            f'<span class="cl-kind">{label}</span>'
            f'<span class="cl-msg">{html.escape(e["message"])}</span></div>'
        )
    return '<div class="cl-timeline">' + "".join(rows) + "</div>"


def history_html(kit):
    """Every attempt of one kit: the failed ones with the Verifier's reason, then the fix."""
    parts = []
    for a in kit["history"]:
        color = "#30a46c" if a["passed"] else "#e5484d"
        verdict = "passed every check" if a["passed"] else "rejected: " + "; ".join(a["issues"])
        parts.append(
            f'<div class="cl-attempt" style="--accent:{color}">'
            f'<b>{"✅" if a["passed"] else "❌"} Attempt {a["attempt"]}</b> · {html.escape(", ".join(a["item_ids"]))}'
            f'<br>{html.escape(verdict)}</div>'
        )
    return "".join(parts)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Run the agents")
    offline = st.toggle("Use sample run", value=True,
                        help="Replays demo/sample_run.json. No API calls, no credits spent.")
    chaos = st.toggle("Simulate outside buyer", value=True, disabled=offline,
                      help="A walk-in buyer grabs an item while the Kit Agents are planning.")
    max_attempts = st.slider("Max attempts per kit", 1, 5, 3, disabled=offline,
                             help="How many plan → verify cycles before escalating to a human.")
    speed = st.slider("Replay speed", 1, 10, 2, disabled=not offline,
                      help="Sample run only: how fast the recorded timeline is replayed.")
    go = st.button("Run agents", type="primary", width="stretch")
    st.divider()
    st.caption("Intake Agent → Kit Agents (parallel) → Verifier → Recursive Controller → Reporter")

# ---------------------------------------------------------------- header
st.title("♻️ CampusLoop AI")
st.markdown("**Autonomous recommerce agents for university move-out**")
st.caption("Powered by Crusoe Managed Inference + NVIDIA Nemotron · Challenge 01: Done Means Done")

# ---------------------------------------------------------------- run
if go:
    st.session_state.pop("result", None)
    st.subheader("Live agent timeline")
    st.caption("Newest event on top")
    status_box = st.status("Agents working…", expanded=False)
    timeline = st.empty()
    seen = []

    def on_event(event):
        seen.append(event)
        # Newest first while running, so the key moments stay on screen; the full log is chronological afterwards.
        timeline.html(timeline_html(reversed(seen)))
        status_box.update(label=md_safe(f"{event['agent']}: {event['message'][:90]}"))

    try:
        if offline:
            result = json.loads(SAMPLE_RUN.read_text(encoding="utf-8"))
            last_ts = 0.0
            for event in result["events"]:
                time.sleep(min(max(event["ts"] - last_ts, 0.15), 3.0) / speed)
                last_ts = event["ts"]
                on_event(event)
        else:
            from campusloop.engine import run  # imported here so the sample mode works without the engine

            result = run(on_event=on_event, simulate_outside_buyer=chaos, max_attempts=max_attempts)
    except Exception as exc:  # show the failure in the UI instead of a stack trace
        status_box.update(label="Run failed", state="error")
        st.error(f"The run failed: {type(exc).__name__}: {exc}")
        st.stop()

    status_box.update(label=f"Finished in {result['duration_s']:.1f}s", state="complete")
    st.session_state.result = result
    st.session_state.source = "sample run" if offline else "live run on Crusoe"
    st.rerun()

result = st.session_state.get("result")
if not result:
    st.info("Press **Run agents** in the sidebar. Leave **Use sample run** on to replay a recorded run "
            "without spending credits, or turn it off to run the real agents on Crusoe.")
    st.stop()

# ---------------------------------------------------------------- summary
kits = result["kits"]
verified = sum(k["status"] == "verified" for k in kits)
blocked = sum(not i["accepted"] for i in result["intake"])
retries = sum(k["attempts"] - 1 for k in kits)
tokens = sum(u["prompt"] + u["completion"] for u in result["usage"].values())
label, blurb = RUN_STATUS.get(result["status"], (result["status"], ""))

st.subheader(label)
st.caption(f"{blurb} · {st.session_state.get('source', 'run')} `{result['run_id']}`")
m = st.columns(5)
m[0].metric("Kits verified", f"{verified}/{len(kits)}")
m[1].metric("Failed attempts fixed", retries)
m[2].metric("Unsafe listings blocked", blocked)
m[3].metric("Duration", f"{result['duration_s']:.1f}s")
m[4].metric("Tokens", f"{tokens:,}")

# ---------------------------------------------------------------- impact
shipped = [i for k in kits if k["status"] == "verified" for i in k["items"]]
paid_by_students = sum(k["price"] for k in kits if k["status"] == "verified")
new_cost = sum(NEW_RETAIL.get(i["category"], NEW_RETAIL["other"]) for i in shipped)
st.subheader("Impact of this run")
m = st.columns(4)
m[0].metric("Items given a second life", len(shipped), help="Move-out items placed in a verified kit instead of a dumpster.")
m[1].metric("Students saved (est.)", f"${max(new_cost - paid_by_students, 0):,.0f}",
            help="Estimated price of the same items bought new, minus what the students pay. See assumptions below.")
m[2].metric("Paid to move-out sellers", f"${sum(i['acquisition_cost'] for i in shipped):,.0f}",
            help="What CampusLoop pays the students who are moving out for these items.")
m[3].metric("CampusLoop profit", f"${sum(k['margin'] for k in kits if k['status'] == 'verified'):,.0f}",
            help="Kit prices minus acquisition, refurbishing and delivery. Every kit keeps at least a 30% margin.")
with st.expander("Assumptions: typical new retail price per category"):
    st.dataframe([{"Category": c.replace("_", " "), "New (USD)": f"${p}"} for c, p in NEW_RETAIL.items()],
                 hide_index=True)
    st.caption("Rough US retail prices for comparable new items, used only for the savings estimate.")

# ---------------------------------------------------------------- done means done
st.subheader("Done means done: what the Verifier caught")
fixed = [k for k in kits if any(not a["passed"] for a in k["history"])]
if fixed:
    cols = st.columns(len(fixed))
    for col, kit in zip(cols, fixed):
        with col, st.container(border=True):
            icon, text, _ = KIT_STATUS.get(kit["status"], ("", kit["status"], "gray"))
            st.markdown(f"**{kit['buyer']}** · {kit['attempts']} attempts → {icon} {text}")
            st.html(history_html(kit))
else:
    st.success("Every kit passed verification on the first attempt.")

# ---------------------------------------------------------------- kit cards
st.subheader("Kits for incoming students")
cols = st.columns(len(kits))
for col, kit in zip(cols, kits):
    icon, text, color = KIT_STATUS.get(kit["status"], ("", kit["status"], "gray"))
    with col, st.container(border=True):
        st.markdown(f"### {kit['buyer']}")
        st.markdown(f":{color}-badge[{icon} {text}] :gray-badge[{kit['attempts']} attempt(s)]")
        st.caption(md_safe(kit["profile"]))
        a, b = st.columns(2)
        a.metric("Price", f"${kit['price']:.0f}")
        b.metric("Margin", f"{kit['margin_pct']:.0f}%")
        st.caption(f"Budget {money(kit['budget'])} · our cost {money(kit['cost'])} · profit {money(kit['margin'])}")
        st.dataframe(
            [{"Item": i["name"], "ID": i["id"], "Cond.": i["condition"], "Price": f"${i['resale_price']:.0f}"}
             for i in kit["items"]],
            hide_index=True, width="stretch",
        )
        with st.expander("Verification checks"):
            for c in kit["checks"]:
                st.markdown(f"{'✅' if c['passed'] else '❌'} **{c['name']}**: {md_safe(c['detail'])}")
        with st.expander("Attempt history"):
            st.html(history_html(kit))
        if kit["rationale"]:
            with st.expander("Kit Agent's reasoning"):
                st.write(md_safe(kit["rationale"]))

# ---------------------------------------------------------------- timeline, intake, report
tab_timeline, tab_intake, tab_report, tab_usage = st.tabs(
    ["Agent timeline", "Move-out intake", "Done Report", "Crusoe usage"])

with tab_timeline:
    st.html(timeline_html(result["events"]))

with tab_intake:
    st.dataframe(
        [{"": "✅" if i["accepted"] else "⛔", "Listing": i["listing_id"], "Seller": i["seller"],
          "Listing text": i["text"], "Decision": i["reason"]} for i in result["intake"]],
        hide_index=True, width="stretch",
        column_config={"Listing text": st.column_config.TextColumn(width="large"),
                       "Decision": st.column_config.TextColumn(width="large")},
    )

with tab_report:
    st.markdown(md_safe(result["report"]))

with tab_usage:
    st.dataframe(
        [{"Model": model, "Requests": u["requests"], "Prompt tokens": u["prompt"],
          "Completion tokens": u["completion"], "Cached": u["cached"],
          "Cache hit rate": f"{u['cache_hit_rate']:.0%}"} for model, u in result["usage"].items()],
        hide_index=True, width="stretch",
    )
    st.caption("All model calls go through Crusoe Managed Inference (api.inference.crusoecloud.com).")
