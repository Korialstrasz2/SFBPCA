"""Compatibilità: entry point che rimanda a modern_app.main."""

from modern_app.main import app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
