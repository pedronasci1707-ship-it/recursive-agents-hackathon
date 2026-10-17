"""CampusLoop AI: storefront for students and sellers, plus an admin view of the agents.

Run from the repo root:  streamlit run app.py
Customers only see the store. The agents' reasoning (live split screen, operations console) is admin-only.
"""

import streamlit as st

from ui import components, state

st.set_page_config(page_title="CampusLoop", page_icon="assets/icon.svg", layout="wide")
st.logo("assets/logo.svg", size="large", icon_image="assets/icon.svg")

PAGES = {
    "login": st.Page("ui/pages/login.py", title="Sign in", url_path="login"),
    "kit": st.Page("ui/pages/student.py", title="My kit", url_path="my-kit"),
    "shop": st.Page("ui/pages/shop.py", title="Shop", url_path="shop"),
    "sell": st.Page("ui/pages/seller.py", title="Sell", url_path="sell"),
    "live": st.Page("ui/pages/live.py", title="Live: agents at work", icon=":material/bolt:", url_path="live"),
    "flow": st.Page("ui/pages/flow.py", title="How it works", icon=":material/account_tree:", url_path="how-it-works"),
    "ops": st.Page("ui/pages/operations.py", title="Operations console", icon=":material/monitoring:",
                   url_path="operations"),
    "preview": st.Page("ui/pages/student.py", title="Storefront preview", icon=":material/storefront:",
                       url_path="preview"),
}
# The first page in each list is where that role lands after signing in.
BY_ROLE = {
    "student": ["kit", "shop", "sell"],
    "seller": ["sell", "shop"],
    "admin": ["live", "flow", "ops", "preview"],
}

user = state.user()
customer = not user or user["role"] != "admin"
components.inject_css(customer=customer)

if not user:
    nav = st.navigation([PAGES["login"]], position="hidden")
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
