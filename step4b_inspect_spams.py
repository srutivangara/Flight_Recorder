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

print("=" * 60)
print("Inspecting span kinds in eval + train")
print("=" * 60)

# Look at both train and eval
for name in ["train", "eval"]:
    sessions = load_jsonl(DATA_DIR / "traces" / f"{name}.jsonl")
    kinds = Counter()
    for s in sessions:
        for sp in s.get("spans", []):
            kinds[sp.get("kind", "UNKNOWN")] += 1
    
    print(f"\n=== {name.upper()} span kinds ===")
    for k, c in kinds.most_common(20):
        print(f"  {c:5d}  {k}")