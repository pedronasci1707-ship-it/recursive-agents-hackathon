"""Admin control room: animated org chart where every request moves through the agents until it is finished."""

import json

import streamlit as st

from ui import flowboard, state

st.markdown("## :material/hub: Agent control room")
st.markdown("Done Means Done: every request moves through the agents and only reaches **Finished** after the "
            "Quality Checker passes it, or after the Coordinator hands it to a human.")

boards, labels = {}, {}
for key, (label, sample, _) in state.SCENARIOS.items():
    boards[key] = flowboard.storyboard(json.loads(sample.read_text(encoding="utf-8")))
    labels[key] = f"Recorded: {label}"

res = state.result()
if res and st.session_state.get("source") == "live run on Crusoe":
    boards["live"] = flowboard.storyboard(res)
    labels["live"] = "Last real run on Crusoe"

left, right = st.columns([3, 1.4], vertical_alignment="bottom")
with left:
    scenario = st.segmented_control("Run the real agents with", list(state.SCENARIOS), default="standard",
                                    format_func=lambda k: state.SCENARIOS[k][0])
with right:
    run_live = st.button("Run the real agents on Crusoe", icon=":material/bolt:", width="stretch",
                         disabled=not state.has_api_key(), help="Runs the real agent team now, then animates that run.")

if run_live:
    with st.status("The real agents are working on Crusoe…", expanded=False) as box:
        count = {"n": 0}

        def on_event(e):
            count["n"] += 1
            box.update(label=f"The real agents are working on Crusoe… {count['n']} steps")

        state.run_agents(on_event, live=True, scenario=scenario or "standard")
        box.update(label="Done", state="complete")
    if st.session_state.get("source") == "live run on Crusoe":
        st.session_state.autoplay_live = True
    st.rerun()

autoplay = st.session_state.pop("autoplay_live", False)
start = "live" if autoplay and "live" in boards else "standard"
html = flowboard.render_html(boards, labels, start, autoplay)
if hasattr(st, "iframe"):
    st.iframe(html, height=780)
else:  # older Streamlit
    import streamlit.components.v1 as components
    components.html(html, height=780, scrolling=False)
