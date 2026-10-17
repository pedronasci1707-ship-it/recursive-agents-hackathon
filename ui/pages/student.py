"""My kit: build a move-in kit, adjust it, book delivery. Customer-facing: no agent internals."""

from datetime import date

import streamlit as st

from ui import components as c
from ui import state, store

WINDOWS = ["8–11 am", "12–3 pm", "4–7 pm"]
FRIENDLY = {  # agent event -> what the customer sees while the kit is being built
    "plan": "Picking items that fit your room and budget",
    "conflict": "An item just sold to someone else, finding a replacement",
    "verify_fail": "Skipping an item that didn't pass our checks",
    "verify_pass": "Your kit passed every check",
    "reserve": "Reserving your items",
    "escalate": "Asking our team for a quick review",
}

u = state.user()
reqs = {r["id"]: r for r in state.requests()}
if u["role"] == "student":
    req = reqs[u["request_id"]]
else:  # admin storefront preview
    req = reqs[st.sidebar.selectbox("Preview as", list(reqs), format_func=lambda r: reqs[r]["buyer"])]
rid = req["id"]
res = state.result()
kit = store.kit_for(res, rid)
prefs = st.session_state.setdefault(f"prefs_{rid}", {
    "move_in": date(2027, 8, 12), "budget": int(req["budget"]), "needs": list(req["needs"]),
})


# ---------------------------------------------------------------- build flow
def build_page():
    c.page_header("Move-in kit", f"Hi {req['buyer']}, let's set up your room",
                  "Tell us about your move-in. We build a kit from items in stock and verify it in seconds.")
    if st.session_state.pop(f"no_kit_{rid}", False):  # e.g. a new account while live runs are rate-limited
        st.info("Our agents are busy with other students right now. Try **Build my kit** again in a few seconds.")
    form_col, info_col = st.columns([1.5, 1], gap="large")
    with form_col, st.container(border=True):
        move_in = st.date_input("Move-in date", value=prefs["move_in"], format="MM/DD/YYYY")
        budget = st.slider("Budget", 80, 400, prefs["budget"], step=10, format="$%d")
        needs = st.pills("What do you need?", list(c.LABEL)[:-1], selection_mode="multi",
                         default=prefs["needs"], format_func=lambda k: c.LABEL[k])
        go = st.button("Build my kit", type="primary", icon=":material/auto_awesome:", width="stretch")
    with info_col:
        info = st.empty()
        info.html(f"""
        <div class="feature">{c.icon("tune")}<h4>1 · Tell us what you need</h4>
          <p>What you need, your budget, your move-in date.</p></div>
        <div class="feature">{c.icon("fact_check")}<h4>2 · We build &amp; verify</h4>
          <p>Every item is checked for availability, safety recalls and price before we show it to you.</p></div>
        <div class="feature">{c.icon("local_shipping")}<h4>3 · Delivered on move-in day</h4>
          <p>Inspected, cleaned and waiting in your room.</p></div>""")
    if not go:
        return
    if not needs:
        st.warning("Pick at least one item you need.")
        return
    prefs.update(move_in=move_in, budget=budget, needs=list(needs))
    custom = {**req, "budget": budget, "needs": list(needs),
              "profile": f"{req['profile']}. Moving in {move_in:%b %d}"}
    with info.container(), st.status("Building your kit…", expanded=True) as box:
        shown = set()

        def on_event(e):
            if e["agent"] == "Intake Agent":
                msg = "Adding items just listed by students moving out"
            elif e["data"].get("buyer") == req["buyer"]:
                msg = FRIENDLY.get(e["kind"])
            else:
                msg = None
            if msg and msg not in shown:
                shown.add(msg)
                box.write(f":material/check_small: {msg}")

        res = state.run_agents(on_event, live=state.has_api_key(), custom_request=custom)
        box.update(label="Your kit is ready", state="complete")
    if store.kit_for(res, rid) is None:
        st.session_state[f"no_kit_{rid}"] = True
    st.session_state.pop(f"order_{rid}", None)
    st.rerun()


if kit is None or st.session_state.get(f"rebuild_{rid}"):
    st.session_state.pop(f"rebuild_{rid}", None)
    build_page()
    st.stop()

# ---------------------------------------------------------------- kit page
verified = kit["status"] == "verified"
order = st.session_state.get(f"order_{rid}")
order_no = f"CL-{res['run_id'][:4].upper()}{rid[-1]}"

head, status_col = st.columns([4, 1], vertical_alignment="bottom")
with head:
    c.page_header("Your move-in kit", f"{req['buyer']}'s room kit",
                  f"Moving in {prefs['move_in']:%B %d} · order {order_no}")
with status_col:
    st.html(c.pill("Verified", ico="verified") if verified else c.pill("Under review", "warn", "schedule"))

st.html(c.stepper(["Kit built", "Verified", "Delivery booked", "Delivered"],
                  done=(3 if order else 2) if verified else 1, now=(3 if order else 2) if verified else 1,
                  icons=["inventory_2", "verified", "event", "home"]))

