"""Demo accounts for the CampusLoop team (judges, video, admin). Not linked from the public sign-in page."""

import streamlit as st

from ui import components as c
from ui import state

ROLE_LABEL = {
    "student": ("school", "Incoming student"),
    "seller": ("sell", "Moving out"),
    "admin": ("admin_panel_settings", "CampusLoop admin"),
}

c.page_header("Team access", "Demo accounts", "Sign in as any demo user. No password needed.")
current = state.user()
_, mid, _ = st.columns([1, 1.4, 1])
with mid, st.container(border=True):
    for email, u in state.USERS.items():
        ico, role = ROLE_LABEL[u["role"]]
        if st.button(f"**{u['name']}** · {role}", key=f"demo_{email}", icon=f":material/{ico}:", width="stretch",
                     disabled=bool(current and current["email"] == email)):
            state.sign_in(email)
            st.rerun()
if not current:
    with mid:
        st.page_link("ui/pages/login.py", label="Back to sign in", icon=":material/arrow_back:")
