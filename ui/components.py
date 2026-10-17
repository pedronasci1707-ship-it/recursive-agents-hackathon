"""Shared look and feel: CSS, product helpers and the agent timeline."""

import html

import streamlit as st

BRAND = "#1F6F5C"

# Event kind -> (label, accent color): failures red, success green, replans orange.
KINDS = {
    "verify_fail": ("FAIL", "#e5484d"),
    "conflict": ("CONFLICT", "#e5484d"),
    "verify_pass": ("PASS", "#30a46c"),
    "reserve": ("RESERVE", "#30a46c"),
    "done": ("DONE", "#30a46c"),
    "replan": ("REPLAN", "#f76b15"),
    "escalate": ("ESCALATE", "#f76b15"),
    "plan": ("PLAN", "#3e63dd"),
    "intake": ("INTAKE", "#8e8c99"),
    "info": ("INFO", "#8e8c99"),
}
# Rough price of a comparable NEW item (USD), only for savings estimates.
NEW_RETAIL = {
    "mini_fridge": 170, "microwave": 90, "desk_lamp": 30, "fan": 40, "desk_chair": 120,
    "desk": 150, "storage_bins": 30, "shelf": 60, "kitchen_basics": 70, "other": 30,
}
ICONS = {
    "mini_fridge": "🧊", "microwave": "♨️", "desk_lamp": "💡", "fan": "🌀", "desk_chair": "🪑",
    "desk": "🗄️", "storage_bins": "📦", "shelf": "📚", "kitchen_basics": "🍳", "other": "🏷️",
}
CONDITION = {"A": "Like new", "B": "Good", "C": "Fair"}

CSS = f"""
<style>
:root {{ --brand: {BRAND}; }}
.cl-hero {{ padding: 22px 26px; border-radius: 16px; color: #fff;
           background: linear-gradient(120deg, {BRAND} 0%, #2E9C7F 100%); margin-bottom: 18px; }}
.cl-hero h1 {{ color: #fff; margin: 0 0 4px 0; font-size: 1.9rem; }}
.cl-hero p {{ margin: 0; opacity: .92; }}
.cl-card {{ border: 1px solid rgba(128,128,128,.25); border-radius: 14px; padding: 16px 18px; margin-bottom: 12px;
           background: rgba(128,128,128,.04); }}
.cl-product {{ display: flex; align-items: center; gap: 14px; padding: 10px 0;
              border-bottom: 1px solid rgba(128,128,128,.15); }}
.cl-product:last-child {{ border-bottom: none; }}
.cl-thumb {{ width: 54px; height: 54px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-size: 1.7rem; background: color-mix(in srgb, var(--brand) 12%, transparent); flex-shrink: 0; }}
.cl-pname {{ font-weight: 600; }}
.cl-pmeta {{ font-size: .85rem; opacity: .7; }}
.cl-price {{ margin-left: auto; font-weight: 700; font-size: 1.05rem; white-space: nowrap; }}
.cl-was {{ font-size: .8rem; opacity: .55; text-decoration: line-through; display: block; text-align: right; font-weight: 400; }}
.cl-badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 4px; }}
.cl-badge {{ font-size: .8rem; padding: 4px 10px; border-radius: 999px; font-weight: 600;
            background: color-mix(in srgb, var(--brand) 14%, transparent); color: var(--brand); }}
.cl-steps {{ display: flex; gap: 6px; margin: 6px 0 16px; }}
.cl-step {{ flex: 1; text-align: center; font-size: .8rem; padding-top: 8px; border-top: 4px solid rgba(128,128,128,.25); opacity: .6; }}
.cl-step.done {{ border-top-color: var(--brand); opacity: 1; font-weight: 600; }}
.cl-step.now {{ border-top-color: #f76b15; opacity: 1; font-weight: 600; }}
.cl-order {{ border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; border-left: 5px solid var(--accent);
            background: color-mix(in srgb, var(--accent) 8%, transparent); }}
.cl-order .who {{ font-weight: 700; font-size: 1.02rem; }}
.cl-order .state {{ font-weight: 600; color: var(--accent); margin: 2px 0 6px; }}
.cl-order .items {{ font-size: .88rem; opacity: .85; }}
.cl-world {{ border-radius: 10px; padding: 8px 12px; margin-bottom: 10px; font-size: .9rem; font-weight: 600;
            background: color-mix(in srgb, #e5484d 12%, transparent); border-left: 4px solid #e5484d; }}
.cl-timeline {{ display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; }}
.cl-row {{ display: grid; grid-template-columns: 48px 132px 78px 1fr; gap: 8px; align-items: baseline;
          padding: 6px 10px; border-radius: 6px; border-left: 4px solid var(--accent);
          background: color-mix(in srgb, var(--accent) 9%, transparent); }}
.cl-ts {{ font-family: ui-monospace, monospace; opacity: 0.65; text-align: right; }}
.cl-agent {{ font-weight: 600; }}
.cl-kind {{ font-family: ui-monospace, monospace; font-size: 0.72rem; font-weight: 700; color: var(--accent); }}
.cl-msg {{ line-height: 1.35; }}
.cl-attempt {{ padding: 8px 12px; border-radius: 6px; margin: 6px 0; border-left: 4px solid var(--accent);
              background: color-mix(in srgb, var(--accent) 10%, transparent); font-size: 0.92rem; }}
.cl-attempt b {{ color: var(--accent); }}
@media (max-width: 700px) {{ .cl-row {{ grid-template-columns: 44px 1fr; }} .cl-kind, .cl-agent {{ grid-column: 2; }} }}
</style>
"""


