# ♻️ CampusLoop AI

**Autonomous recommerce agents for university move-out.**
Built at the Recursive Agents Hackathon (Crusoe x Cerebral Valley, San Francisco, Oct 17, 2026) for
**Challenge 01: Done Means Done**, on **Crusoe Managed Inference + NVIDIA Nemotron**.

🎬 **Demo video (1 min):** _link coming soon_

## Problem

Every move-out, students throw away or dump mini-fridges, microwaves, desk chairs and lamps that still work.
A few weeks later, the next class of students buys the same things new. The waste and the spending happen
on the same campus, just a few weeks apart, and nobody runs the loop in between.

## Solution

CampusLoop AI is a team of AI agents that runs campus recommerce end to end: it takes move-out listings,
rejects unsafe items, assembles move-in kits for incoming students, and **verifies its own work before it
says it is finished**. If something is wrong, it does not ship. It replans, fixes the problem, or hands it to a
human.

## How it works

```
 move-out listings                     incoming students (Ana, Marcus, Priya)
        │                                          │
        ▼                                          ▼
 ┌──────────────┐   accepted items   ┌──────────────────────────────┐
 │ Intake Agents│ ─────────────────► │ Kit Agents (one per student, │
 │  (parallel)  │                    │  planning in parallel)       │
 └──────────────┘                    └──────────────┬───────────────┘
   rejects recalled                                 │ proposed kits
   or unclear items                                 ▼
                                     ┌──────────────────────────────┐
                                     │ Verifier (deterministic code)│
                                     │ live inventory · recalls ·   │
                                     │ needs · budget · min margin  │
                                     └──────────────┬───────────────┘
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │ Recursive Controller         │
                                     │  pass  → reserve items, done │
                                     │  fail  → feedback → replan   │
                                     │  stuck → escalate to a human │
                                     │  limit → stop (max attempts) │
                                     └──────────────┬───────────────┘
                                                    ▼
                                      Final audit → Reporter → Done Report
```

- **Intake Agents** read free-text listings, extract the item, model and condition, and price them.
  A listing whose model is under a safety recall is rejected before it ever reaches inventory.
- **Kit Agents** (one per incoming student) pick items for that student's needs and budget, and explain why.
- **Verifier** checks every proposal against the **live** inventory with seven deterministic checks: items
  exist, no duplicates, still available, no recalled models, covers every need, within budget and at least
  a 30% margin.
- **Recursive Controller** loops plan → verify → replan with explicit limits. When the Verifier learns
  something (for example, that a fridge is recalled), it broadcasts it to every Kit Agent so none of them
  repeats the mistake.
- **Final audit** re-checks the finished state (no double bookings, no recalled items) before declaring done,
  and the **Reporter** writes the Done Report.

**Design rule:** the LLMs decide and reason; money, inventory and safety rules are plain code, so they are
reliable and testable.

## Done Means Done

The key moment of the demo: three Kit Agents plan **in parallel from the same inventory snapshot**, and
while they are planning, a walk-in buyer from outside the system buys the best mini-fridge.

1. Ana's and Marcus's agents both picked that fridge (`FRIDGE-01`). The Verifier rejects both kits:
   *"FRIDGE-01 is already reserved for walk-in buyer"*. The system **does not** declare the task done.
2. The Controller sends the Verifier's feedback back and the agents replan one at a time against live inventory.
3. Ana's second plan picks `FRIDGE-03`, a ChillCube CC-17, which is **under a safety recall**. It is rejected
   again, and the Controller broadcasts *"FRIDGE-03 is a recalled model: never use it"* to every Kit Agent.
4. Marcus switches to `FRIDGE-02` and passes. Ana passes on her third attempt with `FRIDGE-04`.
   Margins are recalculated each time.
5. Final audit: 3/3 kits verified, 9 items reserved, 0 double bookings, 0 recalled items shipped.
   The same recalled fridge model was also blocked at intake.

If a kit still fails after the attempt limit, the Controller escalates it to a human instead of shipping a bad kit.

## Built on Crusoe

Every model call goes through **Crusoe Managed Inference** (`api.inference.crusoecloud.com`), with
role-based model routing, retries with backoff and token/cache accounting in `core/crusoe_client.py`.

| Agent | Model |
|---|---|
| Kit Agents (planning) | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` |
| Reporter | `nvidia/Nemotron-3.5-Lightning-30B-A3B` |
| Intake Agents | `deepseek-ai/Deepseek-V4-Flash` |

A full run takes about 12 seconds.

## Run it

Requires Python 3.11+ and a Crusoe **Intelligence API key** (Console → Intelligence Foundry → Get API Key).

```bash
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then paste your key inside the single quotes
python check_crusoe.py      # verifies key, model IDs and one call per agent role
streamlit run app.py        # opens the demo UI in your browser
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process Bypass` first.

In the app, keep **Use sample run** on to replay a recorded run without API calls, or turn it off and press
**Run agents** to run the real agents on Crusoe. Other ways to run it:

```bash
python -m campusloop.engine   # live run in the terminal, prints the timeline
python -m pytest              # offline tests for the rules and the engine
```

## Layout

```
app.py                  Streamlit demo UI: live timeline, kit cards, attempt history, Done Report
campusloop/engine.py    Recursive Controller: plan → verify → replan, final audit, report
campusloop/agents.py    LLM agents: Intake, Kit, Reporter
campusloop/rules.py     Deterministic verification: inventory, recalls, budget, margin
campusloop/data/        Test catalog, move-out listings, student requests, recall list
core/crusoe_client.py   Crusoe client: model routing per agent role, retries with backoff, token/cache accounting
docs/CONTRACT.md        Engine ↔ UI contract
demo/sample_run.json    Recorded run used by the UI's sample mode
check_crusoe.py         Smoke test for the Crusoe endpoint
```

## Team

- **Pedro Nascimento** ([@pedronasci1707-ship-it](https://github.com/pedronasci1707-ship-it)): agent engine
- **Augusto** ([@augustolps10](https://github.com/augustolps10)): demo UI, README and video

**Next:** a pilot with student apartment buildings near NC State.
