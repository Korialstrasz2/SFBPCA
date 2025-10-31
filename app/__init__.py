from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from flask import Flask, abort, jsonify, render_template, request

from app.data.data_store import DATA_STORE
from app.services.alert_engine import AlertEngine
from app.services.alert_definition_store import AlertDefinitionStore
from app.services.importer import CSVImporter


def create_app() -> Flask:
    app = Flask(__name__)

    importer = CSVImporter(DATA_STORE)
    definition_store = AlertDefinitionStore(Path(app.root_path) / "data" / "alert_definitions.json")
    alert_engine = AlertEngine(DATA_STORE, definition_store)

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
        definitions = definition_store.list_definitions()
        blueprints = alert_engine.definition_blueprints()
        return jsonify({
            "definitions": definitions,
            "blueprints": blueprints,
        })

    @app.post("/alert-definitions")
    def create_alert_definition():
        payload = request.get_json(silent=True)
        if payload is None:
            abort(400, description="Request payload must be valid JSON")
        try:
            definition = _prepare_definition_payload(payload, blueprints=alert_engine.definition_blueprints())
        except ValueError as exc:
            abort(400, description=str(exc))
        if definition_store.get_definition(definition["id"]):
            abort(409, description=f"Alert definition '{definition['id']}' already exists")
        stored = definition_store.upsert_definition(definition)
        return jsonify({"definition": stored}), 201

    @app.put("/alert-definitions/<definition_id>")
    def update_alert_definition(definition_id: str):
        payload = request.get_json(silent=True)
        if payload is None:
            abort(400, description="Request payload must be valid JSON")
        if not definition_store.get_definition(definition_id):
            abort(404, description=f"Alert definition '{definition_id}' was not found")
        try:
            definition = _prepare_definition_payload(
                payload,
                definition_id=definition_id,
                blueprints=alert_engine.definition_blueprints(),
            )
        except ValueError as exc:
            abort(400, description=str(exc))
        stored = definition_store.upsert_definition(definition)
        return jsonify({"definition": stored})

    @app.delete("/alert-definitions/<definition_id>")
    def delete_alert_definition(definition_id: str):
        try:
            definition_store.delete_definition(definition_id)
        except KeyError:
            abort(404, description=f"Alert definition '{definition_id}' was not found")
        return jsonify({"status": "deleted"})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def _prepare_definition_payload(
    payload: Dict[str, Any],
    *,
    definition_id: str | None = None,
    blueprints: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")

    identifier = definition_id or str(payload.get("id", "")).strip()
    if not identifier:
        raise ValueError("Alert definition requires an 'id'")

    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Alert definition requires a 'name'")

    description = str(payload.get("description", "")).strip()
    logic_payload = payload.get("logic", {}) or {}
    if not isinstance(logic_payload, dict):
        raise ValueError("'logic' must be an object")

    logic_type = str(logic_payload.get("type", "")).strip()
    if not logic_type:
        raise ValueError("'logic.type' is required")

    raw_parameters = logic_payload.get("parameters", {}) or {}
    if raw_parameters is None:
        raw_parameters = {}
    if not isinstance(raw_parameters, dict):
        raise ValueError("'logic.parameters' must be an object")

    sanitized_parameters = _apply_parameter_defaults(logic_type, raw_parameters, blueprints or {})

    logic_copy: Dict[str, Any] = dict(logic_payload)
    logic_copy["type"] = logic_type
    if sanitized_parameters or "parameters" in logic_payload:
        logic_copy["parameters"] = sanitized_parameters
    else:
        logic_copy.pop("parameters", None)

    enabled_value = payload.get("enabled", True)
    if isinstance(enabled_value, str):
        enabled = enabled_value.strip().lower() not in {"false", "0", "no"}
    else:
        enabled = bool(enabled_value)

    return {
        "id": identifier,
        "name": name,
        "description": description,
        "enabled": enabled,
        "logic": logic_copy,
    }


def _apply_parameter_defaults(
    logic_type: str,
    parameters: Dict[str, Any],
    blueprints: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    blueprint = (blueprints or {}).get(logic_type, {})
    blueprint_params: Dict[str, Any] = blueprint.get("parameters", {})

    for key, definition in blueprint_params.items():
        default_value = definition.get("default")
        if key in parameters and parameters[key] not in (None, ""):
            sanitized[key] = parameters[key]
        elif default_value is not None:
            sanitized[key] = default_value

    for key, value in parameters.items():
        if key not in sanitized:
            sanitized[key] = value

    return sanitized