def inject_css():
    st.html(CSS)


def esc(text):
    return html.escape(str(text))


def money(value):
    """Dollar amount safe for st.markdown ("$" would otherwise start a LaTeX formula)."""
    return f"\\${value:,.0f}"


def md_safe(text):
    return str(text).replace("$", "\\$")


def hero(title, subtitle):
    st.html(f'<div class="cl-hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>')


def product_rows(items, show_was=True):
    rows = []
    for i in items:
        was = NEW_RETAIL.get(i["category"], NEW_RETAIL["other"])
        was_html = f'<span class="cl-was">${was} new</span>' if show_was else ""
        rows.append(
            f'<div class="cl-product"><div class="cl-thumb">{ICONS.get(i["category"], "🏷️")}</div>'
            f'<div><div class="cl-pname">{esc(i["name"])}</div>'
            f'<div class="cl-pmeta">{CONDITION.get(i["condition"], i["condition"])} · inspected &amp; cleaned · {esc(i["id"])}</div></div>'
            f'<div class="cl-price">${i["resale_price"]:.0f}{was_html}</div></div>'
        )
    return "".join(rows)


def badges(labels):
    return '<div class="cl-badges">' + "".join(f'<span class="cl-badge">{esc(b)}</span>' for b in labels) + "</div>"


def steps(labels, done_upto, now=None):
    """Progress tracker: labels[:done_upto] done, labels[now] in progress."""
    cells = []
    for idx, label in enumerate(labels):
        cls = "done" if idx < done_upto else ("now" if idx == now else "")
        cells.append(f'<div class="cl-step {cls}">{esc(label)}</div>')
    return '<div class="cl-steps">' + "".join(cells) + "</div>"


def savings(items, price):
    new_cost = sum(NEW_RETAIL.get(i["category"], NEW_RETAIL["other"]) for i in items)
    return max(new_cost - price, 0)


def timeline_html(events):
    rows = []
    for e in events:
        label, color = KINDS.get(e["kind"], (e["kind"].upper(), "#8e8c99"))
        rows.append(
            f'<div class="cl-row" style="--accent:{color}">'
            f'<span class="cl-ts">{e["ts"]:.1f}s</span>'
            f'<span class="cl-agent">{esc(e["agent"])}</span>'
            f'<span class="cl-kind">{label}</span>'
            f'<span class="cl-msg">{esc(e["message"])}</span></div>'
        )
    return '<div class="cl-timeline">' + "".join(rows) + "</div>"


def history_html(kit):
    """Every attempt of one kit: the failed ones with the Verifier's reason, then the fix."""
    parts = []
    for a in kit["history"]:
        color = "#30a46c" if a["passed"] else "#e5484d"
        verdict = "passed every check" if a["passed"] else "rejected: " + "; ".join(a["issues"])
        parts.append(
            f'<div class="cl-attempt" style="--accent:{color}">'
            f'<b>{"✅" if a["passed"] else "❌"} Attempt {a["attempt"]}</b> · {esc(", ".join(a["item_ids"]))}'
            f'<br>{esc(verdict)}</div>'
        )
    return "".join(parts)


def customer_story(kit):
    """The attempt history in words a student understands (no internal margins)."""
    story = []
    for a in kit["history"]:
        if a["passed"]:
            continue
        text = " ".join(a["issues"])
        if "already reserved" in text:
            story.append("An item we picked was bought by someone else while we were planning, so we replaced it.")
        if "safety recall" in text:
            story.append("We blocked an item whose model is under a safety recall and picked a safe alternative.")
        if "budget" in text:
            story.append("The first combination went over your budget, so we found better-priced items.")
        if "Missing" in text:
            story.append("A combination missed something you asked for, so we completed it.")
    return list(dict.fromkeys(story))
