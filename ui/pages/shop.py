"""Shop: browse what is in stock and add it to your kit (re-verified on every change)."""

import streamlit as st

from ui import components as c
from ui import state, store

SORTS = {
    "Recommended": lambda i: ("ABC".index(i["condition"]), -c.new_price(i) + i["resale_price"]),
    "Price: low to high": lambda i: i["resale_price"],
    "Price: high to low": lambda i: -i["resale_price"],
    "Biggest savings": lambda i: i["resale_price"] / c.new_price(i),
}

u = state.user()
res = state.result()
kit = store.kit_for(res, u.get("request_id")) if u["role"] == "student" else None
locked = kit is not None and st.session_state.get(f"order_{kit['request_id']}")

c.page_header("Shop", "Everything for your room",
              "Pre-loved, inspected and recall-checked. Delivered with your kit on move-in day.")
if kit:
    st.html(c.pill(f"Adding to your kit · ${kit['price']:.0f} of ${kit['budget']:.0f} budget", ico="shopping_bag"))
elif u["role"] == "student":
    st.page_link("ui/pages/student.py", label="Build your kit first to add items", icon=":material/arrow_forward:")

items = store.shop_items(res)
f1, f2, f3 = st.columns([3, 1.2, 1.2], vertical_alignment="bottom")
cats = f1.pills("Category", sorted({i["category"] for i in items}, key=list(c.LABEL).index),
                selection_mode="multi", format_func=lambda k: c.LABEL[k], label_visibility="collapsed")
sort = f2.selectbox("Sort", list(SORTS), label_visibility="collapsed")
max_price = f3.slider("Max price", 10, 100, 100, step=5, format="$%d", label_visibility="collapsed")

shown = sorted((i for i in items if (not cats or i["category"] in cats) and i["resale_price"] <= max_price),
               key=SORTS[sort])
st.caption(f"{len(shown)} items in stock")

if not shown:
    st.info("Nothing matches those filters right now. New items arrive every day during move-out season.")
for start in range(0, len(shown), 3):
    for col, item in zip(st.columns(3, gap="medium"), shown[start:start + 3]):
        with col:
            st.html(c.product_card(item))
            if kit and not locked:
                if st.button("Add to my kit", key=f"add_{item['id']}", icon=":material/add:", width="stretch"):
                    ok, msgs = store.add(res, kit, item["id"])
                    if ok:
                        st.toast(f"Added {item['name']} · kit re-verified", icon=":material/verified:")
                        st.rerun()
                    for m in msgs:
                        st.error(m)
            else:
                st.button("Add to my kit", key=f"add_{item['id']}", icon=":material/add:", width="stretch",
                          disabled=True, help="Your order is confirmed." if locked else "Build your move-in kit first.")
            st.write("")
