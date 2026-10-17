"""Sell before you leave: photo or text -> instant offer -> pickup. Customer-facing."""

from datetime import date

import streamlit as st

from campusloop import agents, db, rules
from ui import components as c
from ui import state

WINDOWS = ["8–11 am", "12–3 pm", "4–7 pm"]

u = state.user()
name = u["name"]
mine = st.session_state.setdefault("my_items", [])

c.page_header("Sell before you leave", f"Moving out, {name}?",
              "Add a photo to get a provisional offer. We confirm condition and operation at pickup.")
tab_new, tab_mine = st.tabs(["Sell an item", f"My items ({len(mine)})"])

with tab_new:
    left, right = st.columns([1.15, 1], gap="large")
    with left, st.container(border=True):
        photo = st.file_uploader("Photo of the item (required)", type=["png", "jpg", "jpeg", "webp"])
        examples = {f"{l['text'][:58]}…": l for l in rules.load("intake.json")}
        pick = st.selectbox("Or try an example listing (with its photo)", ["Write my own"] + list(examples))
        example = examples.get(pick)
        if photo:
            image, mime, ext = photo.getvalue(), photo.type, photo.name.rsplit(".", 1)[-1].lower()
        elif example and (c.STATIC / example["photo"]).exists():
            image, mime, ext = (c.STATIC / example["photo"]).read_bytes(), "image/jpeg", "jpg"
        else:
            image, mime, ext = None, None, None
        if image:
            st.image(image, width=220)
        text = st.text_area("Describe it (optional)", value=example["text"] if example else "", height=90,
                            placeholder="e.g. Black mini fridge, 2 years old, works great, model XYZ-12")
        if st.button("Get my instant offer", type="primary", icon=":material/bolt:", width="stretch"):
            if not image:
                st.warning("Add a photo of the item. Our agent grades its quality from the photo.")
            elif not state.has_api_key():
                st.error("Instant offers are offline right now. Please try again later.")
            else:
                with st.spinner("Looking at your item…"):
                    try:
                        parsed = agents.intake_listing({"seller": name, "text": text.strip()}, image=image, mime=mime)
                        st.session_state.offer = {
                            "parsed": parsed, "accepted": False, "photo": image, "ext": ext,
                            "recall": rules.recall_reason(parsed.get("model"), rules.recall_list()),
                            **rules.price_listing(parsed["category"], parsed["condition"], parsed.get("quality_score")),
                        }
                    except agents.AgentError:
                        st.error("We couldn't read that. Try adding what the item is and its condition.")

    with right:
        offer = st.session_state.get("offer")
        if not offer:
            st.html(f"""<div class="offer" style="text-align:center;padding:40px 24px">
                <div class="tile" style="--tint:var(--mint);margin:0 auto 14px">{c.icon("sell")}</div>
                <h4 style="margin:0 0 6px">Your offer appears here</h4>
                <p style="color:var(--muted);margin:0">We price by item type, condition and campus demand.
                Recalled models can't be sold.</p></div>""")
        else:
            p = offer["parsed"]
            if p["category"] == "other" and p.get("name", "").lower() in ("", "unknown", "unnamed item"):
                st.html(f"""<div class="offer reject"><h4 style="margin-top:0">{c.icon("help")} We couldn't recognize an item</h4>
                    <p style="margin:0">{c.esc(p.get("notes", ""))} Try a clearer photo or add a short description.</p></div>""")
            elif p.get("quality_score", 3) < 3:
                st.error("This item appears broken or unsafe. We need a human inspection before making an offer.")
            elif offer["recall"]:
                st.html(f"""<div class="offer reject">
                    <div style="display:flex;gap:14px;align-items:center">{c.tile(p["category"])}
                    <div><b>{c.esc(p.get("name", "Item"))}</b><div style="color:var(--muted);font-size:.86rem">
                    Model {c.esc(p.get("model", ""))}</div></div></div>
                    <h4 style="margin:16px 0 6px">{c.icon("block")} We can't accept this item</h4>
                    <p style="margin:0 0 8px">This model is under a safety recall: {c.esc(offer["recall"])}.</p>
                    <p style="margin:0;color:var(--muted);font-size:.9rem">For your safety, please stop using it and
                    follow the manufacturer's recall instructions for a repair or refund.</p></div>""")
            else:
                if offer.get("photo"):
                    st.image(offer["photo"], width=200)
                defects = ", ".join(p.get("defects") or []) or "no visible defects"
                st.html(f"""<div class="offer">
                    <div style="font-weight:700;margin-bottom:8px">Quality: {c.CONDITION.get(p["condition"], p["condition"])}
                    {c.quality_chip(p)} · {c.esc(defects)}</div>
                    <div style="display:flex;gap:14px;align-items:center">{c.tile(p["category"])}
                    <div><b>{c.esc(p.get("name", "Item"))}</b><div style="color:var(--muted);font-size:.86rem">
                    {c.CONDITION.get(p["condition"], p["condition"])} condition · {c.LABEL.get(p["category"], "Item")}{c._look(p)}</div></div></div>
                    <div style="margin:18px 0 4px;color:var(--muted);font-size:.85rem">Your instant offer</div>
                    <div class="big">${offer["acquisition_cost"]}</div>
                    <div style="color:var(--muted);font-size:.88rem;margin-top:6px">Provisional · paid after inspection at pickup</div>
                    </div>""")
                if offer["accepted"]:
                    st.success("Pickup booked. Find it under **My items**.")
                else:
                    with st.container(border=True):
                        st.markdown("**Schedule pickup**")
                        when = st.date_input("Pickup date", value=date(2027, 5, 7), format="MM/DD/YYYY")
                        window = st.segmented_control("Time window", WINDOWS, default=WINDOWS[0], key="pickup_window")
                        where = st.text_input("Pickup address", placeholder="e.g. Wolf Village, Bldg C, Room 214")
                        if st.button("Accept offer & book pickup", type="primary", width="stretch"):
                            if not where.strip():
                                st.error("Add where we should pick it up.")
                            else:
                                listed = db.add_product(
                                    {"id": c.ID_PREFIX.get(p["category"], "ITEM") + "-00", "name": p.get("name", "Item"),
                                     "category": p["category"], "condition": p["condition"],
                                     "quality_score": p.get("quality_score"), "defects": p.get("defects") or [],
                                     "model": p.get("model") or "", "color": p.get("color"), "style": p.get("style"),
                                     **rules.price_listing(p["category"], p["condition"], p.get("quality_score"))},
                                    photo_bytes=offer.get("photo"), ext=offer.get("ext") or "jpg")
                                offer["accepted"] = True
                                mine.append({"id": listed["id"], "photo": listed.get("photo"),
                                             "name": p.get("name", "Item"), "category": p["category"],
                                             "offer": offer["acquisition_cost"], "date": when,
                                             "window": window or WINDOWS[0], "where": where})
                                st.toast(f"Pickup booked · listed in the store as {listed['id']}", icon=":material/task_alt:")
                                st.rerun()
            with st.expander("What we understood from your listing"):
                st.json({k: p.get(k) for k in ("name", "category", "condition", "model", "color", "style", "notes")})

with tab_mine:
    if not mine:
        st.info("Items you sell will show up here with their pickup details.")
    for item in mine:
        with st.container(border=True):
            row, status = st.columns([5, 1.2], vertical_alignment="center")
            row.html(f"""<div class="line" style="border:none;padding:4px 0">{c.tile(item["category"], 72, item)}
                <div><div class="name">{c.esc(item["name"])}</div>
                <div class="meta">Pickup {item['date']:%a, %b %d} · {item['window']} · {c.esc(item['where'])}</div></div>
                <div class="price">${item['offer']}</div></div>""")
            status.html(c.pill("Pickup booked", ico="event_available"))