left, right = st.columns([1.65, 1], gap="large")

with left:
    with st.container(border=True):
        st.markdown(f"**{len(kit['items'])} items in your kit**")
        for item in kit["items"]:
            row, actions = st.columns([5, 1.3], vertical_alignment="center")
            row.html(c.line_item(item))
            with actions:
                alts = store.alternatives(res, item)
                with st.popover("Swap", icon=":material/swap_horiz:", disabled=not alts or bool(order),
                                width="stretch"):
                    st.markdown(f"**Other {c.LABEL[item['category']].lower()}s in stock**")
                    pick = st.radio("Choose", alts, key=f"swap_{item['id']}", label_visibility="collapsed",
                                    format_func=lambda i: f"{i['name']} · {c.CONDITION[i['condition']]} · ${i['resale_price']:.0f}")
                    if st.button("Swap item", key=f"do_swap_{item['id']}", type="primary", width="stretch"):
                        ok, msgs = store.swap(res, kit, item["id"], pick["id"])
                        if ok:
                            st.toast("Kit updated and re-verified", icon=":material/verified:")
                            st.rerun()
                        for m in msgs:
                            st.error(m)
                extra = item["category"] not in kit["needs"] or \
                    sum(i["category"] == item["category"] for i in kit["items"]) > 1
                if extra and not order and st.button("Remove", key=f"rm_{item['id']}", icon=":material/close:",
                                                    width="stretch"):
                    store.remove(res, kit, item["id"])
                    st.rerun()
        if u["role"] == "student":  # the admin storefront preview has no Shop page in its navigation
            st.page_link("ui/pages/shop.py", label="Add more for your room", icon=":material/add_shopping_cart:")
    st.html(c.trust_strip())
    with st.expander("How we verified your kit"):
        caught = " ".join(x for a in kit["history"] for x in a["issues"])
        if "already reserved" in caught:
            st.markdown("- An item we picked sold to someone else while we were building your kit, so we replaced it.")
        if "safety recall" in caught:
            st.markdown("- We blocked an item whose model is under a safety recall and chose a safe alternative.")
        for chk, text in [("available_now", "Every item is in stock and reserved for you"),
                          ("no_safety_recalls", "No recalled models"),
                          ("covers_needs", "Covers everything you asked for"),
                          ("within_budget", "Fits your budget")]:
            passed = next((x["passed"] for x in kit["checks"] if x["name"] == chk), False)
            st.markdown(f"{':material/check_circle:' if passed else ':material/cancel:'} {text}")

with right:
    saved = c.savings(kit["items"], kit["price"])
    pct = min(kit["price"] / kit["budget"], 1.0) if kit["budget"] else 0
    with st.container(border=True):
        st.markdown("**Order summary**")
        st.html(f"""
        <div class="sum"><span>Items ({len(kit['items'])})</span><span>${kit['price']:.0f}</span></div>
        <div class="sum muted"><span>Delivery on move-in day</span><span>Free</span></div>
        <div class="sum total"><span>Total</span><span>${kit['price']:.0f}</span></div>
        <div class="sum save"><span>You save vs. buying new</span><span>${saved:.0f}</span></div>
        <div style="margin-top:12px;font-size:.85rem;color:var(--muted)">${kit['price']:.0f} of your ${kit['budget']:.0f} budget</div>
        <div class="meter"><div style="width:{pct * 100:.0f}%"></div></div>""")

    with st.container(border=True):
        if not verified:
            st.markdown("**Delivery**")
            st.info("Our team is reviewing your kit. We never confirm a kit that hasn't passed every check.")
        elif order:
            st.html(f"""<div class="confirm"><h3>{c.icon("task_alt")} Order confirmed</h3>
                <div>Order <b>{order_no}</b></div>
                <div>{order['date']:%A, %B %d} · {order['window']}</div>
                <div>{c.esc(order['where'])}</div></div>""")
            if st.button("Change delivery", icon=":material/edit_calendar:", width="stretch"):
                st.session_state.pop(f"order_{rid}")
                st.rerun()
        else:
            st.markdown("**Book delivery**")
            when = st.date_input("Delivery date", value=prefs["move_in"], format="MM/DD/YYYY")
            window = st.segmented_control("Time window", WINDOWS, default=WINDOWS[1])
            where = st.text_input("Residence and room", placeholder="e.g. Wolf Village, Bldg C, Room 214")
            if st.button("Confirm order", type="primary", icon=":material/lock:", width="stretch"):
                if not where.strip():
                    st.error("Add your residence and room so we know where to deliver.")
                else:
                    st.session_state[f"order_{rid}"] = {"date": when, "window": window or WINDOWS[1], "where": where}
                    st.toast("Order confirmed", icon=":material/task_alt:")
                    st.rerun()
            st.caption("Pay on delivery. Free cancellation until 48h before move-in.")
    if not order and st.button("Start over with new preferences", icon=":material/restart_alt:", width="stretch"):
        st.session_state[f"rebuild_{rid}"] = True
        st.rerun()
