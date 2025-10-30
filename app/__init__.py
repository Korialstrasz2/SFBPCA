from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from typing import Dict

from app.data.data_store import DATA_STORE
from app.services.alert_engine import AlertEngine
from app.services.importer import CSVImporter


def create_app() -> Flask:
    app = Flask(__name__)

    importer = CSVImporter(DATA_STORE)
    alert_engine = AlertEngine(DATA_STORE)

    @app.get("/")
    def index():
        return render_template("index.html", entities=list(importer.ENTITY_FIELDS.keys()))

    @app.post("/import")
    def import_data():
        payload = {key: request.files.get(key) for key in importer.ENTITY_FIELDS}
        summary = importer.import_payload(payload)
        return jsonify({
            "message": "Import completed",
            "summary": summary,
        })

    @app.get("/alerts")
    def get_alerts():
        alerts = alert_engine.build_alerts()
        return jsonify({"alerts": alerts})

    @app.get("/alerts/config")
    def get_alert_configuration():
        return jsonify({"rules": alert_engine.get_rule_configuration()})

    @app.patch("/alerts/config")
    def update_alert_configuration():
        payload = request.get_json(silent=True) or {}
        rules_payload = payload.get("rules", [])
        if not isinstance(rules_payload, list):
            return jsonify({"error": "Payload must include a 'rules' list."}), 400

        updates: Dict[str, bool] = {}
        invalid_entries = []
        for entry in rules_payload:
            if not isinstance(entry, dict):
                invalid_entries.append("Invalid rule entry")
                continue
            rule_id = entry.get("id")
            enabled = entry.get("enabled")
            if not isinstance(rule_id, str) or not isinstance(enabled, bool):
                invalid_entries.append(rule_id or "unknown")
                continue
            updates[rule_id] = enabled

        if invalid_entries:
            return (
                jsonify({"error": "Invalid rule configuration entries.", "details": invalid_entries}),
                400,
            )

        try:
            alert_engine.update_rule_configuration(updates)
        except ValueError as exc:  # pragma: no cover - defensive programming
            return jsonify({"error": str(exc)}), 400

        return jsonify({"rules": alert_engine.get_rule_configuration()})

    @app.post("/alerts/config/reset")
    def reset_alert_configuration():
        alert_engine.reset_rule_configuration()
        return jsonify({"rules": alert_engine.get_rule_configuration()})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
