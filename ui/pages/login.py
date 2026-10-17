"""Sign in or create an account. Demo accounts live on a separate page (/demo) for the team."""

import base64
from pathlib import Path

import streamlit as st

from ui import components as c
from ui import state

HANDOFF = base64.b64encode((Path(__file__).resolve().parents[2] / "assets" / "handoff.svg").read_bytes()).decode()

st.write("")
left, right = st.columns([1.3, 1], gap="large")

with left:
    # As an <img>: st.html's sanitizer drops inline <svg> (its CSS animation still runs inside the image).
    st.html(f"""
    <h1 class="landing-title"><span>Move-in <em>ready.</em></span><span>Move-out <em>easy.</em></span></h1>
    <div class="handoff">
      <img src="data:image/svg+xml;base64,{HANDOFF}"
           alt="A student who is moving out hands a box of room essentials to a student who is moving in">
    </div>
    {c.scribble("made by students, for students ♥")}""")

with right:
    st.html('<div class="eyebrow">Welcome</div><div class="page-title">Your room, sorted.</div>'
            '<p class="page-sub">Sell what you leave behind. Get what you need when you arrive.</p>')
    with st.container(border=True):
        tab_in, tab_new = st.tabs(["Sign in", "Create account"])
        with tab_in:
            with st.form("login", border=False):
                email = st.text_input("University email", placeholder="you@ncsu.edu")
                if st.form_submit_button("Sign in", type="primary", width="stretch"):
                    email = email.strip().lower()
                    if state.account(email):
                        state.sign_in(email)
                        st.rerun()
                    st.error("We couldn't find that account. New here? Open **Create account**.")
        with tab_new:
            with st.form("signup", border=False):
                name = st.text_input("Your first name", placeholder="e.g. Sam")
                new_email = st.text_input("University email", placeholder="you@ncsu.edu", key="signup_email")
                role = st.radio("I'm…", ["student", "seller"], horizontal=True,
                                format_func=lambda r: "Moving in" if r == "student" else "Moving out")
                if st.form_submit_button("Create my account", type="primary", width="stretch"):
                    new_email = new_email.strip().lower()
                    if not name.strip() or "@" not in new_email:
                        st.error("Add your first name and your university email.")
                    elif state.account(new_email):
                        st.error("That email already has an account. Use **Sign in**.")
                    else:
                        state.register(name.strip(), new_email, role)
                        state.sign_in(new_email)
                        st.rerun()
    st.caption("No password needed in this demo. Accounts last for this browser session.")
    if st.button("Just looking? Try a demo account", icon=":material/play_circle:", width="stretch"):
        st.switch_page("ui/pages/demo.py")

st.write("")
cols = st.columns(2, gap="large")
for col, (icons, title, text) in zip(cols, [
    (["skillet", "dinner_dining", "table_lamp"], "Kits for your room",
     "Pans, plates, a lamp, a fridge: picked for your room and budget."),
    (["sell"], "Sell before you leave", "Snap a photo, get an instant offer, we pick it up."),
]):
    stickers = "".join(c.icon(i) for i in icons)
    col.html(f'<div class="feature"><span class="stickers">{stickers}</span><h4>{title}</h4><p>{text}</p></div>')
