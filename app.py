from __future__ import annotations

import os
from typing import Callable

from app import create_app
from airflow_app.cli import main as airflow_cli_main
from airflow_app.runtime.runner import AirflowAppRunner


def run_legacy() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


def run_airflow_interactive() -> None:
    runner = AirflowAppRunner()
    runner.run_interactive()


def select_mode() -> Callable[[], None]:
    env_mode = os.environ.get("SRI_APP_MODE", "").strip().lower()
    if env_mode in {"legacy", "flask"}:
        return run_legacy
    if env_mode in {"airflow", "dag"}:
        return run_airflow_interactive
    if env_mode == "airflow-cli":
        return lambda: airflow_cli_main([])

    prompt = (
        "Select application mode:\n"
        "  1. Legacy Flask tool\n"
        "  2. Airflow interactive console\n"
        "  3. Airflow command-line runner (single execution)\n"
    )
    print(prompt)
    choice = input("Enter choice: ").strip()
    if choice == "1":
        return run_legacy
    if choice == "2":
        return run_airflow_interactive
    if choice == "3":
        return lambda: airflow_cli_main(["--run-once"])

    print("Invalid choice. Defaulting to legacy mode.")
    return run_legacy


if __name__ == "__main__":
    mode = select_mode()
    mode()
