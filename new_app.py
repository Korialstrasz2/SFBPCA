"""Flask application factory for the alternate workspace."""

from __future__ import annotations

import io

from flask import Flask, Response, jsonify, render_template, request, send_file

from new_alert_loop import ALERT_LOOP
from new_alert_summary import ALERT_SUMMARY
from new_csv_import_logic import IMPORT_COORDINATOR


SUPPORTED_ENTITIES = [
    "accounts",
    "contacts",
    "individuals",
    "account_contact_relations",
    "contact_point_phones",
    "contact_point_emails",
]


def create_app() -> Flask:
    app = Flask(__name__, template_folder="new_app/templates", static_folder="new_app/static")

    @app.route("/")
    def index() -> str:
        return render_template("index.html", entities=SUPPORTED_ENTITIES)

    @app.post("/api/import")
    def import_csv() -> Response:
        payload = {key: request.files.get(key) for key in SUPPORTED_ENTITIES}
        try:
            summary = IMPORT_COORDINATOR.import_payload(payload)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"summary": summary})

    @app.post("/api/alerts/run")
    def run_alerts() -> Response:
        results = ALERT_LOOP.run()
        return jsonify(results)

    @app.get("/api/alerts/download")
    def download_alerts() -> Response:
        csv_bytes = ALERT_SUMMARY.to_csv()
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name="alert_summary.csv",
        )

    return app


