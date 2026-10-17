"""Operations console: the full picture of a run (built by Augusto)."""

import streamlit as st

from ui import state
from ui.components import NEW_RETAIL, history_html, md_safe, money, timeline_html

KIT_STATUS = {
    "verified": ("✅", "verified", "green"),
    "needs_approval": ("⚠️", "needs approval", "orange"),
    "failed": ("❌", "failed", "red"),
    "pending": ("⏳", "pending", "gray"),
}
RUN_STATUS = {
    "done": ("✅ Done", "Every kit verified and the final audit passed."),
    "done_with_escalations": ("⚠️ Done with escalations", "Some kits were handed to a human instead of shipping a bad kit."),
    "failed": ("❌ Failed", "The final audit found problems; nothing ships."),
}

st.title("🛠️ Operations console")
st.caption("Everything the agents did in the last run: verification, kits, impact, timeline and Crusoe usage.")

live, chaos, max_attempts, speed = state.run_mode_controls("ops")
if st.sidebar.button("Run agents", type="primary", width="stretch"):
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
        result = state.run_agents(on_event, live=live, chaos=chaos, max_attempts=max_attempts, speed=speed)
    except Exception as exc:  # show the failure in the UI instead of a stack trace
        status_box.update(label="Run failed", state="error")
        st.error(f"The run failed: {type(exc).__name__}: {exc}")
        st.stop()
    status_box.update(label=f"Finished in {result['duration_s']:.1f}s", state="complete")
    st.rerun()

result = state.result()
if not result:
    st.info("Press **Run agents** in the sidebar to run the agent team.")
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
