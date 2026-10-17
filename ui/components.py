"""Design system: CSS tokens, product components and the admin agent timeline."""

import html
from urllib.parse import quote

import streamlit as st

BRAND = "#2D4BB8"   # cobalt: cut-paper collage palette, "by students, for students"

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
    "mini_fridge": ("kitchen", "#BFD6FA"), "microwave": ("microwave", "#FBC9AE"),
    "desk_lamp": ("emoji_objects", "#FBE08A"), "fan": ("mode_fan", "#C9D1FA"),
    "desk_chair": ("chair", "#DCC8F5"), "desk": ("desk", "#F7C3D7"),
    "storage_bins": ("inventory_2", "#BFE6CC"), "shelf": ("shelves", "#F9C7B8"),
    "kitchen_basics": ("skillet", "#F8C2CB"), "other": ("category", "#E6DFD0"),
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

# Hand-drawn underline. Fully URL-encoded: raw "<" inside a <style> block gets it stripped by st.html's sanitizer.
SQUIGGLE = "url(\"data:image/svg+xml," + quote(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 12' preserveAspectRatio='none'>"
    "<path d='M2 7 Q 12 1 22 7 T 42 7 T 62 7 T 82 7 T 102 7 T 118 6' fill='none' stroke='#EF5A2B' "
    "stroke-width='3.2' stroke-linecap='round'/></svg>", safe="") + "\")"

# Cut-paper collage look: warm paper background, flat bold colors, ink outlines with offset "sticker" shadows,
# heavy grotesk headlines mixed with an italic serif and a handwritten note. Class names are the product's API.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Averia+Serif+Libre:ital,wght@1,400;1,700&family=Homemade+Apple&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,300..500,0..1,0&display=block');
:root { --brand: __BRAND__; --ink: #111111; --muted: #5E5A52; --line: #E3DCCD; --soft: #EFE9DD; --paper: #F7F4ED;
        --mint: #FBE08A; --sun: #F5C431; --tomato: #EF5A2B; --leaf: #12985A; --sky: #79A9F2; --peach: #F8D2BC;
        --cobalt: __BRAND__; --shadow: 4px 4px 0 var(--ink); }
html, body, .stApp, .stMarkdown, p, li, h1, h2, h3, h4, h5, label, input, textarea, button,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] { font-family: 'Inter', system-ui, sans-serif; }
.stApp, [data-testid="stHeader"] { background: var(--paper); }
[data-testid="stSidebar"] { background: var(--soft); border-right: 2px solid var(--ink); }
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
h1, h2, h3 { letter-spacing: -0.035em; font-weight: 800; color: var(--ink); }
em.serif, .serif { font-family: 'Averia Serif Libre', Georgia, serif; font-style: italic; font-weight: 700; letter-spacing: -0.01em; }
footer { visibility: hidden; }
a { color: var(--cobalt); }
.ms { font-family: 'Material Symbols Rounded'; font-weight: 400; font-style: normal; line-height: 1;
      letter-spacing: normal; text-transform: none; white-space: nowrap; direction: ltr;
      -webkit-font-smoothing: antialiased; font-feature-settings: 'liga'; }
.scribble { font-family: 'Homemade Apple', cursive; font-size: 1.05rem; color: var(--tomato); line-height: 1.4;
            display: inline-block; transform: rotate(-3deg); }
.squig { background: __SQUIGGLE__ no-repeat left bottom / 100% 10px; padding-bottom: 6px; }

/* ---------- Streamlit widgets: rounded, outlined, playful ---------- */
[data-testid^="stBaseButton-primary"], [data-testid^="stBaseButton-secondary"], [data-testid="stPopoverButton"] {
  border-radius: 999px !important; border: 2px solid var(--ink) !important; font-weight: 700 !important;
  box-shadow: 3px 3px 0 var(--ink); transition: transform .12s ease, box-shadow .12s ease; }
