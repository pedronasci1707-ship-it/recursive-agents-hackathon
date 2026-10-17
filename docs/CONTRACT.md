# Engine ↔ UI contract

The UI (`app.py`, Streamlit) talks to the agent engine through **one function**:

```python
from campusloop.engine import run

result = run(
    on_event=None,                 # optional callback(event: dict), called live for every event
    simulate_outside_buyer=True,   # chaos switch: an outside buyer grabs an item mid-run
    max_attempts=3,                # per buyer request, before escalating to a human
)
```

`run()` blocks until the run finishes and returns a `dict` (JSON-serializable) with the shape below.
`on_event` is always called from the same thread that called `run()`, so it is safe to update Streamlit
elements from it.

While the engine is being built, develop the UI against **`demo/sample_run.json`** — it has exactly this shape:

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
| `config` | dict | `max_attempts`, `min_margin_pct`, `simulate_outside_buyer` |
| `intake` | list[Intake] | Move-out listings processed by the Intake Agent |
| `kits` | list[Kit] | One per buyer request |
| `events` | list[Event] | Full timeline, in order |
| `inventory` | list[Item] | Inventory at the end of the run (with reservations) |
| `report` | str | Markdown "Done Report" written by the Reporter agent |
| `usage` | dict | Per-model tokens: `{model: {requests, prompt, completion, cached, cache_hit_rate}}` |

### Intake
`{listing_id, seller, text, accepted: bool, reason: str, item: Item | null}` — `item` is set when accepted.

### Kit
| Field | Type | Meaning |
|---|---|---|
| `request_id`, `buyer`, `profile` | str | Who the kit is for |
| `budget` | float | Buyer budget (USD) |
| `needs` | list[str] | Required categories, e.g. `["mini_fridge", "desk_lamp"]` |
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
- `kind`: `info` · `intake` · `plan` · `verify_pass` · `verify_fail` · `conflict` · `replan` · `reserve` · `escalate` · `done`
- `message`: one human-readable line (show it as-is)
- `data`: optional extra fields (dict)

Suggested colors: `verify_fail`/`conflict` red, `verify_pass`/`reserve`/`done` green, `replan`/`escalate` orange, the rest neutral.

### Item
`{id, name, category, condition ("A"|"B"|"C"), model, acquisition_cost, refurb_cost, resale_price, status ("available"|"reserved"), reserved_for}`
