from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from airflow_app.configuration import AirflowAppConfig
from airflow_app.services.alerting import build_and_persist_alerts, load_alert_configuration
from airflow_app.services.backup import create_backup_archive
from airflow_app.services.context import AirflowRuntimeContext
from airflow_app.services.data_changes import build_reassignment_catalog
from airflow_app.services.data_management import initialize_environment, load_salesforce_dataset
from airflow_app.services.reporting import generate_operational_report

CONFIG = AirflowAppConfig.load()
RUNTIME_CONTEXT = AirflowRuntimeContext(CONFIG)
DEFAULT_ARGS = {
    "owner": "relationship-engineering",
    "depends_on_past": False,
}


def _initialize_environment(**_: dict):
    return initialize_environment(RUNTIME_CONTEXT)


def _load_dataset(**_: dict):
    return load_salesforce_dataset(RUNTIME_CONTEXT)


def _load_alert_configuration(**_: dict):
    return load_alert_configuration(RUNTIME_CONTEXT)


def _build_alerts(**_: dict):
    return build_and_persist_alerts(RUNTIME_CONTEXT)


def _generate_report(**_: dict):
    return generate_operational_report(RUNTIME_CONTEXT)


def _create_backup(**_: dict):
    return create_backup_archive(RUNTIME_CONTEXT)


def _plan_data_changes(**context: dict):
    role = context.get("params", {}).get("role")
    return build_reassignment_catalog(RUNTIME_CONTEXT, role=role)


def build_dag(config: AirflowAppConfig | None = None) -> DAG:
    global RUNTIME_CONTEXT
    runtime_config = config or CONFIG
    if runtime_config is not CONFIG:
        RUNTIME_CONTEXT = AirflowRuntimeContext(runtime_config)

    with DAG(
        dag_id=runtime_config.dag_id,
        start_date=datetime(2023, 1, 1),
        catchup=False,
        schedule_interval=runtime_config.schedule_interval,
        default_args=DEFAULT_ARGS,
        tags=["salesforce", "data-quality", "airflow-app"],
        description=(
            "Salesforce Relationship Inspector orchestrated via Airflow. "
            "Imports CSV extracts, refreshes alerts, generates reports, and prepares data-change insights."
        ),
    ) as dag:
        initialize_task = PythonOperator(
            task_id="initialize_environment",
            python_callable=_initialize_environment,
        )

        load_dataset_task = PythonOperator(
            task_id="load_salesforce_dataset",
            python_callable=_load_dataset,
        )

        alert_config_task = PythonOperator(
            task_id="load_alert_configuration",
            python_callable=_load_alert_configuration,
        )

        build_alerts_task = PythonOperator(
            task_id="build_alerts",
            python_callable=_build_alerts,
        )

        report_task = PythonOperator(
            task_id="generate_operational_report",
            python_callable=_generate_report,
        )

        backup_task = PythonOperator(
            task_id="create_backup_archive",
            python_callable=_create_backup,
        )

        data_changes_task = PythonOperator(
            task_id="plan_data_changes_placeholder",
            python_callable=_plan_data_changes,
            params={"role": "Primary"},
        )

        initialize_task >> load_dataset_task >> alert_config_task >> build_alerts_task
        build_alerts_task >> report_task >> backup_task >> data_changes_task

    return dag


dag = build_dag(CONFIG)
globals()[CONFIG.dag_id] = dag
