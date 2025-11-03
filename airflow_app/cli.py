from __future__ import annotations

import argparse
import json

from airflow_app.runtime.runner import AirflowAppRunner


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Interact with the Airflow-based app")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run the entire pipeline once and print the results",
    )
    parser.add_argument(
        "--show-alerts",
        action="store_true",
        help="Print the latest alert payload",
    )
    parser.add_argument(
        "--show-report",
        action="store_true",
        help="Print the latest generated report",
    )
    parser.add_argument(
        "--show-data-changes",
        action="store_true",
        help="Print the data-change placeholder artifact",
    )

    args = parser.parse_args(argv)
    runner = AirflowAppRunner()

    if args.run_once:
        print(json.dumps(runner.run_pipeline(), indent=2))
        return
    if args.show_alerts:
        print(json.dumps(runner.show_alerts(), indent=2))
        return
    if args.show_report:
        print(json.dumps(runner.show_report(), indent=2))
        return
    if args.show_data_changes:
        print(json.dumps(runner.show_data_change_placeholder(), indent=2))
        return

    runner.run_interactive()


if __name__ == "__main__":
    main()
