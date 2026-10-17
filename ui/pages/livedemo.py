"""Live demo: the whole agent pipeline, step by step, with the real models on Crusoe.

1 upload a photo -> 2 Listing Reader grades it (vision) -> 3 saved to the product repository ->
4 a student's request -> 5 the agent team builds and verifies a kit live -> 6 the kit, with product photos.
"""

from pathlib import Path

import streamlit as st

from campusloop import agents, db, engine, rules
from core.crusoe_client import MODELS
from ui import components as c

STATIC = Path(__file__).resolve().parents[2] / "static"
SAMPLES = {  # photos that ship with the repo, for a quick demo without your own picture
    "Box fan (listing)": ("listings/LIST-3.jpg", "20 inch box fan, a bit dusty but runs fine, Lasko 3733"),
    "Desk lamp (listing)": ("listings/LIST-2.jpg", "black desk lamp with USB port, used one semester"),
    "Recalled mini fridge (listing)": ("listings/LIST-1.jpg", "ChillCube mini fridge model CC-17, works great"),
    "Mesh chair (quality test)": ("quality_tests/new_mesh_chair.jpg", ""),
    "Worn laundry basket (quality test)": ("quality_tests/worn_laundry_basket.jpg", ""),
    "Broken light (quality test)": ("quality_tests/broken_light.jpg", ""),
}
ss = st.session_state


def step(n, title, agent=None, model=None):
    who = f" · <b>{c.esc(agent)}</b>" if agent else ""
    on = f' <span style="opacity:.6">({c.esc(model)})</span>' if model else ""
    st.html(f'<div class="eyebrow" style="font-size:1rem">Step {n}{who}{on}</div>'
            f'<div class="page-title" style="font-size:1.6rem">{c.esc(title)}</div>')


def photo_of(item):
    p = item.get("photo")
    return str(STATIC / p) if p and (STATIC / p).exists() else None


st.markdown("## :material/play_circle: Live demo: from a photo to a verified kit")
st.caption("Every step below calls the real agents on Crusoe Managed Inference. Done Means Done: nothing reaches "
           "the student until the Quality Checker has verified it.")

# ---------------------------------------------------------------- 1. upload
step(1, "A student moving out uploads a photo")
up_col, prev_col = st.columns([1.3, 1], gap="large")
with up_col:
    pick = st.selectbox("Use a sample photo", ["(upload my own)"] + list(SAMPLES))
    upload = st.file_uploader("Or upload a photo", type=["png", "jpg", "jpeg", "webp"]) if pick == "(upload my own)" else None
    text = st.text_input("Seller's description (optional)", value=SAMPLES.get(pick, ("", ""))[1], key=f"desc_{pick}")
if upload:
    image, mime, ext = upload.getvalue(), upload.type, upload.name.rsplit(".", 1)[-1].lower()
elif pick in SAMPLES:
    path = STATIC / SAMPLES[pick][0]
    image, mime, ext = path.read_bytes(), "image/jpeg", "jpg"
else:
    image = None
with prev_col:
    if image:
        st.image(image, width=260)

# ---------------------------------------------------------------- 2. listing reader
step(2, "The Listing Reader grades the item", "Listing Reader", MODELS["vision"])
if st.button("Run the Listing Reader", type="primary", icon=":material/visibility:", disabled=not image):
    with st.spinner("Looking at the photo on Crusoe…"):
        try:
            parsed = agents.intake_listing({"seller": "Demo seller", "text": text}, image=image, mime=mime)
            ss.ld_parsed, ss.ld_photo = parsed, (image, ext)
            ss.pop("ld_saved", None)
        except agents.AgentError as e:
            st.error(f"The model call failed ({e}). Wait a few seconds and try again.")
