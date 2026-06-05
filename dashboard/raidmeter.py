"""AI RaidMeter - main orchestrator.

Runs the full pipeline over every session and writes a coaching
report (data/report.json) the dashboard renders. One pass per session:
detect signals -> clinical level -> three-part score -> assemble.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "detectors"))
sys.path.insert(0, os.path.join(BASE, "scoring"))
import detector
import clinical
import score as scoring


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_report():
    rules = load_json(os.path.join(BASE, "detectors", "rules.json"))
    criteria = load_json(os.path.join(BASE, "scoring", "criteria.json"))
    weights = load_json(os.path.join(BASE, "scoring", "weights.json"))
    sessions = load_json(os.path.join(BASE, "data", "sessions.json"))["sessions"]
    by_id = {s["id"]: s for s in sessions}

    report = {"sessions": []}
    for s in sessions:
        fired = detector.detect(s, rules)
        verdict = clinical.classify(fired, s, criteria)
        sc = scoring.score_session(s, by_id, rules, criteria, weights)
        report["sessions"].append({
            "id": s["id"],
            "developer_id": s.get("developer_id"),
            "task": s.get("task"),
            "difficulty": s.get("difficulty"),
            "metrics": {
                "total_tokens": s.get("total_tokens"),
                "duration_min": s.get("duration_min"),
                "pr_status": s.get("pr_status"),
            },
            "signals": fired,
            "level": verdict["level"],
            "level_label": verdict["label"],
            "waste_score": verdict["score"],
            "scores": sc,
            "baseline_ref": s.get("baseline_ref"),
        })
    return report


if __name__ == "__main__":
    report = build_report()
    out = os.path.join(BASE, "data", "report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("wrote %s (%d sessions)" % (out, len(report["sessions"])))
    for s in report["sessions"]:
        print("  %s: L%d %s | total=%.1f | %d signals"
              % (s["id"], s["level"], s["level_label"],
                 s["scores"]["total"], len(s["signals"])))
