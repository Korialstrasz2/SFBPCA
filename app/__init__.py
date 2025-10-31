from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from app.data.alert_config_store import AlertConfigStore
from app.data.data_store import DATA_STORE
from app.services.alert_engine import AlertEngine
from app.services.importer import CSVImporter


def create_app() -> Flask:
    app = Flask(__name__)

    importer = CSVImporter(DATA_STORE)
    config_store = AlertConfigStore()
    alert_engine = AlertEngine(DATA_STORE, config_store)

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

    @app.get("/alert-configs")
    def list_alert_configs():
        configs = config_store.list_configs()
        available_logic = alert_engine.list_available_logic()
        return jsonify({
            "configs": configs,
            "available_logic": available_logic,
        })

    @app.post("/alert-configs")
    def create_alert_config():
        payload = request.get_json(force=True) or {}
        logic_id = payload.get("logic_id")
        if not logic_id or not alert_engine.is_valid_logic(logic_id):
            return jsonify({"message": "Unknown logic_id"}), 400
        try:
            normalized = _normalize_payload(payload)
            config = config_store.add_config(normalized)
        except ValueError as error:
            return jsonify({"message": str(error)}), 400
        return jsonify({"config": config}), 201

    @app.put("/alert-configs/<config_id>")
    def update_alert_config(config_id: str):
        payload = request.get_json(force=True) or {}
        logic_id = payload.get("logic_id")
        if logic_id and not alert_engine.is_valid_logic(logic_id):
            return jsonify({"message": "Unknown logic_id"}), 400
        try:
            normalized = _normalize_payload(payload)
            config = config_store.update_config(config_id, normalized)
        except ValueError as error:
            return jsonify({"message": str(error)}), 400
        except KeyError:
            return jsonify({"message": "Alert configuration not found"}), 404
        return jsonify({"config": config})

    @app.delete("/alert-configs/<config_id>")
    def delete_alert_config(config_id: str):
        try:
            config_store.delete_config(config_id)
        except KeyError:
            return jsonify({"message": "Alert configuration not found"}), 404
        return jsonify({"message": "Deleted"}), 200

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def _normalize_payload(payload: dict) -> dict:
    normalized = dict(payload)
    for key in ["name", "description", "type_template", "message_template"]:
        value = normalized.get(key)
        if isinstance(value, str):
            value = value.strip()
            if key in {"type_template", "message_template"} and value == "":
                value = None
        normalized[key] = value

    enabled = normalized.get("enabled")
    if isinstance(enabled, str):
        normalized["enabled"] = enabled.lower() not in {"", "false", "0", "no"}

    parameters = normalized.get("parameters")
    if parameters is None:
        normalized["parameters"] = {}
    elif not isinstance(parameters, dict):
        raise ValueError("parameters must be an object if provided")

    return normalized
