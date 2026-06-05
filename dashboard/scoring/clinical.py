"""AI RaidMeter - Layer 3 Clinical Waste-Tendency Judgment.

Turns fired anti-pattern signals into a waste level (L0-L3) using a
multi-criteria, config-driven rubric (scoring/criteria.json): a
severity-weighted score, justification credits for legitimate
exceptions, and an L3 safety guard so a high score with a good
outcome is not over-penalized. Deliberately NOT single-signal verdicts.
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def waste_score(fired, session, criteria):
    """Severity-weighted signal score minus justification credits (clamped >=0)."""
    weights = criteria["severity_weights"]
    score = sum(weights.get(sig["severity"], 0) for sig in fired)
    credits = criteria["justification_credits"]
    for j in session.get("justifications", []):
        score += credits.get(j, 0)
    return max(0, score)


def classify(fired, session, criteria):
    """Return {score, level, label}, applying the L3 outcome guard."""
    score = waste_score(fired, session, criteria)
    level_info = next(l for l in criteria["levels"] if score <= l["max"])
    level, label = level_info["level"], level_info["label"]
    # L3 safety guard: do not assign the worst level if the outcome was fine.
    if level == 3:
        bad = criteria.get("level3_guard", {}).get("bad_outcomes", [])
        if session.get("pr_status") not in bad:
            guarded = next(l for l in criteria["levels"] if l["level"] == 2)
            level, label = guarded["level"], guarded["label"] + " (L3 guarded)"
    return {"score": score, "level": level, "label": label}


def classify_all(sessions_path=None, criteria_path=None):
    """Full pipeline: detect signals then classify each session."""
    import sys
    sys.path.insert(0, os.path.join(BASE, "detectors"))
    import detector
    sessions_path = sessions_path or os.path.join(BASE, "data", "sessions.json")
    criteria_path = criteria_path or os.path.join(BASE, "scoring", "criteria.json")
    criteria = load_json(criteria_path)
    rules = load_json(os.path.join(BASE, "detectors", "rules.json"))
    sessions = load_json(sessions_path)["sessions"]
    out = {}
    for s in sessions:
        fired = detector.detect(s, rules)
        out[s["id"]] = classify(fired, s, criteria)
    return out


if __name__ == "__main__":
    for sid, r in classify_all().items():
        print("=== %s ===" % sid)
        print("  score=%d  ->  Level %d: %s" % (r["score"], r["level"], r["label"]))
