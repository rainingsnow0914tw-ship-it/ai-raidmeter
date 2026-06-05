"""data/arize_adapter.py - turn real Arize/Phoenix traces into RaidMeter sessions.

Reads LLM spans from the Phoenix project via the Phoenix client and maps
the real OpenInference attributes (token counts, latency) onto the
normalized session schema, so the SAME detector/scoring that runs on the
mock dataset also runs on real Arize traces. This is the live half of the
demo: RaidMeter eats its own coaching traces (dogfooding).

Auth / endpoint come from env (PHOENIX_COLLECTOR_ENDPOINT, PHOENIX_API_KEY),
same secret file as the rest of the app. Nothing hard-coded.
"""
import os
from phoenix.client import Client

PROJECT = os.environ.get("PHOENIX_PROJECT", "ai-raidmeter")


def _int(v):
    """Safe int from a possibly-NaN/None pandas cell."""
    try:
        f = float(v)
        return 0 if f != f else int(f)  # f != f detects NaN
    except (TypeError, ValueError):
        return 0


def _duration_min(start, end):
    try:
        return round((end - start).total_seconds() / 60.0, 2)
    except Exception:
        return 0.0


def _is_llm(row):
    return (row.get("span_kind") == "LLM"
            or row.get("attributes.openinference.span.kind") == "LLM")


def fetch_live_sessions(project_identifier=None, limit=50):
    """Read real LLM spans from Phoenix and map them to normalized sessions.

    A single LLM span has no coding-workflow signals (full-file reads,
    local loops, etc.), so those map to safe defaults -- a clean live call
    should score L0. The point is that real token/latency flow through the
    exact same pipeline as the mock sessions.
    """
    client = Client()
    df = client.spans.get_spans_dataframe(
        project_identifier=project_identifier or PROJECT, limit=limit
    )
    sessions = []
    for _, row in df.iterrows():
        if not _is_llm(row):
            continue
        span_id = str(row.get("context.span_id") or "")[:8]
        sessions.append({
            "id": "live-" + span_id,
            "developer_id": "live-trace",
            "task": str(row.get("name") or "gemini_call"),
            "difficulty": "n/a",
            "total_tokens": _int(row.get("attributes.llm.token_count.total")),
            "duration_min": _duration_min(row.get("start_time"), row.get("end_time")),
            "context_tokens_peak": _int(row.get("attributes.llm.token_count.prompt")),
            "full_file_read_ratio": 0.0,
            "local_runs": 0,
            "cloud_deploys": 0,
            "brute_retries": 0,
            "diagnosis_steps": 0,
            "multi_command_blocks": 0,
            "context_cleared": True,
            "pr_status": "n/a",
            "baseline_ref": None,
            "model": row.get("attributes.llm.model_name"),
            "source": "arize_phoenix",
        })
    return sessions


if __name__ == "__main__":
    import sys
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(BASE, "detectors"))
    import detector

    rules = detector.load_json(os.path.join(BASE, "detectors", "rules.json"))
    sessions = fetch_live_sessions()
    print("fetched %d live session(s) from Arize Phoenix\n" % len(sessions))
    for s in sessions:
        fired = detector.detect(s, rules)
        print("=== %s ===" % s["id"])
        print("  task=%s | model=%s" % (s["task"], s.get("model")))
        print("  REAL tokens=%d | duration=%.2f min" % (
            s["total_tokens"], s["duration_min"]))
        print("  anti-pattern signals fired: %d" % len(fired))
        for f in fired:
            print("    [%s] %s" % (f["severity"].upper(), f["display"]))
        print("")
