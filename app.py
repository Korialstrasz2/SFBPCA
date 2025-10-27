"""Flask application for Salesforce relationship analysis."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from services.alert_service import AlertService
from services.import_service import ImportService
from storage.data_store import DataStore

app = Flask(__name__)

_data_store = DataStore()
_import_service = ImportService(_data_store)
_alert_service = AlertService(_data_store)


@app.route("/")
def index() -> str:
    return render_template("index.html", alerts=AlertService.DEFAULT_ALERTS)


@app.route("/api/import", methods=["POST"])
def import_data():
    files = {name: request.files.get(name) for name in ImportService.REQUIRED_FILES if request.files.get(name)}
    try:
        counts = _import_service.import_data(files)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"status": "success", "counts": counts})


@app.route("/api/alerts", methods=["POST"])
def evaluate_alerts():
    payload = request.get_json(silent=True) or {}
    alerts = payload.get("alerts")
    results = _alert_service.evaluate(alerts)
    return jsonify({"alerts": results})


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=5000, debug=True)
