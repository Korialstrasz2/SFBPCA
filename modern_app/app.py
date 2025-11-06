from __future__ import annotations

import io
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

from .alert_loop import ALERT_LOOP
from .alert_summary import ALERT_SUMMARY
from .importer import IMPORT_COORDINATOR


PACKAGE_DIR = Path(__file__).resolve().parent
SUPPORTED_ENTITIES = [
    "accounts",
    "contacts",
    "individuals",
    "account_contact_relations",
    "contact_point_phones",
    "contact_point_emails",
]


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(PACKAGE_DIR / "templates"),
        static_folder=str(PACKAGE_DIR / "static"),
    )

    @app.route("/")
    def index() -> str:
        return render_template("index.html", entities=SUPPORTED_ENTITIES)

    @app.post("/api/import")
    def import_csv() -> Response:
        payload = {key: request.files.get(key) for key in SUPPORTED_ENTITIES}
        try:
            summary = IMPORT_COORDINATOR.import_payload(payload)
        except ValueError as error:
            return jsonify({"errore": str(error)}), 400
        return jsonify({"riepilogo": summary})

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
            download_name="riepilogo_avvisi.csv",
        )

    return app
