"""Primary Airflow DAG for orchestrating the SFBPCA data quality workflows."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.utils.dates import days_ago

from airflow_app.config import AirflowAppConfig, DEFAULT_CONFIG_PATH
from airflow_app.tasks import (
    backup_runtime_artifacts,
    build_account_reports,
    build_data_change_candidates,
    extract_csv_records,
    export_runtime_manifest,
    generate_alerts,
    normalise_records,
)

CONFIG_VARIABLE_KEY = "sfbpca_config_path"


def _config_path() -> Path:
    return Path(
        Variable.get(CONFIG_VARIABLE_KEY, default_var=str(DEFAULT_CONFIG_PATH))
    ).expanduser().resolve()


@dag(
    dag_id="sfbpca_data_quality",
    schedule="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["sfbpca", "data-quality"],
    default_args={"owner": "sfbpca", "retries": 1, "retry_delay": timedelta(minutes=5)},
)
def sfbpca_data_quality_dag():
    @task()
    def load_config() -> dict:
        config = AirflowAppConfig.load(_config_path())
        os.environ.setdefault("AIRFLOW_HOME", str(config.airflow_home))
        return config.as_dict()

    @task()
    def extract(config_dict: dict) -> dict:
        config = AirflowAppConfig.from_dict(config_dict)
        return extract_csv_records(config)

    @task()
    def normalise(records: dict, config_dict: dict) -> str:
        config = AirflowAppConfig.from_dict(config_dict)
        snapshot_path = normalise_records(records, config)
        return str(snapshot_path)

    @task()
    def run_alerts(snapshot_path: str, config_dict: dict) -> str:
        config = AirflowAppConfig.from_dict(config_dict)
        path = generate_alerts(Path(snapshot_path), config)
        return str(path)

    @task()
    def create_reports(snapshot_path: str, config_dict: dict) -> str:
        config = AirflowAppConfig.from_dict(config_dict)
        path = build_account_reports(Path(snapshot_path), config)
        return str(path)

    @task()
    def build_data_changes(snapshot_path: str, config_dict: dict) -> str:
        config = AirflowAppConfig.from_dict(config_dict)
        path = build_data_change_candidates(Path(snapshot_path), config)
        return str(path)

    @task()
    def backup(snapshot_path: str, alert_path: str, report_path: str, data_change_path: str, config_dict: dict) -> str:
        config = AirflowAppConfig.from_dict(config_dict)
        backup_path = backup_runtime_artifacts(
            Path(snapshot_path),
            config,
            [Path(alert_path), Path(report_path), Path(data_change_path)],
        )
        return str(backup_path)

    @task()
    def write_manifest(snapshot_path: str, artifacts: list[str], config_dict: dict) -> str:
        config = AirflowAppConfig.from_dict(config_dict)
        manifest_path = export_runtime_manifest(
            Path(snapshot_path), [Path(item) for item in artifacts], config
        )
        return str(manifest_path)

    config_dict = load_config()
    records = extract(config_dict)
    snapshot_path = normalise(records, config_dict)
    alert_path = run_alerts(snapshot_path, config_dict)
    report_path = create_reports(snapshot_path, config_dict)
    data_change_path = build_data_changes(snapshot_path, config_dict)
    backup_path = backup(snapshot_path, alert_path, report_path, data_change_path, config_dict)
    manifest_path = write_manifest(snapshot_path, [alert_path, report_path, data_change_path, backup_path], config_dict)

    # Provide nice task grouping (Airflow 2.6 has TaskGroup?). we just reference outputs.
    return {
        "config": config_dict,
        "snapshot": snapshot_path,
        "alerts": alert_path,
        "report": report_path,
        "data_changes": data_change_path,
        "backup": backup_path,
        "manifest": manifest_path,
    }


globals()["sfbpca_data_quality"] = sfbpca_data_quality_dag()
