#!/usr/bin/env python3
"""
PS-I3 participant tools.

  python tools.py verify traces/eval.jsonl
      -> reports sessions whose hash chain does not verify (tampered logs)

  python tools.py score-policy my_policy.json
      -> scores a confirmation policy against the cost model.
         Requires the answer key, so this path runs for judges only. Teams can
         still self-check by scoring against train_labels.json:
         score("my_policy.json", "traces/train.jsonl", "train_labels.json")

A policy file is: {"session_id": {"span_id": true/false, ...}, ...}
where true = "this action would have been sent to a human for confirmation".
"""
import json, sys, hashlib


def h(prev, payload):
    return hashlib.sha256((prev + json.dumps(payload, sort_keys=True)).encode()).hexdigest()


def verify(path):
    bad = []
    for line in open(path):
        s = json.loads(line)
        prev = "0" * 64
        for sp in s["spans"]:
            expect = h(prev, {k: v for k, v in sp.items() if k != "hash"})
            if sp["prev_hash"] != prev or sp["hash"] != expect:
                bad.append((s["session_id"], sp["span_id"]))
                break
            prev = sp["hash"]
    print(f"{len(bad)} sessions failed chain verification")
    for sid, span in bad:
        print(f"  {sid}: first bad span {span}")
    return bad


def score(policy_path, traces="traces/eval.jsonl", key="../answer_key/eval_labels.json",
          costs="policy_costs.json"):
    pol = json.load(open(policy_path))
    friction = json.load(open(costs))["confirm_friction_inr"]
    keys = {k["session_id"]: k for k in json.load(open(key))}
    n_conf, loss = 0, 0
    for line in open(traces):
        s = json.loads(line)
        p = pol.get(s["session_id"], {})
        n_conf += sum(1 for v in p.values() if v)
        k = keys[s["session_id"]]
        if k["harmful_action_span"] and k["should_have_confirmed"]:
            if not p.get(k["harmful_action_span"], False):
                loss += k["realised_loss_inr"]
    total = n_conf * friction + loss
    print(f"confirmations={n_conf} friction={n_conf*friction} unprevented_loss={loss} TOTAL={total}")
    return total


if __name__ == "__main__":
    if sys.argv[1] == "verify":
        verify(sys.argv[2])
    else:
        score(sys.argv[2])