[data-testid^="stBaseButton-primary"] { background: var(--cobalt) !important; color: #fff !important; }
[data-testid^="stBaseButton-secondary"], [data-testid="stPopoverButton"] { background: #fff !important; color: var(--ink) !important; }
[data-testid^="stBaseButton-primary"]:hover, [data-testid^="stBaseButton-secondary"]:hover, [data-testid="stPopoverButton"]:hover {
  transform: translate(-2px, -2px); box-shadow: 5px 5px 0 var(--ink); }
[data-testid^="stBaseButton-primary"]:active, [data-testid^="stBaseButton-secondary"]:active { transform: translate(2px, 2px); box-shadow: 0 0 0 var(--ink); }
[data-testid^="stBaseButton"]:disabled { box-shadow: none; opacity: .45; transform: none; }
/* bordered st.container(): only containers that already have a border style show these */
[data-testid="stVerticalBlock"], div[data-testid="stForm"] { border-width: 2px !important; border-radius: 22px !important; }
[data-testid="stButtonGroup"] button { border-radius: 999px !important; border: 2px solid var(--ink) !important;
  background: #fff !important; color: var(--ink) !important; font-weight: 600; }
[data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[aria-pressed="true"] {
  background: var(--sun) !important; box-shadow: 2px 2px 0 var(--ink); font-weight: 800; }
[data-testid="stTopNavLink"] { border-radius: 999px; font-weight: 700; }
[data-testid="stTopNavLink"]:hover { background: var(--mint); }
[data-testid="stTextInputRootElement"], [data-testid="stDateInputField"], [data-baseweb="select"] > div,
[data-testid="stTextAreaRootElement"], [data-baseweb="input"] { border-radius: 14px !important; border-color: var(--ink) !important; background: #fff !important; }
[data-testid="stFileUploaderDropzone"] { border-radius: 18px; border: 2px dashed var(--ink); background: #fff; }
[data-testid="stExpander"] details { border-radius: 16px; border: 2px solid var(--ink); background: #fff; }
[data-testid="stAlert"] { border-radius: 16px; }
[data-testid="stTab"] p { font-weight: 700; }

/* ---------- storefront ---------- */
.eyebrow { font-family: 'Averia Serif Libre', Georgia, serif; font-style: italic; font-weight: 700; font-size: 1.15rem;
           color: var(--cobalt); display: inline-block; letter-spacing: 0;
           background: __SQUIGGLE__ no-repeat left bottom / 100% 9px; padding-bottom: 7px; }
.page-title { font-size: 2.7rem; font-weight: 900; letter-spacing: -0.045em; margin: 6px 0 6px; color: var(--ink); line-height: 1.05; }
.page-sub { color: var(--muted); margin: 0 0 20px; font-size: 1.06rem; max-width: 640px; }
.hero { border-radius: 28px; padding: 42px 44px; background: var(--cobalt); color: #fff; position: relative; overflow: hidden;
        margin-bottom: 22px; border: 2px solid var(--ink); box-shadow: 6px 6px 0 var(--ink); isolation: isolate; }
.hero::before { content: ""; position: absolute; width: 230px; height: 230px; border-radius: 50%; background: var(--sun);
                top: -70px; right: -50px; z-index: -1; }
.hero::after { content: ""; position: absolute; width: 150px; height: 150px; background: var(--tomato); right: 70px; bottom: -40px;
               z-index: -1; transform: rotate(14deg);
               clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%); }
.hero h1 { color: #fff; font-size: 3rem; font-weight: 900; letter-spacing: -0.045em; margin: 0 0 12px; line-height: 1.02; }
.hero h1 em { font-family: 'Averia Serif Libre', Georgia, serif; font-style: italic; font-weight: 700; color: var(--sun); letter-spacing: -0.01em; }
.hero p { color: #E8ECFB; font-size: 1.1rem; margin: 0; max-width: 520px; line-height: 1.5; }
.hero > .ms { position: absolute; right: 26px; top: 26px; font-size: 64px; opacity: 1; color: var(--ink);
              background: #fff; border: 2px solid var(--ink); border-radius: 50%; padding: 12px; transform: rotate(-12deg); }
.hero .scribble { color: var(--sun); font-size: 1.1rem; margin-top: 18px; }
.pill { display: inline-flex; align-items: center; gap: 6px; font-size: .8rem; font-weight: 700; padding: 5px 12px;
        border-radius: 999px; background: var(--mint); color: var(--ink); border: 2px solid var(--ink); }
.pill.warn { background: var(--peach); color: var(--ink); }
.pill.grey { background: #fff; color: var(--muted); }
.pill .ms { font-size: 17px; }
.trust { display: flex; flex-wrap: wrap; gap: 10px; padding: 16px 0 4px; color: var(--ink); font-size: .88rem; font-weight: 600; }
.trust span { display: inline-flex; align-items: center; gap: 8px; background: #fff; border: 2px solid var(--ink);
              border-radius: 999px; padding: 6px 12px 6px 8px; }
.trust span:nth-child(1) .ms { color: var(--cobalt); } .trust span:nth-child(2) .ms { color: var(--tomato); }
.trust span:nth-child(3) .ms { color: #B88A00; }       .trust span:nth-child(4) .ms { color: var(--leaf); }
.trust .ms { font-size: 20px; }

.tile { width: 64px; height: 64px; border-radius: 18px; display: flex; align-items: center; justify-content: center;
        background: var(--tint); color: var(--ink); flex-shrink: 0; border: 2px solid var(--ink); }
.tile .ms { font-size: 32px; }
.line { display: flex; align-items: center; gap: 16px; padding: 14px 0; border-bottom: 2px dashed var(--line); }
.line:last-child { border-bottom: none; }
.line .name { font-weight: 700; color: var(--ink); }
.line .meta { font-size: .86rem; color: var(--muted); margin-top: 2px; }
.line .price { margin-left: auto; text-align: right; font-weight: 900; font-size: 1.15rem; white-space: nowrap; }
.line .price s { display: block; font-size: .78rem; font-weight: 500; color: var(--muted); }

.pc { border: 2px solid var(--ink); border-radius: 22px; overflow: hidden; background: #fff; box-shadow: var(--shadow);
      transition: transform .15s ease, box-shadow .15s ease; }
.pc:hover { transform: translate(-2px, -3px) rotate(-.6deg); box-shadow: 7px 8px 0 var(--ink); }
.pc-media { height: 160px; display: flex; align-items: center; justify-content: center; background: var(--tint); position: relative;
            border-bottom: 2px solid var(--ink); }
.pc-media .ms { font-size: 80px; color: var(--ink); }
.pc-cond { position: absolute; top: 12px; left: 12px; background: #fff; border: 2px solid var(--ink); border-radius: 999px;
           font-size: .74rem; font-weight: 700; padding: 3px 10px; }
.pc-save { position: absolute; top: 10px; right: 10px; background: var(--tomato); color: #fff; border: 2px solid var(--ink);
           border-radius: 999px; font-size: .8rem; font-weight: 900; padding: 4px 10px; transform: rotate(6deg); }
.pc-body { padding: 14px 16px 16px; }
.pc-name { font-weight: 700; color: var(--ink); line-height: 1.3; min-height: 2.6em; }
.pc-meta { font-size: .82rem; color: var(--muted); margin: 4px 0 8px; }
.pc-price { font-weight: 900; font-size: 1.35rem; color: var(--ink); letter-spacing: -0.02em; }
.pc-price s { font-weight: 500; font-size: .85rem; color: var(--muted); margin-left: 6px; }

.stepper { display: flex; gap: 0; margin: 10px 0 26px; }
.step { flex: 1; position: relative; text-align: center; font-size: .84rem; color: var(--muted); font-weight: 600; }
.step .dot { width: 34px; height: 34px; border-radius: 50%; margin: 0 auto 8px; display: flex; align-items: center;
             justify-content: center; background: #fff; border: 2px solid var(--ink); position: relative; z-index: 1; color: var(--muted); }
.step .dot .ms { font-size: 19px; }
.step::before { content: ""; position: absolute; top: 16px; left: -50%; width: 100%; height: 0; border-top: 2px dashed var(--ink); opacity: .35; }
.step:first-child::before { display: none; }
.step.done .dot { background: var(--leaf); color: #fff; }
.step.done::before, .step.now::before { border-top-style: solid; opacity: 1; }
.step.done, .step.now { color: var(--ink); font-weight: 800; }
.step.now .dot { background: var(--sun); color: var(--ink); transform: scale(1.12) rotate(-6deg); }

.sum { display: flex; justify-content: space-between; padding: 6px 0; color: var(--ink); }
.sum.muted { color: var(--muted); }
.sum.total { border-top: 2px solid var(--ink); margin-top: 6px; padding-top: 12px; font-weight: 900; font-size: 1.35rem; letter-spacing: -0.02em; }
.sum.save { color: var(--ink); font-weight: 800; background: var(--mint); border: 2px solid var(--ink); border-radius: 12px;
            padding: 8px 12px; margin-top: 8px; }
.meter { height: 12px; border-radius: 99px; background: #fff; border: 2px solid var(--ink); overflow: hidden; margin: 6px 0 2px; }
.meter > div { height: 100%; background: var(--leaf); }
.confirm { border-radius: 20px; padding: 22px 24px; background: var(--mint); color: var(--ink); border: 2px solid var(--ink);
           box-shadow: var(--shadow); }
.confirm h3 { margin: 0 0 6px; }
.offer { border-radius: 22px; border: 2px solid var(--ink); padding: 24px 26px; background: #fff; box-shadow: var(--shadow); }
.offer .big { font-size: 3.4rem; font-weight: 900; letter-spacing: -0.05em; color: var(--cobalt); line-height: 1; }
.offer.reject { background: #FFE9DF; }
.feature { padding: 22px 20px; background: #fff; border: 2px solid var(--ink); border-radius: 22px; box-shadow: var(--shadow);
           height: 100%; margin-bottom: 14px; }
.feature .ms { font-size: 28px; color: var(--ink); background: var(--sun); border: 2px solid var(--ink); border-radius: 50%;
               padding: 8px; display: inline-block; }
[data-testid="stColumn"]:nth-child(2) .feature .ms { background: var(--sky); }
[data-testid="stColumn"]:nth-child(3) .feature .ms { background: var(--peach); }
[data-testid="stColumn"]:nth-child(4) .feature .ms { background: #BFE6CC; }
.feature h4 { margin: 12px 0 4px; font-size: 1.06rem; font-weight: 800; }
.feature p { color: var(--muted); font-size: .92rem; margin: 0; }

/* ---------- admin ---------- */
.cl-order { border-radius: 14px; padding: 12px 14px; margin-bottom: 10px; border: 2px solid var(--ink); border-left: 8px solid var(--accent);
            background: #fff; }
.cl-order .who { font-weight: 800; font-size: 1.02rem; }
.cl-order .state { font-weight: 700; color: var(--accent); margin: 2px 0 6px; }
.cl-order .items { font-size: .88rem; opacity: .85; }
.cl-world { border-radius: 12px; padding: 8px 12px; margin-bottom: 10px; font-size: .9rem; font-weight: 700;
            background: #FFE9DF; border: 2px solid var(--ink); border-left: 8px solid var(--tomato); }
.cl-timeline { display: flex; flex-direction: column; gap: 4px; font-size: 0.9rem; }
.cl-row { display: grid; grid-template-columns: 48px 132px 78px 1fr; gap: 8px; align-items: baseline;
          padding: 6px 10px; border-radius: 8px; border-left: 4px solid var(--accent);
          background: color-mix(in srgb, var(--accent) 10%, #fff); }
.cl-ts { font-family: ui-monospace, monospace; opacity: 0.65; text-align: right; }
.cl-agent { font-weight: 700; }
.cl-kind { font-family: ui-monospace, monospace; font-size: 0.72rem; font-weight: 800; color: var(--accent); }
.cl-msg { line-height: 1.35; }
.cl-attempt { padding: 8px 12px; border-radius: 8px; margin: 6px 0; border-left: 4px solid var(--accent);
              background: color-mix(in srgb, var(--accent) 10%, #fff); font-size: 0.92rem; }
.cl-attempt b { color: var(--accent); }
@media (max-width: 700px) {
  .cl-row { grid-template-columns: 44px 1fr; } .cl-kind, .cl-agent { grid-column: 2; }
  .hero { padding: 28px 22px; } .hero h1 { font-size: 2.1rem; } .hero > .ms { display: none; }
  .page-title { font-size: 2rem; }
}
</style>
""".replace("__BRAND__", BRAND).replace("__SQUIGGLE__", SQUIGGLE)

CUSTOMER_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none; }
.block-container { max-width: 1160px; padding-top: 4.6rem; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { background: #fff; }
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


def scribble(text):
    """Handwritten note, like one student writing to another."""
    return f'<div class="scribble">{esc(text)}</div>'


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
