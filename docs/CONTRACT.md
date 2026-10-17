# Engine ↔ UI contract

The UI (`app.py`, Streamlit) talks to the agent engine through **one function**:

```python
from campusloop.engine import run

result = run(
    on_event=None,                 # optional callback(event: dict), called live for every event
    simulate_outside_buyer=True,   # chaos switch: an outside buyer grabs an item mid-run
    max_attempts=3,                # per buyer request, before escalating to a human
    requests=None,                 # optional: override campusloop/data/requests.json (e.g. a student's own request)
    listings=None,                 # optional: override campusloop/data/intake.json
)
```

`run()` blocks until the run finishes and returns a `dict` (JSON-serializable) with the shape below.
`on_event` is always called from the same thread that called `run()`, so it is safe to update Streamlit
elements from it.

Recorded runs with exactly this shape live in **`demo/`** (`sample_run.json`: conflict + recall,
`sample_escalation.json`: impossible request). Regenerate the first with `python -m campusloop.engine --save`.

```python
import json
result = json.load(open("demo/sample_run.json", encoding="utf-8"))
```

## Result

| Field | Type | Meaning |
|---|---|---|
| `run_id` | str | Unique id of the run |
| `status` | str | `"done"` (every kit verified) · `"done_with_escalations"` (some kits need a human) · `"failed"` |
| `started_at`, `finished_at` | str | ISO timestamps |
| `duration_s` | float | Wall-clock duration |
| `config` | dict | `max_attempts`, `min_margin_pct`, `simulate_outside_buyer`, `models` |
| `intake` | list[Intake] | Move-out listings processed by the Intake Agent |
| `kits` | list[Kit] | One per buyer request |
| `events` | list[Event] | Full timeline, in order |
| `inventory` | list[Item] | Inventory at the end of the run (with reservations) |
| `report` | str | Markdown "Done Report" written by the Reporter agent |
| `usage` | dict | Per-model tokens: `{model: {requests, prompt, completion, cached, cache_hit_rate}}` |

### Intake
`{listing_id, seller, text, photo, accepted: bool, reason: str, item: Item | null}` — `photo` is retained even
when the listing is rejected; `item` is set only when accepted.

### Kit
| Field | Type | Meaning |
|---|---|---|
| `request_id`, `buyer`, `profile` | str | Who the kit is for |
| `budget` | float | Buyer budget (USD) |
| `needs` | list[str] | Required categories, e.g. `["mini_fridge", "desk_lamp"]` |
| `min_condition` | str \| null | Whole-kit minimum quality (`"A"`, `"B"` or `"C"`) |
| `item_prefs` | dict | Per-category quality/color/style preferences |
| `status` | str | `"verified"` · `"needs_approval"` · `"failed"` |
| `attempts` | int | How many plan → verify cycles it took |
| `items` | list[Item] | Final items in the kit |
| `price` | float | What the buyer pays |
| `cost` | float | Our cost (acquisition + refurbishing + delivery) |
| `margin`, `margin_pct` | float | Profit in USD and in % of price |
| `checks` | list[Check] | Final verification checks |
| `history` | list[Attempt] | Every attempt, including the failed ones |
| `rationale` | str | The Kit Agent's explanation for the final choice |

`Check` = `{name, passed: bool, detail}` · `Attempt` = `{attempt, item_ids: [str], passed: bool, issues: [str]}`

### Event
`{ts, agent, kind, message, data}`

- `ts`: seconds since the run started (float)
- `agent`: `"Controller"`, `"Intake Agent"`, `"Kit Agent · Ana"`, `"Verifier"`, `"Outside world"`, `"Reporter"`
- `kind`: `info` · `photo_received` · `inventory_add` · `inventory_take` · `intake` · `plan` · `verify_pass` · `verify_fail` · `conflict` · `replan` · `reserve` · `escalate` · `done`
- `message`: one human-readable line (show it as-is)
- `data`: optional extra fields (dict). Events about one student carry `buyer`; proposals and passes carry
  `item_ids`; rejections carry `issues`; photo events carry `listing_id`, `item_id` and/or `photo`; accepted listings
  carry `item` (`id`, `name`, `category`, `resale_price`); the outside buyer carries `item_id`.

Suggested colors: `verify_fail`/`conflict` red, `verify_pass`/`reserve`/`inventory_add`/`done` green,
`replan`/`escalate` orange, photo and inventory movement blue, the rest neutral.

### Item
`{id, name, category, condition ("A"|"B"|"C"), quality_score (1..10), defects: [str], model, color, style, acquisition_cost, refurb_cost, resale_price, status ("available"|"reserved"), reserved_for, photo, source?}`

`photo` is a path relative to `static/`, such as `products/FRIDGE-01.jpg`, `listings/LIST-2.jpg` or
`uploads/LAMP-04.jpg`. `source` is present on SQLite rows (`catalog` or `seller`) and may be absent on temporary
items accepted only for the current engine run.
