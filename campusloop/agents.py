"""LLM agents running on Crusoe Managed Inference.

Each agent returns plain dicts. If a model call fails or returns unusable output,
the agent raises AgentError and the controller decides what to do.
"""

import base64
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


def _ask(role, system, user, max_tokens, thinking=None, allow_reasoning=True, timeout=60.0, max_tries=6):
    """One model call. thinking=False turns off the reasoning phase (Nemotron) for speed."""
    kwargs = {}
    if thinking is not None:
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": thinking}}
    try:
        resp = chat(role, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=max_tokens, temperature=0.3, timeout=timeout, max_tries=max_tries, **kwargs)
    except Exception as e:
        raise AgentError(f"{type(e).__name__}: {e}") from e
    return text(resp) if allow_reasoning else (resp.choices[0].message.content or "")


INTAKE_SYSTEM = f"""You are the Intake Agent of CampusLoop, a company that buys items from college students moving out and resells them.
Turn a seller's free-text listing into structured data.
Reply with ONLY a JSON object with these keys:
  "name": short product name (brand + product if known),
  "category": one of {rules.CATEGORIES},
  "condition": quality grade, the most important field. "A" = Excellent (like new, perfect, no visible wear),
               "B" = Good (used, works fine, light cosmetic wear), "C" = Fair (worn, scratches or dents, but works).
               Grade from the evidence (photo, age, words like "scratched", "like new"); when unsure, pick the lower grade,
  "model": the model number exactly as written by the seller, or "" if none,
  "color": main color, one of {rules.COLORS},
  "style": the look it fits best, one of {rules.STYLES},
  "notes": one short sentence on anything a buyer should know."""


def intake_listing(listing, image=None, mime="image/jpeg"):
    """Structure a move-out listing. With `image` (bytes), a vision model also reads the photo."""
    text = f"Listing from {listing['seller']}:\n{listing.get('text') or '(no text, see the photo)'}"
    if image:
        uri = f"data:{mime};base64," + base64.b64encode(image).decode()
        content = [{"type": "text", "text": text + "\nUse the photo to identify the item, its condition "
                                                    "and any visible model number."},
                   {"type": "image_url", "image_url": {"url": uri}}]
        raw = _ask("vision", INTAKE_SYSTEM, content, 1024)
    else:
        raw = _ask("fast", INTAKE_SYSTEM, text, 1024)
    data = parse_json(raw)
    if data.get("category") not in rules.CATEGORIES:
        data["category"] = "other"
    if data.get("condition") not in rules.CONDITION_FACTOR:
        data["condition"] = "C"
    if data.get("color") not in rules.COLORS:
        data["color"] = "other"
    if data.get("style") not in rules.STYLES:
        data["style"] = "minimal"
    return data


KIT_SYSTEM = f"""You are a Kit Agent at CampusLoop. You assemble a move-in kit of used items for ONE incoming college student.
Rules:
- Pick exactly one item for each category in the student's needs, using ONLY item IDs from the available list.
- The kit price is the sum of item prices and must not exceed the student's budget.
- CampusLoop spends ${rules.DELIVERY_COST:.0f} delivering each kit; the kit margin must stay at or above {rules.MIN_MARGIN_PCT:.0f}% of the price.
- Quality comes first: condition A = Excellent, B = Good, C = Fair. NEVER pick an item below the student's minimum quality.
  Above that minimum, prefer better condition when the budget allows.
- Then match the room: prefer items in the student's colors and room style. These are preferences, not hard rules:
  a safe, in-budget kit beats a perfect color match. Mention the match in the rationale.
- If a Verifier rejected your previous proposal, fix EVERY issue it reported.
- If no combination can satisfy every rule, return the closest valid combination and say so in the rationale.
Reply with ONLY a JSON object: {{"item_ids": ["ID", ...], "rationale": "one or two sentences"}}"""


def _inventory_table(items):
    rows = [f"{i['id']} | {i['name']} | {i['category']} | condition {i['condition']} | model {i['model']} "
            f"| color {i.get('color', 'unknown')} | style {i.get('style', 'unknown')} "
            f"| price ${i['resale_price']} | unit margin ${rules.unit_margin(i)}" for i in items]
    return "\n".join(rows)


def plan_kit(request, available_items, feedback=None, shared_notes=None):
    user = (
        f"Student: {request['buyer']} ({request['profile']})\n"
        f"Budget: ${request['budget']}\n"
        f"Needs: {', '.join(request['needs'])}\n"
    )
    if request.get("min_condition") in rules.QUALITY_LABEL:
        user += f"Minimum quality: {rules.QUALITY_LABEL[request['min_condition']]} (condition {request['min_condition']}) or better\n"
    if request.get("colors"):
        user += f"Preferred colors: {', '.join(request['colors'])}\n"
    if request.get("style"):
        user += f"Room style: {request['style']}\n"
    for cat, p in (request.get("item_prefs") or {}).items():  # per-item choices override the whole-kit ones
        wants = [f"minimum quality {rules.QUALITY_LABEL[p['min_condition']]}" if p.get("min_condition") in rules.QUALITY_LABEL else "",
                 f"color {p['color']}" if p.get("color") else "", f"style {p['style']}" if p.get("style") else ""]
        if any(wants):
            user += f"For the {cat}: {', '.join(w for w in wants if w)}\n"
    user += f"\nAvailable inventory (snapshot):\n{_inventory_table(available_items)}"
    if shared_notes:
        user += "\n\nTeam notes from the Verifier (apply them):\n- " + "\n- ".join(shared_notes)
    if feedback:
        user += "\n\nThe Verifier REJECTED your previous proposal:\n- " + "\n- ".join(feedback)
    data = parse_json(_ask("planner", KIT_SYSTEM, user, 4096 if PLANNER_THINKING else 700,
                           thinking=PLANNER_THINKING, timeout=30.0, max_tries=2))
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
