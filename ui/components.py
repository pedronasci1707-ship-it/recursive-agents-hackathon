"""Design system: CSS tokens, product components and the admin agent timeline."""

import html

import streamlit as st

BRAND = "#0B6E4F"

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
ICONS = {  # emoji, used in the admin views
    "mini_fridge": "🧊", "microwave": "♨️", "desk_lamp": "💡", "fan": "🌀", "desk_chair": "🪑",
    "desk": "🗄️", "storage_bins": "📦", "shelf": "📚", "kitchen_basics": "🍳", "other": "🏷️",
}
# Customer-facing product art: (Material Symbols icon, tile tint)
ART = {
    "mini_fridge": ("kitchen", "#E3F1FB"), "microwave": ("microwave", "#FDEEDC"),
    "desk_lamp": ("emoji_objects", "#FBF5D5"), "fan": ("mode_fan", "#E7EAFB"),
    "desk_chair": ("chair", "#F1E8FB"), "desk": ("desk", "#FBE7F0"),
    "storage_bins": ("inventory_2", "#E2F5E9"), "shelf": ("shelves", "#FBE9E6"),
    "kitchen_basics": ("skillet", "#FCE8EC"), "other": ("category", "#EEF0EE"),
}
LABEL = {
    "mini_fridge": "Mini fridge", "microwave": "Microwave", "desk_lamp": "Desk lamp", "fan": "Fan",
    "desk_chair": "Desk chair", "desk": "Desk", "storage_bins": "Storage", "shelf": "Shelf",
    "kitchen_basics": "Kitchen", "other": "Other",
}
CONDITION = {"A": "Excellent", "B": "Good", "C": "Fair"}
CONDITION_HELP = {
    "A": "Like new. No visible wear.",
    "B": "Light signs of use. Works perfectly.",
    "C": "Visible wear. Fully working.",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..500,0..1,0&display=block');
:root {{ --brand: {BRAND}; --ink: #14201B; --muted: #66706B; --line: #E6E8E5; --soft: #F5F6F4; --mint: #E3F4EC; }}
html, body, .stApp, .stMarkdown, p, li, h1, h2, h3, h4, h5, label, input, textarea, button,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ font-family: 'Inter', system-ui, sans-serif; }}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
h1, h2, h3 {{ letter-spacing: -0.02em; font-weight: 700; }}
footer {{ visibility: hidden; }}
.ms {{ font-family: 'Material Symbols Rounded'; font-weight: 300; font-style: normal; line-height: 1;
      letter-spacing: normal; text-transform: none; white-space: nowrap; direction: ltr;
      -webkit-font-smoothing: antialiased; font-feature-settings: 'liga'; }}

/* ---------- storefront ---------- */
.eyebrow {{ font-size: .78rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--brand); }}
.page-title {{ font-size: 2.1rem; font-weight: 800; letter-spacing: -0.03em; margin: 2px 0 4px; color: var(--ink); }}
.page-sub {{ color: var(--muted); margin: 0 0 18px; font-size: 1.02rem; }}
.hero {{ border-radius: 22px; padding: 38px 40px; background: linear-gradient(135deg, #0B6E4F 0%, #128C66 60%, #3FB68B 100%);
        color: #fff; position: relative; overflow: hidden; margin-bottom: 22px; }}
.hero h1 {{ color: #fff; font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em; margin: 0 0 8px; line-height: 1.1; }}
.hero p {{ color: #E6F6EF; font-size: 1.08rem; margin: 0; max-width: 560px; }}
.hero .ms {{ position: absolute; right: 36px; bottom: -18px; font-size: 190px; opacity: .14; }}
.pill {{ display: inline-flex; align-items: center; gap: 6px; font-size: .78rem; font-weight: 600; padding: 4px 10px;
        border-radius: 999px; background: var(--mint); color: var(--brand); }}
.pill.warn {{ background: #FFF1E2; color: #B4580D; }}
.pill.grey {{ background: var(--soft); color: var(--muted); }}
.pill .ms {{ font-size: 16px; }}
.trust {{ display: flex; flex-wrap: wrap; gap: 22px; padding: 14px 0 4px; color: var(--muted); font-size: .9rem; }}
.trust span {{ display: inline-flex; align-items: center; gap: 8px; }}
.trust .ms {{ color: var(--brand); font-size: 20px; }}

.tile {{ width: 64px; height: 64px; border-radius: 14px; display: flex; align-items: center; justify-content: center;
        background: var(--tint); color: #22302A; flex-shrink: 0; }}
.tile .ms {{ font-size: 32px; }}
.line {{ display: flex; align-items: center; gap: 16px; padding: 14px 0; border-bottom: 1px solid var(--line); }}
.line:last-child {{ border-bottom: none; }}
.line .name {{ font-weight: 600; color: var(--ink); }}
.line .meta {{ font-size: .86rem; color: var(--muted); margin-top: 2px; }}
.line .price {{ margin-left: auto; text-align: right; font-weight: 700; font-size: 1.05rem; white-space: nowrap; }}
.line .price s {{ display: block; font-size: .78rem; font-weight: 400; color: var(--muted); }}

.pc {{ border: 1px solid var(--line); border-radius: 18px; overflow: hidden; background: #fff; transition: box-shadow .15s; }}
.pc:hover {{ box-shadow: 0 8px 24px rgba(20,32,27,.08); }}
.pc-media {{ height: 150px; display: flex; align-items: center; justify-content: center; background: var(--tint); position: relative; }}
.pc-media .ms {{ font-size: 72px; color: #22302A; }}
.pc-cond {{ position: absolute; top: 12px; left: 12px; background: #fff; border-radius: 999px; font-size: .74rem;
           font-weight: 600; padding: 3px 9px; }}
.pc-save {{ position: absolute; top: 12px; right: 12px; background: var(--ink); color: #fff; border-radius: 999px;
           font-size: .74rem; font-weight: 700; padding: 3px 9px; }}
.pc-body {{ padding: 14px 16px 16px; }}
.pc-name {{ font-weight: 600; color: var(--ink); line-height: 1.3; min-height: 2.6em; }}
.pc-meta {{ font-size: .82rem; color: var(--muted); margin: 4px 0 8px; }}
.pc-price {{ font-weight: 800; font-size: 1.2rem; color: var(--ink); }}
.pc-price s {{ font-weight: 400; font-size: .85rem; color: var(--muted); margin-left: 6px; }}

.stepper {{ display: flex; gap: 0; margin: 8px 0 24px; }}
.step {{ flex: 1; position: relative; text-align: center; font-size: .82rem; color: var(--muted); }}
.step .dot {{ width: 30px; height: 30px; border-radius: 50%; margin: 0 auto 8px; display: flex; align-items: center;
             justify-content: center; background: var(--soft); border: 2px solid var(--line); position: relative; z-index: 1; }}
.step .dot .ms {{ font-size: 18px; }}
.step::before {{ content: ""; position: absolute; top: 15px; left: -50%; width: 100%; height: 2px; background: var(--line); }}
.step:first-child::before {{ display: none; }}
.step.done .dot {{ background: var(--brand); border-color: var(--brand); color: #fff; }}
.step.done::before, .step.now::before {{ background: var(--brand); }}
.step.done, .step.now {{ color: var(--ink); font-weight: 600; }}
.step.now .dot {{ border-color: var(--brand); color: var(--brand); background: #fff; }}

.sum {{ display: flex; justify-content: space-between; padding: 6px 0; color: var(--ink); }}
.sum.muted {{ color: var(--muted); }}
.sum.total {{ border-top: 1px solid var(--line); margin-top: 6px; padding-top: 12px; font-weight: 800; font-size: 1.2rem; }}
.sum.save {{ color: var(--brand); font-weight: 600; }}
.meter {{ height: 8px; border-radius: 99px; background: var(--soft); overflow: hidden; margin: 6px 0 2px; }}
.meter > div {{ height: 100%; background: var(--brand); border-radius: 99px; }}
.confirm {{ border-radius: 18px; padding: 22px 24px; background: var(--mint); color: var(--ink); }}
.confirm h3 {{ margin: 0 0 6px; }}
.offer {{ border-radius: 18px; border: 1px solid var(--line); padding: 22px 24px; }}
.offer .big {{ font-size: 2.6rem; font-weight: 800; letter-spacing: -0.03em; color: var(--ink); line-height: 1; }}
.offer.reject {{ border-color: #F3C2C2; background: #FFF6F6; }}
.feature {{ padding: 18px 4px; }}
.feature .ms {{ font-size: 30px; color: var(--brand); }}
.feature h4 {{ margin: 8px 0 4px; font-size: 1.02rem; }}
.feature p {{ color: var(--muted); font-size: .92rem; margin: 0; }}

/* ---------- admin ---------- */
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
@media (max-width: 700px) {{
  .cl-row {{ grid-template-columns: 44px 1fr; }} .cl-kind, .cl-agent {{ grid-column: 2; }}
  .hero {{ padding: 26px 22px; }} .hero h1 {{ font-size: 1.8rem; }}
}}
</style>
"""

CUSTOMER_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none; }
.block-container { max-width: 1160px; padding-top: 4.6rem; }
</style>
"""


def inject_css(customer=False):
    st.html(CSS + (CUSTOMER_CSS if customer else ""))


def esc(text):
    return html.escape(str(text))


def money(value):
    """Dollar amount safe for st.markdown ("$" would otherwise start a LaTeX formula)."""
    return f"\\${value:,.0f}"


def md_safe(text):
    return str(text).replace("$", "\\$")


def icon(name, size=None):
    style = f' style="font-size:{size}px"' if size else ""
    return f'<span class="ms"{style}>{name}</span>'


def page_header(eyebrow, title, sub=None):
    st.html(f'<div class="eyebrow">{esc(eyebrow)}</div><div class="page-title">{esc(title)}</div>'
            + (f'<p class="page-sub">{esc(sub)}</p>' if sub else ""))


def hero(title, sub, art="autorenew"):
    st.html(f'<div class="hero"><h1>{esc(title)}</h1><p>{esc(sub)}</p>{icon(art)}</div>')


def pill(text, kind="", ico=None):
    return f'<span class="pill {kind}">{icon(ico) if ico else ""}{esc(text)}</span>'


def trust_strip():
    return ('<div class="trust">'
            f'<span>{icon("verified_user")}Safety-recall checked</span>'
            f'<span>{icon("cleaning_services")}Inspected &amp; cleaned</span>'
            f'<span>{icon("local_shipping")}Delivered on move-in day</span>'
            f'<span>{icon("eco")}Second life, less waste</span></div>')


def new_price(item):
    return NEW_RETAIL.get(item["category"], NEW_RETAIL["other"])


def tile(category, size=64):
    ico, tint = ART.get(category, ART["other"])
    return (f'<div class="tile" style="--tint:{tint};width:{size}px;height:{size}px">'
            f'<span class="ms" style="font-size:{int(size * .5)}px">{ico}</span></div>')


def line_item(item):
    return (f'<div class="line">{tile(item["category"])}'
            f'<div><div class="name">{esc(item["name"])}</div>'
            f'<div class="meta">{CONDITION.get(item["condition"], item["condition"])} condition · '
            f'{LABEL.get(item["category"], "Item")}</div></div>'
            f'<div class="price">${item["resale_price"]:.0f}<s>${new_price(item)} new</s></div></div>')


def product_card(item):
    ico, tint = ART.get(item["category"], ART["other"])
    save = round(100 * (1 - item["resale_price"] / new_price(item)))
    return (f'<div class="pc"><div class="pc-media" style="--tint:{tint}"><span class="ms">{ico}</span>'
            f'<span class="pc-cond">{CONDITION.get(item["condition"], item["condition"])}</span>'
            f'<span class="pc-save">-{save}%</span></div>'
            f'<div class="pc-body"><div class="pc-name">{esc(item["name"])}</div>'
            f'<div class="pc-meta">{LABEL.get(item["category"], "Item")} · inspected &amp; cleaned</div>'
            f'<div class="pc-price">${item["resale_price"]:.0f}<s>${new_price(item)}</s></div></div></div>')


def stepper(labels, done, now=None, icons=None):
    cells = []
    for idx, label in enumerate(labels):
        cls = "done" if idx < done else ("now" if idx == now else "")
        mark = icon("check") if idx < done else icon(icons[idx] if icons else "radio_button_unchecked")
        cells.append(f'<div class="step {cls}"><div class="dot">{mark}</div>{esc(label)}</div>')
    return '<div class="stepper">' + "".join(cells) + "</div>"


def savings(items, price):
    return max(sum(new_price(i) for i in items) - price, 0)


# ---------------------------------------------------------------- admin helpers

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
