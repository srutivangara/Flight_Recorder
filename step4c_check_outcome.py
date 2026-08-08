import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")

def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

eval_sessions = load_jsonl(DATA_DIR / "traces" / "eval.jsonl")

print("=" * 60)
print("Checking outcome field in eval sessions")
print("=" * 60)
print()

harm_values = Counter()
for s in eval_sessions:
    outcome = s.get("outcome", {})
    harm = outcome.get("harm_observed")
    harm_values[str(harm)] += 1

print("harm_observed value counts:")
for val, cnt in harm_values.most_common():
    print(f"  {cnt:3d}  →  {val}")

print()
print("=== Example outcome from first 3 sessions ===")
for s in eval_sessions[:3]:
    print(s["session_id"], "→", s.get("outcome"))