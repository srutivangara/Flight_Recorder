import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")

print("=" * 60)
print("STEP 4 (final for now): Predictions for 150 eval sessions")
print("=" * 60)
print()

def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

eval_sessions = load_jsonl(DATA_DIR / "traces" / "eval.jsonl")
print(f"Loaded {len(eval_sessions)} eval sessions")

def predict_session(session):
    spans = session.get("spans", [])
    session_id = session["session_id"]
    
    # Collect spans by kind
    user_span = None
    retrieval_spans = []
    tool_call_spans = []
    delegation_spans = []
    confirmation_spans = []
    plan_spans = []
    
    for sp in spans:
        kind = sp.get("kind", "")
        if kind == "user_message":
            user_span = sp
        elif kind == "retrieval":
            retrieval_spans.append(sp)
        elif kind == "tool_call":
            tool_call_spans.append(sp)
        elif kind == "delegation":
            delegation_spans.append(sp)
        elif kind == "confirmation_request":
            confirmation_spans.append(sp)
        elif kind == "plan":
            plan_spans.append(sp)
    
    # Default
    root_cause = "no_fault_correct_behaviour"
    first_cause_span = user_span["span_id"] if user_span else (spans[0]["span_id"] if spans else None)
    
    # ---------- Decision rules (highest priority first) ----------
    
    # 1. Retrieval present → prompt injection (most common real failure)
    if retrieval_spans:
        root_cause = "prompt_injection_via_retrieval"
        first_cause_span = retrieval_spans[0]["span_id"]
    
    # 2. Delegation present → delegated agent compromise
    elif delegation_spans:
        root_cause = "delegated_agent_compromise"
        first_cause_span = delegation_spans[0]["span_id"]
    
    # 3. Confirmation request exists → missing confirmation gate
    elif confirmation_spans:
        root_cause = "missing_confirmation_gate"
        first_cause_span = confirmation_spans[0]["span_id"]
    
    # 4. Has plan + tool calls → agent planning error
    elif plan_spans and tool_call_spans:
        root_cause = "agent_planning_error"
        first_cause_span = plan_spans[0]["span_id"]
    
    # 5. Only tool calls → tool API misresponse
    elif tool_call_spans:
        root_cause = "tool_api_misresponse"
        first_cause_span = tool_call_spans[0]["span_id"]
    
    # 6. Fallback
    else:
        root_cause = "user_instruction_ambiguity"
        first_cause_span = user_span["span_id"] if user_span else first_cause_span
    
    return {
        "session_id": session_id,
        "root_cause": root_cause,
        "first_cause_span": first_cause_span
    }

# Run
predictions = []
for sess in eval_sessions:
    predictions.append(predict_session(sess))

# Save
with open("predictions.json", "w", encoding="utf-8") as f:
    json.dump(predictions, f, indent=2)

print("Saved → predictions.json\n")

# Show distribution
causes = Counter([p["root_cause"] for p in predictions])
print("Prediction distribution:")
for cause, count in causes.most_common():
    print(f"  {count:3d}  {cause}")

print("\nFirst 8 predictions:")
for p in predictions[:8]:
    print(f"  {p['session_id']}: {p['root_cause']} | {p['first_cause_span']}")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)