"""My kit: build a move-in kit, adjust it, book delivery. Customer-facing: no agent internals."""

import time
from datetime import date, datetime, timedelta

import streamlit as st

from campusloop import rules
from ui import components as c
from ui import state, store

WINDOWS = ["8–11 am", "12–3 pm", "4–7 pm"]
HOLD_MINUTES = 10   # how long items stay reserved at checkout before going back to the shop
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
    "min_condition": "B", "colors": [], "style": None,
})
QUALITY_OPTIONS = ["C", "B", "A"]   # Fair, Good, Excellent: "at least this good"


# ---------------------------------------------------------------- checkout (demo, Stripe-style; nothing is charged)
TEST_CARD_HELP = "Demo checkout: no real payment. Use test card 4242 4242 4242 4242, any future date, any CVC."
DECLINED_TEST_CARD = "4000000000000002"   # same convention as Stripe's test cards


def _luhn_ok(number):
    digits = [int(d) for d in number][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digits))
    return len(number) in (15, 16) and total % 10 == 0


def _card_problems(name, address, number, expiry, cvc):
    problems = []
    if not name.strip():
        problems.append("Add the name on the card.")
    if not address.strip():
        problems.append("Add your delivery address so we know where to bring your kit.")
    if not _luhn_ok(number):
        problems.append("That card number doesn't look right.")
    parts = expiry.replace(" ", "").split("/")
    if len(parts) != 2 or not all(p.isdigit() for p in parts) or not 1 <= int(parts[0]) <= 12 \
            or (2000 + int(parts[1][-2:]), int(parts[0])) < (date.today().year, date.today().month):
        problems.append("Expiry should be a future month, like 08/28.")
    if not (cvc.isdigit() and len(cvc) in (3, 4)):
        problems.append("CVC is the 3 digits on the back of the card.")
    return problems


def checkout(kit, order_no):
    """Name, delivery address and card. On 'Pay', the agents re-check the kit before the order is confirmed."""
    until = st.session_state[f"hold_until_{rid}"]
    st.markdown("**Checkout**")
    st.html(c.pill(f"Your items are held for you until {until:%I:%M %p}".replace(" 0", " "), ico="timer"))
    st.caption(f":material/info: {TEST_CARD_HELP}")
    name = st.text_input("Full name", placeholder="Ana Souza", key=f"co_name_{rid}")
    address = st.text_input("Delivery address", placeholder="Wolf Village, Bldg C, Room 214, Raleigh NC",
                            key=f"co_addr_{rid}")
    number = st.text_input("Card number", placeholder="1234 1234 1234 1234", max_chars=19, key=f"co_card_{rid}")
    exp_col, cvc_col = st.columns(2)
    expiry = exp_col.text_input("Expiry", placeholder="MM / YY", max_chars=7, key=f"co_exp_{rid}")
    cvc = cvc_col.text_input("CVC", placeholder="123", max_chars=4, type="password", key=f"co_cvc_{rid}")
    pay = st.button(f"Pay ${kit['price']:.0f}", type="primary", icon=":material/lock:", width="stretch")
    if st.button("Cancel and release my items", icon=":material/close:", width="stretch"):
        store.release(res, kit)
        st.toast("Items released back to the shop", icon=":material/undo:")
        st.rerun()
    if not pay:
        st.caption(f"Delivered on move-in day, {prefs['move_in']:%B %d}. Free cancellation until 48h before.")
        return
    if datetime.now() > until:   # the hold ran out while the form was open
        store.release(res, kit)
        st.error("Your hold expired and the items went back to the shop. You were not charged.")
        return
    digits = "".join(ch for ch in number if ch.isdigit())
    problems = _card_problems(name, address, digits, expiry, cvc)
    if problems:
        for p in problems:
            st.error(p)
        return
    with st.status("Processing your order…", expanded=True) as box:
        box.write(":material/lock: Securing your payment")
        time.sleep(0.9)
        if digits == DECLINED_TEST_CARD:
            box.update(label="Payment declined", state="error")
            st.error("Your card was declined. Try another card.")
            return
        box.write(":material/fact_check: Our agents are re-checking every item is still reserved for you")
        time.sleep(0.9)
        if problems := store.final_check(res, kit):
            box.update(label="We couldn't confirm your kit", state="error")
            for p in problems:
                st.error(p)
            st.info("You were not charged. Swap the item or start over to rebuild your kit.")
            return
        box.write(":material/local_shipping: Scheduling delivery for move-in day")
        time.sleep(0.7)
        box.update(label="Payment approved · order confirmed", state="complete")
    store.mark_sold(res, kit)
    st.session_state.pop(f"hold_until_{rid}", None)
    brand = {"4": "Visa", "5": "Mastercard", "3": "Amex"}.get(digits[0], "Card")
    # Only the last 4 digits are kept, never the full card number or CVC.
    st.session_state[f"order_{rid}"] = {"date": prefs["move_in"], "window": WINDOWS[1], "where": address.strip(),
                                        "name": name.strip(), "brand": brand, "last4": digits[-4:],
                                        "amount": kit["price"]}
    for k in (f"co_card_{rid}", f"co_cvc_{rid}", f"co_exp_{rid}"):
        st.session_state.pop(k, None)
    st.toast(f"Order {order_no} confirmed", icon=":material/task_alt:")
    time.sleep(0.6)
    st.rerun()


