import json
from pathlib import Path

DATA_DIR = Path("data")

print("=" * 60)
print("STEP 5: Smart Confirmation Policy")
print("=" * 60)
print()

# Load action catalog
with open(DATA_DIR / "action_catalog.json", "r", encoding="utf-8") as f:
    catalog_list = json.load(f)

# Convert to dict for easy lookup: tool_name → info
catalog = {item["tool"]: item for item in catalog_list}

print(f"Loaded {len(catalog)} tools from catalog\n")

# Tools that should ALWAYS be confirmed (high risk)
HIGH_RISK_TOOLS = set()
for tool, info in catalog.items():
    loss = info.get("expected_loss_if_wrong_inr", 0)
    reversibility = info.get("reversibility_window_min", -1)
    side_effect = info.get("side_effect", False)
    action_class = info.get("action_class", "")

    # Confirm if:
    # - expected loss is high, OR
    # - irreversible (reversibility <= 0), OR
    # - money / filing / infra / high-comms
    if (loss >= 2000 or 
        reversibility == 0 or 
        reversibility == -1 and side_effect or
        action_class in ["money", "filing", "infra", "comms_high", "share"]):
        HIGH_RISK_TOOLS.add(tool)

print("High-risk tools that will be confirmed:")
for t in sorted(HIGH_RISK_TOOLS):
    print(f"  - {t}")
print()

# Load eval sessions
def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

eval_sessions = load_jsonl(DATA_DIR / "traces" / "eval.jsonl")
print(f"Loaded {len(eval_sessions)} eval sessions")

# Build policy
policy = {}
total_confirmations = 0

for sess in eval_sessions:
    sid = sess["session_id"]
    policy[sid] = {}
    
    for sp in sess.get("spans", []):
        if sp.get("kind") != "tool_call":
            continue
        
        # Try to get the tool name from the span
        tool_name = None
        
        # Common places where tool name appears
        if "tool" in sp:
            tool_name = sp["tool"]
        elif "name" in sp:
            tool_name = sp["name"]
        elif "content" in sp and isinstance(sp["content"], dict):
            tool_name = sp["content"].get("tool") or sp["content"].get("name")
        elif "arguments" in sp and isinstance(sp["arguments"], dict):
            tool_name = sp["arguments"].get("tool")
        
        # Fallback: look inside the whole span as string
        if tool_name is None:
            span_str = json.dumps(sp).lower()
            for t in catalog.keys():
                if t.lower() in span_str:
                    tool_name = t
                    break
        
        should_confirm = False
        if tool_name and tool_name in HIGH_RISK_TOOLS:
            should_confirm = True
        
        policy[sid][sp["span_id"]] = should_confirm
        if should_confirm:
            total_confirmations += 1

# Save policy
with open("policy.json", "w", encoding="utf-8") as f:
    json.dump(policy, f, indent=2)

print(f"\nSaved → policy.json")
print(f"Total confirmations across all sessions: {total_confirmations}")
print()
print("=" * 60)
print("Policy created successfully.")
print("=" * 60)