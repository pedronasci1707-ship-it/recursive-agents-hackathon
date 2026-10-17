"""Live visual-quality smoke test. Uses Crusoe credits; run explicitly.

    .venv/Scripts/python.exe scripts/evaluate_photos.py
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from campusloop import agents, rules

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("quality_tests/new_mesh_chair.jpg", "desk_chair", "B", "Mesh chair for sale; operation and age not verified."),
    ("quality_tests/worn_laundry_basket.jpg", "storage_bins", "C", "Used laundry basket with repaired handles."),
    ("quality_tests/broken_light.jpg", "desk_lamp", "reject", "Broken light fixture with shattered glass."),
    ("listings/LIST-1.jpg", "mini_fridge", "A/B", "ChillCube mini fridge, model CC-17, works great."),
    ("listings/LIST-2.jpg", "desk_lamp", "A", "White battery-powered LED desk lamp, like new after one semester."),
    ("listings/LIST-3.jpg", "fan", "B", "20-inch Lasko box fan, dusty but runs on all speeds."),
]


def evaluate(case):
    rel, category, expected, description = case
    try:
        actual = agents.intake_listing({"seller": "photo evaluation", "text": description},
                                      image=(ROOT / "static" / rel).read_bytes())
        price = (None if actual["quality_score"] < 3 else
                 rules.price_listing(actual["category"], actual["condition"], actual["quality_score"]))
        passed = actual["category"] == category and (
            actual["quality_score"] < 3 if expected == "reject" else actual["condition"] in expected.split("/"))
        return {"photo": rel, "expected": expected, "passed": passed, "result": actual, "price": price}
    except Exception as exc:
        return {"photo": rel, "expected": expected, "passed": False, "error": str(exc)}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(evaluate, CASES))
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"PASS {sum(r['passed'] for r in results)}/{len(results)}")
