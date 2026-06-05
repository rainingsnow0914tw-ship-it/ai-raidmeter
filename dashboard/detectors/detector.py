"""AI RaidMeter - Seven Sins Signal Detector.

Config-driven anti-pattern detection. Reads detection rules from
detectors/rules.json and runs them against normalized session traces.
Pure detection only: emits which signals fire per session. No scoring
or judgment here (that belongs to Layer 3 / scoring).
"""
import json
import os

# Comparison operators referenced by rules.json condition "op" field.
OPS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def eval_condition(session, cond):
    """One condition against one session. Missing field = not met."""
    if cond["field"] not in session:
        return False
    op = OPS.get(cond["op"])
    if op is None:
        return False
    return op(session[cond["field"]], cond["value"])


def detect(session, rules):
    """Return the list of fired signals for a single session."""
    fired = []
    for rule in rules["rules"]:
        if all(eval_condition(session, c) for c in rule["conditions"]):
            fired.append({
                "rule_id": rule["rule_id"],
                "display": rule["display"],
                "severity": rule["severity"],
                "intervention": rule["intervention"],
            })
    return fired


def detect_all(sessions_path=None, rules_path=None):
    """Run detection over every session. Returns {session_id: [signals]}."""
    sessions_path = sessions_path or os.path.join(BASE, "data", "sessions.json")
    rules_path = rules_path or os.path.join(BASE, "detectors", "rules.json")
    sessions = load_json(sessions_path)["sessions"]
    rules = load_json(rules_path)
    return {s["id"]: detect(s, rules) for s in sessions}


if __name__ == "__main__":
    for sid, fired in detect_all().items():
        print("\n=== %s ===" % sid)
        if not fired:
            print("  (no anti-pattern signals)")
        for f in fired:
            print("  [%s] %s %s" % (f["severity"].upper(), f["rule_id"], f["display"]))
            print("        -> %s" % f["intervention"])
