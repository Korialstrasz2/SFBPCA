"""Entry point allowing the operator to choose between legacy Flask and Airflow modes."""

from __future__ import annotations

import argparse
import sys
from typing import Literal

from app import create_app
from airflow_app import launch_airflow_app

# Expose a Flask application instance for tooling that relies on the module-level ``app`` symbol
# (for example ``flask --app app:flask_app run``).
flask_app = create_app()


def run_legacy_server() -> None:
    flask_app.run(host="0.0.0.0", port=5000, debug=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SFBPCA tooling entry point")
    parser.add_argument(
        "--mode",
        choices=["legacy", "airflow"],
        help="Select which application to start. If omitted you will be prompted.",
    )
    return parser.parse_args(argv)


def prompt_for_mode() -> Literal["legacy", "airflow"]:
    while True:
        choice = input("Select startup mode ([L]egacy/[A]irflow): ").strip().lower()
        if choice in {"l", "legacy"}:
            return "legacy"
        if choice in {"a", "airflow"}:
            return "airflow"
        print("Invalid choice, please enter 'L' or 'A'.")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    mode: Literal["legacy", "airflow"]
    if args.mode:
        mode = args.mode  # type: ignore[assignment]
    else:
        mode = prompt_for_mode()

    if mode == "legacy":
        print("Starting legacy Flask tooling on http://localhost:5000 ...")
        run_legacy_server()
    else:
        print("Launching Airflow orchestrator...")
        launch_airflow_app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - user initiated stop
        sys.exit(130)
