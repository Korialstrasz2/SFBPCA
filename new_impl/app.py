from __future__ import annotations

import io
from pathlib import Path
from typing import Dict

from flask import Flask, Response, jsonify, render_template, request, send_file

from .alert_loop import ALERT_LOOP
from .alert_summary import ALERT_SUMMARY
from .csv_import_logic import IMPORT_COORDINATOR


BASE_DIR = Path(__file__).resolve().parent
ENTITY_LABELS = {
    "accounts": "Account",
    "contacts": "Contatti",
    "individuals": "Individual",
    "account_contact_relations": "Relazioni Account-Contatto",
    "contact_point_phones": "Contact Point Phone",
    "contact_point_emails": "Contact Point Email",
}
SUPPORTED_ENTITIES = list(ENTITY_LABELS)


def create_app() -> Flask:
    print("[new_impl] Inizializzazione dell'app Flask alternativa")
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "web" / "templates"),
        static_folder=str(BASE_DIR / "web" / "static"),
    )

    @app.route("/")
    def index() -> str:
        return render_template("index.html", entities=ENTITY_LABELS)

    @app.post("/api/import")
    def import_csv() -> Response:
        print("[new_impl] Richiesta di importazione ricevuta")
        payload: Dict[str, object] = {key: request.files.get(key) for key in SUPPORTED_ENTITIES}
        try:
            summary = IMPORT_COORDINATOR.import_payload(payload)
        except ValueError as error:
            print(f"[new_impl] Errore importazione: {error}")
            return jsonify({"error": str(error)}), 400
        print("[new_impl] Importazione completata", summary)
        return jsonify({"summary": summary})

    @app.post("/api/alerts/run")
    def run_alerts() -> Response:
        print("[new_impl] Avvio del ciclo degli avvisi")
        results = ALERT_LOOP.run()
        print(f"[new_impl] Avvisi generati: {len(results.get('details', []))}")
        return jsonify(results)

    @app.get("/api/alerts/download")
    def download_alerts() -> Response:
        print("[new_impl] Download del riepilogo richiesto")
        csv_bytes = ALERT_SUMMARY.to_csv()
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name="riepilogo_avvisi.csv",
        )

    return app
