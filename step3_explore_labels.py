import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")

print("=" * 60)
print("STEP 3: Understanding the labels and root-cause classes")
print("=" * 60)
print()

# Load train labels
with open(DATA_DIR / "train_labels.json", "r", encoding="utf-8") as f:
    train_labels = json.load(f)

print(f"Number of training labels: {len(train_labels)}")
print()

# Show the structure of one label
print("=== Example of one training label ===")
print(json.dumps(train_labels[0], indent=2))
print()

# Find all possible root_cause values
root_causes = []
for lab in train_labels:
    # Try common field names
    rc = lab.get("root_cause") or lab.get("cause") or lab.get("label") or lab.get("class")
    if rc:
        root_causes.append(rc)

print("=== All root_cause classes found ===")
counter = Counter(root_causes)
for cause, count in counter.most_common():
    print(f"  {count:4d}  →  {cause}")

print()
print("Total unique classes:", len(counter))
print()

# Also show keys present in a label
print("Keys present in a label object:")
print(list(train_labels[0].keys()))