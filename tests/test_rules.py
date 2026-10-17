from campusloop import rules

RECALLS = {"CC-17": "fire hazard"}


def item(id, category, price=50, status="available", model="OK-1", acq=10, refurb=5):
    return {"id": id, "name": id, "category": category, "condition": "A", "model": model,
            "acquisition_cost": acq, "refurb_cost": refurb, "resale_price": price,
            "status": status, "reserved_for": None if status == "available" else "someone"}


REQ = {"id": "R", "buyer": "Ana", "budget": 200, "needs": ["mini_fridge", "desk_lamp"]}


def test_recall_matching_ignores_formatting():
    assert rules.recall_reason("cc 17", RECALLS)
    assert rules.recall_reason("ChillCube CC-17", RECALLS)
    assert rules.recall_reason("GLR31", RECALLS) is None
    assert rules.recall_reason("", RECALLS) is None


def test_valid_kit_passes():
    inv = {"F": item("F", "mini_fridge", 90), "L": item("L", "desk_lamp", 20)}
    checks, issues, soft = rules.verify_kit(REQ, ["F", "L"], inv, RECALLS)
    assert issues == [] and not soft
    assert all(c["passed"] for c in checks)


def test_reserved_item_is_a_conflict():
    inv = {"F": item("F", "mini_fridge", status="reserved"), "L": item("L", "desk_lamp")}
    _, issues, soft = rules.verify_kit(REQ, ["F", "L"], inv, RECALLS)
    assert any("already reserved" in i for i in issues) and not soft


def test_recalled_and_missing_and_unknown():
    inv = {"F": item("F", "mini_fridge", model="CC-17")}
    _, issues, _ = rules.verify_kit(REQ, ["F", "NOPE"], inv, RECALLS)
    text = " ".join(issues)
    assert "safety recall" in text and "desk_lamp" in text and "NOPE" in text


def test_small_budget_overrun_needs_approval_large_one_fails():
    inv = {"F": item("F", "mini_fridge", 190, acq=20), "L": item("L", "desk_lamp", 20, acq=2, refurb=1)}
    _, issues, soft = rules.verify_kit(REQ, ["F", "L"], inv, RECALLS)   # $210 vs $200
    assert issues and soft
    inv["F"]["resale_price"] = 300
    _, issues, soft = rules.verify_kit(REQ, ["F", "L"], inv, RECALLS)
    assert issues and not soft


def test_low_margin_fails():
    inv = {"F": item("F", "mini_fridge", 50, acq=40), "L": item("L", "desk_lamp", 10, acq=8)}
    _, issues, _ = rules.verify_kit(REQ, ["F", "L"], inv, RECALLS)
    assert any("below" in i for i in issues)


def test_min_quality_is_a_hard_rule_when_set():
    inv = {"F": item("F", "mini_fridge", 90), "L": item("L", "desk_lamp", 20)}
    inv["L"]["condition"] = "C"
    _, issues, soft = rules.verify_kit({**REQ, "min_condition": "B"}, ["F", "L"], inv, RECALLS)
    assert any("below the Good quality" in i for i in issues) and not soft
    checks, issues, _ = rules.verify_kit(REQ, ["F", "L"], inv, RECALLS)   # no minimum set: no quality check
    assert not issues and "min_quality" not in {c["name"] for c in checks}


def test_per_item_quality_overrides_the_kit_minimum():
    inv = {"F": item("F", "mini_fridge", 90), "L": item("L", "desk_lamp", 20)}
    inv["F"]["condition"], inv["L"]["condition"] = "B", "C"
    req = {**REQ, "item_prefs": {"mini_fridge": {"min_condition": "A"}}}   # only the fridge must be Excellent
    _, issues, _ = rules.verify_kit(req, ["F", "L"], inv, RECALLS)
    assert len(issues) == 1 and "F (F) is Good" in issues[0]
    inv["F"]["condition"] = "A"
    _, issues, _ = rules.verify_kit(req, ["F", "L"], inv, RECALLS)
    assert not issues                                                       # the Fair lamp is fine


def test_fallback_plan_skips_recalls_and_respects_item_prefs():
    from campusloop.engine import _fallback_plan
    snapshot = [i for i in rules.load("catalog.json") if i["status"] == "available"]
    req = {**REQ, "needs": ["mini_fridge", "desk_chair"],
           "item_prefs": {"mini_fridge": {"min_condition": "A"}, "desk_chair": {"color": "blue"}}}
    ids = _fallback_plan(req, snapshot)["item_ids"]
    assert ids == ["FRIDGE-01", "CHAIR-02"]   # FRIDGE-03 is also A but recalled; CHAIR-02 is the blue one


def test_fallback_plan_chooses_a_complete_combination_that_fits_budget():
    from campusloop.engine import _fallback_plan

    def choice(item_id, category, price):
        return {"id": item_id, "name": item_id, "category": category, "condition": "A", "model": "OK",
                "color": "black", "style": "modern", "acquisition_cost": 5, "refurb_cost": 2,
                "resale_price": price, "status": "available", "reserved_for": None}

    snapshot = [choice("F-HIGH", "mini_fridge", 80), choice("F-LOW", "mini_fridge", 40),
                choice("L-HIGH", "desk_lamp", 50), choice("L-LOW", "desk_lamp", 30)]
    request = {**REQ, "budget": 100}
    ids = _fallback_plan(request, snapshot)["item_ids"]
    inventory = {item["id"]: item for item in snapshot}
    _, issues, _ = rules.verify_kit(request, ids, inventory, RECALLS)
    assert issues == []
    assert ids == ["F-LOW", "L-LOW"]


def test_price_listing_scales_with_condition():
    a, b = rules.price_listing("mini_fridge", "A"), rules.price_listing("mini_fridge", "B")
    assert a["resale_price"] > b["resale_price"] > 0
    assert rules.price_listing("spaceship", "A")["resale_price"] == rules.BASE_RESALE["other"]
