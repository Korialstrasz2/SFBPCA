"""Factory Flask per la nuova implementazione."""

from __future__ import annotations

import io
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

from .alert_loop import ALERT_LOOP
from .alert_summary import ALERT_SUMMARY
from .csv_import import IMPORT_COORDINATOR
from .run_log import RUN_LOG


SUPPORTED_ENTITIES = [
    "accounts",
    "contacts",
    "individuals",
    "account_contact_relations",
    "contact_point_phones",
    "contact_point_emails",
]

ENTITY_LABELS = {
    "accounts": "Account",
    "contacts": "Contatti",
    "individuals": "Individual",
    "account_contact_relations": "Relazioni Account-Contact",
    "contact_point_phones": "Contact Point Phone",
    "contact_point_emails": "Contact Point Email",
}

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_FOLDER = str(BASE_DIR / "ui" / "templates")
STATIC_FOLDER = str(BASE_DIR / "ui" / "static")


def create_app() -> Flask:
    app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)

    @app.route("/")
    def index() -> str:
        return render_template("index.html", entities=SUPPORTED_ENTITIES, entity_labels=ENTITY_LABELS)

    @app.route("/guide")
    def guide() -> str:
        return render_template("guide.html", entities=SUPPORTED_ENTITIES, entity_labels=ENTITY_LABELS)

    @app.post("/api/import")
    def import_csv() -> Response:
        RUN_LOG.reset("import")
        RUN_LOG.info("Richiesta di caricamento ricevuta.")
        payload = {key: request.files.get(key) for key in SUPPORTED_ENTITIES}
        try:
            summary = IMPORT_COORDINATOR.import_payload(payload)
        except ValueError as error:
            RUN_LOG.error("Errore durante il caricamento", error=str(error))
            return jsonify({"error": str(error)}), 400
        RUN_LOG.info("Caricamento completato", summary=summary)
        return jsonify({"summary": summary})

    @app.post("/api/alerts/run")
    def run_alerts() -> Response:
        RUN_LOG.reset("alerts")
        RUN_LOG.info("Avvio del ciclo di controllo allerte.")
        results = ALERT_LOOP.run()
        RUN_LOG.info("Ciclo allerte completato.")
        return jsonify(results)

    @app.get("/api/alerts/download")
    def download_alerts() -> Response:
        excel_bytes = ALERT_SUMMARY.to_excel()
        return send_file(
            io.BytesIO(excel_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="riepilogo_allerte.xlsx",
        )

    @app.get("/api/logs")
    def get_logs() -> Response:
        return jsonify({"entries": RUN_LOG.entries()})

    @app.get("/api/logs/download")
    def download_logs() -> Response:
        log_bytes = RUN_LOG.to_text().encode("utf-8")
        return send_file(
            io.BytesIO(log_bytes),
            mimetype="text/plain",
            as_attachment=True,
            download_name="registro_esecuzione.txt",
        )

    return app
