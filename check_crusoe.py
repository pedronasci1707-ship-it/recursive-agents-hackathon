"""Smoke test for Crusoe Managed Inference: API key, model IDs, one call per role.

Run from the repo root:  python check_crusoe.py
"""

import sys
import time

from core.crusoe_client import MODELS, chat, get_client, text, usage_summary

sys.stdout.reconfigure(errors="replace")


def suggest(model_id, available):
    """Closest catalog ID for a configured one (IDs are case-sensitive)."""
    same_case = [a for a in available if a.lower() == model_id.lower()]
    if same_case:
        return same_case[0]
    stem = model_id.split("/")[-1].lower()[:12]
    partial = sorted(a for a in available if stem in a.lower())
    return partial[0] if partial else None


def main():
    try:
        client = get_client()
    except RuntimeError as e:
        print(f"[FAIL] {e}")
        return 1

    print("1) Listing models (GET /v1/models)...")
    try:
        available = {m.id for m in client.models.list()}
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}")
        print("       401/403 -> key wrong/expired or quotes missing in .env")
        return 1
    print(f"   {len(available)} models available:")
    for model_id in sorted(available):
        print(f"   - {model_id}")

    print("\n2) Model configured for each agent role...")
    ok = True
    for role, model_id in MODELS.items():
        if model_id in available:
            print(f"   [OK]   {role:8} {model_id}")
            continue
        ok = False
        hint = suggest(model_id, available)
        fix = f"set MODEL_{role.upper()}={hint} in .env" if hint else "pick another model in .env"
        print(f"   [MISS] {role:8} {model_id}  -> {fix}")

    print("\n3) One real call per role...")
    for role, model_id in MODELS.items():
        if model_id not in available:
            continue
        start = time.time()
        try:
            resp = chat(role, [{"role": "user", "content": "Reply with exactly: pong"}], max_tokens=1024)
        except Exception as e:
            ok = False
            print(f"   [FAIL] {role:8} {type(e).__name__}: {e}")
            continue
        answer = text(resp).strip().replace("\n", " ")[:60]
        finish = resp.choices[0].finish_reason
        print(f"   [OK]   {role:8} {time.time() - start:5.1f}s  finish={finish:6}  -> {answer!r}")

    print("\n4) Token usage this run:")
    for model_id, u in usage_summary().items():
        print(f"   {model_id}: {u}")

    print("\nALL GOOD - ready to build." if ok else "\nSome checks failed - see above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