# ---------------------------------------------------------------- build flow
def item_pref_rows(needs):
    """One row per needed item: its own minimum quality, color and style."""
    saved = prefs.get("item_prefs", {})
    out = {}
    for cat in needs:
        p = saved.get(cat, {})
        with st.container(border=True):
            st.markdown(f"**{c.LABEL[cat]}**")
            q_col, c_col, s_col = st.columns(3)
            q = q_col.selectbox("Quality", QUALITY_OPTIONS, key=f"ip_q_{rid}_{cat}",
                                index=QUALITY_OPTIONS.index(p.get("min_condition", "B")),
                                format_func=lambda q: f"{c.CONDITION[q]}{'+' if q != 'A' else ''}")
            colors = [None] + [k for k in rules.COLORS if k != "other"]
            col = c_col.selectbox("Color", colors, key=f"ip_c_{rid}_{cat}", index=colors.index(p.get("color")),
                                  format_func=lambda k: "Any" if k is None else k.capitalize())
            styles = [None] + rules.STYLES
            sty = s_col.selectbox("Style", styles, key=f"ip_s_{rid}_{cat}", index=styles.index(p.get("style")),
                                  format_func=lambda k: "Any" if k is None else k.capitalize())
        out[cat] = {"min_condition": q, "color": col, "style": sty}
    return out


