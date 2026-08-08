import streamlit as st
import json
from pathlib import Path

DATA_DIR = Path("data")

st.set_page_config(page_title="Flight Recorder Investigation", layout="wide")
st.title("🕵️ PS-I3 Flight Recorder – Investigation Interface")

# -----------------------------
# Load data
# -----------------------------
@st.cache_data
def load_data():
    def load_jsonl(path):
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    eval_sessions = load_jsonl(DATA_DIR / "traces" / "eval.jsonl")
    sessions = {s["session_id"]: s for s in eval_sessions}

    with open("predictions.json", "r", encoding="utf-8") as f:
        preds = {p["session_id"]: p for p in json.load(f)}

    with open("policy.json", "r", encoding="utf-8") as f:
        policy = json.load(f)

    return sessions, preds, policy

sessions, predictions, policy = load_data()

# -----------------------------
# Sidebar – select session
# -----------------------------
st.sidebar.header("Select Incident")
session_ids = sorted(sessions.keys())
selected_id = st.sidebar.selectbox("Session ID", session_ids)

session = sessions[selected_id]
pred = predictions.get(selected_id, {})
pol = policy.get(selected_id, {})

# -----------------------------
# Main view
# -----------------------------
st.header(f"Session: `{selected_id}`")

col1, col2, col3 = st.columns(3)
col1.metric("Predicted Root Cause", pred.get("root_cause", "—"))
col2.metric("First Cause Span", pred.get("first_cause_span", "—"))
col3.metric("User Goal", session.get("user_goal", "—")[:60] + "...")

st.subheader("Outcome")
st.write(session.get("outcome", {}))

st.subheader("Timeline of Spans")

for sp in session.get("spans", []):
    span_id = sp["span_id"]
    kind = sp.get("kind", "")
    agent = sp.get("agent_id", "")
    
    # Highlight important spans
    is_first_cause = span_id == pred.get("first_cause_span")
    needs_confirm = pol.get(span_id, False)
    
    if is_first_cause:
        st.markdown(f"### 🔴 **{span_id}** — `{kind}` (PREDICTED FIRST CAUSE)")
    elif needs_confirm:
        st.markdown(f"### 🟡 **{span_id}** — `{kind}` (would require confirmation)")
    else:
        st.markdown(f"**{span_id}** — `{kind}`")
    
    st.caption(f"Agent: {agent} | Time: {sp.get('ts', '')}")
    
    # Show content if useful
    content = sp.get("content")
    if content:
        if isinstance(content, (dict, list)):
            st.json(content, expanded=False)
        else:
            st.text(str(content)[:500])
    
    st.divider()

st.sidebar.success("Investigation interface ready")