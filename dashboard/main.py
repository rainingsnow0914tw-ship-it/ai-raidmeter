"""AI RaidMeter - Cloud Run web entry.

Serves the dashboard (static/index.html) and the coaching report.
The report is generated on demand by the orchestrator so the page
always reflects the current sessions/rules/criteria/weights config.
"""
import os
import sys
from flask import Flask, jsonify, request, send_from_directory

import raidmeter

app = Flask(__name__, static_folder="static")
HERE = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/data/report.json")
def report_data():
    """Path the dashboard fetches (../data/report.json from /)."""
    return jsonify(raidmeter.build_report())


@app.route("/api/report")
def api_report():
    """Clean JSON API for the same coaching report."""
    return jsonify(raidmeter.build_report())


@app.route("/api/coach")
def api_coach():
    sid = request.args.get("session_id", "")
    report = raidmeter.build_report()
    session = next((s for s in report["sessions"] if s["id"] == sid), None)
    if session is None:
        return jsonify({"error": "session not found: %s" % sid}), 404
    try:
        sys.path.insert(0, os.path.join(HERE, "agent"))
        import coach
        return jsonify(coach.coach_session(session))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/live")
def api_live():
    try:
        sys.path.insert(0, os.path.join(HERE, "data"))
        sys.path.insert(0, os.path.join(HERE, "detectors"))
        import arize_adapter
        import detector
        rules = detector.load_json(os.path.join(HERE, "detectors", "rules.json"))
        sessions = arize_adapter.fetch_live_sessions(limit=10)
        for s in sessions:
            s["signals"] = detector.detect(s, rules)
        return jsonify({"sessions": sessions})
    except Exception as e:
        return jsonify({"error": str(e), "sessions": []})


@app.route("/api/preflight")
def api_preflight():
    task = request.args.get("task", "cloud_deployment_bugfix")
    difficulty = request.args.get("difficulty", "high")
    developer_id = request.args.get("developer_id", "dev-001")
    report = raidmeter.build_report()
    try:
        sys.path.insert(0, os.path.join(HERE, "agent"))
        import preflight as pf
        return jsonify(pf.preflight(task, difficulty, developer_id, report["sessions"]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
