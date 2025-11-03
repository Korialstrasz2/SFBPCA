from __future__ import annotations

import json
import textwrap
from typing import Callable, Dict, List, Tuple

from airflow_app.configuration import AirflowAppConfig
from airflow_app.dags.salesforce_relationships_dag import build_dag
from airflow_app.services.alerting import build_and_persist_alerts, load_alert_configuration
from airflow_app.services.backup import create_backup_archive
from airflow_app.services.context import AirflowRuntimeContext
from airflow_app.services.data_changes import PLACEHOLDER_MESSAGE, build_reassignment_catalog
from airflow_app.services.data_management import initialize_environment, load_salesforce_dataset
from airflow_app.services.reporting import generate_operational_report


class AirflowAppRunner:
    """Interactive helper that mimics a lightweight Airflow deployment."""

    def __init__(self, config: AirflowAppConfig | None = None) -> None:
        self.config = config or AirflowAppConfig.load()
        self.context = AirflowRuntimeContext(self.config)
        self.dag = build_dag(self.config)

    # ------------------------------------------------------------------
    # Runtime helpers
    # ------------------------------------------------------------------
    def run_pipeline(self) -> Dict[str, object]:
        steps: List[Tuple[str, Callable[..., Dict[str, object]]]] = [
            ("initialize_environment", lambda: initialize_environment(self.context)),
            ("load_salesforce_dataset", lambda: load_salesforce_dataset(self.context)),
            ("load_alert_configuration", lambda: load_alert_configuration(self.context)),
            ("build_alerts", lambda: build_and_persist_alerts(self.context)),
            ("generate_operational_report", lambda: generate_operational_report(self.context)),
            ("create_backup_archive", lambda: create_backup_archive(self.context)),
            (
                "plan_data_changes_placeholder",
                lambda: build_reassignment_catalog(self.context, role="Primary"),
            ),
        ]

        results: Dict[str, object] = {}
        for task_id, callable_ in steps:
            results[task_id] = callable_()
        return results

    def show_alerts(self) -> Dict[str, object]:
        alerts_path = self.config.alerts_output_path
        if alerts_path.exists():
            return json.loads(alerts_path.read_text(encoding="utf-8"))
        return {"alerts": [], "message": "No alerts generated yet"}

    def show_report(self) -> Dict[str, object]:
        report_path = self.config.reports_index_path
        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
        return {"report": None, "message": "No report generated yet"}

    def show_data_change_placeholder(self) -> Dict[str, object]:
        artifact_path = self.config.base_dir / "artifacts" / "pending_data_changes.json"
        if artifact_path.exists():
            return json.loads(artifact_path.read_text(encoding="utf-8"))
        return {"status": PLACEHOLDER_MESSAGE, "contacts": []}

    def describe_configuration(self) -> Dict[str, object]:
        return self.config.to_dict()

    # ------------------------------------------------------------------
    # Interactive prompt
    # ------------------------------------------------------------------
    def run_interactive(self) -> None:
        banner = textwrap.dedent(
            f"""
            Salesforce Relationship Inspector (Airflow Edition)
            ---------------------------------------------------
            Airflow home: {self.config.base_dir}
            DAG id: {self.config.dag_id}
            Schedule: {self.config.schedule_interval}
            """
        )
        print(banner)

        menu = textwrap.dedent(
            """
            Select an action:
              1. Run full Airflow pipeline now
              2. Show latest alerts
              3. Show latest report
              4. Show data-change placeholder (STILL TO BE IMPLEMENTED)
              5. Show configuration
              6. Exit
            """
        )

        while True:
            print(menu)
            choice = input("Enter choice: ").strip()
            if choice == "1":
                results = self.run_pipeline()
                print(json.dumps(results, indent=2))
            elif choice == "2":
                print(json.dumps(self.show_alerts(), indent=2))
            elif choice == "3":
                print(json.dumps(self.show_report(), indent=2))
            elif choice == "4":
                print(json.dumps(self.show_data_change_placeholder(), indent=2))
            elif choice == "5":
                print(json.dumps(self.describe_configuration(), indent=2))
            elif choice == "6":
                print("Exiting Airflow runner.")
                break
            else:
                print("Invalid choice. Please select a valid option.")


__all__ = ["AirflowAppRunner"]
