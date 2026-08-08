import json, hashlib, os, re
from collections import Counter
from flask import Flask, render_template, jsonify, request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = os.path.dirname(__file__)
DATA = os.path.join(ROOT, "data")

CLASSES = [
    "prompt_injection_via_retrieval",
    "user_instruction_ambiguity",
    "no_fault_correct_behaviour",
    "delegated_agent_compromise",
    "missing_confirmation_gate",
    "tool_api_misresponse",
    "stale_state_assumption",
    "agent_planning_error",
]

CLASS_LABELS = {
    "prompt_injection_via_retrieval": "Prompt injection via retrieval",
    "user_instruction_ambiguity": "User instruction ambiguity",
    "no_fault_correct_behaviour": "No fault / correct behaviour",
    "delegated_agent_compromise": "Delegated agent compromise",
    "missing_confirmation_gate": "Missing confirmation gate",
    "tool_api_misresponse": "Tool/API misresponse",
    "stale_state_assumption": "Stale state assumption",
    "agent_planning_error": "Agent planning error",
}

def load_json(path):
    with open(os.path.join(DATA, path), encoding="utf-8") as f:
        return json.load(f)

def load_jsonl(path):
    with open(os.path.join(DATA, path), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

TRAIN = load_jsonl("traces/train.jsonl")
EVAL = load_jsonl("traces/eval.jsonl")
LABELS = {x["session_id"]: x for x in load_json("train_labels.json")}
ACTIONS = load_json("action_catalog.json")
COSTS = load_json("policy_cost.json")
ACTION_MAP = {x["tool"]: x for x in ACTIONS}

def verify_session(session):
    prev = "0" * 64
    bad = None
    for sp in session["spans"]:
        payload = {k: v for k, v in sp.items() if k != "hash"}
        expected = hashlib.sha256((prev + json.dumps(payload, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
        # Dataset generator uses default json.dumps separators. Try exact verifier form too.
        expected_default = hashlib.sha256((prev + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
        if sp.get("prev_hash") != prev or sp.get("hash") not in (expected, expected_default):
            bad = sp["span_id"]
            break
        prev = sp["hash"]
    return {"ok": bad is None, "first_bad_span": bad}

def is_injection_text(text):
    t = (text or "").lower()
    patterns = [
        "assistant:", "ignore previous", "ignore the user", "urgent per finance",
        "update the primary", "submit the return now", "send the corrected",
        "use the following", "override", "do not ask", "system instruction"
    ]
    return any(p in t for p in patterns)

def session_text(s):
    bits = [s.get("user_goal", "")]
    for sp in s["spans"]:
        for key in ("content", "mandate", "plan", "prompt"):
            if sp.get(key):
                bits.append(str(sp[key]))
        if sp.get("tool"):
            bits.append(sp["tool"])
    return " ".join(bits)

def structured_features(s):
    spans = s["spans"]
    calls = [x for x in spans if x["kind"] == "tool_call"]
    results = [x for x in spans if x["kind"] == "tool_result"]
    retrievals = [x for x in spans if x["kind"] == "retrieval"]
    delegations = [x for x in spans if x["kind"] == "delegation"]
    confirms = [x for x in spans if x["kind"] == "confirmation_request"]
    responses = [x for x in spans if x["kind"] == "confirmation_response"]
    harmful = [x for x in calls if ACTION_MAP.get(x.get("tool"), {}).get("side_effect")]
    failed = sum(1 for x in results if x.get("status") not in ("ok", None))
    untrusted = sum(1 for x in retrievals if x.get("trust_domain") != "first_party")
    injected = sum(1 for x in retrievals if is_injection_text(x.get("content")))
    out_of_mandate = 0
    for d in delegations:
        if d.get("inherited_authority") == "scoped":
            mandate = (d.get("mandate") or "").lower()
            for c in calls:
                if c.get("agent_id") == d.get("delegate_to"):
                    tool = c.get("tool", "")
                    if tool and tool not in mandate:
                        out_of_mandate += 1
    # Confirmation exists for a tool if the request immediately precedes a call.
    confirmed_calls = sum(1 for c in calls if c.get("human_confirmed") is True)
    missing_gate = sum(1 for c in harmful if c.get("human_confirmed") is None)
    side_effecting = len(harmful)
    return [
        len(spans), len(calls), len(retrievals), len(delegations), len(confirms),
        len(responses), side_effecting, confirmed_calls, missing_gate,
        failed, untrusted, injected, out_of_mandate,
        int(s.get("multi_agent", False)),
    ]

# Train a compact text model and combine it with deterministic safety signals.
VEC = TfidfVectorizer(ngram_range=(1,2), min_df=1, max_features=6000, sublinear_tf=True)
X_text = VEC.fit_transform([session_text(s) for s in TRAIN])
y = [LABELS[s["session_id"]]["root_cause"] for s in TRAIN]
MODEL = LogisticRegression(max_iter=1500, class_weight="balanced")
MODEL.fit(X_text, y)

def deterministic_boost(s, scores):
    spans = s["spans"]
    calls = [x for x in spans if x["kind"] == "tool_call"]
    results = [x for x in spans if x["kind"] == "tool_result"]
    retrievals = [x for x in spans if x["kind"] == "retrieval"]
    delegations = [x for x in spans if x["kind"] == "delegation"]

    injection = any(x.get("trust_domain") != "first_party" and is_injection_text(x.get("content")) for x in retrievals)
    failed = any(x.get("kind") == "tool_result" and x.get("status") not in ("ok", None) for x in spans)
    missing = any(
        ACTION_MAP.get(x.get("tool"), {}).get("side_effect")
        and x.get("human_confirmed") is None
        for x in calls
    )
    scoped = any(x.get("inherited_authority") == "scoped" for x in delegations)
    # Dataset patterns: a scoped delegate followed by a tool not in its mandate is a strong signal.
    out = False
    for d in delegations:
        if d.get("inherited_authority") == "scoped":
            mandate = (d.get("mandate") or "").lower()
            delegate = d.get("delegate_to")
            for c in calls:
                if c.get("agent_id") == delegate and c.get("tool") and c["tool"] not in mandate:
                    out = True

    if injection:
        scores["prompt_injection_via_retrieval"] += 2.2
    if failed:
        scores["tool_api_misresponse"] += 1.7
    if missing:
        scores["missing_confirmation_gate"] += 1.5
    if out:
        scores["delegated_agent_compromise"] += 2.4
    if not any(ACTION_MAP.get(x.get("tool"), {}).get("side_effect") for x in calls):
        scores["no_fault_correct_behaviour"] += 0.8
    return scores

def likely_first_span(s, cause):
    spans = s["spans"]
    calls = [x for x in spans if x["kind"] == "tool_call"]
    retrievals = [x for x in spans if x["kind"] == "retrieval"]
    results = [x for x in spans if x["kind"] == "tool_result"]
    delegations = [x for x in spans if x["kind"] == "delegation"]

    if cause == "prompt_injection_via_retrieval":
        for x in retrievals:
            if x.get("trust_domain") != "first_party" and is_injection_text(x.get("content")):
                return x["span_id"]
    if cause == "tool_api_misresponse":
        for x in results:
            if x.get("status") not in ("ok", None):
                # Usually the tool call immediately before the failed result is the causal action.
                idx = spans.index(x)
                if idx > 0 and spans[idx-1]["kind"] == "tool_call":
                    return spans[idx-1]["span_id"]
                return x["span_id"]
    if cause == "delegated_agent_compromise":
        for d in delegations:
            if d.get("inherited_authority") == "scoped":
                return d["span_id"]
    if cause == "missing_confirmation_gate":
        for x in calls:
            if ACTION_MAP.get(x.get("tool"), {}).get("side_effect") and x.get("human_confirmed") is None:
                return x["span_id"]
    if cause == "stale_state_assumption":
        for x in calls:
            if ACTION_MAP.get(x.get("tool"), {}).get("side_effect"):
                return x["span_id"]
    if cause in ("user_instruction_ambiguity", "agent_planning_error"):
        for x in calls:
            if ACTION_MAP.get(x.get("tool"), {}).get("side_effect"):
                return x["span_id"]
    return None

def analyze(s):
    scores = {c: float(p) for c, p in zip(MODEL.classes_, MODEL.predict_proba(VEC.transform([session_text(s)]))[0])}
    scores = deterministic_boost(s, scores)
    total = sum(scores.values()) or 1
    probs = {c: v / total for c, v in scores.items()}
    cause = max(probs, key=probs.get)
    integrity = verify_session(s)
    first = likely_first_span(s, cause)
    # Extra investigation signals
    suspicious_retrievals = [
        x for x in s["spans"]
        if x["kind"] == "retrieval" and x.get("trust_domain") != "first_party" and is_injection_text(x.get("content"))
    ]
    unconfirmed = [
        x for x in s["spans"]
        if x["kind"] == "tool_call"
        and ACTION_MAP.get(x.get("tool"), {}).get("side_effect")
        and x.get("human_confirmed") is None
    ]
    failed_results = [x for x in s["spans"] if x["kind"] == "tool_result" and x.get("status") not in ("ok", None)]
    return {
        "session_id": s["session_id"],
        "user_goal": s["user_goal"],
        "multi_agent": s.get("multi_agent", False),
        "agents": s.get("agents", []),
        "prediction": cause,
        "prediction_label": CLASS_LABELS[cause],
        "confidence": round(probs[cause], 3),
        "probabilities": {k: round(v, 3) for k, v in sorted(probs.items(), key=lambda kv: -kv[1])},
        "first_cause_span": first,
        "integrity": integrity,
        "suspicious_retrievals": [x["span_id"] for x in suspicious_retrievals],
        "unconfirmed_side_effects": [x["span_id"] for x in unconfirmed],
        "failed_results": [x["span_id"] for x in failed_results],
    }
app = Flask(__name__)

CACHE = {}

def get_analysis(sid):
    if sid not in CACHE:
        s = next((x for x in EVAL if x["session_id"] == sid), None)
        if not s:
            return None
        CACHE[sid] = analyze(s)
    return CACHE[sid]

@app.route("/")
def index():
    verified = [verify_session(s) for s in EVAL]
    bad = sum(not x["ok"] for x in verified)
    side_effects = sum(
        1 for s in EVAL for sp in s["spans"]
        if sp["kind"] == "tool_call" and ACTION_MAP.get(sp.get("tool"), {}).get("side_effect")
    )
    return render_template("index.html", stats={
        "train": len(TRAIN), "eval": len(EVAL), "tools": len(ACTIONS),
        "bad_chains": bad, "side_effects": side_effects
    })

@app.route("/api/sessions")
def sessions():
    q = request.args.get("q", "").lower().strip()
    rows = []
    for s in EVAL:
        if q and q not in s["session_id"].lower() and q not in s["user_goal"].lower():
            continue
        a = get_analysis(s["session_id"])
        rows.append({
            "session_id": s["session_id"], "goal": s["user_goal"],
            "prediction": a["prediction_label"], "confidence": a["confidence"],
            "integrity": a["integrity"]["ok"],
        })
    return jsonify(rows)

@app.route("/api/session/<sid>")
def session_detail(sid):
    s = next((x for x in EVAL if x["session_id"] == sid), None)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    a = get_analysis(sid)
    spans = []
    for sp in s["spans"]:
        row = dict(sp)
        row["action_meta"] = ACTION_MAP.get(sp.get("tool"), {}) if sp.get("tool") else None
        row["is_predicted_cause"] = sp["span_id"] == a["first_cause_span"]
        spans.append(row)
    return jsonify({"session": s, "analysis": a, "spans": spans})

@app.route("/api/verify")
def verify_all():
    bad = []
    for s in EVAL:
        r = verify_session(s)
        if not r["ok"]:
            bad.append({"session_id": s["session_id"], **r})
    return jsonify({"bad_count": len(bad), "bad": bad})

@app.route("/api/policy")
def policy():
    # Risk-aware confirmation policy: confirm side-effecting actions with high
    # expected loss, sensitive data or high blast radius. Read-only actions pass.
    rows = []
    confirmations = 0
    loss = 0
    for s in EVAL:
        confirmed = []
        for sp in s["spans"]:
            if sp["kind"] != "tool_call":
                continue
            meta = ACTION_MAP.get(sp.get("tool"), {})
            risk = meta.get("expected_loss_if_wrong_inr", 0)
            score = risk + meta.get("blast_radius", 0) * 15000 + meta.get("data_sensitivity", 0) * 8000
            should = bool(meta.get("side_effect") and score >= 12000)
            if should:
                confirmations += 1
                confirmed.append(sp["span_id"])
        rows.append({"session_id": s["session_id"], "confirmations": confirmed})
    friction = confirmations * COSTS["confirm_friction_inr"]
    # Since answer key is hidden, we report policy mechanics rather than pretending
    # to know unprevented loss on evaluation.
    return jsonify({
        "confirmation_count": confirmations,
        "confirmation_rate": round(confirmations / max(sum(len([sp for sp in s["spans"] if sp["kind"] == "tool_call" and ACTION_MAP.get(sp.get("tool"), {}).get("side_effect")]) for s in EVAL),1), 3),
        "friction_inr": friction,
        "policy": rows
    })

@app.route("/api/train")
def train_stats():
    return jsonify({
        "classes": Counter(y),
        "class_labels": CLASS_LABELS,
        "training_sessions": len(TRAIN)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
