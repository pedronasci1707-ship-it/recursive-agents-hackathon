# Recursive Agents Hackathon — Crusoe x Cerebral Valley

Built at the Recursive Agents Hackathon (San Francisco, Oct 17, 2026) on **Crusoe Managed Inference**.

> Project description, architecture and demo video coming soon.

## Setup

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
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process Bypass` first.

## Layout

```
core/crusoe_client.py   Crusoe client: model routing per agent role, retries with backoff, token/cache accounting
check_crusoe.py         Smoke test for the Crusoe endpoint
.claude/skills/         Official Crusoe hackathon skill file (reference for coding agents)
```
