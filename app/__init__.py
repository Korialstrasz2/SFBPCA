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

    @app.get("/alerts/config")
    def get_alert_configuration():
        return jsonify({"config": alert_engine.get_config()})

    @app.post("/alerts/config")
    def update_alert_configuration():
        payload = request.get_json(silent=True) or {}
        config_entries = payload.get("config", [])
        if not isinstance(config_entries, list):
            return jsonify({"error": "Config payload must be a list"}), 400
        updated = alert_engine.update_config(config_entries)
        return jsonify({"config": updated})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
