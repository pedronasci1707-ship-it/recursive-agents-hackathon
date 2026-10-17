"""Session state, demo accounts and how the UI runs the agents."""

import json
import time
from pathlib import Path

import streamlit as st

from campusloop import rules

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RUN = ROOT / "demo" / "sample_run.json"


def _impossible(reqs):
    """Priya's budget cannot cover what she needs: the agents must stop and escalate, not loop."""
    return [{**r, "budget": 40, "profile": r["profile"] + " (budget cut to $40)"} if r["id"] == "REQ-3" else r
            for r in reqs]


# Demo scenarios for the admin views: label, recorded sample, how the buyer requests change.
SCENARIOS = {
    "standard": ("Conflict + recall: agents recover", SAMPLE_RUN, None),
    "escalation": ("Impossible request: agents know when to stop", ROOT / "demo" / "sample_escalation.json", _impossible),
}

# Demo accounts: no passwords, nothing stored. The deployed site is a public demo.
USERS = {
    "ana@ncsu.edu": {"name": "Ana", "role": "student", "request_id": "REQ-1"},
    "marcus@ncsu.edu": {"name": "Marcus", "role": "student", "request_id": "REQ-2"},
    "priya@ncsu.edu": {"name": "Priya", "role": "student", "request_id": "REQ-3"},
    "jake@ncsu.edu": {"name": "Jake", "role": "seller"},
    "admin@campusloop.ai": {"name": "Admin", "role": "admin"},
}

# Public deployment guard: live runs spend Crusoe credits.
LIVE_COOLDOWN_S = 20
LIVE_MAX_RUNS = 300


def user():
    return st.session_state.get("user")


def sign_in(email):
    st.session_state.user = {"email": email, **USERS[email]}


def sign_out():
    st.session_state.pop("user", None)


def result():
    return st.session_state.get("result")


def requests():
    return rules.load("requests.json")


def has_api_key():
    try:
        from core.crusoe_client import api_key
        api_key()
        return True
    except RuntimeError:
        return False


@st.cache_resource
def _live_gate():
    return {"last": 0.0, "runs": 0}


def claim_live_run():
    """Rate-limit live runs across all visitors of the public site. Returns an error message or None."""
    gate, now = _live_gate(), time.time()
    if gate["runs"] >= LIVE_MAX_RUNS:
        return "The live demo reached its run limit. Showing the recorded run instead."
    if now - gate["last"] < LIVE_COOLDOWN_S:
        return f"Another live run just happened. Try again in {LIVE_COOLDOWN_S - int(now - gate['last'])}s."
    gate["last"], gate["runs"] = now, gate["runs"] + 1
    return None


def run_agents(on_event, live, chaos=True, max_attempts=3, speed=2.0, custom_request=None, scenario=None):
    """Run the real agents (live) or replay the recorded sample run with its original pacing.

    `custom_request` replaces the demo request with the same id (a student's own kit request).
    `scenario` picks one of SCENARIOS (admin views); defaults to the one chosen in the sidebar.
    """
    _, sample_path, transform = SCENARIOS[scenario or st.session_state.get("scenario", "standard")]
    if live and (blocked := claim_live_run()):
        st.toast(blocked)
        live = False
    if live:
        from campusloop.engine import run
        reqs = transform(requests()) if transform else requests()
        if custom_request:
            reqs = [custom_request if r["id"] == custom_request["id"] else r for r in reqs]
        res = run(on_event=on_event, simulate_outside_buyer=chaos, max_attempts=max_attempts, requests=reqs)
        st.session_state.source = "live run on Crusoe"
    else:
        res = json.loads(sample_path.read_text(encoding="utf-8"))
        last = 0.0
        for event in res["events"]:
            time.sleep(min(max(event["ts"] - last, 0.15), 3.0) / speed)
            last = event["ts"]
            on_event(event)
        st.session_state.source = "recorded run"
    st.session_state.result = res
    return res


def run_mode_controls(key):
    """Sidebar controls shared by pages that run the agents. Returns (live, chaos, max_attempts, speed)."""
    st.session_state.scenario = st.sidebar.selectbox(
        "Scenario", list(SCENARIOS), key=f"{key}_scenario", format_func=lambda k: SCENARIOS[k][0],
        index=list(SCENARIOS).index(st.session_state.get("scenario", "standard")))
    can_live = has_api_key()
    live = st.sidebar.toggle("Run real agents on Crusoe", value=can_live, key=f"{key}_live", disabled=not can_live,
                             help="Off: replay a recorded run (no API calls)." if can_live
                             else "No Crusoe API key configured: replaying a recorded run.")
    chaos = st.sidebar.toggle("Simulate outside buyer", value=True, key=f"{key}_chaos", disabled=not live,
                              help="A walk-in buyer grabs an item while the Kit Agents are planning.")
    max_attempts = st.sidebar.slider("Max attempts per kit", 1, 5, 3, key=f"{key}_max", disabled=not live)
    speed = st.sidebar.slider("Replay speed", 1, 10, 2, key=f"{key}_speed", disabled=live)
    return live, chaos, max_attempts, speed
