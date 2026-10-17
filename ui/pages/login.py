import streamlit as st

from ui import components as c
from ui import state

c.hero("♻️ CampusLoop", "Move-out leftovers, move-in ready. Verified kits for students, built by AI agents.")

left, right = st.columns([1.1, 1], gap="large")

with left:
    st.markdown("### Sign in")
    with st.form("login", border=True):
        email = st.text_input("University email", placeholder="you@ncsu.edu")
        if st.form_submit_button("Continue", type="primary", width="stretch"):
            if email.strip().lower() in state.USERS:
                state.sign_in(email.strip().lower())
                st.rerun()
            st.error("Unknown account. Use one of the demo accounts on the right.")
    st.caption("Demo sign-in: no passwords, nothing is stored.")

with right:
    st.markdown("### Demo accounts")
    for email, u in state.USERS.items():
        role = {"student": "Incoming student · move-in kit", "seller": "Moving out · sell items",
                "ops": "CampusLoop operations · agents console"}[u["role"]]
        if st.button(f"**{u['name']}**  \n{role}", key=f"login_{email}", width="stretch"):
            state.sign_in(email)
            st.rerun()

st.divider()
a, b, d = st.columns(3)
a.markdown("**🧊 Move-in kits**  \nFridge, lamp, chair, kitchen basics: picked for your room and budget.")
b.markdown("**🛡️ Verified by agents**  \nEvery kit is checked for availability, safety recalls and price before it ships.")
d.markdown("**💸 Sell before you leave**  \nGet an instant offer for the things you can't take home.")
