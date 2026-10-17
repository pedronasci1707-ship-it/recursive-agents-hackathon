"""Controller tests with the LLM agents replaced by fakes (no API calls, no credits)."""

import json
from pathlib import Path

import pytest

from campusloop import agents, engine
from ui import flowboard

ROOT = Path(__file__).resolve().parents[1]


def fake_intake(listing, image=None, mime="image/jpeg"):
    if "ChillCube" in listing["text"]:
        return {"name": "ChillCube fridge", "category": "mini_fridge", "condition": "A", "model": "CC-17"}
    return {"name": "Desk lamp", "category": "desk_lamp", "condition": "A", "model": "X-1"}


def greedy_planner(request, available, feedback=None, shared_notes=None):
    """Always grabs the priciest available item per need: guarantees collisions in round 1."""
    banned = {n.split()[0] for n in shared_notes or []}
    ids = []
    for need in request["needs"]:
        options = [i for i in available if i["category"] == need and i["id"] not in banned]
        ids.append(max(options, key=lambda i: i["resale_price"])["id"])
    return {"item_ids": ids, "rationale": "greedy"}


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr(agents, "intake_listing", fake_intake)
    monkeypatch.setattr(agents, "plan_kit", greedy_planner)
    monkeypatch.setattr(agents, "write_report", lambda summary: "- narrative")


def test_run_recovers_from_conflicts_and_finishes(offline):
    events = []
    result = engine.run(on_event=events.append, simulate_outside_buyer=True, max_attempts=3)

    assert result["status"] == "done"
    assert all(k["status"] == "verified" for k in result["kits"])
    kinds = {e["kind"] for e in result["events"]}
    assert {"conflict", "replan", "verify_pass", "done"} <= kinds
    assert events == result["events"]                     # live callback saw every event
    assert any(k["attempts"] > 1 for k in result["kits"])  # someone had to recover

    reserved = [i["id"] for k in result["kits"] for i in k["items"]]
    assert len(reserved) == len(set(reserved))             # no double-booking
    assert not any(i["model"] == "CC-17" for k in result["kits"] for i in k["items"])
    assert any(not e["accepted"] for e in result["intake"])  # recalled listing blocked


def test_escalates_instead_of_looping_forever(offline, monkeypatch):
    monkeypatch.setattr(agents, "plan_kit", lambda *a, **k: {"item_ids": ["FRIDGE-01"], "rationale": "stubborn"})
    result = engine.run(simulate_outside_buyer=False, max_attempts=2)
    assert result["status"] == "done_with_escalations"
    assert all(k["attempts"] <= 2 for k in result["kits"])
    assert any(e["kind"] == "escalate" for e in result["events"])


def test_model_failure_uses_fallback_planner(offline, monkeypatch):
    def broken(*a, **k):
        raise agents.AgentError("boom")
    monkeypatch.setattr(agents, "plan_kit", broken)
    result = engine.run(simulate_outside_buyer=False, max_attempts=3)
    assert any("fallback planner" in e["message"] for e in result["events"])
    assert result["status"] in ("done", "done_with_escalations")


def test_sample_run_matches_contract():
    sample = json.loads((ROOT / "demo" / "sample_run.json").read_text(encoding="utf-8"))
    for key in ("run_id", "status", "started_at", "finished_at", "duration_s", "config",
                "intake", "kits", "events", "inventory", "report", "usage"):
        assert key in sample
    for key in ("request_id", "buyer", "profile", "budget", "needs", "status", "attempts", "items",
                "price", "cost", "margin", "margin_pct", "checks", "history", "rationale"):
        assert key in sample["kits"][0]
    for key in ("ts", "agent", "kind", "message", "data"):
        assert key in sample["events"][0]


def test_run_feeds_listing_photos_to_vision_agent(offline, monkeypatch):
    seen = []

    def capture(listing, image=None, mime="image/jpeg"):
        seen.append((listing["id"], image, mime))
        return fake_intake(listing, image, mime)

    monkeypatch.setattr(agents, "intake_listing", capture)
    result = engine.run(requests=[], simulate_outside_buyer=False)
    assert len(seen) == 3
    assert all(image and image.startswith(b"\xff\xd8") and mime == "image/jpeg" for _, image, mime in seen)
    assert {"photo_received", "inventory_add"} <= {e["kind"] for e in result["events"]}
    assert all(entry["photo"].startswith("listings/") for entry in result["intake"])
    assert all(entry["item"]["photo"].startswith("listings/") for entry in result["intake"] if entry["accepted"])
    board = flowboard.storyboard(result)
    assert any(frame["kind"] == "photo_received" and frame["node"] == "listing_reader"
               for frame in board["frames"])
    assert any(frame["kind"] == "inventory_add" and frame["node"] == "inventory"
               for frame in board["frames"])
    assert board["history"]["LIST-1"]["photo"] == "listings/LIST-1.jpg"  # recalled, but still auditable


def test_broken_photo_result_never_enters_inventory(offline, monkeypatch):
    monkeypatch.setattr(agents, "intake_listing", lambda *a, **k: {
        "name": "Broken lamp", "category": "desk_lamp", "condition": "C", "quality_score": 1, "model": "X"})
    result = engine.run(requests=[], simulate_outside_buyer=False)
    assert all(not entry["accepted"] for entry in result["intake"])
    assert all(entry["item"] is None for entry in result["intake"])


def test_offline_run_is_personalized_and_never_calls_models(monkeypatch):
    monkeypatch.setattr(agents, "plan_kit", lambda *a, **k: pytest.fail("model planner called"))
    monkeypatch.setattr(agents, "write_report", lambda *a, **k: pytest.fail("reporter called"))
    request = {"id": "REQ-CUSTOM", "buyer": "Sam", "profile": "Incoming student", "budget": 200,
               "needs": ["mini_fridge", "desk_lamp"], "min_condition": "B"}
    result = engine.run(requests=[request], listings=[], offline=True, simulate_outside_buyer=False)
    assert result["config"]["offline"] is True
    assert result["kits"][0]["request_id"] == "REQ-CUSTOM"
    assert result["kits"][0]["status"] == "verified"
    assert result["usage"] == {}


def test_final_audit_rejects_an_item_that_is_not_actually_reserved():
    item = {"id": "F", "name": "Fridge", "category": "mini_fridge", "condition": "A", "model": "OK",
            "acquisition_cost": 10, "refurb_cost": 5, "resale_price": 100,
            "status": "available", "reserved_for": "Ana (REQ-1)"}
    kit = {"request_id": "REQ-1", "buyer": "Ana", "budget": 120, "needs": ["mini_fridge"],
           "min_condition": None, "item_prefs": {}, "status": "verified", "items": [item.copy()]}
    events = []
    assert not engine._final_audit([kit], {"F": item}, {}, lambda *args, **kwargs: events.append(args))
    assert "not reserved" in events[-1][2]


def test_run_rejects_invalid_limits_and_duplicate_requests():
    with pytest.raises(ValueError, match="max_attempts"):
        engine.run(max_attempts=0, offline=True)
    request = {"id": "DUP", "buyer": "A", "profile": "", "budget": 100, "needs": []}
    with pytest.raises(ValueError, match="unique"):
        engine.run(requests=[request, {**request, "buyer": "B"}], listings=[], offline=True)