def build_page():
    c.page_header("Move-in kit", f"Hi {req['buyer']}, let's set up your room",
                  "Tell us about your move-in. We build a kit from items in stock and verify it in seconds.")
    if st.session_state.pop(f"no_kit_{rid}", False):  # e.g. a new account while live runs are rate-limited
        st.info("Our agents are busy with other students right now. Try **Build my kit** again in a few seconds.")
    form_col, info_col = st.columns([1.5, 1], gap="large")
    with form_col, st.container(border=True):
        move_in = st.date_input("Move-in date", value=max(prefs["move_in"], date.today()),
                                min_value=date.today(), format="MM/DD/YYYY")
        budget = st.slider("Budget", 80, 400, prefs["budget"], step=10, format="$%d")
        needs = st.pills("What do you need?", list(c.LABEL)[:-1], selection_mode="multi",
                         default=prefs["needs"], format_func=lambda k: c.LABEL[k])
        mode = st.segmented_control("Select by", ["kit", "item"], default=prefs.get("mode", "kit"),
                                    format_func=lambda m: "Whole kit" if m == "kit" else "Individual item",
                                    help="Whole kit: one quality, color and style for everything. "
                                         "Individual item: choose them for each item.")
        quality, colors, style, item_prefs = "C", [], None, {}
        if mode != "item":
            quality = st.segmented_control(
                "Minimum quality", QUALITY_OPTIONS, default=prefs.get("min_condition", "B"),
                format_func=lambda q: f"{c.CONDITION[q]}{' or better' if q != 'A' else ' (like new)'}",
                help="Our agents never put an item below this quality in your kit.")
            colors = st.pills("Colors you like", [k for k in rules.COLORS if k != "other"], selection_mode="multi",
                              default=prefs.get("colors", []), format_func=str.capitalize)
            style = st.segmented_control("Room style", rules.STYLES, default=prefs.get("style"),
                                         format_func=str.capitalize)
        else:
            item_prefs = item_pref_rows(needs or [])
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
    prefs.update(move_in=move_in, budget=budget, needs=list(needs), min_condition=quality or "C",
                 colors=list(colors), style=style, mode=mode or "kit", item_prefs=item_prefs)
    custom = {**req, "budget": budget, "needs": list(needs), "min_condition": quality or "C",
              "colors": list(colors), "style": style, "item_prefs": item_prefs,
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
        built = store.kit_for(res, rid)
        box.update(label="Your kit is ready" if built and built["status"] == "verified"
                   else "Your request needs a quick human review", state="complete")
    if store.kit_for(res, rid) is None:
        st.session_state[f"no_kit_{rid}"] = True
    st.session_state.pop(f"order_{rid}", None)
    st.rerun()


if kit is None or st.session_state.get(f"rebuild_{rid}"):
    if kit and st.session_state.pop(f"rebuild_{rid}", None) and not st.session_state.get(f"order_{rid}"):
        store.release(res, kit)   # starting over gives the held items back to the shop
    st.session_state.pop(f"hold_until_{rid}", None)
    build_page()
    st.stop()

# ---------------------------------------------------------------- kit page
verified = kit["status"] == "verified"
order = st.session_state.get(f"order_{rid}")
order_no = f"CL-{res['run_id'][:4].upper()}-{rid[-4:].upper()}"

# Checkout hold: the verified kit's items stay reserved for this student for HOLD_MINUTES. If they don't pay in
# time (or cancel), the items go back to the shop for other students.
hold_key = f"hold_until_{rid}"
if verified and not order:
    if store.is_held(res, kit) and hold_key not in st.session_state:
        st.session_state[hold_key] = datetime.now() + timedelta(minutes=HOLD_MINUTES)
    if store.is_held(res, kit) and datetime.now() > st.session_state[hold_key]:
        store.release(res, kit)
held = verified and not order and store.is_held(res, kit)
if verified and not order and not held:
    st.session_state.pop(hold_key, None)

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
                    rank = {"A": 3, "B": 2, "C": 1}
                    better = sorted((a for a in alts if rank[a["condition"]] > rank[item["condition"]]),
                                    key=lambda a: a["resale_price"])
                    cheaper = sorted((a for a in alts if a["resale_price"] < item["resale_price"]),
                                     key=lambda a: (-rank[a["condition"]], a["resale_price"]))
                    choice = None
                    q1, q2 = st.columns(2)
                    if q1.button("Better quality", key=f"up_{item['id']}", icon=":material/arrow_upward:",
                                 disabled=not better, width="stretch"):
                        choice = better[0]
                    if q2.button("Lower price", key=f"down_{item['id']}", icon=":material/arrow_downward:",
                                 disabled=not cheaper, width="stretch"):
                        choice = cheaper[0]
                    st.markdown(f"**Other {c.LABEL[item['category']].lower()}s in stock**")
                    for alt in alts:
                        a_row, a_btn = st.columns([4, 1.2], vertical_alignment="center")
                        a_row.html(c.line_item(alt))
                        if a_btn.button("Choose", key=f"pick_{item['id']}_{alt['id']}", width="stretch"):
                            choice = alt
                    if choice:
                        ok, msgs = store.swap(res, kit, item["id"], choice["id"])
                        if ok:
                            st.toast(f"Swapped for {choice['name']} · kit re-verified", icon=":material/verified:")
                            st.rerun()
                        for m in msgs:
                            st.error(m)
                extra = item["category"] not in kit["needs"] or \
                    sum(i["category"] == item["category"] for i in kit["items"]) > 1
                if extra and not order and st.button("Remove", key=f"rm_{item['id']}", icon=":material/close:",
                                                    width="stretch"):
                    ok, msgs = store.remove(res, kit, item["id"])
                    if ok:
                        st.toast(f"Removed {item['name']} · kit re-verified", icon=":material/verified:")
                        st.rerun()
                    for message in msgs:
                        st.error(message)
        if u["role"] == "student":  # the admin storefront preview has no Shop page in its navigation
            st.page_link("ui/pages/shop.py", label="Add more for your room", icon=":material/add_shopping_cart:")
    st.html(c.trust_strip())
    with st.expander("How we verified your kit"):
        caught = " ".join(x for a in kit["history"] for x in a["issues"])
        if "already reserved" in caught:
            st.markdown("- An item we picked sold to someone else while we were building your kit, so we replaced it.")
        if "safety recall" in caught:
            st.markdown("- We blocked an item whose model is under a safety recall and chose a safe alternative.")
        if "quality the student asked for" in caught:
            st.markdown("- We swapped an item that was below the quality you asked for.")
        min_q = prefs.get("min_condition")
        quality_text = ("Every item meets the quality you chose for it" if prefs.get("mode") == "item"
                        else f"Every item is {c.CONDITION.get(min_q, 'the chosen')} quality or better")
        quality_row = [("min_quality", quality_text)] if any(x["name"] == "min_quality" for x in kit["checks"]) else []
        for chk, text in quality_row + [("available_now", "Every item is in stock and reserved for you"),
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
                <div>Order <b>{order_no}</b> · paid ${order.get('amount', kit['price']):.0f} with
                     {order.get('brand', 'card')} •••• {order.get('last4', '----')}</div>
                <div>Delivery {order['date']:%A, %B %d} · {order['window']}</div>
                <div>{c.esc(order.get('name', ''))} · {c.esc(order['where'])}</div></div>""")
            st.caption("A receipt would be emailed to you. This is a demo: no real payment was made.")
        elif held:
            checkout(kit, order_no)
        else:
            st.markdown("**Checkout**")
            st.warning("Your hold ended, so these items went back to the shop for other students. "
                       "You were not charged.", icon=":material/timer_off:")
            if st.button("Hold my items again", type="primary", icon=":material/lock_clock:", width="stretch"):
                ok, msgs = store.hold_again(res, kit)
                if ok:
                    st.toast(f"Items held for {HOLD_MINUTES} minutes", icon=":material/timer:")
                    st.rerun()
                for m in msgs:
                    st.error(m)
                st.info("Some items were taken. Swap them or start over to rebuild your kit.")
    if not order and st.button("Start over with new preferences", icon=":material/restart_alt:", width="stretch"):
        st.session_state[f"rebuild_{rid}"] = True
        st.rerun()
