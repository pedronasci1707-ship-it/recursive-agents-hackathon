import streamlit as st

from ui import components as c
from ui import state

STEPS = ["Requested", "Agents assembling", "Verified", "Out for delivery", "Delivered"]
FRIENDLY = {
    "plan": "Picking items that fit your room and budget…",
    "conflict": "An item just sold to someone else. Finding a replacement…",
    "verify_fail": "Blocked an item that didn't pass our checks. Fixing it…",
    "replan": "Re-checking the new combination…",
    "verify_pass": "Your kit passed every check ✓",
    "reserve": "Items reserved for you ✓",
    "escalate": "Handing your kit to our team for a quick review…",
}

u = state.user()
reqs = {r["id"]: r for r in state.requests()}
if u["role"] == "student":
    req = reqs[u["request_id"]]
else:
    req = reqs[st.sidebar.selectbox("View as student", list(reqs), format_func=lambda r: reqs[r]["buyer"])]

c.hero(f"Hi {req['buyer']} 👋", f"Your move-in kit · {req['profile']}")

res = state.result()
kit = next((k for k in res["kits"] if k["request_id"] == req["id"]), None) if res else None

if kit is None:
    with st.container(border=True):
        st.markdown("### Your kit is not assembled yet")
        st.write(f"You asked for: **{', '.join(n.replace('_', ' ') for n in req['needs'])}** · "
                 f"budget **{c.money(req['budget'])}**.")
        if st.button("Assemble my kit", type="primary"):
            box = st.status("Our agents are assembling your kit…", expanded=True)

            def on_event(e):
                if e["data"].get("buyer") == req["buyer"] and e["kind"] in FRIENDLY:
                    box.write(FRIENDLY[e["kind"]])

            state.run_agents(on_event, live=state.has_api_key())
            box.update(label="Done", state="complete")
            st.rerun()
    st.stop()

confirmed = st.session_state.get(f"confirmed_{req['id']}", False)
verified = kit["status"] == "verified"
if verified:
    st.html(c.steps(STEPS, 4 if confirmed else 3, now=3 if confirmed else None))
else:
    st.html(c.steps(STEPS, 1, now=1))
    st.warning("Our team is reviewing your kit before we confirm it. We never ship a kit that hasn't passed every check.")

left, right = st.columns([1.7, 1], gap="large")
with left:
    st.markdown("### Your kit")
    st.html('<div class="cl-card">' + c.product_rows(kit["items"]) + "</div>")
    st.html(c.badges(["🛡️ Safety-recall checked", "✨ Inspected & cleaned", "📌 Reserved for you",
                      f"🔁 Verified {kit['attempts']}x by our agents"]))
    story = c.customer_story(kit)
    with st.expander("How our agents built your kit"):
        if story:
            for line in story:
                st.markdown(f"- {line}")
        st.markdown(f"- Every combination was checked against live inventory, safety recalls and your budget "
                    f"({kit['attempts']} attempt(s)) before we showed it to you.")
        if kit["rationale"]:
            st.caption(c.md_safe(f"Kit Agent: {kit['rationale']}"))

with right:
    saved = c.savings(kit["items"], kit["price"])
    with st.container(border=True):
        st.markdown("### Order summary")
        st.metric("Kit price", f"${kit['price']:.0f}", f"you save ${saved:.0f} vs. new")
        st.caption(f"Your budget {c.money(kit['budget'])} · delivery included · arrives before move-in")
        if not verified:
            st.button("Confirm kit", disabled=True, width="stretch")
        elif confirmed:
            st.success("Confirmed! Delivery scheduled for your move-in day.")
        elif st.button("Confirm kit & schedule delivery", type="primary", width="stretch"):
            st.session_state[f"confirmed_{req['id']}"] = True
            st.balloons()
            st.rerun()
    st.caption("Estimated savings use typical new retail prices for comparable items.")
