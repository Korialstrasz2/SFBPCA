"""Punto di ingresso per l'applicazione alternativa."""

from __future__ import annotations

from .app_factory import create_app

app = create_app()

if __name__ == "__main__":
    print("[Server] Avvio dell'applicazione alternativa sulla porta 5001...")
    app.run(host="0.0.0.0", port=5001, debug=True)
