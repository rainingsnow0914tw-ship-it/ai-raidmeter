"""AI RaidMeter - Gemini coaching agent (Layer 5).

Turns a scored session into a personal, clinical-style coaching report
using Gemini 3.1 Pro on Vertex AI (same setup as the 小寶 family backend:
google-genai SDK, vertexai=True, location="global", thinking_level="low").

Medical framing (diagnosis / prescription) reflects the clinical
decision-support angle. Config-driven: model / project / location come
from env so nothing is hard-coded.
"""
import os
import json
from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "ai-raidmeter-2026")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
MODEL_ID = os.environ.get("RAIDMETER_MODEL", "gemini-3.1-pro-preview")

_client = None


def _gem():
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    return _client


COACH_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "diagnosis": {"type": "string"},
        "prescriptions": {"type": "array", "items": {"type": "string"}},
        "encouragement": {"type": "string"},
    },
    "required": ["headline", "diagnosis", "prescriptions", "encouragement"],
}


def _build_prompt(session):
    signals = "; ".join(
        "%s [%s]: %s" % (s["display"], s["severity"], s["intervention"])
        for s in session.get("signals", [])
    ) or "none (clean run)"
    sc = session.get("scores", {})
    m = session.get("metrics", {})
    return (
        "You are AI RaidMeter, a green-coding coach that reviews an "
        "AI-assisted engineering session like a clinician: multi-criteria, "
        "never a single-signal verdict, and you compare the developer only "
        "with their own past self.\n\n"
        "Session: %s (task: %s, difficulty: %s)\n"
        "Waste level: L%s %s (waste score %s)\n"
        "Tokens: %s | Duration: %s min | PR: %s\n"
        "Anti-pattern signals fired: %s\n"
        "Scores -> Value %.1f, Delta %.1f, Green %.1f, Total %.1f\n\n"
        "Write a short, warm but precise coaching report with a medical "
        "framing:\n"
        "- headline: one line.\n"
        "- diagnosis: why this waste level, in plain language.\n"
        "- prescriptions: concrete next-session actions tied to the fired "
        "signals (if the run is clean, give light reinforcement instead).\n"
        "- encouragement: frame any improvement against the developer's own "
        "baseline, not against other people.\n"
        "Use polished, grammatically correct English. Keep each field tight. Return JSON." % (
            session.get("id"), session.get("task"), session.get("difficulty"),
            session.get("level"), session.get("level_label"),
            session.get("waste_score", 0),
            m.get("total_tokens"), m.get("duration_min"), m.get("pr_status"),
            signals,
            sc.get("value", 0), sc.get("delta", 0),
            sc.get("green", 0), sc.get("total", 0),
        )
    )


def coach_session(session):
    """Generate a clinical-style coaching report for one scored session."""
    resp = _gem().models.generate_content(
        model=MODEL_ID,
        contents=[_build_prompt(session)],
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=4096,
            response_mime_type="application/json",
            response_schema=COACH_SCHEMA,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return json.loads(resp.text or "{}")


if __name__ == "__main__":
    import sys
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, BASE)
    import raidmeter

    report = raidmeter.build_report()
    for s in report["sessions"]:
        print("\n=== %s (L%s, total %.1f) ===" % (
            s["id"], s["level"], s["scores"]["total"]))
        c = coach_session(s)
        print("HEADLINE:    ", c.get("headline"))
        print("DIAGNOSIS:   ", c.get("diagnosis"))
        print("PRESCRIPTIONS:")
        for rx in c.get("prescriptions", []):
            print("   -", rx)
        print("ENCOURAGEMENT:", c.get("encouragement"))
