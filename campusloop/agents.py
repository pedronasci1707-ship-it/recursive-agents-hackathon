"""LLM agents running on Crusoe Managed Inference.

Each agent returns plain dicts. If a model call fails or returns unusable output,
the agent raises AgentError and the controller decides what to do.
"""

import json
import os
import re

from core.crusoe_client import chat, text

from . import rules

# Reasoning makes the Kit Agent ~10x slower; off by default so the live demo stays snappy.
PLANNER_THINKING = os.getenv("PLANNER_THINKING", "false").lower() == "true"


class AgentError(Exception):
    pass


def parse_json(raw):
    """First JSON object in a model reply (tolerates ```json fences and prose)."""
    raw = re.sub(r"```(?:json)?", "", raw or "")
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise AgentError(f"no JSON object in reply: {raw[:120]!r}")
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise AgentError(f"invalid JSON: {e}") from e


def _ask(role, system, user, max_tokens, thinking=None, allow_reasoning=True):
    """One model call. thinking=False turns off the reasoning phase (Nemotron) for speed."""
    kwargs = {}
    if thinking is not None:
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": thinking}}
    try:
        resp = chat(role, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=max_tokens, temperature=0.3, **kwargs)
    except Exception as e:
        raise AgentError(f"{type(e).__name__}: {e}") from e
    return text(resp) if allow_reasoning else (resp.choices[0].message.content or "")


INTAKE_SYSTEM = f"""You are the Intake Agent of CampusLoop, a company that buys items from college students moving out and resells them.
Turn a seller's free-text listing into structured data.
Reply with ONLY a JSON object with these keys:
  "name": short product name (brand + product if known),
  "category": one of {rules.CATEGORIES},
  "condition": "A" (like new), "B" (used, works fine, cosmetic wear) or "C" (worn or questionable),
  "model": the model number exactly as written by the seller, or "" if none,
  "notes": one short sentence on anything a buyer should know."""


def intake_listing(listing):
    raw = _ask("fast", INTAKE_SYSTEM, f"Listing from {listing['seller']}:\n{listing['text']}", 1024)
    data = parse_json(raw)
    if data.get("category") not in rules.CATEGORIES:
        data["category"] = "other"
    if data.get("condition") not in rules.CONDITION_FACTOR:
        data["condition"] = "C"
    return data


KIT_SYSTEM = f"""You are a Kit Agent at CampusLoop. You assemble a move-in kit of used items for ONE incoming college student.
Rules:
- Pick exactly one item for each category in the student's needs, using ONLY item IDs from the available list.
- The kit price is the sum of item prices and must not exceed the student's budget.
- CampusLoop spends ${rules.DELIVERY_COST:.0f} delivering each kit; the kit margin must stay at or above {rules.MIN_MARGIN_PCT:.0f}% of the price.
- Prefer better condition (A > B > C) when the budget allows, and respect the student's profile.
- If a Verifier rejected your previous proposal, fix EVERY issue it reported.
Reply with ONLY a JSON object: {{"item_ids": ["ID", ...], "rationale": "one or two sentences"}}"""


def _inventory_table(items):
    rows = [f"{i['id']} | {i['name']} | {i['category']} | condition {i['condition']} | model {i['model']} "
            f"| price ${i['resale_price']} | unit margin ${rules.unit_margin(i)}" for i in items]
    return "\n".join(rows)


def plan_kit(request, available_items, feedback=None, shared_notes=None):
    user = (
        f"Student: {request['buyer']} ({request['profile']})\n"
        f"Budget: ${request['budget']}\n"
        f"Needs: {', '.join(request['needs'])}\n\n"
        f"Available inventory (snapshot):\n{_inventory_table(available_items)}"
    )
    if shared_notes:
        user += "\n\nTeam notes from the Verifier (apply them):\n- " + "\n- ".join(shared_notes)
    if feedback:
        user += "\n\nThe Verifier REJECTED your previous proposal:\n- " + "\n- ".join(feedback)
    data = parse_json(_ask("planner", KIT_SYSTEM, user, 4096, thinking=PLANNER_THINKING))
    ids = data.get("item_ids")
    if not isinstance(ids, list) or not ids:
        raise AgentError("reply has no item_ids")
    return {"item_ids": [str(i).strip() for i in ids], "rationale": str(data.get("rationale", "")).strip()}


REPORT_SYSTEM = """You are the Reporter Agent of CampusLoop. You receive the facts of one run of the agent team.
Write 2 to 4 short Markdown bullets (max 80 words total) explaining what problems the agents caught and how they recovered,
naming the students and item IDs. Do NOT write a verdict, a title or a table, and do NOT invent anything that is not in the facts.
How to read the facts: each entry in "rejected_attempts" is a proposal the Verifier blocked. If the kit's "status" is "verified",
the agents RECOVERED and the kit ships with "final_items". Only a kit whose status is not "verified" was escalated to a human."""


def write_report(summary):
    raw = _ask("worker", REPORT_SYSTEM, json.dumps(summary, indent=1), 1500,
               thinking=False, allow_reasoning=False)
    if not raw.strip():
        raise AgentError("empty report")
    return raw.strip()
