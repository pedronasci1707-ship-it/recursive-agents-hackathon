import streamlit as st

from ui import components as c
from ui import state

ROLE_LABEL = {
    "student": ("school", "Incoming student"),
    "seller": ("sell", "Moving out"),
    "admin": ("admin_panel_settings", "CampusLoop admin"),
}

st.write("")
left, right = st.columns([1.35, 1], gap="large")

with left:
    st.html(f"""
    <div class="hero" style="min-height: 430px; display:flex; flex-direction:column; justify-content:flex-end">
      <div class="pill" style="width:fit-content;margin-bottom:18px">
        {c.icon("verified_user")}Every kit verified before it ships</div>
      <h1>Move-in <em>ready.</em><br>Move-out <em>easy.</em></h1>
      <p>Pre-loved mini-fridges, desks, lamps and kitchen basics from students who just moved out,
         inspected, recall-checked and delivered to your room on move-in day.</p>
      {c.scribble("made by students, for students ♥")}
      {c.icon("autorenew")}
    </div>""")

with right:
    st.html('<div class="eyebrow">Welcome</div><div class="page-title">Sign in to CampusLoop</div>'
            '<p class="page-sub">Use your university email.</p>')
    with st.form("login", border=False):
        email = st.text_input("University email", placeholder="you@ncsu.edu", label_visibility="collapsed")
        if st.form_submit_button("Continue", type="primary", width="stretch"):
            if email.strip().lower() in state.USERS:
                state.sign_in(email.strip().lower())
                st.rerun()
            st.error("We couldn't find that account. Try one of the demo accounts below.")
    st.caption("DEMO ACCOUNTS · no password needed")
    for email, u in state.USERS.items():
        ico, role = ROLE_LABEL[u["role"]]
        if st.button(f"**{u['name']}** · {role}", key=f"login_{email}", icon=f":material/{ico}:", width="stretch"):
            state.sign_in(email)
            st.rerun()

st.write("")
cols = st.columns(4)
for col, (ico, title, text) in zip(cols, [
    ("inventory_2", "Kits for your room", "Fridge, lamp, chair, kitchen basics: picked for your room and budget."),
    ("verified_user", "Checked twice", "Availability, safety recalls and price are verified before we confirm."),
    ("savings", "Up to 60% off new", "Quality second-hand at student prices, delivered on move-in day."),
    ("sell", "Sell before you leave", "Snap a photo, get an instant offer, we pick it up."),
]):
    col.html(f'<div class="feature">{c.icon(ico)}<h4>{title}</h4><p>{text}</p></div>')
