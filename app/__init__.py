from __future__ import annotations

from flask import Flask, jsonify, render_template, request

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

    @app.get("/alert-definitions")
    def list_alert_definitions():
        return jsonify({"alerts": alert_engine.get_definitions()})

    @app.post("/alert-definitions")
    def save_alert_definitions():
        payload = request.get_json(silent=True) or {}
        alerts = payload.get("alerts")
        if not isinstance(alerts, list):
            return jsonify({"error": "Payload must include an 'alerts' list"}), 400
        try:
            alert_engine.save_definitions(alerts)
        except Exception as exc:  # pragma: no cover - returned to the UI
            return jsonify({"error": str(exc)}), 400
        return jsonify({"alerts": alert_engine.get_definitions()})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
