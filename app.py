"""CampusLoop AI: storefront for students + live agents view + operations console.

Run from the repo root:  streamlit run app.py
Talks to the engine only through campusloop.engine.run() (see docs/CONTRACT.md).
"""

import streamlit as st

from ui import components, state

st.set_page_config(page_title="CampusLoop AI", page_icon="♻️", layout="wide")
components.inject_css()

PAGES = {
    "login": st.Page("ui/pages/login.py", title="Sign in", icon="🔑", url_path="login"),
    "student": st.Page("ui/pages/student.py", title="My move-in kit", icon="📦", url_path="my-kit"),
    "seller": st.Page("ui/pages/seller.py", title="Sell before you leave", icon="💸", url_path="sell"),
    "live": st.Page("ui/pages/live.py", title="Live: agents at work", icon="⚡", url_path="live"),
    "ops": st.Page("ui/pages/operations.py", title="Operations console", icon="🛠️", url_path="operations"),
}
# The first page in each list is where that role lands after signing in.
BY_ROLE = {
    "student": ["student", "live", "seller"],
    "seller": ["seller", "student", "live"],
    "ops": ["live", "ops", "student", "seller"],
}

user = state.user()
if not user:
    nav = st.navigation([PAGES["login"]], position="hidden")
else:
    nav = st.navigation([PAGES[k] for k in BY_ROLE[user["role"]]])
    with st.sidebar:
        st.markdown(f"**♻️ CampusLoop** · signed in as **{user['name']}**")
        if st.button("Sign out", width="stretch"):
            state.sign_out()
            st.rerun()
        st.divider()
nav.run()
