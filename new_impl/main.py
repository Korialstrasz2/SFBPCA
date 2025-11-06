"""Entry point for the alternate Flask application."""

from __future__ import annotations

from new_impl import create_app

app = create_app()


if __name__ == "__main__":
    print("[new_impl] Avvio del server di sviluppo sulla porta 5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
