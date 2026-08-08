import json
from pathlib import Path
import sys

DATA_DIR = Path("data")

print("=" * 60)
print("STEP 1: Checking your dataset")
print("=" * 60)
print()

print("Looking in:", DATA_DIR.resolve())
print("Exists?", DATA_DIR.exists())
print()

# 1. Show everything inside data/
print("=== Contents of data/ folder ===")
for item in sorted(DATA_DIR.iterdir()):
    kind = "DIR " if item.is_dir() else "FILE"
    print(f"  {kind}  {item.name}")
print()

# 2. Check tools.py
tools_path = DATA_DIR / "tools.py"
if tools_path.exists():
    print("Found tools.py")
    sys.path.insert(0, str(DATA_DIR))
    try:
        import tools
        print("Successfully imported tools")
        print("Available functions:", [x for x in dir(tools) if not x.startswith("_")])
    except Exception as e:
        print("Could not import tools.py →", e)
        tools = None
else:
    print("tools.py NOT found")
    tools = None

print()

# 3. Check the main data files
print("=== Checking main data files ===")
files_to_check = [
    "traces/train.jsonl",
    "traces/eval.jsonl",
    "train_labels.json",
    "incidents.csv",
    "action_catalog.json",
    "policy_cost.json"
]

for f in files_to_check:
    path = DATA_DIR / f
    if path.exists():
        size = path.stat().st_size
        print(f"  OK  {f}  ({size:,} bytes)")
    else:
        print(f"  MISSING  {f}")

print()

# 4. Peek at train.jsonl (first 2 lines)
train_path = DATA_DIR / "traces" / "train.jsonl"
if train_path.exists():
    print("=== First 2 lines of train.jsonl ===")
    with open(train_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 2:
                break
            print(f"Line {i+1}:")
            try:
                obj = json.loads(line)
                print(json.dumps(obj, indent=2)[:800])  # first 800 chars
                print("...")
            except:
                print(line[:300])
            print()

print("=" * 60)
print("Copy the FULL output above and paste it back to me.")
print("=" * 60)