parsed = ss.get("ld_parsed")
if parsed:
    recall = rules.recall_reason(parsed.get("model"), rules.recall_list())
    price = rules.price_listing(parsed["category"], parsed["condition"])
    a, b = st.columns([1.3, 1], gap="large")
    with a:
        st.json({k: parsed.get(k) for k in ("name", "category", "condition", "quality_score", "defects",
                                             "model", "color", "style")})
    with b:
        st.metric("Quality", f"{c.CONDITION.get(parsed['condition'], parsed['condition'])} · "
                             f"{parsed.get('quality_score', '?')}/10")
        if recall:
            st.error(f"Blocked: model {parsed.get('model')} is under a safety recall. It never enters the repository.")
        else:
            st.metric("Offer to the seller / resale price", f"${price['acquisition_cost']} / ${price['resale_price']}")

    # ------------------------------------------------------------ 3. repository
    step(3, "Accepted items go into the product repository", "Product repository", "SQLite + photos")
    if recall:
        st.info("Nothing saved: recalled models are rejected before the repository.")
    else:
        if not ss.get("ld_saved") and st.button("Save to the repository", icon=":material/database:"):
            img, ext = ss.ld_photo
            item = {"id": f"{engine.ID_PREFIX.get(parsed['category'], 'ITEM')}-00",
                    "name": parsed.get("name") or "Unnamed item", "category": parsed["category"],
                    "condition": parsed["condition"], "quality_score": parsed.get("quality_score"),
                    "defects": parsed.get("defects", []), "model": parsed.get("model") or "",
                    "color": parsed.get("color", "other"), "style": parsed.get("style", "minimal"), **price}
            ss.ld_saved = db.add_product(item, photo_bytes=img, ext=ext)
        if ss.get("ld_saved"):
            st.success(f"Saved as **{ss.ld_saved['id']}**, with its photo. The agents can now use it.")

repo = db.products()
available = [i for i in repo if i["status"] == "available"]
st.caption(f"Repository: {len(repo)} products, {len(available)} available")
thumbs = [i for i in available if photo_of(i)][-8:]
for col, item in zip(st.columns(8), thumbs):
    col.image(photo_of(item), caption=f"{item['id']} · {c.CONDITION.get(item['condition'], '')}", width="stretch")

# ---------------------------------------------------------------- 4. request
step(4, "A student moving in asks for a kit")
r1, r2, r3 = st.columns([2, 1, 1.2])
needs = r1.pills("Needs", list(c.LABEL)[:-1], selection_mode="multi", default=["mini_fridge", "desk_lamp", "fan"],
                 format_func=lambda k: c.LABEL[k])
budget = r2.number_input("Budget ($)", 50, 500, 200, step=10)
min_q = r3.segmented_control("Minimum quality", ["C", "B", "A"], default="B",
                             format_func=lambda q: c.CONDITION[q] + ("+" if q != "A" else ""))
chaos = st.toggle("Simulate an outside buyer taking an item mid-run", value=True)

# ---------------------------------------------------------------- 5. agent team
step(5, "The agent team builds and verifies the kit", "Coordinator → Kit Builder → Quality Checker",
     MODELS["planner"])
if st.button("Run the agent team", type="primary", icon=":material/bolt:", disabled=not needs):
    request = {"id": "REQ-LIVE", "buyer": "Sam", "profile": "Incoming student (live demo)", "budget": budget,
               "needs": list(needs), "min_condition": min_q or "C"}
    feed, seen = st.empty(), []

    def on_event(e):
        seen.append(e)
        feed.html(c.timeline_html(list(reversed(seen))))

    with st.status("Agents working on Crusoe…", expanded=True):
        ss.ld_result = engine.run(on_event=on_event, simulate_outside_buyer=chaos, max_attempts=3,
                                  requests=[request], listings=[])
    st.rerun()

res = ss.get("ld_result")
if res:
    kit = res["kits"][0]
    with st.expander(f"Agent timeline ({len(res['events'])} steps, {res['duration_s']:.0f} s)", expanded=False):
        st.html(c.timeline_html(res["events"]))
    st.html(c.stepper([f"Attempt {a['attempt']}: {'passed' if a['passed'] else 'rejected'}" for a in kit["history"]],
                      done=len(kit["history"]), icons=["sync"] * len(kit["history"])))
    for a in kit["history"]:
        if not a["passed"]:
            st.markdown(f":red[**Attempt {a['attempt']} rejected:**] {c.md_safe('; '.join(a['issues']))}")

    # ------------------------------------------------------------ 6. result
    step(6, "The verified kit the student receives" if kit["status"] == "verified" else "Handed to a human")
    by_id = {i["id"]: i for i in db.products()}
    cols = st.columns(max(len(kit["items"]), 1))
    for col, item in zip(cols, kit["items"]):
        with col, st.container(border=True):
            img = photo_of(by_id.get(item["id"], item))
            if img:
                st.image(img, width="stretch")
            st.markdown(f"**{c.esc(item['name'])}**  \n{c.CONDITION.get(item['condition'], '')} · "
                         f"{c.md_safe('$')}{item['resale_price']:.0f}")
    passed = sum(x["passed"] for x in kit["checks"])
    st.markdown(f"**{kit['status'].upper()}** · {passed}/{len(kit['checks'])} checks passed · "
                f"{c.md_safe('$')}{kit['price']:.0f} · margin {kit['margin_pct']:.0f}%")
