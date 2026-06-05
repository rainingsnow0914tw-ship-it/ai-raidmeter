"""agent/preflight.py - Layer 0 Pre-flight Guardrail.

BEFORE an AI-coding task starts, predict which of the seven sins this
developer is most likely to fall into -- based on THEIR OWN past
sessions -- and hand back a flight plan of pre-set guardrails.

Clinical decision support: warn about interactions before writing the
prescription, not an autopsy after. Gemini (Flash) on Vertex,
config-driven (same env / model as coach.py).
"""
import os
import json

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "ai-raidmeter-2026")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
MODEL_ID = os.environ.get("RAIDMETER_MODEL", "gemini-3.5-flash")

_client = None


def _gem():
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    return _client


PREFLIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "predicted_risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sin": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["sin", "why"],
            },
        },
        "guardrails": {"type": "array", "items": {"type": "string"}},
        "flight_note": {"type": "string"},
    },
    "required": ["task", "predicted_risks", "guardrails", "flight_note"],
}


def _history_summary(developer_id, past_sessions):
    """Which sins has this developer fired before, and how often."""
    sins = {}
    for s in past_sessions or []:
        if s.get("developer_id") != developer_id:
            continue
        for sig in s.get("signals", []):
            sins[sig["display"]] = sins.get(sig["display"], 0) + 1
    if not sins:
        return "no prior anti-patterns on record (cold start)"
    return ", ".join("%s x%d" % (k, v) for k, v in sins.items())


def preflight(task, difficulty="medium", developer_id="dev-001", past_sessions=None):
    """Return a pre-flight guardrail plan for an upcoming task."""
    history = _history_summary(developer_id, past_sessions)
    instruction = (
        "You are AI RaidMeter's pre-flight guardrail. BEFORE the developer "
        "starts the task below, give a flight plan: predict which of the seven "
        "AI-coding sins (full-file devotion, local loop, blind retry, context "
        "hoarding, sticky command) they are most likely to fall into, based on "
        "THEIR OWN history, and prescribe concrete pre-set guardrails to avoid "
        "them. Think like a clinician giving decision support before the "
        "prescription, not an autopsy after.\n\n"
        "Upcoming task: %s (difficulty: %s)\n"
        "This developer's past anti-patterns: %s\n\n"
        "Return JSON: task, predicted_risks (each with sin + why), guardrails "
        "(concrete pre-set rules), flight_note (one clinical one-liner). Use polished, grammatically correct English." % (
            task, difficulty, history)
    )
    resp = _gem().models.generate_content(
        model=MODEL_ID,
        contents=[instruction],
        config=types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=PREFLIGHT_SCHEMA,
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
    plan = preflight("similar cloud deployment bugfix", "high", "dev-001",
                     report["sessions"])
    print(json.dumps(plan, indent=2, ensure_ascii=False))
