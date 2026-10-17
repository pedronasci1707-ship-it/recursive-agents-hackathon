"""CampusLoop AI: storefront for students and sellers, plus an admin view of the agents.

Run from the repo root:  streamlit run app.py
Customers only see the store. The agents' reasoning (agent control room) is admin-only.
"""

import streamlit as st

from ui import components, state

st.set_page_config(page_title="CampusLoop", page_icon="assets/icon.svg", layout="wide")
st.logo("assets/logo.svg", size="large", icon_image="assets/icon.svg")

PAGES = {
    "login": st.Page("ui/pages/login.py", title="Sign in", url_path="login"),
    "demo": st.Page("ui/pages/demo.py", title="Demo accounts", icon=":material/badge:", url_path="demo"),
    "kit": st.Page("ui/pages/student.py", title="My kit", url_path="my-kit"),
    "shop": st.Page("ui/pages/shop.py", title="Shop", url_path="shop"),
    "sell": st.Page("ui/pages/seller.py", title="Sell", url_path="sell"),
    "control": st.Page("ui/pages/control.py", title="Agent control room", icon=":material/hub:",
                       url_path="control-room"),
}
# The first page in each list is where that role lands after signing in.
BY_ROLE = {
    "student": ["kit", "shop", "sell"],
    "seller": ["sell", "shop"],
    "admin": ["control"],
}

user = state.user()
customer = not user or user["role"] != "admin"
components.inject_css(customer=customer)

if not user:
    # /demo (demo accounts for the team) is reachable by URL only; the public page offers sign-in and sign-up.
    nav = st.navigation([PAGES["login"], PAGES["demo"]], position="hidden")
elif customer:
    nav = st.navigation([PAGES[k] for k in BY_ROLE[user["role"]]], position="top")
    _, account = st.columns([5, 1])
    with account.popover(user["name"], icon=":material/account_circle:", width="stretch"):
        st.caption(user["email"])
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            state.sign_out()
            st.rerun()
else:
    nav = st.navigation([PAGES[k] for k in BY_ROLE["admin"]])
    with st.sidebar:
        st.caption(f"Signed in as **{user['name']}**")
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            state.sign_out()
            st.rerun()
        st.divider()
nav.run()
