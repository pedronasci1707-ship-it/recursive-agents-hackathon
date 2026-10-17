"""Split screen for the demo: the storefront on the left, the agents' reasoning on the right."""

import streamlit as st

from campusloop import rules
from ui import components as c
from ui import state

GREY, BLUE, RED, ORANGE, GREEN = "#8e8c99", "#3e63dd", "#e5484d", "#f76b15", "#30a46c"

st.markdown("## ⚡ Live: the platform and the agents, side by side")
st.caption("Left: what students see on CampusLoop. Right: what the agents are thinking. "
           "Challenge 01: Done Means Done. Nothing is confirmed until it passes verification.")

live, chaos, max_attempts, speed = state.run_mode_controls("live")
start = st.sidebar.button("▶ Start", type="primary", width="stretch")

reqs = state.requests()
catalog = {i["id"]: i for i in rules.load("catalog.json")}


def order_html(req, order):
    items = " · ".join(f"{c.ICONS.get(catalog[i]['category'], '🏷️')} {c.esc(catalog[i]['name'])}"
                       for i in order["items"] if i in catalog)
    price = sum(catalog[i]["resale_price"] for i in order["items"] if i in catalog)
    items_html = f'<div class="items">{items} · <b>${price:.0f}</b></div>' if items else ""
    return (f'<div class="cl-order" style="--accent:{order["color"]}">'
            f'<div class="who">{c.esc(req["buyer"])} <span style="font-weight:400;opacity:.7">· '
            f'{c.esc(req["profile"].split(",")[0])}</span></div>'
            f'<div class="state">{c.esc(order["label"])}</div>{items_html}</div>')


def apply_event(orders, e):
    """Update the customer-facing state of an order from one agent event."""
    if e["kind"] == "intake" and (item := e["data"].get("item")):
        catalog[item["id"]] = item
    buyer = e["data"].get("buyer")
    if buyer not in orders:
        return
    o = orders[buyer]
    if e["kind"] == "plan":
        o.update(label="🛠️ Assembling your kit…", color=BLUE, items=e["data"].get("item_ids", []))
    elif e["kind"] == "conflict":
        o.update(label="🔁 An item just sold to someone else: replacing it", color=RED)
    elif e["kind"] == "verify_fail":
        recall = "recall" in e["message"]
        o.update(label="🛡️ Blocked a recalled item: picking a safe one" if recall
                 else "⚠️ Didn't pass our checks: fixing it", color=RED)
    elif e["kind"] == "replan":
        o.update(color=ORANGE)
    elif e["kind"] == "verify_pass":
        o.update(label="✅ Verified & reserved: ready to confirm", color=GREEN, items=e["data"].get("item_ids", o["items"]))
    elif e["kind"] == "escalate":
        o.update(label="👤 Our team is reviewing this kit", color=ORANGE)


left, right = st.columns([1, 1.25], gap="large")
with left:
    st.markdown("#### 🛍️ What students see")
    world = st.empty()
    slots = {r["buyer"]: st.empty() for r in reqs}
with right:
    st.markdown("#### 🧠 What the agents are thinking")
    feed = st.container(height=560, border=True).empty()
summary = st.container()


def render(orders, events, banner=None):
    for r in reqs:
        slots[r["buyer"]].html(order_html(r, orders[r["buyer"]]))
    if banner:
        world.html(f'<div class="cl-world">🏃 {c.esc(banner)}</div>')
    feed.html(c.timeline_html(list(reversed(events))))   # newest on top


orders = {r["buyer"]: {"label": "⏳ Waiting for agents", "color": GREY, "items": []} for r in reqs}

if start:
    seen, ctx = [], {"banner": None}

    def on_event(e):
        seen.append(e)
        apply_event(orders, e)
        if e["agent"] == "Outside world":
            ctx["banner"] = e["message"]
        render(orders, seen, ctx["banner"])

    render(orders, seen)
    state.run_agents(on_event, live=live, chaos=chaos, max_attempts=max_attempts, speed=speed)
    st.rerun()

res = state.result()
if not res:
    render(orders, [])
    st.info("Press **▶ Start** in the sidebar to watch the agents build and verify every kit.")
    st.stop()

banner = None
for e in res["events"]:
    apply_event(orders, e)
    if e["agent"] == "Outside world":
        banner = e["message"]
render(orders, res["events"], banner)

with summary:
    kits = res["kits"]
    fixed = sum(not a["passed"] for k in kits for a in k["history"])
    m = st.columns(5)
    m[0].metric("Kits verified", f"{sum(k['status'] == 'verified' for k in kits)}/{len(kits)}")
    m[1].metric("Problems caught", fixed)
    m[2].metric("Escalated to a human", sum(k["status"] != "verified" for k in kits))
    m[3].metric("Shipped unverified", sum(k["status"] == "verified" and not all(ch["passed"] for ch in k["checks"])
                                          for k in kits), help="Kits marked done without passing every check. Must be 0.")
    m[4].metric("Run time", f"{res['duration_s']:.1f}s")
    st.caption(f"Source: {st.session_state.get('source', 'run')} · run `{res['run_id']}`")
