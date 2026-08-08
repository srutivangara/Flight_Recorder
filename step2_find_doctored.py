import sys
from pathlib import Path

# Make sure we can import tools from the data folder
DATA_DIR = Path("data")
sys.path.insert(0, str(DATA_DIR))

import tools

print("=" * 60)
print("STEP 2: Finding the 5 doctored sessions")
print("=" * 60)
print()

print("Checking TRAIN sessions...")
print("-" * 40)
bad_train = tools.verify("data/traces/train.jsonl")

print()
print("Checking EVAL sessions...")
print("-" * 40)
bad_eval = tools.verify("data/traces/eval.jsonl")

print()
print("=" * 60)
print("SUMMARY - All broken sessions:")
print("=" * 60)

all_bad = bad_train + bad_eval
print(f"Total broken sessions found: {len(all_bad)}")
print()

for sid, span in all_bad:
    print(f"  {sid}  (first bad span: {span})")

print()
if len(all_bad) == 5:
    print("SUCCESS! Exactly 5 doctored sessions found (as expected in the problem).")
else:
    print(f"Found {len(all_bad)} broken sessions.")