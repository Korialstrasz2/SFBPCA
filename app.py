from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable

from app import create_app

if TYPE_CHECKING:  # pragma: no cover - imports only needed for type checking
    from airflow_app.cli import main as AirflowCliMain
    from airflow_app.runtime.runner import AirflowAppRunner


def run_legacy() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)


def run_airflow_interactive() -> None:
    from airflow_app.runtime.runner import AirflowAppRunner

    runner: AirflowAppRunner = AirflowAppRunner()
    runner.run_interactive()


def run_airflow_cli(args: list[str] | None = None) -> None:
    from airflow_app.cli import main as airflow_cli_main

    cli_main: AirflowCliMain = airflow_cli_main
    cli_main(args or [])


def select_mode() -> Callable[[], None]:
    env_mode = os.environ.get("SRI_APP_MODE", "").strip().lower()
    if env_mode in {"legacy", "flask"}:
        return run_legacy
    if env_mode in {"airflow", "dag"}:
        return run_airflow_interactive
    if env_mode == "airflow-cli":
        return lambda: run_airflow_cli([])

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
        return lambda: run_airflow_cli(["--run-once"])

    print("Invalid choice. Defaulting to legacy mode.")
    return run_legacy


if __name__ == "__main__":
    mode = select_mode()
    mode()
