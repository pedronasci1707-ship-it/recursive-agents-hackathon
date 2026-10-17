"""Session state, demo accounts and how the UI runs the agents."""

import hashlib
import json
import threading
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


def account(email):
    """Demo account or one created in this browser session (public demo: nothing is stored server-side)."""
    return USERS.get(email) or st.session_state.get("accounts", {}).get(email)


def sign_in(email):
    st.session_state.user = {"email": email, **account(email)}


def register(name, email, role):
    """Create a session-only account. A new incoming student also gets their own kit request."""
    acct = {"name": name, "role": role}
    if role == "student":
        # Python's hash() changes after every process restart. A stable digest keeps
        # session data internally consistent and makes collisions with demo IDs negligible.
        rid = "REQ-U" + hashlib.sha256(email.encode("utf-8")).hexdigest()[:10].upper()
        acct["request_id"] = rid
        st.session_state.setdefault("my_requests", {})[rid] = {
            "id": rid, "buyer": name, "profile": "Incoming student", "budget": 200,
            "needs": ["mini_fridge", "desk_lamp", "storage_bins"],
        }
    st.session_state.setdefault("accounts", {})[email] = acct


def sign_out():
    st.session_state.pop("user", None)


def result():
    return st.session_state.get("result")


def requests():
    return rules.load("requests.json") + list(st.session_state.get("my_requests", {}).values())


def has_api_key():
    try:
        from core.crusoe_client import api_key
        api_key()
        return True
    except RuntimeError:
        return False


@st.cache_resource
def _live_gates():
    return {"lock": threading.Lock(), "channels": {}}


def claim_live_run(channel="agents", cooldown_s=LIVE_COOLDOWN_S, max_runs=LIVE_MAX_RUNS):
    """Atomically rate-limit a live API action across every visitor and mark it active."""
    gates, now = _live_gates(), time.time()
    with gates["lock"]:
        gate = gates["channels"].setdefault(channel, {"last": 0.0, "runs": 0, "active": False})
        if gate["active"]:
            return "Another live run is still working. Try again when it finishes."
        if gate["runs"] >= max_runs:
            return "The live demo reached its run limit. Showing the safe local fallback instead."
        remaining = cooldown_s - (now - gate["last"])
        if remaining > 0:
            return f"Another live run just happened. Try again in {max(1, int(remaining + 0.999))}s."
        gate.update(last=now, runs=gate["runs"] + 1, active=True)
    return None


def finish_live_run(channel="agents"):
    """Release a live API action even when its caller failed."""
    gates = _live_gates()
    with gates["lock"]:
        if channel in gates["channels"]:
            gates["channels"][channel]["active"] = False


def run_agents(on_event, live, chaos=True, max_attempts=3, speed=2.0, custom_request=None, scenario=None,
               requests_override=None, listings_override=None):
    """Run the real agents (live) or replay the recorded sample run with its original pacing.

    `custom_request` replaces the demo request with the same id (a student's own kit request).
    `scenario` picks one of SCENARIOS (admin views); defaults to the one chosen in the sidebar.
    """
    scenario_key = scenario or st.session_state.get("scenario", "standard")
    scenario_key = scenario_key if scenario_key in SCENARIOS else "standard"
    _, sample_path, transform = SCENARIOS[scenario_key]
    claimed = False
    if live and (blocked := claim_live_run()):
        st.toast(blocked)
        live = False
    elif live:
        claimed = True
    if live:
        from campusloop.engine import run
        reqs = list(requests_override) if requests_override is not None else requests()
        reqs = transform(reqs) if transform else reqs
        if custom_request:
            reqs = [custom_request if r["id"] == custom_request["id"] else r for r in reqs]
            if all(r["id"] != custom_request["id"] for r in reqs):  # a newly created student account
                reqs.append(custom_request)
        try:
            res = run(on_event=on_event, simulate_outside_buyer=chaos, max_attempts=max_attempts,
                      requests=reqs, listings=listings_override)
            st.session_state.source = "live run on Crusoe"
        finally:
            if claimed:
                finish_live_run()
    elif custom_request or requests_override is not None:
        # Recorded runs contain only the three demo students. A deterministic local run
        # keeps custom accounts and changed preferences functional without spending API credits.
        from campusloop.engine import run
        reqs = list(requests_override) if requests_override is not None else [custom_request]
        res = run(on_event=on_event, simulate_outside_buyer=chaos, max_attempts=max_attempts,
                  requests=reqs, listings=[], offline=True)
        st.session_state.source = "local deterministic fallback"
    else:
        res = json.loads(sample_path.read_text(encoding="utf-8"))
        last = 0.0
        for event in res["events"]:
            time.sleep(min(max(event["ts"] - last, 0.15), 3.0) / max(float(speed), 0.1))
            last = event["ts"]
            if on_event:
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
