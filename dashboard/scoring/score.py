"""AI RaidMeter - Layer 4 Three-Part Scoring.

Composite = 0.45*Value + 0.35*Delta + 0.20*Green (weights in
scoring/weights.json, config-driven). Delta and Green compare a
session against its own historical baseline (baseline_ref) -- you
only compete with your past self. Green is an estimated/proxy figure,
never presented as precise carbon accounting.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "detectors"))
sys.path.insert(0, os.path.join(BASE, "scoring"))
import detector
import clinical

OUTCOME_RANK = {"merged": 2, "rejected": 0}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def improvement_rate(before_val, after_val):
    """Fraction reduced from before to after; 0 if no improvement."""
    if before_val <= 0:
        return 0.0
    return max(0.0, (before_val - after_val) / float(before_val))


def current_value(session, fired, criteria, weights):
    """Outcome base value minus waste penalty, clamped to [0, max]."""
    vcfg = weights["value"]
    base = vcfg["outcome_base"].get(session.get("pr_status"), vcfg["outcome_base"]["default"])
    ws = clinical.waste_score(fired, session, criteria)
    val = base - vcfg["waste_penalty_per_point"] * ws
    return max(0, min(vcfg["max"], val))


def delta_score(before, after, before_fired, after_fired, criteria, weights):
    """Weighted improvement of tokens, time, waste pattern, and outcome."""
    d = weights["delta"]
    tok = improvement_rate(before["total_tokens"], after["total_tokens"])
    tim = improvement_rate(before["duration_min"], after["duration_min"])
    bws = clinical.waste_score(before_fired, before, criteria)
    aws = clinical.waste_score(after_fired, after, criteria)
    wst = improvement_rate(bws, aws)
    br = OUTCOME_RANK.get(before.get("pr_status"), 1)
    ar = OUTCOME_RANK.get(after.get("pr_status"), 1)
    out = 1.0 if ar > br else 0.0
    return 100 * (d["token"] * tok + d["time"] * tim + d["waste"] * wst + d["outcome"] * out)


def green_score(before, after, weights):
    """Estimated/proxy green-efficiency score. NOT precise carbon accounting."""
    g = weights["green"]
    tok = improvement_rate(before["total_tokens"], after["total_tokens"])
    tim = improvement_rate(before["duration_min"], after["duration_min"])
    proxy = (tok + tim) / 2.0
    return 100 * (g["token_saved"] * tok + g["time_saved"] * tim + g["compute_proxy"] * proxy)


def score_session(session, by_id, rules, criteria, weights):
    fired = detector.detect(session, rules)
    value = current_value(session, fired, criteria, weights)
    delta = green = 0.0
    base_id = session.get("baseline_ref")
    if base_id and base_id in by_id:
        before = by_id[base_id]
        before_fired = detector.detect(before, rules)
        delta = delta_score(before, session, before_fired, fired, criteria, weights)
        green = green_score(before, session, weights)
    c = weights["composite"]
    total = c["value"] * value + c["delta"] * delta + c["green"] * green
    return {"value": round(value, 1), "delta": round(delta, 1),
            "green": round(green, 1), "total": round(total, 1)}


def score_all():
    rules = load_json(os.path.join(BASE, "detectors", "rules.json"))
    criteria = load_json(os.path.join(BASE, "scoring", "criteria.json"))
    weights = load_json(os.path.join(BASE, "scoring", "weights.json"))
    sessions = load_json(os.path.join(BASE, "data", "sessions.json"))["sessions"]
    by_id = {s["id"]: s for s in sessions}
    return {s["id"]: score_session(s, by_id, rules, criteria, weights) for s in sessions}


if __name__ == "__main__":
    for sid, r in score_all().items():
        print("=== %s ===" % sid)
        print("  Value=%.1f  Delta=%.1f  Green=%.1f  =>  TOTAL=%.1f"
              % (r["value"], r["delta"], r["green"], r["total"]))
