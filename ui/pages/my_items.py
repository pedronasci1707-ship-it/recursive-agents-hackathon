"""My items: everything the signed-in user has sold, with pickup details. Customer-facing."""

import streamlit as st

from ui import components as c
from ui import state

u = state.user()
mine = st.session_state.setdefault(f"my_items:{u['email']}", [])

c.page_header("My items", f"Your items, {u['name']}",
              "Items you sold show up here with their pickup details.")

if not mine:
    st.info("Items you sell will show up here with their pickup details.")
    st.page_link("ui/pages/seller.py", label="Sell an item", icon=":material/sell:")
for item in mine:
    with st.container(border=True):
        row, status = st.columns([5, 1.2], vertical_alignment="center")
        row.html(f"""<div class="line" style="border:none;padding:4px 0">{c.tile(item["category"], 72, item)}
            <div><div class="name">{c.esc(item["name"])}</div>
            <div class="meta">Pickup {item['date']:%a, %b %d} · {item['window']} · {c.esc(item['where'])}</div></div>
            <div class="price">${item['offer']}</div></div>""")
        status.html(c.pill("Pickup booked", ico="event_available"))
