import streamlit as st

from campusloop import agents, rules
from ui import components as c
from ui import state

u = state.user()
name = u["name"] if u["role"] == "seller" else "there"
c.hero(f"Moving out, {name}? Sell before you leave", "Describe an item the way you'd post it. Our Intake Agent "
       "reads it, checks it for safety recalls and makes you an instant offer.")

examples = {f"{l['seller']}: {l['text'][:60]}…": l["text"] for l in rules.load("intake.json")}
left, right = st.columns([1.2, 1], gap="large")

with left:
    pick = st.selectbox("Start from an example (or write your own)", ["Write my own"] + list(examples))
    with st.form("listing", border=True):
        text = st.text_area("Your listing", value=examples.get(pick, ""), height=130,
                            placeholder="e.g. Black mini fridge, 2 years old, works great, model XYZ-12")
        submitted = st.form_submit_button("Get instant offer", type="primary", width="stretch")
    if submitted and text.strip():
        if not state.has_api_key():
            st.error("Live offers need a Crusoe API key on the server.")
            st.stop()
        with st.spinner("Our Intake Agent is reading your listing…"):
            try:
                parsed = agents.intake_listing({"seller": name, "text": text.strip()})
            except agents.AgentError as e:
                st.error(f"Our agent couldn't read that listing ({e}). Try adding the product type and condition.")
                st.stop()
        recall = rules.recall_reason(parsed.get("model"), rules.recall_list())
        st.session_state.offer = {"parsed": parsed, "recall": recall, "accepted": False,
                                  **rules.price_listing(parsed["category"], parsed["condition"])}

with right:
    offer = st.session_state.get("offer")
    if not offer:
        st.info("Your offer will appear here.")
    else:
        p = offer["parsed"]
        icon = c.ICONS.get(p["category"], "🏷️")
        if offer["recall"]:
            st.html(f'<div class="cl-card" style="border-color:#e5484d">'
                    f'<h3 style="margin-top:0">⛔ We can\'t accept this item</h3>'
                    f'<p><b>{icon} {c.esc(p.get("name", "Item"))}</b> · model {c.esc(p.get("model", ""))}</p>'
                    f'<p>This model is under a safety recall: {c.esc(offer["recall"])}.</p>'
                    f'<p style="opacity:.75">Please don\'t sell or keep using it. Follow the manufacturer\'s recall '
                    f'instructions for a repair or refund.</p></div>')
        else:
            st.html(f'<div class="cl-card"><div class="cl-product"><div class="cl-thumb">{icon}</div>'
                    f'<div><div class="cl-pname">{c.esc(p.get("name", "Item"))}</div>'
                    f'<div class="cl-pmeta">{c.CONDITION.get(p["condition"], p["condition"])} · '
                    f'{c.esc(p["category"].replace("_", " "))}</div></div>'
                    f'<div class="cl-price">${offer["acquisition_cost"]}</div></div>'
                    f'<p style="margin:10px 0 0">Our offer: <b>${offer["acquisition_cost"]}</b>, paid at pickup. '
                    f'Free pickup before you leave campus.</p></div>')
            if offer["accepted"]:
                st.success("Pickup scheduled! We'll text you a time window before your move-out day.")
            elif st.button("Accept offer & schedule pickup", type="primary", width="stretch"):
                offer["accepted"] = True
                st.rerun()
        with st.expander("What our agent understood"):
            st.json({k: p.get(k) for k in ("name", "category", "condition", "model", "notes")})
